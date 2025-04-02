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
from typing import Dict, Any, Type, Union, Set

# Mistletoe imports
from mistletoe import Document
from mistletoe.html_renderer import HTMLRenderer
from mistletoe.block_token import BlockToken
from mistletoe.span_token import SpanToken
from mistletoe.latex_token import Math

# Local Pyxie imports
from .errors import log, format_error_html, PyxieError
from .types import ContentItem
from .layouts import handle_cache_and_layout, LayoutResult, LayoutNotFoundError
from .fasthtml import execute_fasthtml
from .slots import process_layout
from .parser import (
    RawBlockToken,
    NestedContentToken,
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
        known_custom_tokens = [RawBlockToken, NestedContentToken, Math]
        # Only register tokens that we know how to handle
        valid_tokens = [token for token in extras if hasattr(self, self._cls_to_func(token.__name__))]
        unique_tokens = list(dict.fromkeys(valid_tokens + known_custom_tokens))
        super().__init__(*unique_tokens)
        self._used_ids: Set[str] = set() # For unique heading IDs
        
        for token in extras:
            if token not in unique_tokens:
                logger.warning(f"Token '{token.__name__}' not registered - no render method found.")

    def render_math(self, token: Math) -> str:
        """Render math tokens using KaTeX.
        
        Handles both inline math ($...$) and display math ($$...$$).
        Outputs HTML that KaTeX can process on the client side.
        """
        content = token.content
        # Check if it's display math ($$) or inline math ($)
        display_mode = content.startswith('$$') and content.endswith('$$')
        if display_mode:
            tex = content[2:-2].strip()  # Remove $$ delimiters
            return f'<div class="katex-block" data-tex="{html.escape(tex)}"></div>'
        else:
            tex = content[1:-1].strip()  # Remove $ delimiters
            return f'<span class="katex-inline" data-tex="{html.escape(tex)}"></span>'

    # --- Custom Token Render Methods ---

    def render_raw_block_token(self, token: RawBlockToken) -> str:
        """Renders raw blocks verbatim, handling potential special cases."""
        if getattr(token, 'is_self_closing', False): # Check flag from parser
            return f"<{token.tag_name}{self._render_attrs(token.attrs)} />"
        
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
        heading_id = self._make_id(inner)
        return f'<h{token.level} id="{heading_id}">{inner}</h{token.level}>'

    def render_paragraph(self, token) -> str:
        """Render a paragraph."""
        if not token.children:
            return ""
                
        inner = self.render_inner(token)
        return f'<p>{inner}</p>' if inner.strip() else ''

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
    """
    module_name = "Renderer"
    operation_name = "render_content"
    file_path = getattr(item, 'source_path', None)    

    try:        
        # 1. Get Layout HTML
        log(logger, module_name, "debug", operation_name, "Fetching layout...", file_path=file_path)
        layout_result: LayoutResult = handle_cache_and_layout(item)
        if layout_result.error:            
            return format_error_html(layout_result.error, "Layout Loading")
        layout_html = layout_result.html
        if not layout_html:             
            return format_error_html("Layout 'default' not found", "Layout Loading")
        log(logger, module_name, "debug", operation_name, "Layout HTML obtained.", file_path=file_path)

        # 2. Prepare Content & Render Fragment
        rendered_fragment = ""
        if item.content and item.content.strip():
            log(logger, module_name, "debug", operation_name, "Preparing Mistletoe render...", file_path=file_path)            
            custom_tokens_for_parsing = [RawBlockToken, NestedContentToken]
            log(logger, module_name, "debug", operation_name, f"Using custom tokens: {[t.__name__ for t in custom_tokens_for_parsing]}", file_path=file_path)

            with PyxieRenderer(*custom_tokens_for_parsing) as renderer:
                try:                                        
                    doc = Document(item.content)
                    rendered_fragment = renderer.render(doc)
                    log(logger, module_name, "debug", operation_name, "Successfully rendered Markdown to fragment.", file_path=file_path)
                except Exception as parse_render_err:                    
                    logger.error("Error during Mistletoe parsing/rendering", exc_info=True)
                    rendered_fragment = format_error_html(parse_render_err, "Content Rendering")
        else:
            log(logger, module_name, "info", operation_name, "Markdown content is empty or whitespace only.", file_path=file_path)

        # 3. Process Layout via Slots Module
        log(logger, module_name, "debug", operation_name, "Processing layout and slots...", file_path=file_path)
        final_html_fragment = process_layout(
            layout_html=layout_html,
            rendered_html=rendered_fragment,
            context=item.metadata,
        )        
        return final_html_fragment

    except LayoutNotFoundError as e:
        logger.error("Layout not found", exc_info=True)
        return format_error_html(str(e), "Layout Loading")
    except PyxieError as pe:
        logger.error("PyxieError during layout processing", exc_info=True)
        return format_error_html(pe, "Layout Processing")
    except Exception as e:
        logger.error("Unexpected error in render_content", exc_info=True)
        return format_error_html(e, "Unexpected Error")