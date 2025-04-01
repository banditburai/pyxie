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
Handles layout processing for Pyxie: slot extraction and filling based on data-slot attributes.
"""

import logging
from typing import Dict, Optional, Any, NamedTuple

from lxml import etree, html
from lxml.html import HtmlElement

from .errors import SlotError
from .parser import RAW_BLOCK_TAGS
from .constants import STANDARD_HTML_TAGS

logger = logging.getLogger(__name__)

# Constants
SLOT_ATTR: str = "data-slot"
CONDITION_ATTR: str = "data-pyxie-show"
CLASS_ATTR: str = "class"
NON_SLOT_TAGS: frozenset[str] = frozenset(RAW_BLOCK_TAGS | STANDARD_HTML_TAGS)

class ParsedContent(NamedTuple):
    """Represents parsed HTML content with extracted slots."""
    main_content: str
    slots: Dict[str, str]

class ParsedLayout(NamedTuple):
    """Represents a parsed layout with its tree."""
    tree: HtmlElement
    original: str

def validate_layout(layout_html: str) -> None:
    """Validate layout requirements."""
    if not layout_html.strip():
        raise SlotError("Layout cannot be empty")
    if SLOT_ATTR not in layout_html:
        raise SlotError("Layout must contain at least one slot")

def parse_html(html_str: str, create_parent: bool = True) -> HtmlElement:
    """Parse HTML string into an HtmlElement."""
    try:
        parser = html.HTMLParser(encoding='utf-8')
        if create_parent:
            fragment = html.fragment_fromstring(html_str, create_parent='div', parser=parser)
        else:
            fragment = html.fromstring(html_str, parser=parser)
        if fragment is None:
            raise SlotError("Failed to parse HTML fragment")
        return fragment
    except (etree.XMLSyntaxError, etree.ParseError) as e:
        raise SlotError(f"Invalid HTML: {e}") from e

def merge_classes(*class_strings: Optional[str]) -> str:
    """Merge multiple HTML class strings, preserving order and removing duplicates."""
    classes = []
    seen = set()
    
    for class_str in class_strings:
        if not class_str:
            continue
        for cls in class_str.split():
            if cls.strip() and cls not in seen:
                classes.append(cls)
                seen.add(cls)
                
    return ' '.join(classes)

def extract_slots(rendered_html: str) -> ParsedContent:
    """Extract slots from rendered HTML content."""
    if not rendered_html.strip():
        return ParsedContent("", {})

    tree = parse_html(rendered_html)
    slots: Dict[str, str] = {}
    main_parts = []

    for element in tree.xpath('./* | ./text()[normalize-space()]'):
        if isinstance(element, HtmlElement):
            slot_name = element.get(SLOT_ATTR)
            if slot_name:
                slots[slot_name] = etree.tostring(element, encoding='unicode', method='html')
            else:
                main_parts.append(etree.tostring(element, encoding='unicode', method='html'))
        elif isinstance(element, etree._ElementUnicodeResult):
            main_parts.append(str(element))

    return ParsedContent("\n".join(main_parts).strip(), slots)

def preserve_tail_text(element: HtmlElement) -> None:
    """Preserve tail text when removing an element."""
    if element.tail and element.tail.strip():
        parent = element.getparent()
        if parent is not None:
            if parent.text:
                parent.text = parent.text + element.tail
            else:
                parent.text = element.tail
    element.getparent().remove(element)

def fill_slot(placeholder: HtmlElement, slot_html: str) -> None:
    """Fill a slot placeholder with content."""
    # Store original content for default handling
    original_text = placeholder.text
    original_children = list(placeholder.xpath('./*'))

    if not slot_html.strip():
        # If no content provided and no default content, remove the element
        if original_text is None and not original_children:
            preserve_tail_text(placeholder)
        return

    content = parse_html(slot_html)
    content_element = content[0] if len(content) > 0 else None

    # Store original attributes and clear content
    original_attrs = dict(placeholder.attrib)
    placeholder.text = None
    for child in placeholder.xpath('./*'):
        placeholder.remove(child)

    if content_element is not None:
        # Handle empty content
        if not content_element.text and not content_element.getchildren():
            # If we have default content, restore it
            if original_text is not None or original_children:
                placeholder.text = original_text
                for child in original_children:
                    placeholder.append(child)
                return
            preserve_tail_text(placeholder)
            return

        # Merge attributes
        for attr, value in content_element.attrib.items():
            if attr != SLOT_ATTR:
                if attr == CLASS_ATTR:
                    placeholder.set(CLASS_ATTR, merge_classes(original_attrs.get(CLASS_ATTR), value))
                else:
                    placeholder.set(attr, value)

        # Restore non-overwritten attributes
        for attr, value in original_attrs.items():
            if attr not in {SLOT_ATTR, CLASS_ATTR} and attr not in content_element.attrib:
                placeholder.set(attr, value)

        # Copy content
        if content_element.text and content_element.text.strip():
            placeholder.text = content_element.text.strip()
        for child in content_element.xpath('./*'):
            placeholder.append(child)

        # Handle tail text
        if content_element.tail and content_element.tail.strip():
            if placeholder.text:
                placeholder.text += content_element.tail.strip()
            else:
                placeholder.text = content_element.tail.strip()
    else:
        # Handle text-only content
        placeholder.text = slot_html.strip()
        # Restore original attributes except slot
        for attr, value in original_attrs.items():
            if attr != SLOT_ATTR:
                placeholder.set(attr, value)

def check_condition(condition: str, slots: Dict[str, str], context: Dict[str, Any]) -> bool:
    """Check if a condition is met based on slot content or metadata context."""
    if not condition:
        return False

    is_negated = condition.startswith('!')
    key = condition[1:] if is_negated else condition
    
    if not key:
        return False
    
    # First check if it's a metadata flag
    if key in context:
        value = context[key]
        return not value if is_negated else value
    
    # Then check if it's a slot existence check
    has_content = key in slots and bool(slots[key].strip())
    return not has_content if is_negated else has_content

def process_conditionals(tree: HtmlElement, slots: Dict[str, str], context: Dict[str, Any]) -> None:
    """Process conditional visibility in the layout."""
    for element in tree.xpath(f'//*[@{CONDITION_ATTR}]'):
        condition = element.get(CONDITION_ATTR, "").strip()
        if condition and not check_condition(condition, slots, context):
            preserve_tail_text(element)
        else:
            element.attrib.pop(CONDITION_ATTR, None)

def fill_slots_in_tree(tree: HtmlElement, slots: Dict[str, str]) -> None:
    """Fill all slots in the layout tree."""
    # First fill slots in conditional elements
    for element in tree.xpath(f'//*[@{CONDITION_ATTR}]//*[@{SLOT_ATTR}]'):
        slot_name = element.get(SLOT_ATTR)
        if slot_name and slot_name in slots:
            fill_slot(element, slots[slot_name])
        element.attrib.pop(SLOT_ATTR, None)

    # Then fill remaining slots
    for element in tree.xpath(f'//*[@{SLOT_ATTR} and not(ancestor::*[@{CONDITION_ATTR}])]'):
        slot_name = element.get(SLOT_ATTR)
        if slot_name:
            if slot_name in slots:
                fill_slot(element, slots[slot_name])
            elif element.text is None and not element.getchildren():
                preserve_tail_text(element)
        element.attrib.pop(SLOT_ATTR, None)

def format_output(tree: HtmlElement, original_layout: str) -> str:
    """Format the final HTML output."""
    # Get raw HTML with pretty printing
    result = etree.tostring(tree, encoding='unicode', method='html', pretty_print=True)
    
    # Handle HTML/body wrappers if needed
    if (tree.tag.lower() == 'html' and 
        not original_layout.strip().lower().startswith('<html')):
        body = tree.find('.//body')
        if body is not None:
            parts = ([body.text] if body.text and body.text.strip() else [] +
                    [etree.tostring(child, encoding='unicode', method='html', pretty_print=True)
                     for child in body])
            result = "".join(parts)

    # Clean up DOCTYPE if present
    if result.startswith('<!DOCTYPE'):
        result = result.split('>', 1)[1].lstrip()

    # Normalize indentation
    lines = [line.rstrip() for line in result.splitlines() if line.strip()]
    return '\n'.join(lines)

def process_layout(
    layout_html: str,
    rendered_html: str,
    context: Dict[str, Any],
    default_slot_name: str = "main"
) -> str:
    """Process layout template with rendered content and context."""
    try:
        # 1. Validate and parse layout
        validate_layout(layout_html)
        layout = ParsedLayout(parse_html(layout_html), layout_html)
        
        # 2. Extract slots from content
        content = extract_slots(rendered_html)
        slots_to_fill = dict(content.slots)
        
        # 3. Handle default slot
        if default_slot_name not in slots_to_fill and content.main_content:
            main_tree = parse_html(content.main_content)
            slots_to_fill[default_slot_name] = (
                f'<div>{content.main_content}</div>'
                if len(main_tree) > 1
                else content.main_content
            )
        
        # 4. Process layout
        process_conditionals(layout.tree, slots_to_fill, context)
        fill_slots_in_tree(layout.tree, slots_to_fill)
        
        # 5. Format and return result
        return format_output(layout.tree, layout.original)

    except Exception as e:
        if not isinstance(e, SlotError):
            e = SlotError(str(e))
        raise e from None