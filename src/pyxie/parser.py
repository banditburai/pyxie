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
from typing import Dict, Iterator, List, Optional, Tuple, Any, Set
from pathlib import Path
import yaml
from .constants import DEFAULT_METADATA
from .types import ContentBlock, ContentProvider, Metadata
from .utilities import log, get_line_number, convert_value
from .params import parse_params

logger = logging.getLogger(__name__)

# Regex patterns
FRONTMATTER_PATTERN = re.compile(r'^---\s*\n(?P<frontmatter>.*?)\n---\s*\n(?P<content>.*)', re.DOTALL)
EMPTY_FRONTMATTER_PATTERN = re.compile(r'^---\s*\n---\s*\n(?P<content>.*)', re.DOTALL)
CODE_BLOCK_PATTERN = re.compile(r'```.*?\n.*?```', re.DOTALL)
UNCLOSED_TAG_PATTERN = re.compile(r'<(?P<tag>[a-zA-Z0-9_-]+)(?P<params>[^>]*)>')
OPEN_TAG_PATTERN = re.compile(r'<(?P<tag_name>[a-zA-Z0-9_-]+)(?P<params>[^>]*)>')
SELF_CLOSING_TAG_PATTERN = re.compile(r'<(?P<tag>[a-zA-Z0-9_-]+)(?P<params>[^>]*)/>')
INLINE_CODE_PATTERN = re.compile(r'`[^`]*`')
HEADER_PATTERN = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
XML_TAG_PATTERN = re.compile(r'<(?P<tag>\w+)(?:\s+(?P<params>[^>]*))?>\s*(?P<content>(?:(?!</(?P=tag)>).)*?)\s*</(?P=tag)>', re.DOTALL)
LINE_NUMBER_PATTERN = re.compile(r'line (\d+)', re.IGNORECASE)
LIST_ITEM_CODE_PATTERN = re.compile(r'- `<[^>]+>`:', re.MULTILINE)
HTML_ENTITY_PATTERN = re.compile(r'&[a-zA-Z]+;|&#\d+;|&#x[a-fA-F0-9]+;')
HTML_CODE_BLOCK_PATTERN = re.compile(r'<pre(?:\s[^>]*)?><code(?:\s[^>]*)?>.*?</code></pre>', re.DOTALL)

# Tag sets
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
class ParsedContent(ContentProvider):
    """Result of parsing a markdown file."""
    metadata: Metadata
    blocks: Dict[str, List[ContentBlock]]
    raw_content: str

    def get_block(self, name: str, index: Optional[int] = None) -> Optional[ContentBlock]:
        """Get content block by name and optional index."""
        blocks = self.blocks.get(name, [])
        return blocks[index or 0] if blocks and (index is None or 0 <= index < len(blocks)) else None
    
    def get_blocks(self, name: str) -> List[ContentBlock]:
        """Get all blocks with given name."""
        return self.blocks.get(name, [])

def find_code_blocks(content: str) -> List[Tuple[int, int]]:
    """Find all code blocks in content and return their start/end positions."""
    # Find all types of code blocks and combine them
    code_blocks = [
        # Fenced code blocks
        *[(m.start(), m.end()) for m in CODE_BLOCK_PATTERN.finditer(content)],
        
        # Inline code blocks
        *[(m.start(), m.end()) for m in INLINE_CODE_PATTERN.finditer(content)],
        
        # List item code blocks with lookahead
        *[(m.start(), min(m.end() + 50, len(content))) for m in LIST_ITEM_CODE_PATTERN.finditer(content)],
        
        # HTML code blocks (<pre><code>...</code></pre>)
        *[(m.start(), m.end()) for m in HTML_CODE_BLOCK_PATTERN.finditer(content)]
    ]
    
    return sorted(code_blocks, key=lambda x: x[0])

def is_in_code_block(position: int, code_blocks: List[Tuple[int, int]]) -> bool:
    """Check if position is within any code block using binary search."""
    # Binary search to find the right code block range
    left, right = 0, len(code_blocks) - 1
    
    while left <= right:
        mid = (left + right) // 2
        start, end = code_blocks[mid]
        
        if start <= position < end:
            return True
        elif position < start:
            right = mid - 1
        else:
            left = mid + 1
            
    # Check immediate neighbors if binary search was inconclusive
    if left > 0 and left < len(code_blocks):
        start, end = code_blocks[left-1]
        if start <= position < end:
            return True
            
    return False

def should_ignore_tag(tag_name: str, tag_pos: int, content: str, code_blocks: List[Tuple[int, int]]) -> bool:
    """Determine if tag should be ignored during content block detection."""
    # Check if tag is in a code block or is a self-closing HTML tag
    if is_in_code_block(tag_pos, code_blocks) or tag_name.lower() in IGNORED_TAGS:
        return True
    
    # Check if it's formatted as a self-closing tag with />
    tag_content = content[tag_pos:tag_pos + 100]  # Look ahead for />
    return "/>" in tag_content[:tag_content.find(">") + 1]

def log_tag_warning(tag: str, line_num: int, parent_name: Optional[str] = None, 
                  parent_line: Optional[int] = None, file_path: Optional[Path] = None) -> None:
    """Log warning about unclosed tag."""
    is_inner = parent_name and parent_line
    message = (f"Unclosed inner tag <{tag}> at line {line_num} inside <{parent_name}> block starting at line {parent_line}"
               if is_inner else f"Unclosed block <{tag}> at line {line_num}")
    log(logger, "Parser", "warning", "blocks", message, file_path)

def find_closing_tag(content: str, tag_name: str, start_pos: int, code_blocks: List[Tuple[int, int]]) -> int:
    """Find the closing tag for the given tag, starting from start_pos."""
    closing_tag = f"</{tag_name}>"
    opening_tag = f"<{tag_name}"
    closing_tag_len = len(closing_tag)
    opening_tag_len = len(opening_tag)
    
    pos = start_pos
    nesting_level = 1
    content_len = len(content)
    
    while pos < content_len and nesting_level > 0:
        # Find next opening and closing tags
        next_opening = content.find(opening_tag, pos)
        next_closing = content.find(closing_tag, pos)
        
        # No closing tag found
        if next_closing == -1:
            return -1
            
        # Skip closing tags in code blocks
        if next_closing != -1 and is_in_code_block(next_closing, code_blocks):
            pos = next_closing + closing_tag_len
            continue
            
        # Found opening tag before closing tag and not in code block
        if next_opening != -1 and next_opening < next_closing and not is_in_code_block(next_opening, code_blocks):
            nesting_level += 1
            pos = next_opening + opening_tag_len
        else:
            # Process closing tag
            nesting_level -= 1
            pos = next_closing + closing_tag_len
            if nesting_level == 0:
                return next_closing
    
    return -1

def _should_skip_inner_tag(inner_tag: str, inner_tag_pos: int, content: str, code_blocks: List[Tuple[int, int]]) -> bool:
    """Determine if an inner tag should be skipped during validation."""
    return (is_in_code_block(inner_tag_pos, code_blocks) or 
            inner_tag.lower() in HTML_TAGS or 
            should_ignore_tag(inner_tag, inner_tag_pos, content, code_blocks))

def _validate_inner_tags(block_content: str, content: str, tag_name: str, start_pos: int, 
                      open_line: int, code_blocks: List[Tuple[int, int]], filename: Optional[str] = None) -> bool:
    """Validate inner tags in a content block to ensure they're properly closed."""
    for inner_match in OPEN_TAG_PATTERN.finditer(block_content):
        inner_tag = inner_match.group('tag_name')
        inner_tag_pos = start_pos + inner_match.start()
        
        # Skip tags that should be ignored
        if _should_skip_inner_tag(inner_tag, inner_tag_pos, content, code_blocks):
            continue
        
        # Check if inner tag has a closing tag
        if find_closing_tag(content, inner_tag, inner_tag_pos + len(inner_tag) + 1, code_blocks) == -1:
            inner_line = get_line_number(content, inner_tag_pos)
            log_tag_warning(inner_tag, inner_line, tag_name, open_line, Path(filename) if filename else None)
            return False
    
    return True

def _create_content_block(tag_name: str, content: str, params_str: str, index: int) -> ContentBlock:
    """Create a ContentBlock instance from tag information."""
    params = parse_params(params_str) if params_str else {}
    return ContentBlock(
        name=tag_name,
        content=content,
        params=params,
        content_type='markdown',
        index=index
    )

def _warn_unclosed_tag(tag_name: str, line_num: int, filename: Optional[str] = None) -> None:
    """Log a warning about an unclosed tag."""
    file_info = f" in file {filename}" if filename else ""
    logger.warning(f"Unclosed block <{tag_name}> at line {line_num}{file_info}")

def _scan_tags(content: str, code_blocks: List[Tuple[int, int]], filename: Optional[str] = None) -> Dict[str, List[Tuple[str, str, int, int, int]]]:
    """
    Scan content for all opening tags and categorize them into valid matches and unclosed tags.
    This is a combined operation to reduce duplicate scanning.
    
    Returns a dictionary with:
    - 'matches': List of (tag_name, params_str, start_pos, closing_pos, open_line) for valid matches
    - 'unclosed': List of (tag_name, line_num) for unclosed tags
    """
    results = {'matches': [], 'unclosed': []}
    
    for open_match in OPEN_TAG_PATTERN.finditer(content):
        tag_name = open_match.group('tag_name')
        params_str = open_match.group('params')
        start_pos = open_match.end()
        open_line = get_line_number(content, open_match.start())
        
        # Skip tags that should be ignored
        if should_ignore_tag(tag_name, open_match.start(), content, code_blocks):
            continue
        
        # Find valid closing tag
        closing_pos = find_closing_tag(content, tag_name, start_pos, code_blocks)
        if closing_pos != -1:
            # Valid tag match found
            results['matches'].append((tag_name, params_str, start_pos, closing_pos, open_line))
        else:
            # Unclosed tag found
            results['unclosed'].append((tag_name, open_line))
    
    return results

def _process_tag_match(content: str, 
                     tag_name: str, 
                     params_str: str, 
                     start_pos: int, 
                     closing_pos: int, 
                     open_line: int,
                     code_blocks: List[Tuple[int, int]], 
                     filename: Optional[str] = None) -> Optional[ContentBlock]:
    """Process a single tag match and create a ContentBlock if valid.
    
    Returns None if the tag has unclosed inner tags.
    """
    # Extract content between tags
    block_content = content[start_pos:closing_pos]
    
    # Skip if inner tags have problems
    if not _validate_inner_tags(block_content, content, tag_name, start_pos, open_line, code_blocks, filename):
        return None
    
    # Check if this tag is inside a code block (either the start or the end)
    is_in_code = (
        is_in_code_block(start_pos, code_blocks) or 
        is_in_code_block(closing_pos, code_blocks) or
        (tag_name.lower() in FASTHTML_BLOCK_NAMES and
         any(is_in_code_block(pos, code_blocks) 
             for pos in range(start_pos, closing_pos, max(1, (closing_pos - start_pos) // 5))))
    )
    
    # Special handling for FastHTML tags
    if tag_name.lower() == 'fasthtml':
        if is_in_code:
            # This is in a code block - keep as plain text (escape it)
            escaped_content = block_content.replace("<", "&lt;").replace(">", "&gt;")
            
            log(logger, "Parser", "info", "blocks", 
                f"Escaping FastHTML content in code block at line {open_line}", 
                Path(filename) if filename else None)
            
            return _create_content_block(
                tag_name, 
                escaped_content, 
                params_str, 
                0  # Index will be set by the caller
            )
        else:
            # NOT in a code block - mark for execution with special wrapper
            # We wrap the content in a special marker that fasthtml.py will recognize
            executable_content = f"__EXECUTABLE_FASTHTML__{block_content}"
            
            log(logger, "Parser", "info", "blocks", 
                f"Marking FastHTML content for execution at line {open_line}", 
                Path(filename) if filename else None)
            
            return _create_content_block(
                tag_name, 
                executable_content, 
                params_str, 
                0  # Index will be set by the caller
            )
    
    # Create content block
    return _create_content_block(
        tag_name, 
        block_content, 
        params_str, 
        0  # Index will be set by the caller
    )

def find_content_blocks(content: str, filename: Optional[str] = None, warn_unclosed: bool = True) -> Dict[str, List[ContentBlock]]:
    """Find all content blocks in the given content string."""
    blocks: Dict[str, List[ContentBlock]] = {}
    code_blocks = find_code_blocks(content)
        
    scan_results = _scan_tags(content, code_blocks, filename)
        
    for tag_name, params_str, start_pos, closing_pos, open_line in scan_results['matches']:
        block = _process_tag_match(
            content, tag_name, params_str, start_pos, closing_pos, 
            open_line, code_blocks, filename
        )
        
        if block: 
            # Set correct index based on existing blocks
            block.index = len(blocks.get(tag_name, []))
            blocks.setdefault(tag_name, []).append(block)
        
    if warn_unclosed:
        for tag_name, line_num in scan_results['unclosed']:
            _warn_unclosed_tag(tag_name, line_num, filename)
    
    return blocks

def iter_blocks(content: str) -> Iterator[ContentBlock]:
    """Iterate through content blocks in the content."""
    yield from chain.from_iterable(find_content_blocks(content).values())

def extract_frontmatter_values(frontmatter_text: str) -> Dict[str, Any]:
    """Extract values from frontmatter text when YAML parsing fails."""
    result = {}
    
    for line in frontmatter_text.splitlines():
        line = line.strip()
        # Skip invalid lines
        if not line or line.startswith('#') or ':' not in line:
            continue
            
        key, value = line.split(':', 1)
        key = key.strip()
        
        # Skip invalid keys
        if not key or ':' in key:
            continue
            
        result[key] = convert_value(value.strip())
        
    return result

def _parse_yaml_frontmatter(frontmatter_text: str) -> Dict[str, Any]:
    """Parse YAML frontmatter and validate/filter results."""
    metadata = yaml.safe_load(frontmatter_text) or {}
    
    # Validate metadata type
    if not isinstance(metadata, dict):
        raise ValueError(f"Frontmatter must be a dictionary, got {type(metadata).__name__}")
    
    # Filter out keys with invalid format
    return {k: v for k, v in metadata.items() 
            if ':' not in str(k) or k.count(':') <= 1}

def parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    """Parse YAML frontmatter from content."""
    # No frontmatter markers
    if not content.strip().startswith('---'):
        return {}, content
        
    # Empty frontmatter
    if empty_match := EMPTY_FRONTMATTER_PATTERN.match(content):
        return {}, empty_match.group('content')
        
    # Check for valid frontmatter pattern
    if not (match := FRONTMATTER_PATTERN.match(content)):
        return {}, content
        
    frontmatter_text, remaining_content = match.group('frontmatter'), match.group('content')
    
    try:
        return _parse_yaml_frontmatter(frontmatter_text), remaining_content
    except Exception as e:
        # Handle malformed YAML
        malformed_line_num = get_line_number(content, match.start(1))
        log(logger, "Parser", "warning", "frontmatter", 
            f"Malformed YAML in frontmatter at line {malformed_line_num}: {e}. Attempting to extract valid keys.")
        return extract_frontmatter_values(frontmatter_text), remaining_content

def parse(content: str, filename: Optional[str] = None) -> ParsedContent:
    """Parse markdown content with frontmatter and content blocks."""
    # Initialize with default metadata and update with parsed frontmatter
    metadata = DEFAULT_METADATA.copy()
    frontmatter, content_without_frontmatter = parse_frontmatter(content)
    metadata.update(frontmatter)
    
    # Find all content blocks
    blocks = find_content_blocks(content_without_frontmatter, filename=filename)
        
    return ParsedContent(
        metadata=metadata,
        blocks=blocks,
        raw_content=content
    )
