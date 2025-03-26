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
from typing import Dict, Optional, Tuple, Any
import yaml

from mistletoe.block_token import BlockToken
from .constants import DEFAULT_METADATA, SELF_CLOSING_TAGS
from .utilities import log, get_line_number, convert_value
from .types import ContentBlock

logger = logging.getLogger(__name__)

# Regex patterns
FRONTMATTER_PATTERN = re.compile(r'^\s*---\s*\n(?P<frontmatter>.*?)\n\s*---\s*\n(?P<content>.*)', re.DOTALL)
EMPTY_FRONTMATTER_PATTERN = re.compile(r'^\s*---\s*\n\s*---\s*\n(?P<content>.*)', re.DOTALL)

HTML_TAGS = {
    'div', 'span', 'p', 'a', 'button', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'ul', 'ol', 'li', 'table', 'tr', 'td', 'th', 'form', 'input', 'select', 
    'option', 'label', 'code', 'pre', 'strong', 'em', 'i', 'b', 'title',
    'head', 'body', 'html', 'nav', 'header', 'footer', 'main', 'article', 'section', 'aside',
    'meta', 'style', 'script'
}
IGNORED_TAGS = SELF_CLOSING_TAGS.copy()

class BaseBlockToken(BlockToken):
    """Base class for block tokens with common read logic."""
    parse_inner = False
    priority = 15  # Higher priority than HTML blocks (10)

    @classmethod
    def read(cls, lines):
        """Read a block token."""
        line = lines.peek()
        if not line:
            return None
        match = cls.pattern.match(line)
        if not match:
            content = []
            while line and not re.match(cls.closing_pattern, line.strip()):
                if hasattr(lines, 'readline'):
                    content.append(lines.readline())
                else:
                    content.append(line)
                    next(lines, None)
                line = lines.peek()
            if line:
                if hasattr(lines, 'readline'):
                    content.append(lines.readline())
                else:
                    content.append(line)
                    next(lines, None)
                match = cls.pattern.match('\n'.join(content))
        else:
            if hasattr(lines, 'readline'):
                lines.readline()
            else:
                next(lines, None)
        return match

class FastHTMLToken(BaseBlockToken):
    """Token for FastHTML blocks."""
    pattern = re.compile(r'^\s*<(ft|fasthtml)(?:\s+[^>]*)?>(.*?)</\1>\s*$', re.DOTALL)
    closing_pattern = r'</(ft|fasthtml)>'

    def __init__(self, match):
        self.content = match.group(2).strip() if match else ''
        self.line_number = getattr(match, 'line_number', 1) if match else 1
        self.children = []
        self.original_content = self.content  # Store original content for markdown processing

    @classmethod
    def start(cls, line):
        """Check if a line starts a FastHTML block."""
        return bool(re.match(r'<(ft|fasthtml)(?:\s+[^>]*)?>', line.strip()))

class ScriptToken(BaseBlockToken):
    """Token for script blocks."""
    pattern = re.compile(r'<script(?:\s+[^>]*)?>(.*?)</script>', re.DOTALL)
    closing_pattern = r'</script>'

    def __init__(self, match):
        self.content = match.group(1).strip() if match else ''
        self.line_number = getattr(match, 'line_number', 1) if match else 1
        self.children = []

    @classmethod
    def start(cls, line):
        """Check if a line starts a script block."""
        return bool(re.match(r'<script(?:\s+[^>]*)?>', line.strip()))

class ContentBlockToken(BlockToken):
    """Token for HTML-like content blocks."""    
    pattern = re.compile(r'<(?!(?:ft|fasthtml|script)(?:\s|>))([a-zA-Z][\w-]*)(?:\s+([^>]*))?>(.*?)</\1>', re.DOTALL)
    priority = 15  # Higher priority than HTML blocks (10)
    parse_inner = True 
    
    def __init__(self, match):
        self.tag_name = match.group(1)
        self.attrs = {}
        self.content = match.group(3)
        
        # Parse attributes if present
        if match.group(2):
            attrs_str = match.group(2)
            # Simple attribute parsing - can be enhanced for more complex cases
            for attr in attrs_str.split():
                if '=' in attr:
                    key, value = attr.split('=', 1)
                    # Remove quotes if present
                    value = value.strip('"\'')
                    self.attrs[key] = value
                else:
                    self.attrs[attr] = True
    
    @classmethod
    def start(cls, line):
        """Check if a line starts a content block."""
        return bool(cls.pattern.match(line))
    
    @classmethod
    def read(cls, lines):
        """Read a content block."""
        line = lines[0]
        match = cls.pattern.match(line)
        if not match:
            return None
        
        # Extract tag name and check if it's excluded
        tag_name = match.group(1)
        if tag_name.lower() in ('ft', 'fasthtml', 'script'):
            return None
            
        return cls(match)

def parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    """Parse YAML frontmatter from content."""
    if not content.strip().startswith('---'):
        return {}, content
        
    if empty_match := EMPTY_FRONTMATTER_PATTERN.match(content):
        return {}, empty_match.group('content')
        
    if not (match := FRONTMATTER_PATTERN.match(content)):
        return {}, content
        
    frontmatter_text, remaining_content = match.group('frontmatter'), match.group('content')
    
    try:
        metadata = yaml.safe_load(frontmatter_text) or {}
        if not isinstance(metadata, dict):
            raise ValueError(f"Frontmatter must be a dictionary, got {type(metadata).__name__}")
        return {k: v for k, v in metadata.items() if ':' not in str(k) or k.count(':') <= 1}, remaining_content
    except Exception as e:
        log(logger, "Parser", "warning", "frontmatter", 
            f"Malformed YAML in frontmatter at line {get_line_number(content, match.start(1))}: {e}. Attempting to extract valid keys.")
        return {k: convert_value(v.strip()) 
                for line in frontmatter_text.splitlines() 
                if line.strip() and not line.startswith('#') and ':' in line 
                for k, v in [line.split(':', 1)] 
                if k.strip() and ':' not in k}, remaining_content
