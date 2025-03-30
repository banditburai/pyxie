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

"""
Custom Mistletoe parser definitions.

This module defines custom block tokens that integrate with
Mistletoe's parsing mechanism via the `read()` pattern for blocks.
It also includes frontmatter parsing. Slot identification happens
post-rendering based on convention (non-standard/raw tags).
"""

import re
import yaml
import logging
import html
from typing import Dict, List, Any, Tuple, Optional, Type, ClassVar, Iterator

# Mistletoe imports
from mistletoe import Document
from mistletoe import block_tokenizer  # Access the core tokenizer
from mistletoe import block_token      # Access the default list of block tokens (_token_types)
from mistletoe.block_token import BlockToken
from mistletoe.block_tokenizer import FileWrapper

logger = logging.getLogger(__name__)

# --- Constants ---

RAW_BLOCK_TAGS: set[str] = {'script', 'style', 'pre', 'fasthtml', 'ft'}

VOID_ELEMENTS: set[str] = {
    'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
    'link', 'meta', 'param', 'source', 'track', 'wbr'
}

ATTR_PATTERN = re.compile(r"""
    (?P<key>[^\s"'=<>`/]+)
    (?:
        \s*=\s*
        (?P<value>
            (?:"(?P<double>[^"]*)") | (?:'(?P<single>[^']*)') | (?P<unquoted>[^\s"'=<>`]+)
        )
    )?
""", re.VERBOSE | re.IGNORECASE)

FRONTMATTER_PATTERN = re.compile(
    r'\A\s*---\s*\n(?P<frontmatter>.*?)\n\s*---\s*\n(?P<content>.*)', re.DOTALL
)

# --- Utility Functions ---

def _parse_attrs_str(attrs_str: Optional[str]) -> Dict[str, Any]:
    """Parse attribute string into a dictionary using ATTR_PATTERN."""
    attrs = {}
    if not attrs_str: return attrs
    for match in ATTR_PATTERN.finditer(attrs_str):
        key = match.group('key')
        val_double, val_single, val_unquoted = match.group("double", "single", "unquoted")
        value = True # Default for boolean attribute
        if val_double is not None: value = val_double
        elif val_single is not None: value = val_single
        elif val_unquoted is not None: value = val_unquoted
        elif match.group("value") is not None: value = "" # Value exists but is empty
        attrs[key] = value
    return attrs

# --- Frontmatter Parsing ---

def parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    """Parses YAML frontmatter from the beginning of the content string."""
    if not content.strip().startswith('---'):
        return {}, content
    match = FRONTMATTER_PATTERN.match(content)
    if not match:
        if content.strip() == '---': return {}, '' # Handle '---' only
        logger.debug("No frontmatter block found despite '---' prefix.")
        return {}, content

    frontmatter_text = match.group('frontmatter')
    remaining_content = match.group('content')

    if not frontmatter_text.strip(): return {}, remaining_content # Empty block

    try:
        metadata = yaml.safe_load(frontmatter_text)
        if metadata is None: metadata = {}
        if not isinstance(metadata, dict):
            logger.warning("Frontmatter is not a dictionary (type: %s). Treating as empty.", type(metadata).__name__)
            return {}, content # Return original content on structure error
        return metadata, remaining_content
    except yaml.YAMLError as e:
        logger.warning("Failed to parse YAML frontmatter: %s. Skipping.", e)
        return {}, content # Return original on YAML error
    except Exception as e:
        logger.warning("Unexpected error parsing frontmatter: %s. Skipping.", e)
        return {}, content

# --- Custom Block Token Definitions ---

class BaseCustomMistletoeBlock(BlockToken):
    """Base class for custom block tokens using Mistletoe's read() pattern."""
    parse_inner: ClassVar[bool]
    _OPEN_TAG_PATTERN: ClassVar[re.Pattern] = re.compile(
        r'^\s*<([a-zA-Z][a-zA-Z0-9\-_]*)' # 1: Tag name
        r'(?:\s+([^>]*?))?'              # 2: Attributes (non-greedy)
        r'\s*(/?)>'                      # 3: Optional self-closing slash and closing >
        , re.VERBOSE | re.IGNORECASE
    )
    _CLOSE_TAG_PATTERN: ClassVar[re.Pattern] = re.compile(
        r'^\s*</([a-zA-Z][a-zA-Z0-9\-_]*)>\s*$', re.IGNORECASE
    )

    def __init__(self, result: Dict):
        """Initialize token from data returned by read()."""
        self.tag_name: str = result.get('tag_name', '')
        self.attrs: Dict[str, Any] = result.get('attrs', {})
        self.content: str = result.get('content', '')
        self.is_self_closing: bool = result.get('is_self_closing', False)
        self._children = []        
        
        if getattr(self.__class__, 'parse_inner', False) and self.content:            
            # Split into lines while preserving newlines and pass directly to Mistletoe's tokenizer
            inner_lines = self.content.splitlines(keepends=True)
            self._children = list(block_tokenizer.tokenize(inner_lines, block_token._token_types))
            
            logger.debug("[%s] Initialized: tag=%s, attrs=%s, children=%d",
                         self.__class__.__name__, self.tag_name, self.attrs, len(self._children))

    @property
    def children(self):
        """Provides access to parsed children tokens."""
        return self._children

    @classmethod
    def start(cls, line: str) -> bool:
        """Check if line matches the opening tag pattern AND specific tag rules."""
        match = cls._OPEN_TAG_PATTERN.match(line)
        if not match: return False
        tag_name = match.group(1).lower()        
        return cls._is_tag_match(tag_name)

    @classmethod
    def _is_tag_match(cls, tag_name: str) -> bool:
        raise NotImplementedError("Subclasses must implement _is_tag_match")

    @classmethod
    def read(cls, lines: FileWrapper) -> Optional[Dict]:
        """Reads the custom block, handling nesting, raw content, and same-line close."""
        start_pos = lines.get_pos()
        start_line_num = lines.line_number()
        line = next(lines) # Consume the starting line
        open_match = cls._OPEN_TAG_PATTERN.match(line)
        if not open_match: lines.set_pos(start_pos); return None # Should not happen if start() worked

        tag_name = open_match.group(1).lower()
        attrs_str = open_match.group(2)
        attrs = _parse_attrs_str(attrs_str)
        
        # Handle self-closing tags (either explicit /> or known void elements)
        if bool(open_match.group(3)) or tag_name in VOID_ELEMENTS:
            return {"tag_name": tag_name, "attrs": attrs, "content": "", "is_self_closing": True}

        # --- Check for closing tag on the SAME line ---
        rest_of_line = line[open_match.end(0):]  # Everything after the opening tag
        close_pattern_same_line = re.compile(f'</({tag_name})>\\s*$', re.IGNORECASE)
        close_match_same_line = close_pattern_same_line.search(rest_of_line)

        if close_match_same_line:
             content_str = rest_of_line[:close_match_same_line.start()]
             logger.debug("[%s] Found closing tag on same line for: %s", cls.__name__, tag_name)
             return {"tag_name": tag_name, "attrs": attrs, "content": content_str, "is_self_closing": False}

        # --- Multi-line content ---
        content_lines = [rest_of_line]  # Start with rest of opening line
        nesting_level = 1
        found_closing_tag = False
        while True:
            try:
                next_line = lines.peek()
                if next_line is None: break # EOF

                close_match = cls._CLOSE_TAG_PATTERN.match(next_line)
                if close_match and close_match.group(1).lower() == tag_name:
                    nesting_level -= 1
                    if nesting_level == 0:
                        next(lines)
                        found_closing_tag = True
                        break

                consumed_line = next(lines)
                content_lines.append(consumed_line)

                if cls is NestedContentToken:
                    nested_open_match = cls._OPEN_TAG_PATTERN.match(consumed_line)
                    if nested_open_match and nested_open_match.group(1).lower() == tag_name:
                        # Only increase nesting level if it's not a self-closing tag
                        if not (bool(nested_open_match.group(3)) or tag_name in VOID_ELEMENTS):
                            nesting_level += 1
            except StopIteration: break # EOF

        if not found_closing_tag:
            logger.warning("[%s] Unclosed tag '%s' starting on line %d", cls.__name__, tag_name, start_line_num + 1)
            lines.set_pos(start_pos); return None
        
        content_str = "".join(content_lines)
        return {"tag_name": tag_name, "attrs": attrs, "content": content_str, "is_self_closing": False}

class RawBlockToken(BaseCustomMistletoeBlock):
    """Token for blocks whose content should not be parsed as Markdown."""
    parse_inner: ClassVar[bool] = False
    @classmethod
    def _is_tag_match(cls, tag_name: str) -> bool: return tag_name in RAW_BLOCK_TAGS


class NestedContentToken(BaseCustomMistletoeBlock):
    """Token for blocks whose content should be parsed as Markdown."""
    parse_inner: ClassVar[bool] = True
    @classmethod
    def _is_tag_match(cls, tag_name: str) -> bool:
        """Matches any tag not handled by RawBlockToken."""
        # Only match custom tags (not standard HTML tags)
        is_match = tag_name not in RAW_BLOCK_TAGS and not tag_name in {
            'div', 'span', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li',
            'table', 'tr', 'td', 'th', 'thead', 'tbody', 'tfoot', 'form', 'input',
            'button', 'select', 'option', 'textarea', 'label', 'fieldset', 'legend',
            'dl', 'dt', 'dd', 'nav', 'header', 'footer', 'main', 'article', 'section',
            'aside', 'figure', 'figcaption', 'time', 'mark', 'ruby', 'rt', 'rp',
            'bdi', 'bdo', 'wbr', 'canvas', 'svg', 'math', 'video', 'audio', 'source',
            'track', 'embed', 'object', 'param', 'iframe', 'picture', 'source',
            'img', 'map', 'area', 'table', 'caption', 'colgroup', 'col', 'thead',
            'tbody', 'tfoot', 'tr', 'td', 'th', 'form', 'input', 'button', 'select',
            'option', 'optgroup', 'textarea', 'label', 'fieldset', 'legend', 'datalist',
            'output', 'progress', 'meter', 'details', 'summary', 'dialog', 'menu',
            'menuitem', 'slot', 'template', 'portal'
        }
        return is_match


