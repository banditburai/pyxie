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

import logging
import re
from html import escape
from typing import Dict, List, Optional, Any, Protocol, Union, NamedTuple, Set, Tuple
from functools import lru_cache

from mistletoe import Document
from mistletoe.html_renderer import HTMLRenderer
from lxml import html

from .types import ContentBlock, ContentItem
from .layouts import get_layout
from .slots import fill_slots
from .errors import RenderError
from .fasthtml import process_fasthtml_in_content
from .utilities import log, extract_scripts, apply_html_attributes, format_error_html

logger = logging.getLogger(__name__)
PYXIE_SHOW_ATTR = "data-pyxie-show"  # Visibility control attribute
SELF_CLOSING_TAGS = frozenset({'br', 'img', 'input', 'hr', 'meta', 'link'})

class RenderResult(NamedTuple):
    """Result from a rendering operation."""
    content: Optional[str] = None
    error: Optional[str] = None
    @property
    def success(self) -> bool: return self.error is None and self.content is not None

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

@lru_cache(maxsize=32)
def render_markdown(content: str) -> str:
    """Render markdown content to HTML with preprocessing."""
    if not content.strip(): return content
    
    # Normalize indentation in content
    lines = content.strip().splitlines()
    if not lines: return ""
    
    min_indent = min((len(line) - len(line.lstrip()) for line in lines if line.strip()), default=0)
    normalized = '\n'.join(line[min_indent:] if line.strip() else '' for line in lines)
    return PyxieHTMLRenderer().render(Document(normalized))

def process_fasthtml(content: str) -> RenderResult:
    """Process FastHTML blocks in content."""
    try:
        return RenderResult(content=process_fasthtml_in_content(content))
    except Exception as e:
        log(logger, "Renderer", "error", "fasthtml", f"Failed to process FastHTML: {e}")
        return RenderResult(error=str(e))

def render_block(block: ContentBlock) -> RenderResult:
    """Render a content block to HTML."""
    if not block.content and block.name != "script":
        return RenderResult(error="Cannot render empty content block")
    
    try:
        log(logger, "Renderer", "debug", "block", f"Processing block: {block.name}")
        
        # Handle special cases
        if block.name == "script" and not block.content:
            if not block.params: return RenderResult(content="")
            attr_str = " ".join(f'{k}="{v}"' for k, v in block.params.items())
            return RenderResult(content=f"<script {attr_str}></script>")
        if block.content_type == "ft": return RenderResult(content=block.content)
        
        # Process FastHTML content
        ft_result = process_fasthtml(block.content)
        if not ft_result.success:
            return RenderResult(error=f"FastHTML error: {ft_result.error}")
        
        # Process content segments
        html_content = ''.join(
            part if is_script else (render_markdown(part) if part.strip() else part)
            for part, is_script in extract_scripts(ft_result.content)
        )
        
        return RenderResult(content=apply_html_attributes(html_content, block.params, logger) 
                           if block.params else html_content)
    except Exception as e:
        log(logger, "Renderer", "error", "block", f"Failed to render block '{block.name}': {e}")
        return RenderResult(error=f"Failed to render block: {e}")

def render_blocks(blocks: Dict[str, List[ContentBlock]]) -> Dict[str, List[str]]:
    """Render multiple content blocks to HTML."""
    return {name: [
        result.content if result.success else format_error_html("block", result.error)
        for block in block_list for result in [render_block(block)]
    ] for name, block_list in blocks.items()}

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

def handle_cache_and_layout(item: ContentItem, cache: Optional[CacheProtocol] = None) -> Tuple[Optional[str], Optional[Any], Optional[str]]:
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
    """Render a content item to HTML using its layout and blocks."""
    try:
        # Get from cache or resolve layout
        cached_html, layout_instance, layout_error = handle_cache_and_layout(item, cache)
        if cached_html: return cached_html
        if layout_error: return format_error_html("rendering", layout_error)
        
        # Render blocks and process conditional visibility
        rendered_blocks = render_blocks(item.blocks)
        filled_slots = extract_slots_with_content(rendered_blocks)
        layout_html = process_conditional_visibility(layout_instance, filled_slots)
        
        # Fill slots
        result = fill_slots(layout_html, rendered_blocks)
        if not result.was_filled:
            error_msg = f"Failed to fill slots: {result.error}"
            log(logger, "Renderer", "error", "render", f"Failed to render {item.slug}: {error_msg}")
            return format_error_html("rendering", error_msg)
        
        # Save to cache if enabled
        html = result.element
        if cache:
            cache.store(item.collection or "content", item.source_path, html, get_layout_name(item))
        return html
    except Exception as e:
        log(logger, "Renderer", "error", "render", f"Failed to render content to HTML: {e}")
        return format_error_html("rendering", str(e)) 