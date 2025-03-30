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

def _dedent_lines(lines: List[str]) -> List[str]:
    """Remove common minimum indentation from non-empty lines."""
    if not lines: return []
    meaningful_lines = [line for line in lines if line.strip()]
    if not meaningful_lines: return ['' for _ in lines] # Preserve line count if all blank
    min_indent = min(len(line) - len(line.lstrip(' ')) for line in meaningful_lines)
    if min_indent == 0: return lines
    return [(line[min_indent:] if line.strip() else '') for line in lines]

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
        #  REMOVE \s*$ - Allow anything after the opening tag's >
        , re.VERBOSE | re.IGNORECASE
    )
    _CLOSE_TAG_PATTERN: ClassVar[re.Pattern] = re.compile(
        r'^\s*</([a-zA-Z][a-zA-Z0-9\-_]*)>\s*$', re.IGNORECASE
    )

    def __init__(self, result: Dict):
        """Initialize token from data returned by read()."""
        self.tag_name: str = result.get('tag_name', '')
        self.attrs: Dict[str, Any] = result.get('attrs', {})
        self.content: str = result.get('content', '') # Raw inner content string
        self.is_self_closing: bool = result.get('is_self_closing', False)
        self._children = []
        self._parent = None

        # Eagerly parse inner content using Document() if needed
        if getattr(self.__class__, 'parse_inner', False) and self.content:
            inner_lines_raw = self.content.splitlines()
            inner_lines_dedented = _dedent_lines(inner_lines_raw)
            # Don't skip empty lines at the start or end, as they might be significant
            inner_lines_final = inner_lines_dedented

            if inner_lines_final:
                inner_doc = Document(inner_lines_final)
                self._children = inner_doc.children
                for child in self._children: child._parent = self

        logger.debug("[%s] Initialized: tag=%s, attrs=%s, children=%d",
                    self.__class__.__name__, self.tag_name, self.attrs, len(self._children))

    @property
    def children(self):
        """Provides access to parsed children tokens."""
        # No lazy parsing needed, parsing happens in __init__
        return self._children

    @classmethod
    def start(cls, line: str) -> bool:
        """Check if line matches the opening tag pattern AND specific tag rules."""
        match = cls._OPEN_TAG_PATTERN.match(line)
        if not match: return False
        tag_name = match.group(1).lower()
        # logger.debug("[%s] Checking start match for tag: %s", cls.__name__, tag_name)
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
        is_xml_self_closing = bool(open_match.group(3))
        attrs = _parse_attrs_str(attrs_str)
        open_tag_end_pos = open_match.end(0) # Position right after the opening tag's >

        # Use line end check as additional self-closing heuristic
        is_self_closing = is_xml_self_closing or line.rstrip().endswith('/>') or tag_name in VOID_ELEMENTS

        if is_self_closing:
            # Ensure no content after self-closing tag on same line? (Optional strictness)
            # if line[open_tag_end_pos:].strip(): logger.warning(...)
            return {"tag_name": tag_name, "attrs": attrs, "content": "", "is_self_closing": True}

        # --- Check for closing tag on the SAME line ---
        rest_of_line = line[open_tag_end_pos:]
        # Need a pattern that finds the *correct* corresponding closing tag,
        # ignoring potential nested ones briefly. This is tricky with regex alone.
        # Let's try finding the LAST closing tag on the line.
        close_pattern_same_line = re.compile(f'</({tag_name})>\\s*$', re.IGNORECASE)
        close_match_same_line = close_pattern_same_line.search(rest_of_line)

        if close_match_same_line:
             # Check if nesting allows this close (level should be 1)
             # Simple check: assume if closing tag is on same line, nesting is 0 or 1.
             # This might be too naive for complex same-line nesting.
             content_str = rest_of_line[:close_match_same_line.start()]
             logger.debug("[%s] Found closing tag on same line for: %s", cls.__name__, tag_name)
             return {"tag_name": tag_name, "attrs": attrs, "content": content_str, "is_self_closing": False}
        else:
            # If no closing tag on same line, add the rest of the line to content
            content_lines_raw = [rest_of_line] # Start content with rest of first line

        # --- Multi-line search (keep previous robust loop) ---
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
                        next(lines); found_closing_tag = True; break

                consumed_line = next(lines)
                content_lines_raw.append(consumed_line)

                if cls is NestedContentToken:
                    nested_open_match = cls._OPEN_TAG_PATTERN.match(consumed_line)
                    if nested_open_match and nested_open_match.group(1).lower() == tag_name:
                        nested_is_self_closing = bool(nested_open_match.group(3)) or consumed_line.rstrip().endswith('/>')
                        if not (tag_name in VOID_ELEMENTS or nested_is_self_closing):
                            nesting_level += 1
            except StopIteration: break # EOF

        if not found_closing_tag:
            logger.warning("[%s] Unclosed tag '%s' starting on line %d", cls.__name__, tag_name, start_line_num + 1)
            lines.set_pos(start_pos); return None

        content_str = "\n".join(content_lines_raw)
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


