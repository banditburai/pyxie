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

"""Convert markdown content to HTML.

This module handles the conversion of markdown content to HTML,
using mistletoe's HTML renderer.
"""

import logging
from html import escape
from typing import Dict, List, Optional, Any, TypedDict, Tuple, Protocol
from mistletoe import Document
from mistletoe.html_renderer import HTMLRenderer
import re

from .types import ContentBlock, ContentItem
from .layouts import get_layout
from .slots import fill_slots
from .errors import RenderError
from .fasthtml import (
    process_fasthtml_in_content
)
from .utilities import (
    log, 
    extract_scripts,
    apply_html_attributes,
    format_error_html
)

logger = logging.getLogger(__name__)

class RenderedBlocks(TypedDict):
    """Type for rendered block collections."""
    name: List[str]

class CacheProtocol(Protocol):
    """Protocol for cache objects."""
    def get(self, collection: str, path: str, layout: str) -> Optional[str]: ...
    def store(self, collection: str, path: str, content: str, layout: str) -> None: ...

class PyxieHTMLRenderer(HTMLRenderer):
    """Custom HTML renderer for markdown with enhanced typography."""
        
    DEFAULT_WIDTH = 800
    DEFAULT_HEIGHT = 600
    PICSUM_URL = "https://picsum.photos/seed/{seed}/{width}/{height}"
    
    def render_raw_html(self, token):
        """Handle raw HTML blocks."""
        return token.content
        
    def render_paragraph(self, token):
        """Custom paragraph rendering."""
        content = self.render_inner(token)
        if content.strip().startswith('<') and content.strip().endswith('>'):
            return content
        return f'<p>{content}</p>'
        
    def render_list(self, token):
        """Custom list rendering."""
        template = '<ul>{}</ul>'
        if hasattr(token, 'start'):
            template = f'<ol start="{token.start}">{{}}</ol>'
        return template.format(self.render_inner(token))
        
    def render_list_item(self, token):
        """Custom list item rendering."""
        return f'<li>{self.render_inner(token)}</li>'
        
    def render_thematic_break(self, token):
        """Custom thematic break (horizontal rule) rendering."""
        return '<hr>'
        
    def render_heading(self, token):
        """Custom heading rendering."""
        return f'<h{token.level}>{self.render_inner(token)}</h{token.level}>'
        
    def render_block_code(self, token):
        """Custom code block rendering."""
        language = token.language or ''
        return f'<pre><code class="language-{language}">{escape(token.content)}</code></pre>'
        
    def render_image(self, token) -> str:
        """Custom image rendering with placeholder support.
        
        Supports special syntax:
        1. pyxie:seed - Uses default 800x600
        2. pyxie:seed/width/height - Custom dimensions
        3. placeholder - Uses alt text as seed with default size
        """
        url = token.src
        title = getattr(token, 'title', '')                
        alt = self.render_inner(token)                
        if url.startswith('pyxie:'):
            parts = url[6:].split('/')
            seed = parts[0]
            width = parts[1] if len(parts) > 1 else self.DEFAULT_WIDTH
            height = parts[2] if len(parts) > 2 else self.DEFAULT_HEIGHT
            url = self.PICSUM_URL.format(seed=seed, width=width, height=height)
        elif url == 'placeholder':            
            seed = re.sub(r'[^\w\s-]', '', alt.lower())
            seed = re.sub(r'[\s-]+', '-', seed).strip('-_')
            url = self.PICSUM_URL.format(seed=seed, width=self.DEFAULT_WIDTH, height=self.DEFAULT_HEIGHT)
            
        title_attr = f' title="{escape(title)}"' if title else ''
        return f'<img src="{escape(url)}" alt="{escape(alt)}"{title_attr}>'

def process_fasthtml(content: str) -> str:
    """Process FastHTML blocks in content."""
    try:
        return process_fasthtml_in_content(content)
    except Exception as e:
        log(logger, "Renderer", "error", "fasthtml", f"Failed to process FastHTML: {e}")
        return format_error_html("FastHTML", str(e))

def render_markdown(content: str) -> str:
    """Render markdown content to HTML."""
    if not content.strip():
        return content            
    renderer = PyxieHTMLRenderer()
    doc = Document(content.strip())
    return renderer.render(doc)

def process_content_parts(parts: List[Tuple[str, bool]]) -> str:
    """Process content parts, rendering markdown for non-script parts."""
    def render_part(part: str, is_script: bool) -> str:
        if is_script:
            return part
        return render_markdown(part) if part.strip() else part
    
    processed_parts = [render_part(part, is_script) for part, is_script in parts]
    return ''.join(processed_parts)

def render_block(block: ContentBlock) -> str:
    """Render a content block to HTML."""
    if not block.content:
        # Allow empty script blocks, reject other empty blocks
        if block.name == "script":
            attr_str = " ".join(f'{k}="{v}"' for k, v in block.params.items())
            return "" if not block.params else f"<script {attr_str}></script>"
        raise RenderError("Cannot render empty content block")
    
    try:
        log(logger, "Renderer", "debug", "block", f"Processing block: {block.name}")
        
        if block.content_type == "ft":
            return block.content
        
        content = process_fasthtml(block.content)
        parts = extract_scripts(content)
        html_str = process_content_parts(parts)
        
        if block.params:
            html_str = apply_html_attributes(html_str, block.params, logger)
        
        return html_str
        
    except Exception as e:
        log(logger, "Renderer", "error", "block", f"Failed to render block '{block.name}': {e}")
        raise RenderError(f"Failed to render block: {e}") from e

def render_blocks(blocks: Dict[str, List[ContentBlock]]) -> Dict[str, List[str]]:
    """Render multiple content blocks to HTML."""
    rendered: Dict[str, List[str]] = {}
    
    for name, block_list in blocks.items():
        try:
            rendered[name] = [render_block(block) for block in block_list]
        except Exception as e:
            log(logger, "Renderer", "error", "blocks", f"Failed to render blocks '{name}': {e}")
            raise RenderError(f"Failed to render blocks: {e}") from e
    
    return rendered 

def get_cached_content(cache: Optional[CacheProtocol], item: ContentItem) -> Optional[str]:
    """Try to retrieve content from cache."""
    if not cache:
        return None
    return cache.get(
        item.collection or "content",
        item.source_path,
        item.metadata.get("layout", "default")
    )

def get_layout_instance(item: ContentItem) -> Tuple[Optional[Any], Optional[str]]:
    """Get layout instance for content item."""
    # Use instance's default_layout if available, otherwise fall back to "default"
    default = getattr(item, "_pyxie", None) and getattr(item._pyxie, "default_layout", "default") or "default"
    layout_name = item.metadata.get("layout", default)
    layout = get_layout(layout_name)
    
    if not layout:
        log(logger, "Renderer", "warning", "layout", f"Layout '{layout_name}' not found")
        return None, f"Layout '{layout_name}' not found"
    
    return layout.create(item.metadata), None

def apply_cache(cache: Optional[CacheProtocol], item: ContentItem, html: str) -> None:
    """Store rendered content in cache if available."""
    if cache:
        cache.store(
            item.collection or "content",
            item.source_path,
            html,
            item.metadata.get("layout", "default")
        )

def handle_slot_filling(layout_instance: Any, rendered_blocks: Dict[str, List[str]], slug: str) -> Tuple[Optional[str], Optional[str]]:
    """Fill slots with rendered blocks and handle errors."""
    result = fill_slots(layout_instance, rendered_blocks)
    
    if not result.was_filled:
        error_msg = f"Failed to fill slots: {result.error}"
        log(logger, "Renderer", "error", "render", f"Failed to render {slug}: {error_msg}")
        return None, error_msg
    
    return result.element, None

def render_content(item: ContentItem, cache: Optional[CacheProtocol] = None) -> str:
    """Render a content item to HTML using its layout and blocks."""
    try:
        if cached_html := get_cached_content(cache, item):
            return cached_html
        
        layout_instance, layout_error = get_layout_instance(item)
        if layout_error:
            log(logger, "Renderer", "error", "render", f"Failed to render {item.slug}: {layout_error}")
            return format_error_html("rendering", layout_error)
        
        rendered_blocks = render_blocks(item.blocks)
        
        html, slot_error = handle_slot_filling(layout_instance, rendered_blocks, item.slug)
        if slot_error:
            return format_error_html("rendering", slot_error)
        
        apply_cache(cache, item, html)
        return html
        
    except Exception as e:
        log(logger, "Renderer", "error", "render", f"Failed to render content to HTML: {e}")
        return format_error_html("rendering", str(e)) 