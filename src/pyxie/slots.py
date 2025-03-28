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

"""Handle slot filling for layouts and content blocks.
"""

import logging
from typing import TypeAlias, TypeVar, Sequence
from collections.abc import Iterator
from dataclasses import dataclass, field
from lxml import html, etree
from lxml.html import HtmlElement
from fastcore.xml import FT, to_xml

from .errors import PyxieError
from .utilities import log, merge_html_classes, parse_html_fragment

__all__ = ['fill_slots', 'SlotError', 'SlotFillResult']

logger = logging.getLogger(__name__)

# Type definitions
HtmlAttrs: TypeAlias = dict[str, str]
SlotBlocks: TypeAlias = dict[str, list[str]]
SlotContent = TypeVar('SlotContent', str, bool)

# Constants
SLOT_ATTR: str = 'data-slot'
CLASS_ATTR: str = 'class'
PYXIE_SHOW_ATTR: str = 'data-pyxie-show'

@dataclass(frozen=True)
class SlotFillResult:
    """Result of filling slots with content."""
    was_filled: bool
    element: str
    error: str | None = None
    
    @classmethod
    def success(cls, element: str) -> 'SlotFillResult':
        """Create a successful result."""
        return cls(True, element)
    
    @classmethod
    def failure(cls, error: str) -> 'SlotFillResult':
        """Create a failure result."""
        return cls(False, "", error)

class SlotError(PyxieError):
    """Raised when slot filling fails."""
    def __init__(self, slot_name: str, message: str):
        super().__init__(f"Error in slot '{slot_name}': {message}")
        self.slot_name = slot_name

def ensure_layout_string(layout: str | FT) -> str:
    """Ensure layout is a string, converting from FT if needed."""
    return to_xml(layout) if isinstance(layout, FT) else layout

def remove_slot_attributes(element: etree._Element) -> None:
    """Remove data-slot attributes from element tree."""
    if hasattr(element, 'attrib') and SLOT_ATTR in element.attrib:
        del element.attrib[SLOT_ATTR]
    
    for child in element.getchildren():
        remove_slot_attributes(child)

def process_single_slot(slot: etree._Element, content: str, attrs: HtmlAttrs) -> None:
    """Process a single slot with its content."""
    content_elem = parse_html_fragment(content)
    remove_slot_attributes(content_elem)
    
    # Clear and update slot
    slot.clear()
    slot_attrs = {k: v for k, v in attrs.items() if k != SLOT_ATTR}
    
    # Merge classes if present
    if classes := content_elem.get(CLASS_ATTR):
        content_classes = set(classes.split())
        if content_classes:
            slot_attrs[CLASS_ATTR] = merge_html_classes(slot_attrs.get(CLASS_ATTR), ' '.join(content_classes))
    
    # Update attributes
    slot.attrib.update(slot_attrs)
    
    # Add content
    if content_elem.tag == 'div':
        slot.text = content_elem.text
        for child in content_elem.getchildren():
            slot.append(child)
    else:
        # For non-div elements, preserve the original tag
        slot.tag = content_elem.tag
        slot.text = content_elem.text
        for child in content_elem.getchildren():
            slot.append(child)
        
    # Unescape any escaped custom tags in text and tail
    for elem in slot.iter():
        if elem.text and '&lt;' in elem.text:
            elem.text = elem.text.replace('&lt;', '<').replace('&gt;', '>')
        if elem.tail and '&lt;' in elem.tail:
            elem.tail = elem.tail.replace('&lt;', '<').replace('&gt;', '>')

def create_slot_copy(original_slot: etree._Element) -> etree._Element:
    """Create a deep copy of a slot element."""
    return html.fromstring(html.tostring(original_slot))

def duplicate_slots(parent_elem: etree._Element, original_slot: etree._Element, contents: list[str]) -> None:
    """Process slots with multiple content blocks."""
    for i, content in enumerate(contents[1:], 1):
        try:
            new_slot = create_slot_copy(original_slot)
            process_single_slot(new_slot, content, dict(original_slot.attrib))
            
            slot_index = parent_elem.index(original_slot)
            parent_elem.insert(slot_index + i, new_slot)
            log(logger, "Slots", "debug", "duplicate", f"Created additional slot instance #{i+1}")
        except Exception as e:
            log(logger, "Slots", "error", "duplicate", f"Failed to duplicate slot: {e}")

def handle_slot_tail_text(slot: etree._Element, parent: etree._Element) -> None:
    """Handle preservation of tail text when removing a slot."""
    if not (slot.tail and slot.tail.strip()):
        return
        
    if prev := slot.getprevious():
        prev.tail = (prev.tail or '') + slot.tail
    else:
        parent.text = (parent.text or '') + slot.tail

def remove_empty_slots(slots_to_remove: list[etree._Element]) -> None:
    """Remove slots with no content, preserving tail text."""
    for slot in filter(lambda s: s.getparent() is not None, slots_to_remove):
        parent = slot.getparent()
        handle_slot_tail_text(slot, parent)
        parent.remove(slot)
        log(logger, "Slots", "debug", "remove", "Removed empty slot")

def find_slots(root: HtmlElement) -> Iterator[etree._Element]:
    """Find all elements with data-slot attribute."""
    return root.xpath(f'//*[@{SLOT_ATTR}]')

def process_slot_content(
    slot: etree._Element, 
    content_blocks: list[str], 
    slots_to_duplicate: dict[etree._Element, tuple[etree._Element, list[str]]]
) -> str | None:
    """Process content for a single slot."""
    original_attrs = dict(slot.attrib)
    
    if len(content_blocks) > 1:
        parent = slot.getparent()
        if parent is not None:
            slots_to_duplicate[slot] = (parent, content_blocks)
    
    try:
        process_single_slot(slot, content_blocks[0], original_attrs)
        return None
    except Exception as e:
        slot_name = slot.get(SLOT_ATTR)
        error = f"Failed to process slot '{slot_name}': {e}"
        log(logger, "Slots", "error", "process", error)
        return error

def identify_slots(
    root: HtmlElement, 
    blocks: SlotBlocks
) -> tuple[list[etree._Element], dict[etree._Element, tuple[etree._Element, list[str]]], str | None]:
    """Identify slots to remove, duplicate, and check for errors."""
    slots_to_remove = []
    slots_to_duplicate = {}
    
    for slot in find_slots(root):
        slot_name = slot.get(SLOT_ATTR)
        
        if slot_name not in blocks or not blocks[slot_name]:
            slots_to_remove.append(slot)
            continue
            
        content_blocks = blocks[slot_name]
        if error := process_slot_content(slot, content_blocks, slots_to_duplicate):
            return [], {}, error
    
    return slots_to_remove, slots_to_duplicate, None

def extract_layout_root(layout: str | FT) -> HtmlElement | None:
    """Convert layout to HTML and extract root element."""
    return html.fromstring(ensure_layout_string(layout))

def process_layout(root: HtmlElement, blocks: SlotBlocks) -> SlotFillResult:
    """Process layout by identifying and filling slots."""
    slots_to_remove, slots_to_duplicate, error = identify_slots(root, blocks)
    
    if error:
        return SlotFillResult.failure(error)
    
    for slot, (parent, contents) in slots_to_duplicate.items():
        duplicate_slots(parent, slot, contents)
        
    remove_empty_slots(slots_to_remove)
    
    result = html.tostring(root, encoding='unicode', method='html', with_tail=False)
    return SlotFillResult.success(result)

def fill_slots(layout: str | FT, blocks: SlotBlocks) -> SlotFillResult:
    """Fill slots in a layout with rendered content."""
    try:
        root = extract_layout_root(layout)
        if root is None:
            return SlotFillResult.failure("Failed to extract layout root element")
            
        return process_layout(root, blocks)
    except Exception as e:
        return SlotFillResult.failure(str(e))

def check_visibility_condition(slot_names: Sequence[str], filled_slots: set[str]) -> bool:
    """Check if element should be visible based on slot conditions."""
    if not slot_names:
        return True
    
    slots = [s.strip() for s in slot_names if s.strip()]
    negative_slots = {s[1:].strip() for s in slots if s.startswith('!')}
    positive_slots = {s for s in slots if not s.startswith('!')}
    
    # Hide if any negative condition matches
    if negative_slots & filled_slots:
        return False
        
    # Show if no positive conditions or any positive condition matches
    return not positive_slots or bool(positive_slots & filled_slots)

def build_visible_tree(element: html.HtmlElement, filled_slots: set[str]) -> html.HtmlElement | None:
    """Build a new tree with only visible elements.
    
    Args:
        element: Root element to process
        filled_slots: Set of filled slot names
        
    Returns:
        New tree with only visible elements, or None if element should be hidden
    """
    # Check if element has visibility condition
    if PYXIE_SHOW_ATTR in element.attrib:
        condition = element.attrib[PYXIE_SHOW_ATTR]
        if not check_visibility_condition(condition.split(','), filled_slots):
            return None
    
    # Process children
    for child in element.getchildren():
        processed_child = build_visible_tree(child, filled_slots)
        if processed_child is None:
            element.remove(child)
    
    return element

def process_conditional_visibility(layout_html: str, filled_slots: set[str]) -> str:
    """Process conditional visibility in layout HTML.
    
    Args:
        layout_html: Layout HTML string
        filled_slots: Set of filled slot names
        
    Returns:
        Processed HTML with conditional elements handled
    """
    try:
        root = html.fromstring(layout_html)
        processed_root = build_visible_tree(root, filled_slots)
        if processed_root is not None:
            return html.tostring(processed_root, encoding='unicode', pretty_print=True)
        return layout_html
    except Exception as e:
        log(logger, "Slots", "error", "visibility", f"Failed to process conditional visibility: {e}")
        return layout_html

def process_slots_and_visibility(
    layout: str | FT, 
    blocks: dict[str, SlotContent]
) -> SlotFillResult:
    """Process layout by handling conditional visibility and filling slots."""
    try:
        root = extract_layout_root(layout)
        if root is None:
            return SlotFillResult.failure("Failed to extract layout root element")
        
        # Process visibility and slots
        filled_slots = {name for name, content in blocks.items() if bool(content)}
        html_str = html.tostring(root, encoding='unicode')
        processed = process_conditional_visibility(html_str, filled_slots)
        
        # Convert string content blocks to lists and preserve slot classes
        list_blocks = {}
        for name, content in blocks.items():
            if isinstance(content, str):
                # Find the slot element in the layout
                slot_elem = root.find(f'.//*[@{SLOT_ATTR}="{name}"]')
                if slot_elem is not None:
                    # Create a div with the slot's class and add the content
                    slot_class = slot_elem.get('class')
                    if slot_class:
                        list_blocks[name] = [f'<div class="{slot_class}">{content}</div>']
                    else:
                        list_blocks[name] = [str(content)]
                else:
                    list_blocks[name] = [str(content)]
        
        return fill_slots(processed, list_blocks)
        
    except Exception as e:
        return SlotFillResult.failure(str(e))