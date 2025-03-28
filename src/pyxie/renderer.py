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

"""Renderer module for Pyxie."""

import re
from typing import Dict, List, Set, Optional, Tuple
from mistletoe import Document, HtmlRenderer
from lxml import html
import inspect
import logging
from .errors import log, format_error_html
from .fasthtml import render_fasthtml
from .types import ContentItem
from .layouts import get_layout
from .slots import process_slots_and_visibility
from .constants import SELF_CLOSING_TAGS

from .parser import FastHTMLToken, ScriptToken, NestedContentToken, custom_tokenize_block
from .cache import CacheProtocol

logger = logging.getLogger(__name__)

def format_html_attrs(attrs: Dict[str, str]) -> str:
    """Format HTML attributes dictionary into a string."""
    
    if not attrs:
        return ''
    attrs_str = ' '.join(f'{k}="{v}"' for k, v in attrs.items())
    return f' {attrs_str}' if attrs_str else ''

class NestedRenderer(HtmlRenderer):
    """A renderer that handles nested markdown content."""
    
    def __init__(self):
        super().__init__()
        self.render_map['NestedContentToken'] = self.render_nested_content
        self.render_map['FastHTMLToken'] = self.render_fasthtml
        self.render_map['ScriptToken'] = self.render_script
        self._used_ids = set()  # Track used header IDs
    
    def _make_id(self, text: str) -> str:
        """Generate a unique ID for a header."""

        # Remove HTML tags and non-word chars, convert to lowercase
        base_id = re.sub(r'<[^>]+>|[^\w\s-]', '', text.lower()).strip('-') or 'section'
        # Convert spaces and repeated dashes to single dash
        base_id = re.sub(r'[-\s]+', '-', base_id)
        
        # Ensure uniqueness
        header_id = base_id
        counter = 1
        while header_id in self._used_ids:
            header_id = f"{base_id}-{counter}"
            counter += 1
        self._used_ids.add(header_id)
        return header_id
    
    def render_heading(self, token):
        """Render heading with automatic ID generation."""
        inner = self.render_inner(token)
        return f'<h{token.level} id="{self._make_id(inner)}">{inner}</h{token.level}>'
    
    def render_nested_content(self, token):
        """Render a content block with nested markdown."""
        try:
            attrs_str = format_html_attrs(token.attrs)
            
            # Handle predefined self-closing tags and explicitly self-closed tags
            if token.tag_name in SELF_CLOSING_TAGS or token.is_self_closing:
                return f'<{token.tag_name}{attrs_str} />'
            
            # For custom content blocks, render with markdown
            rendered_blocks = []
            for child in token.children:
                if isinstance(child, NestedContentToken):
                    # Recursively render nested content
                    rendered = self.render_nested_content(child)
                    rendered_blocks.append(rendered)
                else:
                    # Render other tokens normally
                    rendered = self.render(child)
                    rendered_blocks.append(rendered)
            
            # Join blocks with newlines
            inner = '\n'.join(rendered_blocks)
            return f'<{token.tag_name}{attrs_str}>\n{inner}\n</{token.tag_name}>'
        except Exception as e:
            log(logger, "Renderer", "error", "nested_content", f"Failed to render nested content: {e}")
            return f'<div class="error">Error: {e}</div>'
    
    def render_fasthtml(self, token):
        """Render a FastHTML block."""
        attrs_str = format_html_attrs(token.attrs)
        
        # Render FastHTML content
        result = render_fasthtml(token.content)
        if result.error:
            return f'<div class="error">Error: {result.error}</div>'
        elif result.content:
            return f'<div{attrs_str}>\n{result.content}\n</div>'
        return ''
    
    def render_script(self, token):
        """Render a script block."""
        try:
            attrs_str = format_html_attrs(token.attrs)
            return f'<script{attrs_str}>\n{token.content}\n</script>'
        except Exception as e:
            log(logger, "Renderer", "error", "script", f"Failed to render script: {e}")
            return f'<div class="error">Error: {e}</div>'

def handle_cache_and_layout(item: ContentItem, cache: Optional[CacheProtocol] = None) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Handle caching and layout resolution in one step."""
    collection = item.collection or "content"
    layout_name = item.metadata.get("layout")  # Don't use default layout
    
    if cache and (cached := cache.get(collection, item.source_path, layout_name or "default")):
        return cached, None, None
    
    if layout_name and (layout := get_layout(layout_name)):
        sig = inspect.signature(layout.func)
        params = list(sig.parameters.values())
        
        # If the layout function expects a single 'metadata' parameter, pass the entire metadata dict
        if len(params) == 1 and params[0].name == 'metadata':
            return None, layout.create(metadata=item.metadata), None
            
        # Otherwise, filter metadata to match the function's parameters
        metadata = {k: v for k, v in item.metadata.items() if k != "layout" and k in sig.parameters}
        return None, layout.create(**metadata), None
    
    if layout_name:
        error_msg = f"Layout '{layout_name}' not found"
        log(logger, "Renderer", "warning", "layout", error_msg)
        return None, None, error_msg
    
    return None, None, None

def render_content(item: ContentItem, cache: Optional[CacheProtocol] = None) -> str:
    """Render a content item to HTML using its layout and blocks."""
    try:
        # Get from cache or resolve layout
        cached_html, layout_html, layout_error = handle_cache_and_layout(item, cache)
        if cached_html: return cached_html
        if layout_error: return format_error_html("rendering", layout_error)
        
        # Create document with custom tokenizer
        doc = Document('')
        doc.children = list(custom_tokenize_block(item.content, [FastHTMLToken, ScriptToken, NestedContentToken]))
        
        # Render document with our custom renderer
        with NestedRenderer() as renderer:
            # Extract content for each slot
            slots = {}
            main_content = []
            
            for child in doc.children:
                rendered = renderer.render(child)
                if isinstance(child, NestedContentToken) and child.tag_name not in SELF_CLOSING_TAGS:
                    # Use the tag name as the slot name
                    slot_name = child.tag_name
                    slots[slot_name] = rendered
                main_content.append(rendered)
            
            # Add main content to slots
            slots['content'] = '\n'.join(main_content)
            
            # If we have a layout, use it
            if layout_html:
                # Process slots and conditional visibility
                result = process_slots_and_visibility(layout_html, slots)
                if not result.was_filled:
                    error_msg = f"Failed to fill slots in layout: {result.error}"
                    log(logger, "Renderer", "error", "render", error_msg)
                    return format_error_html("rendering", error_msg)
                
                # Save to cache if enabled
                if cache:
                    cache.store(item.collection or "content", item.source_path, result.element, get_layout("default"))
                
                return result.element
                
            # If no layout, just return the rendered HTML
            return slots['content']
            
    except Exception as e:
        log(logger, "Renderer", "error", "render", f"Failed to render content to HTML: {e}")
        return format_error_html("rendering", str(e)) 