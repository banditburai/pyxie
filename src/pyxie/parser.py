# Copyright 2025 firefly
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License. 

"""Parse markdown content with frontmatter and content blocks."""

import logging
import re
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass
from itertools import chain
from pathlib import Path
from typing import Any

from yaml import safe_load

from .constants import DEFAULT_METADATA
from .errors import FrontmatterError, ParseError
from .params import parse_params
from .types import ContentBlock
from .utilities import convert_value, get_line_number, merge_metadata, log

logger = logging.getLogger(__name__)

# Regex patterns for parsing content
XML_TAG_PATTERN = re.compile(r'<([^/!][^>]*?)>')
UNCLOSED_TAG_PATTERN = re.compile(r'<([^/!][^>]*?)(?:>|$)')
CODE_BLOCK_PATTERN = re.compile(r'```.*?\n.*?```', re.DOTALL)
INLINE_CODE_PATTERN = re.compile(r'`[^`]+`')
FRONTMATTER_PATTERN = re.compile(r'^---\s*\n(?P<frontmatter>.*?)\n---\s*\n(?P<content>.*)', re.DOTALL)
EMPTY_FRONTMATTER_PATTERN = re.compile(r'^---\s*\n\s*\n---\s*\n(?P<content>.*)', re.DOTALL)
LIST_ITEM_CODE_PATTERN = re.compile(r'- `<[^>]+>`:', re.MULTILINE)

# Constants
FASTHTML_BLOCK_NAMES = frozenset({'ft', 'fasthtml'})
HTML_TAGS = {
    'div', 'span', 'p', 'a', 'button', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'ul', 'ol', 'li', 'table', 'tr', 'td', 'th', 'form', 'input', 'select', 
    'option', 'label', 'code', 'pre', 'strong', 'em', 'i', 'b'
}
SELF_CLOSING_TAGS = {
    'img', 'br', 'hr', 'input', 'meta', 'link', 'area', 'base', 'col', 'embed', 'param', 'source',
}
IGNORED_TAGS = SELF_CLOSING_TAGS.copy()

@dataclass
class TagContext:
    """Context for tag validation."""
    content: str
    code_blocks: list[tuple[int, int]]
    inline_spans: list[tuple[int, int]]
    list_item_spans: list[tuple[int, int]]
    parent_info: tuple[str | None, int | None] | None = None

@dataclass
class ParsedContent:
    """Result of parsing a markdown file."""
    metadata: dict[str, Any]
    blocks: dict[str, list[ContentBlock]]
    raw_content: str

    def get_block(self, name: str, index: int | None = None) -> ContentBlock | None:
        """Get content block by name and optional index."""
        if name not in self.blocks:
            return None
        blocks = self.blocks[name]
        return blocks[index or 0] if blocks and (index is None or 0 <= index < len(blocks)) else None
    
    def get_blocks(self, name: str) -> list[ContentBlock]:
        """Get all blocks with given name."""
        return self.blocks.get(name, [])

def find_ranges(content: str, pattern: re.Pattern, extra_chars: int = 0) -> list[tuple[int, int]]:
    """Find all matches for a regex pattern and return their ranges."""
    return [(m.start(), m.end() + extra_chars) for m in pattern.finditer(content)]

def is_in_code_block(content: str, position: int, code_blocks: list[tuple[int, int]] | None = None) -> bool:
    """Check if position is inside a code block or inline code."""
    if code_blocks is not None:
        return any(start <= position < end for start, end in code_blocks)
    return any(start <= position < end for start, end in chain(
        find_ranges(content, CODE_BLOCK_PATTERN),
        find_ranges(content, INLINE_CODE_PATTERN)
    ))

def should_ignore_tag(ctx: TagContext, tag_pos: int, tag: str) -> bool:
    """Determine if a tag should be ignored based on context."""
    tag_name = tag.split()[0].lower()
    if is_in_code_block(ctx.content, tag_pos, ctx.code_blocks) or tag_name in IGNORED_TAGS:
        return True
    if tag_name in HTML_TAGS:
        return True
    if any(start <= tag_pos < end for spans in [ctx.inline_spans, ctx.list_item_spans] for start, end in spans):
        return True
    line_with_tag = ctx.content[:tag_pos].split('\n')[-1] + ctx.content[tag_pos:].split('\n')[0]
    if '`<' in line_with_tag or '<`' in line_with_tag or '- <' in line_with_tag:
        return True
    preceding_text = ctx.content[max(0, tag_pos-20):tag_pos]
    return "example" in preceding_text.lower() or "xml" in preceding_text.lower()

def log_tag_warning(tag: str, line_num: int, parent_name: str | None = None, 
                  parent_line: int | None = None, file_path: Path | None = None) -> None:
    """Log warning about unclosed tag."""
    message = f"Unclosed inner tag <{tag}> at line {line_num} inside <{parent_name}> block starting at line {parent_line}" \
        if parent_name and parent_line else f"Unclosed block <{tag}> at line {line_num}"
    log(logger, "Parser", "warning", "blocks", message, file_path)

def find_closing_tag(content: str, tag_name: str, start_pos: int = 0, code_blocks: list[tuple[int, int]] | None = None) -> int:
    """Find closing tag position, skipping tags in code blocks."""
    closing_tag = f"</{tag_name}>"
    pos = start_pos
    
    while pos < len(content):
        pos = content.find(closing_tag, pos)
        if pos == -1:
            return -1
        if not is_in_code_block(content, pos, code_blocks):
            return pos
        pos += 1
    return -1

def check_for_unclosed_tags(ctx: TagContext, start_pos: int = 0, file_path: Path | None = None) -> bool:
    """Check for unclosed tags in content and log warnings. Returns True if unclosed tags found."""
    parent_name, parent_line = ctx.parent_info or (None, None)
    has_unclosed = False
    
    for match in UNCLOSED_TAG_PATTERN.finditer(ctx.content, start_pos):
        tag = match.group(1)
        tag_pos = match.start()
        
        # Extract just the tag name without attributes
        tag_name = tag.split()[0].lower()
        
        if should_ignore_tag(ctx, tag_pos, tag_name) or tag_name in SELF_CLOSING_TAGS:
            continue
        
        if find_closing_tag(ctx.content, tag_name, tag_pos + 1, ctx.code_blocks) == -1:
            log_tag_warning(tag, get_line_number(ctx.content, tag_pos), parent_name, parent_line, file_path)
            has_unclosed = True
    
    return has_unclosed

def find_next_tag(content: str, pos: int, ctx: TagContext) -> tuple[str, int, int] | None:
    """Find the next valid tag in content."""
    while pos < len(content):
        if is_in_code_block(content, pos, ctx.code_blocks):
            for start, end in ctx.code_blocks:
                if start <= pos < end:
                    pos = end
                    break
            continue
            
        opening_match = re.search(r'<(\w+)(?:\s+[^>]*)?>', content[pos:], re.DOTALL)
        if not opening_match:
            break
            
        tag_name = opening_match.group(1)
        tag_start = pos + opening_match.start()
        
        if tag_name.lower() in IGNORED_TAGS or is_in_code_block(content, tag_start, ctx.code_blocks):
            pos = tag_start + 1
            continue
            
        return tag_name, tag_start, pos + opening_match.end()
    
    return None

def create_block(content: str, tag_name: str, tag_start: int, match_end: int, 
                closing_pos: int, params_text: str) -> ContentBlock:
    """Create a ContentBlock from tag information."""
    block_content = content[match_end:closing_pos].strip()
    return ContentBlock(
        name=tag_name,
        content=block_content,
        params=parse_params(params_text) if params_text else {}
    )

def find_content_blocks(content: str, start_pos: int = 0, parent_info: tuple[str | None, int | None] | None = None) -> list[ContentBlock]:
    """Find all content blocks in the given content."""
    blocks = []
    ctx = TagContext(
        content=content,
        code_blocks=find_ranges(content, CODE_BLOCK_PATTERN),
        inline_spans=find_ranges(content, INLINE_CODE_PATTERN),
        list_item_spans=find_ranges(content, LIST_ITEM_CODE_PATTERN, 50),
        parent_info=parent_info
    )
    pos = start_pos
    
    while (tag_info := find_next_tag(content, pos, ctx)) is not None:
        tag_name, tag_start, match_end = tag_info
        closing_pos = find_closing_tag(content, tag_name, match_end, ctx.code_blocks)
        
        if closing_pos == -1:
            log_tag_warning(tag_name, get_line_number(content, tag_start), None, None, None)
            pos = tag_start + 1
            continue
            
        block_content = content[match_end:closing_pos].strip()
        tag_line = get_line_number(content, tag_start)
        
        # Create a new context for checking inner tags
        inner_ctx = TagContext(
            content=block_content,
            code_blocks=ctx.code_blocks,
            inline_spans=ctx.inline_spans,
            list_item_spans=ctx.list_item_spans,
            parent_info=(tag_name, tag_line)
        )
        
        # Check for unclosed tags in the block content
        if check_for_unclosed_tags(inner_ctx):
            pos = tag_start + 1
            continue
        
        params_text = content[tag_start:match_end][1+len(tag_name):-1].strip()
        block = create_block(content, tag_name, tag_start, match_end, closing_pos, params_text)
        
        blocks.append(block)
        blocks.extend(find_content_blocks(block_content, 0, (tag_name, tag_line)))
        
        pos = closing_pos + len(f"</{tag_name}>")
    
    check_for_unclosed_tags(ctx, start_pos)
    return blocks

def extract_frontmatter_values(frontmatter_text: str) -> dict[str, Any]:
    """Extract values from frontmatter text."""
    return {
        parts[0].strip(): convert_value(parts[1].strip())
        for raw_line in frontmatter_text.splitlines()
        if (line := raw_line.strip()) and not line.startswith('#') and ':' in line and line.count(':') <= 1
        and (parts := line.split(':', 1)) and (key := parts[0].strip()) and ':' not in key
    }

def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Parse YAML frontmatter from content."""
    if not content.strip().startswith('---'):
        return {}, content
    if empty_match := EMPTY_FRONTMATTER_PATTERN.match(content):
        return {}, empty_match.group(1)
    if not (match := FRONTMATTER_PATTERN.match(content)):
        return {}, content
        
    frontmatter_text, remaining_content = match.group('frontmatter'), match.group('content')
    line_offset = get_line_number(content, match.start('frontmatter')) + 1  # Add 1 to account for the opening --- line
    
    try:
        metadata = safe_load(frontmatter_text) or {}
        
        if not isinstance(metadata, dict):
            raise FrontmatterError(f"Frontmatter must be a dictionary, got {type(metadata).__name__}")
            
        return {k: v for k, v in metadata.items() if ':' not in str(k) or k.count(':') <= 1}, remaining_content
    except Exception as e:
        log(logger, "Parser", "warning", "frontmatter", 
            f"Malformed YAML in frontmatter at line {line_offset}: {e}. Attempting to extract valid keys.")
        return extract_frontmatter_values(frontmatter_text), remaining_content

def find_tag_line_number(content: str, tag_name: str, start_pos: int = 0) -> int:
    """Find line number for a tag in content. Used for backward compatibility."""
    tag_pattern = re.compile(f"<{tag_name}(?:\\s+[^>]*)?>")
    match = tag_pattern.search(content, start_pos)
    return get_line_number(content, match.start()) if match else 0

def parse(content: str, file_path: Path | None = None) -> ParsedContent:
    """Parse markdown content with frontmatter and blocks."""
    try:
        metadata, content_without_frontmatter = parse_frontmatter(content)        
        metadata = merge_metadata(DEFAULT_METADATA, metadata)
        
        blocks = defaultdict(list)
        for block in find_content_blocks(content_without_frontmatter):
            blocks[block.name].append(block)
        
        check_for_unclosed_tags(TagContext(
            content=content_without_frontmatter,
            code_blocks=find_ranges(content_without_frontmatter, CODE_BLOCK_PATTERN),
            inline_spans=find_ranges(content_without_frontmatter, INLINE_CODE_PATTERN),
            list_item_spans=find_ranges(content_without_frontmatter, LIST_ITEM_CODE_PATTERN, 50)
        ), 0, file_path)
        
        return ParsedContent(metadata=metadata, blocks=dict(blocks), raw_content=content_without_frontmatter)
    except FrontmatterError as e:
        log(logger, "Parser", "error", "parse", str(e), file_path)
        raise ParseError(str(e)) from e
    except Exception as e:
        log(logger, "Parser", "error", "parse", f"Failed to parse content: {e}", file_path)
        raise ParseError(f"Failed to parse content: {e}") from e 