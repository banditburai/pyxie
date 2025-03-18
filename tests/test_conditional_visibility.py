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

"""Test conditional visibility with data-pyxie-show attributes."""

import pytest
from lxml import html, etree

from pyxie.renderer import process_conditional_visibility, PYXIE_SHOW_ATTR, check_visibility_condition


def test_process_conditional_visibility_single_slot():
    """Test conditional visibility with a single slot."""
    # HTML with conditional elements
    html_content = f"""
    <div>
        <h2 {PYXIE_SHOW_ATTR}="toc">Table of Contents</h2>
        <p {PYXIE_SHOW_ATTR}="sidebar">Sidebar content</p>
        <footer>Always visible</footer>
    </div>
    """
    
    # Test when all slots are filled
    result = process_conditional_visibility(html_content, {"toc", "sidebar"})
    doc = html.fromstring(result)
    
    assert len(doc.xpath(f'//h2[@{PYXIE_SHOW_ATTR}="toc"]')) == 1
    assert "display: none" not in doc.xpath(f'//h2[@{PYXIE_SHOW_ATTR}="toc"]')[0].get("style", "")
    
    assert len(doc.xpath(f'//p[@{PYXIE_SHOW_ATTR}="sidebar"]')) == 1
    assert "display: none" not in doc.xpath(f'//p[@{PYXIE_SHOW_ATTR}="sidebar"]')[0].get("style", "")
    
    # Test when one slot is empty
    result = process_conditional_visibility(html_content, {"toc"})
    doc = html.fromstring(result)
    
    assert len(doc.xpath(f'//h2[@{PYXIE_SHOW_ATTR}="toc"]')) == 1
    assert "display: none" not in doc.xpath(f'//h2[@{PYXIE_SHOW_ATTR}="toc"]')[0].get("style", "")
    
    assert len(doc.xpath(f'//p[@{PYXIE_SHOW_ATTR}="sidebar"]')) == 1
    assert "display: none" in doc.xpath(f'//p[@{PYXIE_SHOW_ATTR}="sidebar"]')[0].get("style", "")
    
    # Test when all slots are empty
    result = process_conditional_visibility(html_content, {"other"})
    doc = html.fromstring(result)
    
    assert len(doc.xpath(f'//h2[@{PYXIE_SHOW_ATTR}="toc"]')) == 1
    assert "display: none" in doc.xpath(f'//h2[@{PYXIE_SHOW_ATTR}="toc"]')[0].get("style", "")
    
    assert len(doc.xpath(f'//p[@{PYXIE_SHOW_ATTR}="sidebar"]')) == 1
    assert "display: none" in doc.xpath(f'//p[@{PYXIE_SHOW_ATTR}="sidebar"]')[0].get("style", "")


def test_process_conditional_visibility_multiple_slots():
    """Test conditional visibility with multiple slots (OR logic)."""
    # HTML with OR conditional visibility
    html_content = f"""
    <div>
        <h2 {PYXIE_SHOW_ATTR}="toc,sidebar">Navigation Elements</h2>
        <p {PYXIE_SHOW_ATTR}="related,comments">User Content</p>
    </div>
    """
    
    # Test with the first slot filled
    result = process_conditional_visibility(html_content, {"toc", "related"})
    doc = html.fromstring(result)
    
    assert len(doc.xpath(f'//h2[@{PYXIE_SHOW_ATTR}="toc,sidebar"]')) == 1
    assert "display: none" not in doc.xpath(f'//h2[@{PYXIE_SHOW_ATTR}="toc,sidebar"]')[0].get("style", "")
    
    assert len(doc.xpath(f'//p[@{PYXIE_SHOW_ATTR}="related,comments"]')) == 1
    assert "display: none" not in doc.xpath(f'//p[@{PYXIE_SHOW_ATTR}="related,comments"]')[0].get("style", "")
    
    # Test with the second slot filled
    result = process_conditional_visibility(html_content, {"sidebar", "comments"})
    doc = html.fromstring(result)
    
    assert len(doc.xpath(f'//h2[@{PYXIE_SHOW_ATTR}="toc,sidebar"]')) == 1
    assert "display: none" not in doc.xpath(f'//h2[@{PYXIE_SHOW_ATTR}="toc,sidebar"]')[0].get("style", "")
    
    assert len(doc.xpath(f'//p[@{PYXIE_SHOW_ATTR}="related,comments"]')) == 1
    assert "display: none" not in doc.xpath(f'//p[@{PYXIE_SHOW_ATTR}="related,comments"]')[0].get("style", "")
    
    # Test with none of the slots filled
    result = process_conditional_visibility(html_content, {"other"})
    doc = html.fromstring(result)
    
    assert len(doc.xpath(f'//h2[@{PYXIE_SHOW_ATTR}="toc,sidebar"]')) == 1
    assert "display: none" in doc.xpath(f'//h2[@{PYXIE_SHOW_ATTR}="toc,sidebar"]')[0].get("style", "")
    
    assert len(doc.xpath(f'//p[@{PYXIE_SHOW_ATTR}="related,comments"]')) == 1
    assert "display: none" in doc.xpath(f'//p[@{PYXIE_SHOW_ATTR}="related,comments"]')[0].get("style", "")


def test_process_conditional_visibility_with_existing_style():
    """Test conditional visibility when elements already have style attributes."""
    # HTML with conditional elements that have existing styles
    html_content = f"""
    <div>
        <h2 {PYXIE_SHOW_ATTR}="toc" style="color: blue;">Table of Contents</h2>
        <p {PYXIE_SHOW_ATTR}="sidebar" style="margin-top: 10px;">Sidebar content</p>
    </div>
    """
    
    # Test with no slots filled
    result = process_conditional_visibility(html_content, set())
    doc = html.fromstring(result)
    
    h2_style = doc.xpath(f'//h2[@{PYXIE_SHOW_ATTR}="toc"]')[0].get("style", "")
    assert "color: blue" in h2_style
    assert "display: none" in h2_style
    
    p_style = doc.xpath(f'//p[@{PYXIE_SHOW_ATTR}="sidebar"]')[0].get("style", "")
    assert "margin-top: 10px" in p_style
    assert "display: none" in p_style


def test_process_conditional_visibility_error_handling():
    """Test error handling in conditional visibility processing."""
    # Use something that will cause an XMLSyntaxError
    invalid_html = "<<<>>>"
    
    # Should gracefully handle the error
    result = process_conditional_visibility(invalid_html, {"toc"})
    # Just ensure no exception is raised and some result is returned
    assert isinstance(result, str)
    
    # Test with a simpler mock approach
    def mock_fromstring(text):
        """Mock function that always raises an exception."""
        raise etree.XMLSyntaxError("test error", None, 0, 0)
    
    # Store the original function and replace it
    original_fromstring = html.fromstring
    html.fromstring = mock_fromstring
    
    try:
        # Process should not raise an exception and return original HTML
        test_html = "<div>test</div>"
        result = process_conditional_visibility(test_html, {"toc"})
        assert result == test_html
    finally:
        # Restore the original function
        html.fromstring = original_fromstring 


def test_process_conditional_visibility_negation():
    """Test conditional visibility with negation operator."""
    from pyxie.renderer import process_conditional_visibility
    
    # HTML with negation condition
    html = '<div><p data-pyxie-show="!optional">Show when optional is not present</p><p data-pyxie-show="required">Show when required is present</p></div>'
    
    # Test when optional slot is NOT present (negation condition should show)
    filled_slots = {"required"}
    result = process_conditional_visibility(html, filled_slots)
    assert 'Show when optional is not present' in result
    assert 'Show when required is present' in result
    assert 'display: none' not in result  # Both conditions met, nothing hidden
    
    # Test when optional slot IS present (negation condition should hide)
    filled_slots = {"required", "optional"}
    result = process_conditional_visibility(html, filled_slots)
    assert 'display: none' in result  # Negation condition not met
    assert 'Show when required is present' in result  # Normal condition met


def test_process_conditional_visibility_complex_conditions():
    """Test conditional visibility with complex conditions combining normal and negated slots."""
    from pyxie.renderer import check_visibility_condition
    
    # Test the check_visibility_condition function directly with various combinations
    # Basic checks
    assert check_visibility_condition(["!missing"], {"present"}) == True
    assert check_visibility_condition(["!present"], {"present"}) == False
    assert check_visibility_condition(["present", "!missing"], {"present"}) == True
    assert check_visibility_condition(["missing", "!present"], {"present"}) == False
    
    # Complex combinations with multiple slots
    test_cases = [
        # slot_names, filled_slots, expected_result
        (["header", "!footer"], {"header"}, True),               # header=yes, footer=no
        (["header", "!footer"], {"header", "footer"}, True),     # header=yes, footer=yes (OR logic)
        (["content", "!sidebar"], {"content", "sidebar"}, True), # content=yes, sidebar=yes (OR logic)
        (["content", "!sidebar"], {"sidebar"}, False),           # content=no, sidebar=yes
        (["header", "content"], {"footer"}, False),              # neither slot is present
        (["!header", "!footer"], {"content"}, True),             # negated slots, neither is present
        (["!header", "!footer"], {"header", "footer"}, False),   # negated slots, both are present
    ]
    
    for slot_names, filled_slots, expected_result in test_cases:
        result = check_visibility_condition(slot_names, filled_slots)
        assert result == expected_result, f"Failed with slot_names={slot_names}, filled_slots={filled_slots}"


def test_process_conditional_visibility_whitespace_handling():
    """Test conditional visibility with whitespace and complex formatting in attributes."""
    # HTML with spaces and varied formatting in the data-pyxie-show attributes
    html_content = f"""
    <div>
        <h2 {PYXIE_SHOW_ATTR}=" toc , sidebar ">Spaced values</h2>
        <p {PYXIE_SHOW_ATTR}="  !featured_image  ,   related  ">Mixed negation with spaces</p>
        <div {PYXIE_SHOW_ATTR}="header,  !footer,  content  ">Multiple conditions with varied spacing</div>
    </div>
    """
    
    # Test with specific slots filled
    filled_slots = {"toc", "related", "content"}
    result = process_conditional_visibility(html_content, filled_slots)
    doc = html.fromstring(result)
    
    # All elements should be visible since their conditions are met
    assert len(doc.xpath(f'//h2[@{PYXIE_SHOW_ATTR}=" toc , sidebar "]')) == 1
    assert "display: none" not in doc.xpath(f'//h2[@{PYXIE_SHOW_ATTR}=" toc , sidebar "]')[0].get("style", "")
    
    assert len(doc.xpath(f'//p[@{PYXIE_SHOW_ATTR}="  !featured_image  ,   related  "]')) == 1
    assert "display: none" not in doc.xpath(f'//p[@{PYXIE_SHOW_ATTR}="  !featured_image  ,   related  "]')[0].get("style", "")
    
    assert len(doc.xpath(f'//div[@{PYXIE_SHOW_ATTR}="header,  !footer,  content  "]')) == 1
    assert "display: none" not in doc.xpath(f'//div[@{PYXIE_SHOW_ATTR}="header,  !footer,  content  "]')[0].get("style", "")
    
    # Test with different slots filled that should trigger some hiding
    filled_slots = {"sidebar", "featured_image", "footer"}
    result = process_conditional_visibility(html_content, filled_slots)
    doc = html.fromstring(result)
    
    # First element should be visible (sidebar is filled)
    assert "display: none" not in doc.xpath(f'//h2[@{PYXIE_SHOW_ATTR}=" toc , sidebar "]')[0].get("style", "")
    
    # Second element should be hidden (featured_image is filled, negating !featured_image, and related is not filled)
    assert "display: none" in doc.xpath(f'//p[@{PYXIE_SHOW_ATTR}="  !featured_image  ,   related  "]')[0].get("style", "")
    
    # Third element should be hidden (header not filled, !footer negated by footer being filled, content not filled)
    assert "display: none" in doc.xpath(f'//div[@{PYXIE_SHOW_ATTR}="header,  !footer,  content  "]')[0].get("style", "") 