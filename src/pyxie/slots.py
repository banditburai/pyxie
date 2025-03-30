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

This module manages the process of:
1. Extracting content from rendered HTML fragments based on data-slot attributes
2. Processing conditional visibility using data-if attributes
3. Filling layout templates with the extracted content
4. Handling HTML class merging and attribute preservation

The slot system uses the data-slot attribute to identify both:
- Slot definitions in the rendered content (e.g., <div data-slot="header">)
- Slot targets in the layout template (e.g., <div data-slot="header">)
"""

import logging
from typing import Dict, List, Optional, Tuple, Any

# Use LXML for robust HTML parsing and manipulation
from lxml import etree, html
from lxml.html import HtmlElement

# Import constants/errors from other modules
from .errors import PyxieError
from .parser import RAW_BLOCK_TAGS

# Define standard HTML tags that should NOT be treated as automatic slots
# (Can be customized based on application needs)
STANDARD_HTML_TAGS = {
    'p', 'div', 'span', 'a', 'img', 'br', 'hr', 'strong', 'em', 'code', 'pre',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'blockquote',
    'table', 'thead', 'tbody', 'tr', 'th', 'td', 'form', 'input', 'label',
    'button', 'select', 'option', 'textarea', 'article', 'section', 'aside', 
    'figure', 'figcaption', 'details', 'summary', 'header', 'footer', 'nav',
    'main', 'article', 'section', 'aside', 'figure', 'figcaption', 'details', 'summary',
    # Add other common HTML tags expected in rendered content that aren't slots
}

# Combine sets of tags NOT to treat as slots based on convention
NON_SLOT_TAGS = RAW_BLOCK_TAGS | STANDARD_HTML_TAGS

# Define a specific error for this module
class SlotError(PyxieError):
    """Raised during slot processing failures."""
    pass

logger = logging.getLogger(__name__)

# --- Module Constants ---
SLOT_ATTR: str = "data-slot"
CONDITION_ATTR: str = "data-pyxie-show"  # Changed from data-if to data-pyxie-show
CLASS_ATTR = "class"  # Class attribute name

def merge_html_classes(existing: Optional[str], new: Optional[str]) -> str:
    """Merge HTML class attributes."""
    classes = set()
    if existing:
        classes.update(c.strip() for c in existing.split())
    if new:
        classes.update(c.strip() for c in new.split())
    return ' '.join(sorted(classes))

def extract_slots_from_rendered(rendered_html: str) -> Tuple[str, Dict[str, str]]:
    """Extract slots from rendered HTML content based on data-slot attributes.
    
    Args:
        rendered_html: The rendered HTML content to process
        
    Returns:
        Tuple containing:
        - The main content (content not in slots)
        - Dictionary mapping slot names to their content
    """
    logger.debug(f"Input rendered HTML:\n{rendered_html}")
    slots = {}
    main_content_parts = []

    if not rendered_html.strip():
        return "", slots

    try:
        # Use fragment_fromstring for potentially incomplete HTML
        parser = html.HTMLParser(encoding='utf-8')
        fragment = html.fragment_fromstring(rendered_html, create_parent='div', parser=parser)
        if fragment is None:
            logger.error("LXML failed to parse rendered HTML fragment.")
            return "", {}

        logger.debug(f"Parsed fragment (internal wrapper):\n{etree.tostring(fragment, encoding='unicode')}")

        # Iterate direct children of the fragment (or its body if lxml added one)
        nodes_to_process = fragment.xpath('./* | ./text()[normalize-space()]')

        for element in nodes_to_process:
            logger.debug(f"Processing node: {type(element)}")
            is_slot = False
            if isinstance(element, HtmlElement):
                slot_name = element.get(SLOT_ATTR)
                if slot_name:
                    is_slot = True
                    slot_html = etree.tostring(element, encoding='unicode', method='html')
                    if slot_name in slots:
                        logger.warning(f"Duplicate slot name '{slot_name}' found in rendered content. Using last occurrence.")
                    slots[slot_name] = slot_html
                    logger.debug(f"Extracted slot '{slot_name}' defined by {SLOT_ATTR}")

            if not is_slot:
                # Append non-slot elements or significant text to main content
                if isinstance(element, HtmlElement):
                    main_content_parts.append(etree.tostring(element, encoding='unicode', method='html'))
                elif isinstance(element, etree._ElementUnicodeResult):
                    main_content_parts.append(str(element))

    except (etree.XMLSyntaxError, etree.ParseError) as parse_err:
        logger.error("LXML failed to parse rendered HTML fragment for slot extraction: %s", parse_err)
        raise ValueError(f"Cannot parse rendered HTML fragment: {parse_err}") from parse_err
    except Exception as e:
        logger.error("Unexpected error during slot extraction: %s", e, exc_info=True)
        raise SlotError(f"Unexpected error extracting slots: {e}") from e

    main_content_str = "\n".join(main_content_parts).strip()
    logger.debug(f"Final main content:\n{main_content_str}")
    logger.debug(f"Extracted slots by attribute: {list(slots.keys())}")
    return main_content_str, slots

def _check_visibility_condition(condition_key: str, context: Dict[str, Any]) -> bool:
    """Checks a single visibility condition key against the context.
    
    The condition is considered true if:
    1. The key exists in context and its value is truthy, OR
    2. The key exists in slots (via context) and has non-empty content
    
    If the condition is negated (starts with '!'), the result is inverted.
    """
    is_negated = condition_key.startswith('!')
    key = condition_key[1:] if is_negated else condition_key
    
    if not key:
        return True
    
    # Check if key exists in context and is truthy
    key_exists_and_true = key in context and bool(context[key])
    
    # If key doesn't exist in context or is falsy, check if it's a slot with content
    if not key_exists_and_true:
        # Slots with content are added to context with value True
        key_exists_and_true = key in context
    
    result = not key_exists_and_true if is_negated else key_exists_and_true
    logger.debug("Condition '%s' evaluated to %s (key: '%s', exists_and_true: %s)", 
                condition_key, result, key, key_exists_and_true)
    return result

def process_conditionals(layout_tree: etree._Element, context: Dict[str, Any]):
    """Process elements with conditional visibility attributes."""
    elements_to_remove = []
    for element in layout_tree.xpath(f'//*[@{CONDITION_ATTR}]'):
        condition_str = element.get(CONDITION_ATTR, "").strip()
        if not condition_str:
            continue
        if not _check_visibility_condition(condition_str, context):
            elements_to_remove.append(element)

    for element in elements_to_remove:
        parent = element.getparent()
        if parent is not None:
            log_tag = f"{element.tag}[@{CONDITION_ATTR}='{element.get(CONDITION_ATTR)}']"
            logger.debug("Removing element %s due to false condition", log_tag)
            # Store tail text before removal
            tail_text = element.tail
            # Remove the element
            parent.remove(element)
            # If there was tail text, add it to the parent's text
            if tail_text and tail_text.strip():
                if parent.text:
                    parent.text = parent.text + tail_text
                else:
                    parent.text = tail_text

def fill_layout_slots(layout_tree: etree._Element, slots_content: Dict[str, str]):
    """
    Fills elements with data-slot attributes in the layout_tree with provided HTML content.
    Modifies the layout_tree in-place.
    """
    logger.debug(f"Attempting to fill slots in layout. Available slots: {list(slots_content.keys())}")

    # Find placeholders in the layout using SLOT_ATTR ('data-slot')
    slot_placeholders = layout_tree.xpath(f'//*[@{SLOT_ATTR}]')
    logger.debug(f"Found {len(slot_placeholders)} slot placeholders in layout.")

    # Track elements to remove (empty slots)
    elements_to_remove = []

    for placeholder in slot_placeholders:
        slot_name = placeholder.get(SLOT_ATTR)
        if not slot_name:
            continue

        logger.debug(f"Processing layout slot target: '{slot_name}'")

        if slot_name in slots_content:
            slot_html = slots_content[slot_name]
            logger.debug(f"Found content for slot '{slot_name}' (length {len(slot_html)})")

            # Clear existing placeholder content (text and children)
            placeholder.text = None
            for child in list(placeholder):
                placeholder.remove(child)

            # Parse the new slot content HTML and insert it
            try:
                if slot_html.strip():
                    # Use fragment_fromstring again, safer for arbitrary HTML
                    parser = html.HTMLParser(encoding='utf-8')
                    content_fragment = html.fragment_fromstring(slot_html, create_parent='div', parser=parser)

                    # Get the first element from the fragment (the actual slot content)
                    content_element = content_fragment[0] if len(content_fragment) > 0 else None

                    # Merge classes from placeholder and content, ensuring layout classes come first
                    if content_element is not None:
                        placeholder_classes = placeholder.get(CLASS_ATTR, '')
                        content_classes = content_element.get(CLASS_ATTR, '')
                        # Ensure layout classes come first
                        merged_classes = merge_html_classes(placeholder_classes, content_classes)
                        placeholder.set(CLASS_ATTR, merged_classes)

                        # Transfer text/tail/children from the parsed fragment's dummy parent
                        if content_fragment.text and content_fragment.text.strip():
                            placeholder.text = (placeholder.text or '') + content_fragment.text
                        for child_node in content_fragment:
                            placeholder.append(child_node)
                else:
                    logger.debug("Slot '%s' content is empty. Marking for removal.", slot_name)
                    elements_to_remove.append(placeholder)

            except (etree.XMLSyntaxError, etree.ParseError) as parse_err:
                logger.warning("LXML failed to parse HTML for slot '%s', inserting as escaped text. Error: %s", slot_name, parse_err)
                placeholder.text = f"<!-- Error parsing slot content: {html.escape(str(parse_err))} -->"
            except Exception as e:
                logger.error("Unexpected error processing slot '%s' content: %s", slot_name, e, exc_info=True)
                placeholder.text = f"<!-- Error inserting slot content: {html.escape(str(e))} -->"
        else:
            logger.debug("Slot target '%s' in layout but no matching content provided. Marking for removal.", slot_name)
            elements_to_remove.append(placeholder)

        # Remove the data-slot attribute after processing
        placeholder.attrib.pop(SLOT_ATTR, None)

    # Remove empty slots, preserving tail text
    for element in elements_to_remove:
        parent = element.getparent()
        if parent is not None:
            # Store tail text before removal
            tail_text = element.tail
            # Remove the element
            parent.remove(element)
            # If there was tail text, add it to the parent's text
            if tail_text and tail_text.strip():
                if parent.text:
                    parent.text = parent.text + tail_text
                else:
                    parent.text = tail_text

def process_layout(
    layout_html: str,
    rendered_html: str,
    context: Dict[str, Any],
    default_slot_name: str = "main"
) -> str:
    """
    Orchestrates layout processing: slot extraction (via 'data-slot'),
    conditional processing, and slot filling.

    Args:
        layout_html: The raw HTML string for the layout template.
        rendered_html: The HTML fragment rendered from the Markdown source.
        context: Dictionary containing metadata (from frontmatter) for conditionals.
        default_slot_name: Name for the slot containing content not extracted.

    Returns:
        The final processed HTML fragment string for the page.
    Raises:
        SlotError: If layout parsing or processing fails significantly.
        ValueError: If the rendered fragment cannot be parsed.
    """
    logger.info("Starting layout processing.")
    try:
        # 1. Extract slots based on 'data-slot' attribute in the rendered fragment
        main_content, extracted_slots = extract_slots_from_rendered(rendered_html)

        # 2. Prepare the final dictionary of slots to fill
        slots_to_fill = extracted_slots.copy()
        if default_slot_name in slots_to_fill:
            if main_content:
                logger.warning("Default slot name '%s' conflicts with an extracted slot. Main content ignored.", default_slot_name)
        else:
            slots_to_fill[default_slot_name] = main_content
        logger.debug("Prepared slots for filling: %s", list(slots_to_fill.keys()))

        # 3. Parse the layout HTML
        try:
            parser = html.HTMLParser(encoding='utf-8')
            layout_tree = html.fromstring(layout_html, parser=parser)
        except (etree.XMLSyntaxError, etree.ParseError) as parse_err:
            raise SlotError(f"Layout Parsing Failed: {parse_err}") from parse_err

        # 4. Fill slots (modifies layout_tree in place)
        fill_layout_slots(layout_tree, slots_to_fill)

        # 5. Add slot existence information to context for conditionals
        context_with_slots = context.copy()
        for slot_name in slots_to_fill:
            context_with_slots[slot_name] = bool(slots_to_fill[slot_name])

        # 6. Process conditional visibility (modifies layout_tree in place)
        process_conditionals(layout_tree, context_with_slots)

        # 7. Serialize the final tree back to HTML FRAGMENT string
        try:
            # Get the final HTML
            final_html = etree.tostring(layout_tree, encoding='unicode', method='html')
            
            # Handle cases where lxml added html/body wrappers
            root_tag = layout_tree.tag.lower() if hasattr(layout_tree, 'tag') else ''
            
            if root_tag == 'html' and not layout_html.strip().lower().startswith('<html'):
                # Extract content from body if it exists
                body = layout_tree.find('.//body')
                if body is not None:
                    inner_parts = []
                    if body.text and body.text.strip():
                        inner_parts.append(body.text)
                    for child in body:
                        inner_parts.append(etree.tostring(child, encoding='unicode', method='html'))
                    final_html = "".join(inner_parts)
                else:
                    logger.warning("Serialized tree has <html> but no <body> found, returning full tree.")
            
            # Remove doctype if present
            if final_html.startswith('<!DOCTYPE'):
                final_html = final_html.split('>', 1)[1].lstrip()

            logger.info("Layout processing finished. Returning final HTML fragment.")
            return final_html.strip()

        except Exception as e:
            raise SlotError(f"Serialization Failed: {e}") from e

    except Exception as e:
        logger.error("Layout processing failed: %s", e, exc_info=True)
        raise SlotError(f"Layout processing failed: {e}") from e