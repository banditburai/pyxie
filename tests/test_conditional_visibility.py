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

from pyxie.renderer import process_conditional_visibility, PYXIE_SHOW_ATTR


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