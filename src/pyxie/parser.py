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
from typing import Dict, Iterator, List, Optional, Tuple, Any, NamedTuple, DefaultDict
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from .constants import DEFAULT_METADATA
from .types import (
    ContentBlock,
    ContentProvider,
    Metadata,
)
from .utilities import (
    merge_metadata,
    normalize_tags,
    parse_date,
    log,
    get_line_number,
    convert_value,
    is_float
)
from .errors import BlockError, FrontmatterError, ParseError
from .params import parse_params
from .fasthtml import is_fasthtml_block

logger = logging.getLogger(__name__)

FRONTMATTER_PATTERN = re.compile(r'^---\s*\n(?P<frontmatter>.*?)\n---\s*\n(?P<content>.*)', re.DOTALL)
EMPTY_FRONTMATTER_PATTERN = re.compile(r'^---\s*\n---\s*\n(?P<content>.*)', re.DOTALL)
XML_TAG_PATTERN = re.compile(r'<(?P<tag>\w+)(?:\s+(?P<params>[^>]*))?>\s*(?P<content>.*?)\s*</(?P=tag)>', re.DOTALL)
UNCLOSED_TAG_PATTERN = re.compile(r'<(?P<tag>\w+)(?:\s+[^>]*)?>', re.DOTALL)
LINE_NUMBER_PATTERN = re.compile(r'line (\d+)', re.IGNORECASE)

CODE_BLOCK_PATTERN = re.compile(r'```(?:\w+)?\s*\n.*?```', re.DOTALL)
INLINE_CODE_PATTERN = re.compile(r'`[^`\n]+`')
HTML_ENTITY_PATTERN = re.compile(r'&[a-zA-Z]+;|&#\d+;|&#x[a-fA-F0-9]+;')
FASTHTML_BLOCK_NAMES = frozenset({'ft', 'fasthtml'})

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
        if name not in self.blocks:
            return None
        blocks = self.blocks[name]
        if index is None:
            return blocks[0] if blocks else None
        return blocks[index] if 0 <= index < len(blocks) else None
    
    def get_blocks(self, name: str) -> List[ContentBlock]:
        """Get all blocks with given name."""
        return self.blocks.get(name, [])

def find_line_for_key(yaml_text: str, key: str) -> int:
    """Find line number where a key appears in YAML text."""
    lines = yaml_text.splitlines()
    for i, line in enumerate(lines, 1):
        if str(key) in line:
            return i
    return 0

def find_tag_line_number(content: str, tag_name: str, start_pos: int = 0) -> int:
    """Find line number where a tag starts."""
    tag_pattern = re.compile(fr'<{tag_name}(?:\s+[^>]*)?>', re.DOTALL)
    if match := tag_pattern.search(content, start_pos):
        return get_line_number(content, match.start())
    return 0

def is_in_code_block(content: str, position: int) -> bool:
    """Check if position is inside a code block or inline code."""
    for match in CODE_BLOCK_PATTERN.finditer(content):
        if match.start() <= position < match.end():
            return True
            
    for match in INLINE_CODE_PATTERN.finditer(content):
        if match.start() <= position < match.end():
            return True
            
    return False

def is_html_entity(content: str, position: int) -> bool:
    """Check if position is part of an HTML entity like &lt; or &#x3C;."""
    for match in HTML_ENTITY_PATTERN.finditer(content):
        if match.start() <= position < match.end():
            return True
    return False

def should_skip_tag_validation(content: str, position: int) -> bool:
    """Determine if tag validation should be skipped at the given position."""
    return is_in_code_block(content, position) or is_html_entity(content, position)

def extract_valid_metadata(frontmatter_text: str) -> Dict[str, Any]:
    """Extract valid key-value pairs from frontmatter text."""
    result = {}
    for line in frontmatter_text.splitlines():
        if not line.strip() or line.strip().startswith('#') or ':' not in line or line.count(':') != 1:
            continue
            
        key, value = line.split(':', 1)
        key = key.strip()        
        if not key or ':' in key:
            continue
            
        result[key] = convert_value(value.strip())
    
    return result

def extract_error_line(e: Exception, content: str, offset: int = 0) -> int:
    """Extract line number from exception message."""
    if "line " not in str(e).lower():
        return 0
        
    if match := LINE_NUMBER_PATTERN.search(str(e)):
        return offset + int(match.group(1)) - 1
    return 0

def log_unclosed_tag(tag: str, line_num: int, parent_name: Optional[str] = None, 
                    parent_line: Optional[int] = None, file_path: Optional[Path] = None) -> None:
    """Log warning about unclosed tag."""
    if parent_name and parent_line:
        message = f"Unclosed inner tag <{tag}> at line {line_num} inside <{parent_name}> block starting at line {parent_line}"
    else:
        message = f"Unclosed block <{tag}> at line {line_num}"
        
    log(logger, "Parser", "warning", "blocks", message, file_path)

def parse_yaml_frontmatter(frontmatter_text: str) -> Dict[str, Any]:
    """Parse YAML frontmatter text into a dictionary."""
    try:
        from yaml import safe_load
        metadata = safe_load(frontmatter_text) or {}
        
        if not isinstance(metadata, dict):
            raise FrontmatterError(f"Frontmatter must be a dictionary, got {type(metadata).__name__}")
            
        return metadata
    except Exception as e:
        raise FrontmatterError(f"Failed to parse YAML: {e}")

def validate_frontmatter_keys(metadata: Dict[str, Any], frontmatter_text: str, line_offset: int) -> Dict[str, Any]:
    """Validate frontmatter keys and remove invalid ones."""
    valid_metadata = {}
    
    for key, value in metadata.items():
        if ':' in str(key) and key.count(':') > 1:
            key_line = find_line_for_key(frontmatter_text, key)
            abs_line = line_offset + key_line - 1
            
            log(logger, "Parser", "warning", "frontmatter", f"Malformed key '{key}' at line {abs_line}, skipping")
            continue
        
        valid_metadata[key] = value
            
    return valid_metadata

def parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    """Parse YAML frontmatter from content."""    
    if not content.strip().startswith('---'):
        return {}, content
            
    if empty_match := EMPTY_FRONTMATTER_PATTERN.match(content):
        return {}, empty_match.group('content')
    
    if not (match := FRONTMATTER_PATTERN.match(content)):
        return {}, content
        
    frontmatter_text = match.group('frontmatter')
    remaining_content = match.group('content')
    line_offset = get_line_number(content, match.start(1))
    
    try:
        metadata = parse_yaml_frontmatter(frontmatter_text)
        
        return validate_frontmatter_keys(metadata, frontmatter_text, line_offset), remaining_content
    except Exception as e:
        malformed_line_num = extract_error_line(e, content, line_offset)
        
        log(logger, "Parser", "warning", "frontmatter", 
             f"Malformed YAML in frontmatter at line {malformed_line_num}: {e}. Attempting to extract valid keys.")
        
        return extract_valid_metadata(frontmatter_text), remaining_content

def check_for_unclosed_tags(content: str, tag_pattern: re.Pattern, start_pos: int = 0, 
                           parent_info: Optional[Tuple[str, int]] = None,
                           file_path: Optional[Path] = None) -> bool:
    """Check for unclosed tags in content and log warnings."""
    is_valid = True
    parent_name, parent_line = parent_info or (None, None)
    
    for match in tag_pattern.finditer(content, start_pos):
        tag = match.group('tag')
        tag_pos = match.start()
        
        if should_skip_tag_validation(content, tag_pos):
            continue
            
        if f"</{tag}>" not in content[tag_pos:]:
            tag_line = get_line_number(content, tag_pos)
            if parent_name and parent_line:
                tag_line = parent_line + tag_line - 1
                
            log_unclosed_tag(tag, tag_line, parent_name, parent_line, file_path)
            is_valid = False
            
    return is_valid

def create_block(name: str, content: str, params_str: str) -> ContentBlock:
    """Create a content block with the appropriate content type."""
    content_type = "ft" if name in FASTHTML_BLOCK_NAMES else "markdown"
    return ContentBlock(
        name=name,
        content=content,
        content_type=content_type,
        params=parse_params(params_str)
    )

def find_content_blocks(content: str, start_pos: int = 0) -> Iterator[Tuple[re.Match, int]]:
    """Find XML-style content blocks and their line numbers."""
    pos = start_pos
    while match := XML_TAG_PATTERN.search(content, pos):
        match_start = match.start()
        
        if should_skip_tag_validation(content, match_start):
            pos = match_start + 1
            continue
            
        line_num = get_line_number(content, match_start)
        yield match, line_num
        pos = match.end()

def process_block_match(match: re.Match, line_num: int, file_path: Optional[Path] = None) -> BlockMatch:
    """Process a matched content block."""
    name = match.group('tag').lower()
    params_str = match.group('params') or ""
    inner_content = match.group('content').strip()
    parent_info = (name, line_num)
    is_valid = check_for_unclosed_tags(inner_content, UNCLOSED_TAG_PATTERN, 0, parent_info, file_path)
    
    block = create_block(name, inner_content, params_str)
    
    return BlockMatch(block, inner_content, is_valid)

def iter_blocks(content: str, file_path: Optional[Path] = None) -> Iterator[ContentBlock]:
    """Iterate through content blocks in text."""
    for match, line_num in find_content_blocks(content):
        block_match = process_block_match(match, line_num, file_path)
        
        if block_match.is_valid:
            yield block_match.block
            
            yield from iter_blocks(block_match.inner_content, file_path)
    
    check_for_unclosed_tags(content, UNCLOSED_TAG_PATTERN, 0, None, file_path)

def parse(content: str, file_path: Optional[Path] = None) -> ParsedContent:
    """Parse markdown content with frontmatter and blocks."""
    try:
        metadata, content_without_frontmatter = parse_frontmatter(content)        
        metadata = merge_metadata(DEFAULT_METADATA, metadata)        
        blocks: DefaultDict[str, List[ContentBlock]] = defaultdict(list)
        for block in iter_blocks(content_without_frontmatter, file_path):
            blocks[block.name].append(block)
            
        return ParsedContent(
            metadata=metadata,
            blocks=dict(blocks), 
            raw_content=content_without_frontmatter
        )
        
    except FrontmatterError as e:
        log(logger, "Parser", "error", "parse", str(e), file_path)
        raise ParseError(str(e)) from e
    except BlockError as e:
        log(logger, "Parser", "error", "parse", str(e), file_path)
        raise ParseError(str(e)) from e
    except Exception as e:
        log(logger, "Parser", "error", "parse", f"Failed to parse content: {e}", file_path)
        raise ParseError(f"Failed to parse content: {e}") from e 