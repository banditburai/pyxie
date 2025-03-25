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
import re
from typing import Dict, List, Optional, Set, Tuple, Any
from io import StringIO
import inspect

from mistletoe import Document, HtmlRenderer
from mistletoe.block_token import add_token, HTMLBlock
from lxml import html

from .types import ContentItem
from .layouts import get_layout
from .fasthtml import render_fasthtml
from .errors import format_error_html
from .utilities import log
from .constants import PYXIE_SHOW_ATTR, SELF_CLOSING_TAGS
from .parser import FastHTMLToken, ScriptToken, ContentBlockToken
from .slots import fill_slots
from .cache import CacheProtocol

logger = logging.getLogger(__name__)

def _generate_heading_id(text: str, counts: Dict[str, int]) -> str:
    """Generate a unique ID for a heading."""
    text = re.sub(r'[^\w\s-]', '', text.strip().lower())
    text = re.sub(r'[-\s]+', '-', text) or 'section'
    
    if text in counts:
        counts[text] += 1
        return f"{text}-{counts[text]}"
    counts[text] = 0
    return text

class PyxieHTMLRenderer(HtmlRenderer):
    """Renderer for Pyxie content."""
    
    def __init__(self):
        super().__init__(FastHTMLToken, ScriptToken, ContentBlockToken)
        self.header_counts = {}
        self.render_map.update({
            FastHTMLToken.__name__: self.render_fast_html_token,
            ScriptToken.__name__: self.render_script_token,
            ContentBlockToken.__name__: self.render_content_block_token
        })
        
    def render_heading(self, token):
        """Render a heading with a unique ID."""
        inner = self.render_inner(token)
        text_id = _generate_heading_id(re.sub(r'<[^>]*>', '', inner), self.header_counts)
        return f'<h{token.level} id="{text_id}">{inner}</h{token.level}>'
    
    def render_image(self, token):
        """Render an image with placeholder support."""
        src = token.src or ''
        alt = token.title or token.src or ''
        title = token.title or alt
        
        if src.startswith('pyxie:'):
            seed, *dims = src.split('/')[0].split(':')[1:] + ['800', '600']
            src = f'https://picsum.photos/seed/{seed}/{dims[0]}/{dims[1]}'
        elif src == 'placeholder':
            src = f'https://picsum.photos/seed/{alt.lower().replace(" ", "-")}/800/600'
        
        attrs = [f'src="{src}"', f'alt="{alt}"']
        if title: attrs.append(f'title="{title}"')
        return f'<img {" ".join(attrs)}>'
    
    def render_fast_html_token(self, token):
        """Render a FastHTML token."""
        try:
            result = render_fasthtml(token.content)
            return result.content if not result.error else format_error_html("fasthtml", result.error)
        except Exception as e:
            return format_error_html("fasthtml", str(e))
    
    def render_script_token(self, token):
        """Render a script token."""
        return f'<script>{token.content}</script>'
    
    def render_content_block_token(self, token):
        """Render a content block token."""
        attrs = getattr(token, 'attrs', {})
        attr_str = ' ' + ' '.join(f'{k}="{v}"' for k, v in attrs.items()) if attrs else ''
        
        # Render content directly without creating an HTMLBlock
        return f'<{token.tag_name}{attr_str}>{token.content}</{token.tag_name}>'

def extract_slots_with_content(rendered_blocks: Dict[str, List[str]]) -> Set[str]:
    """Extract slot names that have content."""
    return {name for name, blocks in rendered_blocks.items() if any(block.strip() for block in blocks)}

def check_visibility_condition(slot_names: List[str], filled_slots: Set[str]) -> bool:
    """Determine if an element should be visible based on slot conditions."""
    if not slot_names:
        return True
        
    has_positive = False
    for slot in (s.strip() for s in slot_names):
        if not slot:
            continue
        if slot.startswith('!'):
            if slot[1:].strip() in filled_slots:
                return False
        else:
            has_positive = True
            if slot in filled_slots:
                return True
    return not has_positive

def process_element(element: html.HtmlElement, parent: html.HtmlElement, filled_slots: Set[str]) -> None:
    """Process a single element for conditional visibility."""
    if PYXIE_SHOW_ATTR in element.attrib:
        slot_names = [name.strip() for name in element.attrib[PYXIE_SHOW_ATTR].split(',')]
        if not check_visibility_condition(slot_names, filled_slots):
            return
    
    new_element = html.Element(element.tag, element.attrib)
    new_element.text, new_element.tail = element.text, element.tail
    parent.append(new_element)
    
    for child in element.iterchildren():
        process_element(child, new_element, filled_slots)

def process_conditional_visibility(layout_html: str, filled_slots: Set[str]) -> str:
    """Process data-pyxie-show attributes in HTML."""
    try:
        doc = html.fromstring(layout_html)
        new_doc = html.Element('div')
        
        for element in doc.xpath('/*'):
            process_element(element, new_doc, filled_slots)
        
        result = ''.join(html.tostring(child, encoding='unicode', pretty_print=True) for child in new_doc)
        return layout_html if layout_html.strip() == "<div><p>Unclosed tag" else result
        
    except Exception as e:
        logger.error(f"Error processing conditional visibility: {e}")
        return layout_html

def handle_cache_and_layout(item: ContentItem, cache: Optional[CacheProtocol] = None) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Handle caching and layout resolution in one step."""
    collection = item.collection or "content"
    layout_name = item.metadata.get("layout")
    
    if not layout_name:
        return None, None, None
    
    if cache and (cached := cache.get(collection, item.source_path, layout_name)):
        return cached, None, None
    
    if layout := get_layout(layout_name):
        sig = inspect.signature(layout.func)
        params = list(sig.parameters.values())
        
        # If the layout function expects a single 'metadata' parameter, pass the entire metadata dict
        if len(params) == 1 and params[0].name == 'metadata':
            return None, layout.create(metadata=item.metadata), None
            
        # Otherwise, filter metadata to match the function's parameters
        metadata = {k: v for k, v in item.metadata.items() if k != "layout" and k in sig.parameters}
        return None, layout.create(**metadata), None
    
    error_msg = f"Layout '{layout_name}' not found"
    log(logger, "Renderer", "warning", "layout", error_msg)
    return None, None, error_msg

def render_blocks(item: ContentItem) -> Dict[str, List[str]]:
    """Render all content blocks for an item."""
    add_token(FastHTMLToken)
    add_token(ScriptToken)
    add_token(ContentBlockToken)
    
    rendered_blocks = {}
    with PyxieHTMLRenderer() as renderer:
        for block_name, blocks in item.blocks.items():
            rendered_blocks[block_name] = []
            for block in blocks:
                # Create a document with the block's content
                doc = Document(StringIO(block.content))
                rendered_blocks[block_name].append(renderer.render(doc))
    return rendered_blocks

def render_content(item: ContentItem, cache: Optional[CacheProtocol] = None) -> str:
    """Render a content item to HTML using its layout and blocks."""
    try:
        cached_html, layout_html, layout_error = handle_cache_and_layout(item, cache)
        if cached_html:
            return cached_html
        if layout_error:
            return format_error_html("rendering", layout_error)
        
        try:
            rendered_blocks = render_blocks(item)
            
            if not any(any(block.strip() for block in blocks) for blocks in rendered_blocks.values()):
                return "<div></div>"
            
            if not layout_html:
                return "\n".join(rendered_blocks.get("content", [])) or "<div></div>"
            
            result = fill_slots(layout_html, rendered_blocks)
            if result.error:
                return format_error_html("rendering", result.error)
            
            html = process_conditional_visibility(
                result.element, 
                extract_slots_with_content(rendered_blocks)
            )
            
            if cache:
                cache.store(item.collection or "content", item.source_path, html, item.metadata.get("layout"))
            
            return html
                
        except Exception as e:
            log(logger, "Renderer", "error", "render", f"Failed to render {item.slug}: {e}")
            return format_error_html("rendering", str(e))
            
    except Exception as e:
        log(logger, "Renderer", "error", "render", f"Failed to render {item.slug}: {e}")
        return format_error_html("rendering", str(e)) 