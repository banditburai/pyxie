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

import re
import logging
from dataclasses import dataclass
from itertools import chain
from typing import Dict, Iterator, List, Optional, Tuple, Any, NamedTuple
from collections import defaultdict
from pathlib import Path

from .constants import DEFAULT_METADATA
from .types import ContentBlock, ContentProvider, Metadata
from .utilities import merge_metadata, log, get_line_number, convert_value
from .errors import BlockError, FrontmatterError, ParseError
from .params import parse_params

logger = logging.getLogger(__name__)

# Regex patterns
FRONTMATTER_PATTERN = re.compile(r'^---\s*\n(?P<frontmatter>.*?)\n---\s*\n(?P<content>.*)', re.DOTALL)
EMPTY_FRONTMATTER_PATTERN = re.compile(r'^---\s*\n---\s*\n(?P<content>.*)', re.DOTALL)
XML_TAG_PATTERN = re.compile(r'<(?P<tag>\w+)(?:\s+(?P<params>[^>]*))?>\s*(?P<content>(?:(?!</(?P=tag)>).)*?)\s*</(?P=tag)>', re.DOTALL)
UNCLOSED_TAG_PATTERN = re.compile(r'<(?P<tag>\w+)(?:\s+[^>]*)?>', re.DOTALL)
LINE_NUMBER_PATTERN = re.compile(r'line (\d+)', re.IGNORECASE)
CODE_BLOCK_PATTERN = re.compile(r'```(?:[\w+-]*)(?:\s*\n).*?```', re.DOTALL)
INLINE_CODE_PATTERN = re.compile(r'`[^`]+`')
LIST_ITEM_CODE_PATTERN = re.compile(r'- `<[^>]+>`:', re.MULTILINE)
HTML_ENTITY_PATTERN = re.compile(r'&[a-zA-Z]+;|&#\d+;|&#x[a-fA-F0-9]+;')

# Constants
FASTHTML_BLOCK_NAMES = frozenset({'ft', 'fasthtml'})

# Common HTML tags to skip validation for
HTML_TAGS = {
    'div', 'span', 'p', 'a', 'button', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'ul', 'ol', 'li', 'table', 'tr', 'td', 'th', 'form', 'input', 'select', 
    'option', 'label', 'code', 'pre', 'strong', 'em', 'i', 'b'
}

# Self-closing tags that don't need validation
SELF_CLOSING_TAGS = {
    'img', 'br', 'hr', 'input', 'meta', 'link', 'area', 'base', 'col', 'embed', 'param', 'source',
}

# Tags that should be skipped during parsing
IGNORED_TAGS = SELF_CLOSING_TAGS.copy()

class BlockMatch(NamedTuple):
    """Structure representing a processed content block match."""
    block: ContentBlock
    inner_content: str
    is_valid: bool

@dataclass
class ParsedContent(ContentProvider):
    """Result of parsing a markdown file."""
    metadata: Metadata
    blocks: Dict[str, List[ContentBlock]]
    raw_content: str

    def get_block(self, name: str, index: Optional[int] = None) -> Optional[ContentBlock]:
        """Get content block by name and optional index."""
        if name not in self.blocks: return None
        blocks = self.blocks[name]
        return blocks[index or 0] if blocks and (index is None or 0 <= index < len(blocks)) else None
    
    def get_blocks(self, name: str) -> List[ContentBlock]:
        """Get all blocks with given name."""
        return self.blocks.get(name, [])

def find_ranges(content: str, pattern: re.Pattern, extra_chars: int = 0) -> List[Tuple[int, int]]:
    """Find all matches for a regex pattern and return their ranges."""
    return [(m.start(), m.end() + extra_chars) for m in pattern.finditer(content)]

def is_in_code_block(content: str, position: int, code_blocks: Optional[List[Tuple[int, int]]] = None) -> bool:
    """Check if position is inside a code block or inline code."""
    if code_blocks is not None:
        return any(start <= position < end for start, end in code_blocks)
    return any(start <= position < end for start, end in chain(
        find_ranges(content, CODE_BLOCK_PATTERN),
        find_ranges(content, INLINE_CODE_PATTERN)
    ))

def should_ignore_tag(content: str, tag_pos: int, tag: str, 
                     code_blocks: List[Tuple[int, int]],
                     inline_spans: List[Tuple[int, int]], 
                     list_item_spans: List[Tuple[int, int]]) -> bool:
    """Determine if a tag should be ignored based on context."""
    # Skip tags in code blocks or those that don't need closing
    if is_in_code_block(content, tag_pos, code_blocks) or tag.lower() in IGNORED_TAGS:
        return True
    # Skip tags in inline code or list items
    if any(start <= tag_pos < end for spans in [inline_spans, list_item_spans] for start, end in spans):
        return True
    # Check if tag is in documentation context
    line_with_tag = content[:tag_pos].split('\n')[-1] + content[tag_pos:].split('\n')[0]
    if '`<' in line_with_tag or '<`' in line_with_tag or '- <' in line_with_tag:
        return True
    # Skip if in example context
    preceding_text = content[max(0, tag_pos-20):tag_pos]
    return "example" in preceding_text.lower() or "xml" in preceding_text.lower()

def log_tag_warning(tag: str, line_num: int, parent_name: Optional[str] = None, 
                  parent_line: Optional[int] = None, file_path: Optional[Path] = None) -> None:
    """Log warning about unclosed tag."""
    message = f"Unclosed inner tag <{tag}> at line {line_num} inside <{parent_name}> block starting at line {parent_line}" \
        if parent_name and parent_line else f"Unclosed block <{tag}> at line {line_num}"
    log(logger, "Parser", "warning", "blocks", message, file_path)

def find_closing_tag(content: str, tag: str, start_pos: int, code_blocks: List[Tuple[int, int]]) -> int:
    """Find the matching closing tag that's not in a code block."""
    closing_tag = f"</{tag}>"
    pos = start_pos
    while pos < len(content):
        pos = content.find(closing_tag, pos)
        if pos == -1: return -1
        if not is_in_code_block(content, pos, code_blocks): return pos
        pos += 1
    return -1

def check_for_unclosed_tags(content: str, start_pos: int = 0, 
                           parent_info: Optional[Tuple[str, int]] = None,
                           file_path: Optional[Path] = None) -> bool:
    """Check for unclosed tags in content and log warnings. Returns True if unclosed tags found."""
    parent_name, parent_line = parent_info or (None, None)
    code_blocks = find_ranges(content, CODE_BLOCK_PATTERN)
    inline_spans = find_ranges(content, INLINE_CODE_PATTERN)
    list_item_spans = find_ranges(content, LIST_ITEM_CODE_PATTERN, 50)
    has_unclosed = False
    
    for match in UNCLOSED_TAG_PATTERN.finditer(content, start_pos):
        tag = match.group('tag')
        tag_pos = match.start()
        
        # Skip tags that should be ignored based on context
        if should_ignore_tag(content, tag_pos, tag, code_blocks, inline_spans, list_item_spans):
            continue
        
        # Check if tag is closed
        if find_closing_tag(content, tag, tag_pos + 1, code_blocks) == -1:
            log_tag_warning(tag, get_line_number(content, tag_pos), parent_name, parent_line, file_path)
            has_unclosed = True
    
    return has_unclosed

def find_content_blocks(content: str, start_pos: int = 0, parent_info: Optional[Tuple[str, int]] = None) -> List[ContentBlock]:
    """Find all content blocks in the given content."""
    blocks = []
    parent_name, parent_line = parent_info or (None, None)
    code_blocks = find_ranges(content, CODE_BLOCK_PATTERN)
    pos = start_pos
    
    # Find potential tags
    while pos < len(content):
        opening_match = re.search(r'<(\w+)(?:\s+[^>]*)?>', content[pos:], re.DOTALL)
        if not opening_match: break
            
        tag_name = opening_match.group(1)
        tag_start = pos + opening_match.start()
        
        # Skip if tag should be ignored
        if tag_name.lower() in IGNORED_TAGS or is_in_code_block(content, tag_start, code_blocks):
            pos = tag_start + 1
            continue
            
        # Find closing tag
        match_end = pos + opening_match.end()
        closing_pos = find_closing_tag(content, tag_name, match_end, code_blocks)
        
        # Skip if no closing tag found
        if closing_pos == -1:
            pos = tag_start + 1
            continue
            
        # Extract content and check for unclosed inner tags
        block_content = content[match_end:closing_pos].strip()
        tag_line = get_line_number(content, tag_start)
        
        # Check for unclosed inner tags and skip if found
        if check_for_unclosed_tags(block_content, 0, (tag_name, tag_line), None):
            pos = tag_start + 1
            continue
        
        # Create block and add recursive parsing results
        params_text = opening_match.group(0)[1+len(tag_name):-1].strip()
        block = ContentBlock(
            name=tag_name,
            content=block_content,
            params=parse_params(params_text) if params_text else {}
        )
        
        blocks.append(block)
        blocks.extend(find_content_blocks(block_content, 0, (tag_name, tag_line)))
        
        # Move position past this block
        pos = closing_pos + len(f"</{tag_name}>")
    
    # Check for unclosed tags
    check_for_unclosed_tags(content, start_pos, parent_info)
    
    return blocks

def iter_blocks(content: str, file_path: Optional[Path] = None) -> Iterator[ContentBlock]:
    """Iterate through content blocks in text."""
    yield from find_content_blocks(content)

def find_tag_line_number(content: str, tag_name: str, start_pos: int = 0) -> int:
    """Find line number for a tag in content. Used for backward compatibility."""
    tag_pattern = re.compile(f"<{tag_name}(?:\\s+[^>]*)?>");
    match = tag_pattern.search(content, start_pos)
    return get_line_number(content, match.start()) if match else 0

def extract_error_line(e: Exception, content: str, offset: int = 0) -> int:
    """Extract line number from exception message."""
    match = LINE_NUMBER_PATTERN.search(str(e))
    return offset + int(match.group(1)) - 1 if match else 0

def extract_valid_metadata(frontmatter_text: str) -> Dict[str, Any]:
    """Extract valid key-value pairs from frontmatter text."""
    result = {}
    for line in frontmatter_text.splitlines():
        line = line.strip()
        if not line or line.startswith('#') or ':' not in line or line.count(':') > 1: continue
        parts = line.split(':', 1)
        key = parts[0].strip()
        if not key or ':' in key: continue
        result[key] = convert_value(parts[1].strip())
    return result

def parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    """Parse YAML frontmatter from content."""
    if not content.strip().startswith('---'): return {}, content
    if empty_match := EMPTY_FRONTMATTER_PATTERN.match(content): return {}, empty_match.group('content')
    if not (match := FRONTMATTER_PATTERN.match(content)): return {}, content
        
    frontmatter_text, remaining_content = match.group('frontmatter'), match.group('content')
    line_offset = get_line_number(content, match.start(1))
    
    try:
        from yaml import safe_load
        metadata = safe_load(frontmatter_text) or {}
        
        if not isinstance(metadata, dict):
            raise FrontmatterError(f"Frontmatter must be a dictionary, got {type(metadata).__name__}")
            
        # Validate keys and return valid metadata
        return {k: v for k, v in metadata.items() if ':' not in str(k) or k.count(':') <= 1}, remaining_content
    except Exception as e:
        malformed_line_num = extract_error_line(e, content, line_offset)
        log(logger, "Parser", "warning", "frontmatter", 
            f"Malformed YAML in frontmatter at line {malformed_line_num}: {e}. Attempting to extract valid keys.")
        return extract_valid_metadata(frontmatter_text), remaining_content

def parse(content: str, file_path: Optional[Path] = None) -> ParsedContent:
    """Parse markdown content with frontmatter and blocks."""
    try:
        # Extract metadata and content
        metadata, content_without_frontmatter = parse_frontmatter(content)        
        metadata = merge_metadata(DEFAULT_METADATA, metadata)
        
        # Find all content blocks
        blocks = defaultdict(list)
        for block in find_content_blocks(content_without_frontmatter):
            blocks[block.name].append(block)
        
        # Additional check for unclosed tags at the document level
        check_for_unclosed_tags(content_without_frontmatter, 0, None, file_path)
        
        return ParsedContent(metadata=metadata, blocks=dict(blocks), raw_content=content_without_frontmatter)
    except FrontmatterError as e:
        log(logger, "Parser", "error", "parse", str(e), file_path)
        raise ParseError(str(e)) from e
    except BlockError as e:
        log(logger, "Parser", "error", "parse", str(e), file_path)
        raise ParseError(str(e)) from e
    except Exception as e:
        log(logger, "Parser", "error", "parse", f"Failed to parse content: {e}", file_path)
        raise ParseError(f"Failed to parse content: {e}") from e 