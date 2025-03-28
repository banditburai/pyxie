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

"""Markdown parser with support for custom tokens and nested content."""

import re
from typing import Dict, List, Set, Any, Tuple, Union, Iterator, Type, ClassVar, Optional
from mistletoe import Document
from mistletoe.block_token import BlockToken, add_token
import yaml
from dataclasses import dataclass
from .constants import SELF_CLOSING_TAGS

# Reserved tag names that should not be treated as nested content
RESERVED_TAGS = {
    'script', 'fasthtml', 'ft', 'html', 'head', 'body', 'div', 'span', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'ul', 'ol', 'li', 'a', 'img', 'table', 'tr', 'td', 'th', 'thead', 'tbody', 'form', 'input', 'button',
    'select', 'option', 'textarea', 'label', 'meta', 'link', 'style', 'title', 'header', 'footer', 'nav',
    'main', 'article', 'section', 'aside', 'figure', 'figcaption', 'blockquote', 'pre', 'code', 'em', 'strong',
    'i', 'b', 'u', 'mark', 'small', 'sub', 'sup', 'del', 'ins', 'q', 'cite', 'abbr', 'address', 'time',
    'progress', 'meter', 'canvas', 'svg', 'video', 'audio', 'source', 'track', 'embed', 'object', 'param',
    'map', 'area', 'col', 'colgroup', 'caption', 'tfoot', 'fieldset', 'legend', 'datalist', 'optgroup',
    'keygen', 'output', 'details', 'summary', 'menuitem', 'menu', 'dialog', 'slot', 'template', 'portal'
}

# Frontmatter pattern - matches only the frontmatter section
FRONTMATTER_PATTERN = re.compile(r'^\s*---\s*\n(.*?)\n\s*---\s*\n', re.DOTALL)

class BaseToken(BlockToken):
    """Base class for custom tokens with common functionality."""
    
    # Class variables that must be defined by subclasses
    pattern: ClassVar[re.Pattern]
    closing_pattern: ClassVar[re.Pattern]
    parse_inner: ClassVar[bool] = False
    priority: ClassVar[int] = 100
    
    def __init__(self, lines: List[str]):
        self.lines = lines
        self.line_number = 1
        self.content = '\n'.join(lines[1:-1])
        self.attrs = self._parse_attrs(lines[0])
    
    @classmethod
    def start(cls, line: str) -> bool:
        """Check if line starts this type of token."""
        return bool(cls.pattern.match(line))
    
    def _parse_attrs(self, opening_line: str) -> Dict[str, Any]:
        """Parse attributes from opening tag."""
        if not (match := self.pattern.match(opening_line)):
            raise ValueError(f"Invalid tag syntax at line {self.line_number}: {opening_line}")
        return self._parse_attrs_str(match.group(1) or '')
            
    @staticmethod
    def _parse_attrs_str(attrs_str: str) -> Dict[str, Any]:
        """Parse a string of attributes into a dictionary."""
        if not attrs_str:
            return {}
            
        parts = []
        current = []
        in_quotes = False
        quote_char = None
        
        for char in attrs_str:
            if char in '"\'':
                if not in_quotes:
                    in_quotes = True
                    quote_char = char
                elif char == quote_char:
                    in_quotes = False
                    quote_char = None
                current.append(char)
            elif char.isspace() and not in_quotes:
                if current:
                    parts.append(''.join(current))
                    current = []
            else:
                current.append(char)
                
        if current:
            parts.append(''.join(current))
            
        return {
            key.strip(): value.strip('"\'') if '=' in attr else True
            for attr in parts
            for key, value in [attr.split('=', 1)]
        }

class FastHTMLToken(BaseToken):
    """Token for FastHTML blocks."""
    pattern = re.compile(r'^<(?:ft|fasthtml)(?:\s+([^>]*))?>')
    closing_pattern = re.compile(r'^\s*</(?:ft|fasthtml)>\s*$')
    parse_inner = False
    priority = 100

class ScriptToken(BaseToken):
    """Token for script blocks."""
    pattern = re.compile(r'^<script(?:\s+([^>]*))?>')
    closing_pattern = re.compile(r'^\s*</script>\s*$')
    parse_inner = False
    priority = 100

class NestedContentToken(BaseToken):
    """Token for handling nested content blocks with markdown support."""
    
    pattern = re.compile(r'^<([a-zA-Z][a-zA-Z0-9-_]*)(.*?)(/?)>')
    closing_pattern = re.compile(r'^</([a-zA-Z][a-zA-Z0-9-_]*)>')
    
    parse_inner = True
    priority = 100

    @staticmethod
    def start(line: str) -> bool:
        """Check if a line starts a valid nested content block."""
        return bool(NestedContentToken.pattern.match(line))

    def __init__(self, lines: List[str]):
        self.lines = lines
        self.line_number = 1
        
        # Parse opening tag
        if not (match := self.pattern.match(lines[0])):
            raise ValueError(f"Invalid tag syntax at line {self.line_number}: {lines[0]}")
            
        self.tag_name = match.group(1)
        self.attrs = self._parse_attrs_str(match.group(2) or '')
        self.is_self_closing = bool(match.group(3)) or lines[0].rstrip().endswith('/>')
        
        # For self-closing tags, we don't need to parse content
        if self.tag_name in SELF_CLOSING_TAGS or self.is_self_closing:
            self.content = ''
            self.children = []
            return
            
        # For custom content blocks, parse the content as markdown
        content_lines = lines[1:-1] if len(lines) > 2 else []
        if content_lines:
            # Find the minimum indentation level (excluding empty lines)
            min_indent = min(
                len(line) - len(line.lstrip())
                for line in content_lines
                if line.strip()
            )
            # Strip the common indentation from all lines
            content_lines = [line[min_indent:] for line in content_lines]
        
        self.content = '\n'.join(content_lines)
        self.children = self._parse_children(content_lines)

    def _parse_children(self, content_lines: List[str]) -> List[Any]:
        """Parse nested content blocks and markdown content."""
        children = []
        current_block = []
        in_nested_block = False
        nested_level = 0
        current_tag = None
        
        for line in content_lines:
            if not in_nested_block:
                # Check for start of nested block
                if match := self.pattern.match(line.strip()):
                    tag_name = match.group(1)
                    is_self_closing = bool(match.group(3)) or line.rstrip().endswith('/>')
                    
                    # Process any accumulated content as markdown
                    if current_block:
                        children.extend(Document('\n'.join(current_block)).children)
                        current_block = []
                    
                    # For self-closing tags, create a token and continue
                    if tag_name in SELF_CLOSING_TAGS or is_self_closing:
                        children.append(NestedContentToken([line.strip()]))
                        continue
                    
                    # For custom blocks, start collecting nested content
                    in_nested_block = True
                    nested_level = 1
                    current_tag = tag_name
                    current_block = [line]
                    continue
                current_block.append(line)
            else:
                # Check for nested levels
                if match := self.pattern.match(line.strip()):
                    if match.group(1) == current_tag:
                        nested_level += 1
                elif match := self.closing_pattern.match(line.strip()):
                    if match.group(1) == current_tag:
                        nested_level -= 1
                        if nested_level == 0:
                            current_block.append(line)
                            children.append(NestedContentToken(current_block))
                            current_block = []
                            in_nested_block = False
                            continue
                current_block.append(line)
        
        # Process any remaining content as markdown
        if current_block:
            children.extend(Document('\n'.join(current_block)).children)
            
        return children

def parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    """Parse YAML frontmatter from content."""
    if not content.strip().startswith('---'):
        return {}, content
        
    if match := FRONTMATTER_PATTERN.match(content):
        frontmatter_text = match.group(1)
        # Split content at the end of frontmatter section
        _, remaining_content = content.split('\n---\n', 1)
        try:
            metadata = yaml.safe_load(frontmatter_text) or {}
            if not isinstance(metadata, dict):
                raise ValueError(f"Frontmatter must be a dictionary, got {type(metadata).__name__}")
            return metadata, remaining_content
        except Exception as e:
            print(f"Warning: Failed to parse frontmatter: {e}")
            return {}, content
    
    return {}, content

class BlockTokenizer:
    """Handles tokenization of content blocks."""
    
    def __init__(self):
        self.code_fence_pattern = re.compile(r'^```\w*\s*$')
    
    def tokenize(self, content: Union[str, List[str]], 
                token_types: List[Type[BlockToken]]) -> Iterator[BlockToken]:
        """Tokenize content into blocks."""
        lines = content.splitlines() if isinstance(content, str) else content
        buffer = []
        line_iter = iter(lines)
        current_line = 1
        in_code_block = False
        
        try:
            while True:
                line = next(line_iter)
                
                # Handle code blocks
                if self._is_code_block(line):
                    in_code_block = not in_code_block
                    buffer.append(line)
                    current_line += 1
                    continue
                
                if in_code_block:
                    buffer.append(line)
                    current_line += 1
                    continue
                
                # Try to create a token
                if token := self._try_create_token(line, token_types, line_iter, current_line):
                    yield from self._yield_buffer(buffer, current_line)
                    yield token
                    current_line += 1
                    continue
                
                buffer.append(line)
                current_line += 1
                
        except StopIteration:
            pass
        
        yield from self._yield_buffer(buffer, current_line)
    
    def _is_code_block(self, line: str) -> bool:
        """Check if line is a code block marker."""
        return bool(self.code_fence_pattern.match(line))
    
    def _yield_buffer(self, buffer: List[str], current_line: int) -> Iterator[BlockToken]:
        """Yield buffered content as markdown tokens."""
        if buffer:
            doc = Document('\n'.join(buffer))
            for child in doc.children:
                child.line_number = current_line - len(buffer)
                yield child
            buffer.clear()
    
    def _create_token(self, line: str, token_class: Type[BlockToken], 
                 line_iter: Iterator[str], current_line: int) -> BlockToken:
            """Create a token from the given line and token class."""
            content_lines = self._collect_block_lines(line, token_class, line_iter)
            token = token_class(content_lines)
            token.line_number = current_line
            return token
    
    def _try_create_token(self, line: str, token_types: List[Type[BlockToken]], 
                         line_iter: Iterator[str], current_line: int) -> Optional[BlockToken]:
        """Try to create a token from the current line."""                
        # Check special tokens first (FastHTML and Script)
        special_tokens = [FastHTMLToken, ScriptToken]
        for token_class in special_tokens:
            if token_class.start(line):
                return self._create_token(line, token_class, line_iter, current_line)
        
        # Check other token types
        for token_class in token_types:
            if token_class in special_tokens or not token_class.start(line):
                continue
                
            if token_class == NestedContentToken:
                return self._handle_nested_content(line, token_class, line_iter, current_line)
                
            return self._create_token(line, token_class, line_iter, current_line)
        
        return None
    
    def _collect_block_lines(self, line: str, token_class: Type[BlockToken], 
                           line_iter: Iterator[str]) -> List[str]:
        """Collect lines for a block until its closing tag."""
        content_lines = [line]
        for next_line in line_iter:
            content_lines.append(next_line)
            if token_class.closing_pattern.match(next_line):
                break
        return content_lines
    
    def _handle_nested_content(self, line: str, token_class: Type[BlockToken],
                             line_iter: Iterator[str], current_line: int) -> BlockToken:
        """Handle nested content blocks with proper nesting level tracking."""
        match = token_class.pattern.match(line)
        tag_name = match.group(1)
        is_self_closing = bool(match.group(3)) or line.rstrip().endswith('/>')
        
        # Skip special tags
        if tag_name in ('fasthtml', 'ft', 'script'):
            return None
            
        # Handle self-closing tags immediately
        if is_self_closing or tag_name in SELF_CLOSING_TAGS:
            token = token_class([line])
            token.line_number = current_line
            return token
        
        # Collect nested content
        content_lines = [line]
        nested_level = 1
        
        for next_line in line_iter:
            content_lines.append(next_line)
            if match := token_class.pattern.match(next_line.strip()):
                if match.group(1) == tag_name and not (bool(match.group(3)) or next_line.rstrip().endswith('/>')):
                    nested_level += 1
            elif match := token_class.closing_pattern.match(next_line.strip()):
                if match.group(1) == tag_name:
                    nested_level -= 1
                    if nested_level == 0:
                        break
        
        if nested_level > 0:
            raise ValueError(f"Unclosed tag '{tag_name}' at line {current_line}")
            
        return token_class(content_lines)

def custom_tokenize_block(content: Union[str, List[str]], token_types: List[Type[BlockToken]]) -> Iterator[BlockToken]:
    """Custom block tokenizer that prioritizes our content blocks."""
    tokenizer = BlockTokenizer()
    yield from tokenizer.tokenize(content, token_types)

# Register our custom tokens
add_token(FastHTMLToken)
add_token(ScriptToken)
add_token(NestedContentToken)