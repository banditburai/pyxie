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

import logging
import html
import re
from typing import Dict, List, Any, Optional, Tuple, Type, Union, Set

# Mistletoe imports
from mistletoe import Document
from mistletoe.html_renderer import HTMLRenderer
from mistletoe.block_token import BlockToken
from mistletoe.span_token import SpanToken

# Local Pyxie imports
from .errors import log, format_error_html, PyxieError
from .types import ContentItem, RenderResult
from .layouts import handle_cache_and_layout, LayoutResult
from .fasthtml import execute_fasthtml
from .slots import process_layout
from .parser import (
    RawBlockToken,
    NestedContentToken,
    VOID_ELEMENTS,
    RAW_BLOCK_TAGS,
)

logger = logging.getLogger(__name__)

# --- Custom Mistletoe Renderer ---

class PyxieRenderer(HTMLRenderer):
    """
    Custom Mistletoe renderer that handles Pyxie's custom block tokens,
    producing an HTML fragment suitable for layout processing.
    """
    def __init__(self, *extras: Type[Union[BlockToken, SpanToken]]):
        # Known custom tokens this renderer handles
        known_custom_tokens = [RawBlockToken, NestedContentToken]
        all_tokens_to_register = list(extras) + known_custom_tokens
        unique_tokens = list(dict.fromkeys(all_tokens_to_register))
        super().__init__(*unique_tokens)
        self._used_ids: Set[str] = set() # For unique heading IDs

        # Check for missing render methods
        for token_cls in unique_tokens:
            render_func_name = self._cls_to_func(token_cls.__name__)
            if not hasattr(self, render_func_name):
                logger.warning(f"Render function '{render_func_name}' not found for token '{token_cls.__name__}'.")

    # --- Custom Token Render Methods ---

    def render_raw_block_token(self, token: RawBlockToken) -> str:
        """Renders raw blocks verbatim, handling potential special cases."""
        if getattr(token, 'is_self_closing', False): # Check flag from parser
            return f"<{token.tag_name}{self._render_attrs(token.attrs)} />"

        # Specific handling for certain raw tags
        if token.tag_name in ('fasthtml', 'ft'):
            # Execute FastHTML code
            try:
                result = execute_fasthtml(token.content)
                if result.error:
                    return f'<div class="error">Error: {result.error}</div>'
                elif result.content:
                    return f'<div{self._render_attrs(token.attrs)}>\n{result.content}\n</div>'
                return ''
            except Exception as e:
                logger.error(f"Failed to execute FastHTML: {e}")
                return f'<div class="error">Error: {e}</div>'

        elif token.tag_name == 'script':
            # Script content should not be escaped
            try:
                return f'<script{self._render_attrs(token.attrs)}>\n{token.content}\n</script>'
            except Exception as e:
                logger.error(f"Failed to render script: {e}")
                return f'<div class="error">Error: {e}</div>'

        elif token.tag_name == 'style':
            # Style content should not be escaped
            try:
                return f'<style{self._render_attrs(token.attrs)}>\n{token.content}\n</style>'
            except Exception as e:
                logger.error(f"Failed to render style: {e}")
                return f'<div class="error">Error: {e}</div>'

        else:
            # Default for other raw tags (like pre, code if added to RAW_BLOCK_TAGS)
            # Raw content should not be escaped
            try:
                return f"<{token.tag_name}{self._render_attrs(token.attrs)}>{token.content}</{token.tag_name}>"
            except Exception as e:
                logger.error(f"Failed to render raw block {token.tag_name}: {e}")
                return f'<div class="error">Error: {e}</div>'

    def render_nested_content_token(self, token: NestedContentToken) -> str:
        """Renders custom blocks by rendering their parsed Markdown children."""
        if getattr(token, 'is_self_closing', False): # Check flag from parser
            return f"<{token.tag_name}{self._render_attrs(token.attrs)} />"

        # Children were already parsed by Document() in __init__
        inner_html = self.render_inner(token) # Recursively render children tokens
        
        # Add data-slot attribute - any tag that makes it here is a slot
        attrs = token.attrs.copy()
        attrs['data-slot'] = token.tag_name
        
        return f"<{token.tag_name}{self._render_attrs(attrs)}>{inner_html}</{token.tag_name}>"

    def render_image(self, token) -> str:
        """Render an image token, handling pyxie: URLs."""
        src = token.src
        if src.startswith('pyxie:'):
            # Parse pyxie: URL format - pyxie:category/width/height
            parts = src[6:].split('/')  # Remove 'pyxie:' prefix and split
            if len(parts) >= 3:
                category = parts[0]
                width = parts[1]
                height = parts[2]
                # Use picsum.photos for placeholder images
                src = f"https://picsum.photos/seed/{category}/{width}/{height}"
        
        # Get alt text from token.children if available, otherwise use empty string
        alt = token.children[0].content if token.children else ""
        attrs = {'src': src, 'alt': alt}
        if token.title:
            attrs['title'] = token.title
        return f"<img{self._render_attrs(attrs)} />"

    def _make_id(self, text: str) -> str:
        """Generate a unique ID from heading text."""
        # Consider using a more robust slugify library if needed
        base_id = re.sub(r'<[^>]+>', '', text) # Strip tags first
        base_id = re.sub(r'[^\w\s-]', '', base_id.lower()).strip()
        base_id = re.sub(r'[-\s]+', '-', base_id) or 'section'
        header_id = base_id
        counter = 1
        while header_id in self._used_ids:
            header_id = f"{base_id}-{counter}"
            counter += 1
        self._used_ids.add(header_id)
        return header_id

    def render_heading(self, token) -> str:
        """Render heading with automatic ID generation."""
        inner = self.render_inner(token)
        # Use the generated ID
        heading_id = self._make_id(inner)
        return f'<h{token.level} id="{heading_id}">{inner}</h{token.level}>'

    def render_paragraph(self, token) -> str:
        """Render a paragraph."""
        # If there are no children, return empty string
        if not token.children:
            return ""

        # If the first child is an Image, use default rendering
        if token.children[0].__class__.__name__ == 'Image':
            return super().render_paragraph(token)

        # Default paragraph rendering
        return super().render_paragraph(token)

    # --- Helper Methods ---

    def _render_attrs(self, attrs: Dict[str, Any]) -> str:
        """Render HTML attributes."""
        if not attrs: return ""
        parts = []
        for k, v in sorted(attrs.items()):
             if k.startswith('_') or k == 'is_self_closing': continue # Skip internal attrs
             if v is True: parts.append(html.escape(k))
             elif v is False or v is None: continue
             else: parts.append(f'{html.escape(k)}="{html.escape(str(v), quote=True)}"')
        return " " + " ".join(parts) if parts else ""

# --- Main Rendering Orchestration Function ---

def render_content(
    item: ContentItem,
) -> str:
    """
    Renders a ContentItem into its layout template fragment.
    ... (rest of docstring) ...
    """
    module_name = "Renderer"
    operation_name = "render_content"
    file_path = getattr(item, 'source_path', None)
    log(logger, module_name, "info", operation_name, f"Starting for item: {file_path or 'N/A'}", file_path=file_path)

    try:
        # 1. Get Layout HTML
        log(logger, module_name, "debug", operation_name, "Fetching layout...", file_path=file_path)
        layout_result: LayoutResult = handle_cache_and_layout(item)
        if layout_result.error:            
            return format_error_html(layout_result.error, "Layout Loading")
        layout_html = layout_result.html
        if not layout_html:             
             return format_error_html("Layout HTML is empty", "Layout Loading")
        log(logger, module_name, "debug", operation_name, "Layout HTML obtained.", file_path=file_path)

        # 2. Prepare Content & Render Fragment
        lines = item.content.splitlines()
        rendered_fragment = ""
        if lines or item.content.strip():
            log(logger, module_name, "debug", operation_name, "Preparing Mistletoe render...", file_path=file_path)
            # Define the custom tokens needed for parsing
            custom_tokens_for_parsing = [RawBlockToken, NestedContentToken]
            log(logger, module_name, "debug", operation_name, f"Using custom tokens: {[t.__name__ for t in custom_tokens_for_parsing]}", file_path=file_path)

            with PyxieRenderer(*custom_tokens_for_parsing) as renderer:
                try:                    
                    doc = Document(lines)
                    rendered_fragment = renderer.render(doc)
                    log(logger, module_name, "debug", operation_name, "Successfully rendered Markdown to fragment.", file_path=file_path)
                except Exception as parse_render_err:
                    rendered_fragment = format_error_html(parse_render_err, "Content Rendering")
        else:
            log(logger, module_name, "info", operation_name, "Markdown content is empty.", file_path=file_path)

        # 3. Process Layout via Slots Module
        log(logger, module_name, "debug", operation_name, "Processing layout and slots...", file_path=file_path)
        final_html_fragment = process_layout(
            layout_html=layout_html, # Pass the string
            rendered_html=rendered_fragment, # Pass the rendered fragment
            context=item.metadata, # Context for conditionals            
        )
        log(logger, module_name, "info", operation_name, "Layout processing completed.", file_path=file_path)
        return final_html_fragment

    except PyxieError as pe:         
         return format_error_html(pe, "Layout Processing")
    except Exception as e:
        return format_error_html(e, "Unexpected Error")