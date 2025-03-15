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
from typing import Dict, List, Optional, Final, Tuple, Iterator
from dataclasses import dataclass
from lxml import html, etree
from lxml.html import HtmlElement
from fastcore.xml import FT, to_xml

from .errors import PyxieError
from .utilities import log, merge_html_classes, parse_html_fragment

__all__ = ['fill_slots', 'SlotError', 'SlotFillResult']

logger = logging.getLogger(__name__)

# Constants
SLOT_ATTR: Final[str] = 'data-slot'
CLASS_ATTR: Final[str] = 'class'

@dataclass
class SlotFillResult:
    """Result of filling slots with content."""
    was_filled: bool
    element: str
    error: Optional[str] = None

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
    
    # Convert to list for iteration
    for child in list(element):
        remove_slot_attributes(child)

def process_single_slot(slot: etree._Element, content: str, original_attrs: Dict[str, str]) -> None:
    """Process a single slot with its content."""
    content_elem = parse_html_fragment(content)
    remove_slot_attributes(content_elem)
    
    slot.clear()
    slot_attrs = original_attrs.copy()
    if SLOT_ATTR in slot_attrs:
        del slot_attrs[SLOT_ATTR]
    
    if content_classes := content_elem.get(CLASS_ATTR):
        slot_attrs[CLASS_ATTR] = merge_html_classes(slot_attrs.get(CLASS_ATTR), content_classes)
    
    for key, value in slot_attrs.items():
        slot.set(key, value)
    
    if content_elem.tag == 'div':
        slot.text = content_elem.text        
        # Convert to list for iteration
        for child in list(content_elem):
            slot.append(child)
    else:
        slot.append(content_elem)

def create_slot_copy(original_slot: etree._Element) -> etree._Element:
    """Create a deep copy of a slot element."""
    return html.fromstring(html.tostring(original_slot))

def duplicate_slots(parent_elem: etree._Element, original_slot: etree._Element, contents: List[str]) -> None:
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
        
    prev = slot.getprevious()
    if prev is not None:
        prev.tail = (prev.tail or '') + slot.tail
    else:
        parent.text = (parent.text or '') + slot.tail

def remove_empty_slots(slots_to_remove: List[etree._Element]) -> None:
    """Remove slots with no content, preserving tail text."""
    for slot in filter(lambda s: s.getparent() is not None, slots_to_remove):
        parent = slot.getparent()
        handle_slot_tail_text(slot, parent)
        parent.remove(slot)
        log(logger, "Slots", "debug", "remove", "Removed empty slot")

def find_slots(root: HtmlElement) -> Iterator[etree._Element]:
    """Find all elements with data-slot attribute."""
    return root.xpath(f'//*[@{SLOT_ATTR}]')

def process_slot_content(slot: etree._Element, content_blocks: List[str], 
                         slots_to_duplicate: Dict[etree._Element, Tuple[etree._Element, List[str]]]) -> Optional[str]:
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

def identify_slots(root: HtmlElement, blocks: Dict[str, List[str]]) -> Tuple[
        List[etree._Element], Dict[etree._Element, Tuple[etree._Element, List[str]]], Optional[str]]:
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

def extract_layout_root(layout: str | FT) -> HtmlElement:
    """Convert layout to HTML and extract root element."""
    return html.fromstring(ensure_layout_string(layout))

def create_success_result(root: HtmlElement) -> SlotFillResult:
    """Create a successful result from the processed HTML."""
    result = html.tostring(root, encoding='unicode', method='html', with_tail=False)
    return SlotFillResult(True, result)

def create_error_result(layout: str | FT, error: Exception) -> SlotFillResult:
    """Create an error result with the original layout."""
    error_msg = f"Failed to fill slots: {error}"
    log(logger, "Slots", "error", "fill", error_msg)
    return SlotFillResult(False, ensure_layout_string(layout), error_msg)

def process_layout(root: HtmlElement, blocks: Dict[str, List[str]]) -> SlotFillResult:
    """Process layout by identifying and filling slots."""
    slots_to_remove, slots_to_duplicate, error = identify_slots(root, blocks)
    
    if error:
        return SlotFillResult(False, "", error)
    
    for slot, (parent, contents) in slots_to_duplicate.items():
        duplicate_slots(parent, slot, contents)
        
    remove_empty_slots(slots_to_remove)
    
    return create_success_result(root)

def fill_slots(layout: str | FT, blocks: Dict[str, List[str]]) -> SlotFillResult:
    """Fill slots in a layout with rendered content."""
    try:
        root = extract_layout_root(layout)
        if root is None:
            return create_error_result(layout, ValueError("Failed to extract layout root element"))
            
        return process_layout(root, blocks)
    except Exception as e:
        return create_error_result(layout, e)