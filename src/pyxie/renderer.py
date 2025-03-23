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

"""Convert markdown content to HTML using mistletoe's HTML renderer."""

from typing import Dict, List, Optional, Protocol, NamedTuple, Set, Tuple
from functools import lru_cache
import re
from html import escape
import logging

from mistletoe import Document
from mistletoe.html_renderer import HTMLRenderer
from lxml import html

from .types import ContentBlock, ContentItem
from .layouts import get_layout
from .fasthtml import render_fasthtml, RenderResult, EXECUTABLE_MARKER_START, EXECUTABLE_MARKER_END
from .errors import format_error_html
from .utilities import log

logger = logging.getLogger(__name__)
PYXIE_SHOW_ATTR = "data-pyxie-show"  # Visibility control attribute
SELF_CLOSING_TAGS = frozenset({'br', 'img', 'input', 'hr', 'meta', 'link'})

# Pattern to find FastHTML blocks
FASTHTML_PATTERN = re.compile(r'<(fasthtml)([^>]*)>(.*?)</\1>', re.DOTALL)
# Pattern to find marked executable FastHTML blocks
EXECUTABLE_FASTHTML_PATTERN = re.compile(
    f"{EXECUTABLE_MARKER_START}(.*?){EXECUTABLE_MARKER_END}", 
    re.DOTALL
)

class CacheProtocol(Protocol):
    """Protocol for cache objects."""
    def get(self, collection: str, path: str, layout: str) -> Optional[str]: ...
    def store(self, collection: str, path: str, content: str, layout: str) -> None: ...

class PyxieHTMLRenderer(HTMLRenderer):
    """Custom HTML renderer for markdown with enhanced features."""
    DEFAULT_WIDTH, DEFAULT_HEIGHT = 800, 600
    PICSUM_URL = "https://picsum.photos/seed/{seed}/{width}/{height}"
    
    def __init__(self):
        super().__init__(process_html_tokens=True)
        self._used_ids = set()
        self._fasthtml_blocks = {}
        self._in_code_block = False
    
    def _make_id(self, text: str) -> str:
        """Generate a unique ID for a header."""
        base_id = re.sub(r'<[^>]+>|[^\w\s-]', '', text.lower()).strip('-') or 'section'
        base_id = re.sub(r'[-\s]+', '-', base_id)
        
        header_id = base_id
        counter = 1
        while header_id in self._used_ids:
            header_id = f"{base_id}-{counter}"
            counter += 1
        self._used_ids.add(header_id)
        return header_id
    
    def render(self, token): return '' if token is None else super().render(token)
    
    def render_code_block(self, token):
        """Render code blocks and track that we're inside a code block."""
        self._in_code_block = True
        result = super().render_code_block(token)
        self._in_code_block = False
        return result
        
    def render_inline_code(self, token):
        """Render inline code blocks and track that we're inside a code block."""
        self._in_code_block = True
        result = super().render_inline_code(token)
        self._in_code_block = False
        return result
    
    def render_heading(self, token):
        """Render heading with automatic ID generation."""
        inner = self.render_inner(token)
        return f'<h{token.level} id="{self._make_id(inner)}">{inner}</h{token.level}>'
        
    def render_image(self, token) -> str:
        """Custom image rendering with placeholder support."""
        url, title, alt = token.src, getattr(token, 'title', ''), self.render_inner(token)                
        
        # Process placeholder URLs
        if url.startswith('pyxie:'):
            parts = url[6:].split('/')
            width = int(parts[1]) if len(parts) > 1 else None
            height = int(parts[2]) if len(parts) > 2 else None
            url = self._get_placeholder_url(parts[0], width, height)
        elif url == 'placeholder':            
            url = self._get_placeholder_url(self._normalize_seed(alt))
            
        title_attr = f' title="{escape(title)}"' if title else ''
        return f'<img src="{escape(url)}" alt="{escape(alt)}"{title_attr}>'
    
    def _normalize_seed(self, text: str) -> str:
        """Normalize text for use as a placeholder seed."""
        seed = re.sub(r'[^\w\s-]', '', text.lower())
        return re.sub(r'[\s-]+', '-', seed).strip('-_')
    
    def _get_placeholder_url(self, seed: str, width: int = None, height: int = None) -> str:
        """Generate a placeholder image URL."""
        return self.PICSUM_URL.format(
            seed=seed, width=width or self.DEFAULT_WIDTH, height=height or self.DEFAULT_HEIGHT
        )

def extract_fasthtml_blocks(content: str) -> tuple:
    """
    Extract executable FastHTML blocks from content and replace them with placeholders.
    Only extracts blocks that:
    1. Are marked with our special HTML comments, or
    2. Are regular <fasthtml> tags that are NOT inside code blocks
    
    Code blocks are identified by the ```...``` syntax in markdown.
    Regular inline code is identified by backticks.
    
    Returns a tuple of (modified_content, fasthtml_blocks)
    """
    fasthtml_blocks = {}
    
    # Helper function to check if a position is inside a code block
    def is_in_code_block(pos, content):
        # Find all code block delimiters
        code_block_starts = [m.start() for m in re.finditer(r'```', content)]
        if not code_block_starts:
            return False
            
        # Group starts and ends
        pairs = []
        for i in range(0, len(code_block_starts) - 1, 2):
            if i + 1 < len(code_block_starts):
                pairs.append((code_block_starts[i], code_block_starts[i + 1]))
        
        # Check if position is inside any code block
        for start, end in pairs:
            if start < pos < end:
                return True
                
        # Also check inline code (surrounded by single backticks)
        # This regex looks for single backticks that aren't part of triple backticks
        inline_code_pattern = r'(?<!`)`(?!`)(.+?)(?<!`)`(?!`)'
        inline_matches = list(re.finditer(inline_code_pattern, content))
        
        # Check if position is inside any inline code block
        for match in inline_matches:
            if match.start() < pos < match.end():
                return True
                
        return False
    
    # STEP 1: First extract marked executable blocks
    # These are always extracted regardless of context because they are explicitly marked
    result_parts = []
    last_pos = 0
    
    for match in EXECUTABLE_FASTHTML_PATTERN.finditer(content):
        block_content = match.group(1)
        start_pos, end_pos = match.span()
        
        # Add content before this match
        result_parts.append(content[last_pos:start_pos])
        
        # Create a placeholder
        index = len(fasthtml_blocks)
        placeholder = f"<!--FASTHTML-PLACEHOLDER:{index}-->"
        
        # Store with markers to ensure it's recognized as executable
        fasthtml_blocks[placeholder] = EXECUTABLE_MARKER_START + block_content + EXECUTABLE_MARKER_END
        
        # Add the placeholder
        result_parts.append(placeholder)
        
        # Update last position
        last_pos = end_pos
    
    # Join partial result after processing marked blocks
    current_content = "".join(result_parts) + content[last_pos:]
    
    # STEP 2: Then extract regular <fasthtml> tags that are NOT in code blocks
    result_parts = []
    last_pos = 0
    
    for match in FASTHTML_PATTERN.finditer(current_content):
        tag_name, attrs, block_content = match.groups()
        start_pos, end_pos = match.span()
        
        # Skip if this is inside a code block
        if is_in_code_block(start_pos, current_content):
            continue
        
        # Add content before this match
        result_parts.append(current_content[last_pos:start_pos])
        
        # Create a placeholder
        index = len(fasthtml_blocks)
        placeholder = f"<!--FASTHTML-PLACEHOLDER:{index}-->"
        
        # Store with markers to ensure it's recognized as executable
        full_content = EXECUTABLE_MARKER_START + block_content + EXECUTABLE_MARKER_END
        fasthtml_blocks[placeholder] = full_content
        
        # Add the placeholder
        result_parts.append(placeholder)
        
        # Update last position
        last_pos = end_pos
    
    # Add remaining content
    result_parts.append(current_content[last_pos:])
    
    # Join the parts to create modified content
    modified_content = "".join(result_parts)
    
    return modified_content, fasthtml_blocks

def restore_fasthtml_blocks(html_content: str, fasthtml_blocks: dict) -> str:
    """
    Process FastHTML blocks and restore them in the rendered HTML.
    """
    for placeholder, content in fasthtml_blocks.items():
        # Render the FastHTML content directly using render_fasthtml 
        # which properly handles execution of the code
        result = render_fasthtml(content)
        
        # Replace the placeholder with the rendered content
        if result.success:
            rendered = result.content            
        else:
            rendered = f"<div class='error'>{result.error}</div>"
        
        # Replace the placeholder with the rendered content
        html_content = html_content.replace(placeholder, rendered)
    
    return html_content

@lru_cache(maxsize=32)
def render_markdown(content: str) -> str:
    """Render markdown content to HTML with preprocessing."""
    if not content.strip():
        return content
    
    # Normalize indentation in content
    lines = content.strip().splitlines()
    if not lines:
        return ""
    
    min_indent = min((len(line) - len(line.lstrip()) for line in lines if line.strip()), default=0)
    content = "\n".join(line[min_indent:] for line in lines)
    
    # Extract FastHTML blocks before markdown processing
    modified_content, fasthtml_blocks = extract_fasthtml_blocks(content)
    
    # Convert markdown to HTML
    renderer = PyxieHTMLRenderer()
    html_content = renderer.render(Document(modified_content))
    
    # Restore and process FastHTML blocks
    if fasthtml_blocks:
        html_content = restore_fasthtml_blocks(html_content, fasthtml_blocks)
    
    return html_content

def render_block(block: ContentBlock, cache: Optional[CacheProtocol] = None) -> RenderResult:
    """Render a content block to HTML."""
    try:
        # Handle special cases
        if block.name == "script" and not block.content:
            if not block.params:
                return RenderResult(content="")
            attr_str = " ".join(f'{k}="{v}"' for k, v in block.params.items())
            return RenderResult(content=f"<script {attr_str}></script>")
        
        # Handle empty content
        if not block.content.strip():
            return RenderResult(error="Cannot render empty content block")
        
        # Handle blocks differently based on their name
        if block.name == "fasthtml":
            # For explicitly named fasthtml blocks, wrap them in our marker
            # to mark them as executable before processing
            if not block.content.startswith(EXECUTABLE_MARKER_START):
                content = EXECUTABLE_MARKER_START + block.content + EXECUTABLE_MARKER_END
            else:
                content = block.content
            return render_fasthtml(content)
        else:
            # For other blocks, use render_markdown which extracts and processes marked FastHTML
            return RenderResult(content=render_markdown(block.content))
    
    except Exception as e:
        log(logger, "Renderer", "error", "block", f"Failed to render block {block.name}: {e}")
        return RenderResult(error=f"{e.__class__.__name__}: {e}")

def extract_slots_with_content(rendered_blocks: Dict[str, List[str]]) -> Set[str]:
    """Extract slot names that have content."""
    return {name for name, blocks in rendered_blocks.items() 
            if any(block.strip() for block in blocks)}

def check_visibility_condition(slot_names: List[str], filled_slots: Set[str]) -> bool:
    """Determine if an element should be visible based on slot conditions."""
    return any(
        (slot[1:] not in filled_slots) if slot.startswith('!') else (slot in filled_slots)
        for slot in slot_names
    )

def process_conditional_visibility(layout_html: str, filled_slots: Set[str]) -> str:
    """Process data-pyxie-show attributes in HTML."""
    try:
        tree = html.fromstring(layout_html)
        for elem in tree.xpath(f'//*[@{PYXIE_SHOW_ATTR}]'):
            slot_names = [s.strip() for s in elem.get(PYXIE_SHOW_ATTR, '').split(',')]
            if not check_visibility_condition(slot_names, filled_slots):
                current_style = elem.get('style', '')
                display_none = "display: none;"
                elem.set('style', f"{current_style}; {display_none}" if current_style else display_none)
        
        # Use a serialization method that handles self-closing tags correctly
        result = html.tostring(tree, encoding='unicode')
        
        # Ensure proper self-closing tags format for compatibility
        for tag in SELF_CLOSING_TAGS:
            # Replace any self-closing tags that might have been expanded
            result = re.sub(f'<{tag}([^>]*)></[^>]*{tag}>', f'<{tag}\\1></{tag}>', result)
        
        return result
    except Exception as e:
        log(logger, "Renderer", "warning", "visibility", f"Failed to process conditional visibility: {e}")
        return layout_html

def get_layout_name(item: ContentItem) -> str:
    """Get the layout name from an item with fallback to defaults."""
    pyxie_attr = getattr(item, "_pyxie", None)
    default = getattr(pyxie_attr, "default_layout", "default") if pyxie_attr else "default"
    return item.metadata.get("layout", default)

def handle_cache_and_layout(item: ContentItem, cache: Optional[CacheProtocol] = None) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Handle caching and layout resolution in one step."""
    collection = item.collection or "content"
    layout_name = get_layout_name(item)
    
    # Check cache first
    if cache and (cached := cache.get(collection, item.source_path, layout_name)):
        return cached, None, None
    
    # Resolve layout
    if layout := get_layout(layout_name):
        return None, layout.create(item.metadata), None
    
    # Layout not found
    error_msg = f"Layout '{layout_name}' not found"
    log(logger, "Renderer", "warning", "layout", error_msg)
    return None, None, error_msg

def render_content(item: ContentItem, cache: Optional[CacheProtocol] = None) -> str:
    """Render a content item to HTML."""
    try:
        # Get from cache or resolve layout
        cached_html, layout_html, layout_error = handle_cache_and_layout(item, cache)
        if cached_html:
            return cached_html
        if layout_error:
            return format_error_html("rendering", layout_error)
        
        # Render blocks
        rendered_blocks = {}
        for name, blocks in item.blocks.items():
            rendered = [render_block(block, cache) for block in blocks]
            rendered_blocks[name] = [r.content if r.success else format_error_html("block", r.error) for r in rendered]
        
        # Fill slots in layout
        from .slots import fill_slots
        result = fill_slots(layout_html, rendered_blocks)
        if result.error:
            return format_error_html("rendering", result.error)
            
        # Process conditional visibility
        html = process_conditional_visibility(result.element, extract_slots_with_content(rendered_blocks))
        
        # Cache the result
        if cache:
            cache.store(item.collection or "content", item.source_path, html, get_layout_name(item))
            
        return html
    except Exception as e:
        log(logger, "Renderer", "error", "render", f"Failed to render {item.slug}: {e}")
        return format_error_html("rendering", str(e)) 