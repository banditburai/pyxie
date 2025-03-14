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
from typing import Dict, Iterator, List, Optional, Tuple, Any, Callable
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

# Regex patterns with named groups for better readability
FRONTMATTER_PATTERN = re.compile(r'^---\s*\n(?P<frontmatter>.*?)\n---\s*\n(?P<content>.*)', re.DOTALL)
EMPTY_FRONTMATTER_PATTERN = re.compile(r'^---\s*\n---\s*\n(?P<content>.*)', re.DOTALL)
XML_TAG_PATTERN = re.compile(r'<(?P<tag>\w+)(?:\s+(?P<params>[^>]*))?>\s*(?P<content>.*?)\s*</(?P=tag)>', re.DOTALL)
UNCLOSED_TAG_PATTERN = re.compile(r'<(?P<tag>\w+)(?:\s+[^>]*)?>', re.DOTALL)
LINE_NUMBER_PATTERN = re.compile(r'line (\d+)', re.IGNORECASE)

# FastHTML block names
FASTHTML_BLOCK_NAMES = {'ft', 'fasthtml'}

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

# Helper functions for parsing
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

def extract_valid_metadata(frontmatter_text: str) -> Dict[str, Any]:
    """Extract valid key-value pairs from frontmatter text."""
    return {
        key.strip(): convert_value(value.strip())
        for line in frontmatter_text.splitlines()
        if line.strip() and not line.startswith('#') and ':' in line and line.count(':') == 1
        for key, value in [line.split(':', 1)]
        if key.strip() and ':' not in key
    }

def extract_error_line(e: Exception, content: str, offset: int = 0) -> int:
    """Extract line number from exception message."""
    if "line " not in str(e).lower():
        return 0
        
    if match := LINE_NUMBER_PATTERN.search(str(e)):
        return offset + int(match.group(1)) - 1
    return 0

def log_unclosed_tag(tag: str, line_num: int, parent_name: Optional[str] = None, parent_line: Optional[int] = None, file_path: Optional[Path] = None) -> None:
    """Log warning about unclosed tag."""
    if parent_name and parent_line:
        log(logger, "Parser", "warning", "blocks", 
            f"Unclosed inner tag <{tag}> at line {line_num} inside <{parent_name}> block starting at line {parent_line}",
            file_path)
    else:
        log(logger, "Parser", "warning", "blocks", f"Unclosed block <{tag}> at line {line_num}", file_path)

def parse_yaml_frontmatter(frontmatter_text: str) -> Dict[str, Any]:
    """Parse YAML frontmatter text into a dictionary."""
    try:
        from yaml import safe_load
        metadata = safe_load(frontmatter_text) or {}
        
        if not isinstance(metadata, dict):
            raise FrontmatterError(f"Frontmatter must be a dictionary, got {type(metadata).__name__}")
            
        return metadata
    except Exception as e:
        # Re-raise with frontmatter-specific error
        raise FrontmatterError(f"Failed to parse YAML: {e}")

def validate_frontmatter_keys(metadata: Dict[str, Any], frontmatter_text: str, line_offset: int) -> Dict[str, Any]:
    """Validate frontmatter keys and remove invalid ones."""
    # Create a new dict to avoid modifying during iteration
    valid_metadata = {}
    
    for key, value in metadata.items():
        if ':' in str(key) and key.count(':') > 1:
            # Find line for error reporting
            key_line = find_line_for_key(frontmatter_text, key)
            abs_line = line_offset + key_line - 1
            
            log(logger, "Parser", "warning", "frontmatter", f"Malformed key '{key}' at line {abs_line}, skipping")
            continue
        
        valid_metadata[key] = value
            
    return valid_metadata

# Frontmatter parsing
def parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    """Parse YAML frontmatter from content."""
    # Handle empty or no frontmatter
    if not content.strip().startswith('---'):
        return {}, content
        
    # Check for empty frontmatter
    if empty_match := EMPTY_FRONTMATTER_PATTERN.match(content):
        return {}, empty_match.group('content')
    
    # Match frontmatter pattern
    if not (match := FRONTMATTER_PATTERN.match(content)):
        return {}, content
        
    frontmatter_text = match.group('frontmatter')
    remaining_content = match.group('content')
    line_offset = get_line_number(content, match.start(1))
    
    try:
        # Parse YAML frontmatter
        metadata = parse_yaml_frontmatter(frontmatter_text)
        
        # Validate keys
        return validate_frontmatter_keys(metadata, frontmatter_text, line_offset), remaining_content
    except Exception as e:
        # Extract error line number if available
        malformed_line_num = extract_error_line(e, content, line_offset)
        
        # Log warning and attempt manual extraction
        log(logger, "Parser", "warning", "frontmatter", 
             f"Malformed YAML in frontmatter at line {malformed_line_num}: {e}. Attempting to extract valid keys.")
        
        # Extract valid key-value pairs manually using the helper function
        return extract_valid_metadata(frontmatter_text), remaining_content

# Block parsing
def validate_nested_tags(content: str, parent_line: int, parent_name: str, file_path: Optional[Path] = None) -> bool:
    """Validate that all tags in content are properly closed."""
    for match in UNCLOSED_TAG_PATTERN.finditer(content):
        tag = match.group('tag')
        tag_pos = match.start()
        
        # Check if this tag is closed
        if f"</{tag}>" not in content[tag_pos:]:
            # Calculate line number for the unclosed tag
            tag_line = parent_line + get_line_number(content[:tag_pos], tag_pos) - 1
            log_unclosed_tag(tag, tag_line, parent_name, parent_line, file_path)
            return False
            
    return True

def create_block(name: str, content: str, params_str: str) -> ContentBlock:
    """Create a content block with the appropriate content type."""
    return ContentBlock(
        name=name,
        content=content,
        content_type="ft" if is_fasthtml_block(name) else "markdown",
        params=parse_params(params_str)
    )

def validate_block_content(inner_content: str, name: str, line_num: int, file_path: Optional[Path] = None) -> bool:
    """Validate block content, checking for unclosed inner tags."""
    if '<' not in inner_content or '>' not in inner_content:
        return True
        
    for inner_match in UNCLOSED_TAG_PATTERN.finditer(inner_content):
        tag = inner_match.group('tag')
        tag_pos = inner_match.start()
        
        if f"</{tag}>" not in inner_content[tag_pos:]:
            inner_line = line_num + get_line_number(inner_content[:tag_pos], tag_pos) - 1
            log_unclosed_tag(tag, inner_line, name, line_num, file_path)
            return False
    
    return True

def check_unclosed_blocks(content: str, blocks_content: str, file_path: Optional[Path] = None) -> None:
    """Check for unclosed blocks in content."""
    for match in UNCLOSED_TAG_PATTERN.finditer(blocks_content):
        tag_name = match.group('tag')
        if original_pos := content.find(match.group(0)):
            if original_pos >= 0:
                line_num = get_line_number(content, original_pos)
                log_unclosed_tag(tag_name, line_num, file_path=file_path)

def find_content_blocks(content: str, start_pos: int = 0) -> Iterator[Tuple[re.Match, int]]:
    """Find XML-style content blocks and their line numbers."""
    while match := XML_TAG_PATTERN.search(content, start_pos):
        line_num = get_line_number(content, match.start())
        yield match, line_num
        start_pos = match.end()

def process_block_match(match: re.Match, line_num: int, file_path: Optional[Path] = None) -> Tuple[ContentBlock, str, bool]:
    """Process a matched content block, returning the block, inner content, and validation status."""
    name = match.group('tag').lower()
    params_str = match.group('params') or ""
    inner_content = match.group('content').strip()
    
    # Validate inner content for unclosed tags
    is_valid = validate_block_content(inner_content, name, line_num, file_path)
    
    # Create the block
    block = create_block(name, inner_content, params_str)
    
    return block, inner_content, is_valid

def iter_blocks(content: str, file_path: Optional[Path] = None) -> Iterator[ContentBlock]:
    """Iterate through content blocks in text."""
    # Track content to check for unclosed blocks later
    content_without_matches = content
    
    # Process each block match
    for match, line_num in find_content_blocks(content):
        # Remove this match from the tracking content
        content_without_matches = content_without_matches.replace(match.group(0), "")
        
        # Process the block match
        block, inner_content, is_valid = process_block_match(match, line_num, file_path)
        
        # Yield the current block if valid
        if is_valid:
            yield block
            
            # Process nested blocks recursively
            yield from iter_blocks(inner_content, file_path)
    
    # Check for unclosed blocks
    check_unclosed_blocks(content, content_without_matches, file_path)

def parse(content: str, file_path: Optional[Path] = None) -> ParsedContent:
    """Parse markdown content with frontmatter and blocks."""
    try:
        # Parse frontmatter
        metadata, content_without_frontmatter = parse_frontmatter(content)
        
        # Merge with defaults
        metadata = merge_metadata(DEFAULT_METADATA, metadata)
        
        # Parse blocks from content
        blocks: Dict[str, List[ContentBlock]] = {}
        for block in iter_blocks(content_without_frontmatter, file_path):
            blocks.setdefault(block.name, []).append(block)
            
        return ParsedContent(
            metadata=metadata,
            blocks=blocks,
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