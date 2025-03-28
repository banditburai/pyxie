"""Tests for conditional visibility with data-pyxie-show attributes."""

from lxml import html, etree

from pyxie.slots import process_conditional_visibility, PYXIE_SHOW_ATTR, check_visibility_condition


def test_process_conditional_visibility_single_slot():
    """Test conditional visibility with a single slot."""
    # HTML with conditional elements
    html_content = f'<div><h2 {PYXIE_SHOW_ATTR}="toc">Table of Contents</h2><p {PYXIE_SHOW_ATTR}="sidebar">Sidebar content</p><footer>Always visible</footer></div>'
    
    # Test when all slots are filled
    result = process_conditional_visibility(html_content, {"toc", "sidebar"})
    doc = html.fromstring(result)
    
    # Both elements should be present
    assert len(doc.xpath(f'//h2[@{PYXIE_SHOW_ATTR}="toc"]')) == 1
    assert len(doc.xpath(f'//p[@{PYXIE_SHOW_ATTR}="sidebar"]')) == 1
    assert "Table of Contents" in result
    assert "Sidebar content" in result
    
    # Test when one slot is empty
    result = process_conditional_visibility(html_content, {"toc"})
    doc = html.fromstring(result)
    
    # Only toc element should be present
    assert len(doc.xpath(f'//h2[@{PYXIE_SHOW_ATTR}="toc"]')) == 1
    assert len(doc.xpath(f'//p[@{PYXIE_SHOW_ATTR}="sidebar"]')) == 0
    assert "Table of Contents" in result
    assert "Sidebar content" not in result
    assert "Always visible" in result


def test_process_conditional_visibility_multiple_slots():
    """Test conditional visibility with multiple slots (OR logic)."""
    # HTML with OR conditional visibility
    html_content = f'<div><h2 {PYXIE_SHOW_ATTR}="toc,sidebar">Navigation Elements</h2><p {PYXIE_SHOW_ATTR}="related,comments">User Content</p></div>'
    
    # Test with the first slot filled
    result = process_conditional_visibility(html_content, {"toc", "related"})
    doc = html.fromstring(result)
    
    # Both elements should be present (each has one matching slot)
    assert len(doc.xpath(f'//h2[@{PYXIE_SHOW_ATTR}="toc,sidebar"]')) == 1
    assert len(doc.xpath(f'//p[@{PYXIE_SHOW_ATTR}="related,comments"]')) == 1
    assert "Navigation Elements" in result
    assert "User Content" in result
    
    # Test with the second slot filled
    result = process_conditional_visibility(html_content, {"sidebar", "comments"})
    doc = html.fromstring(result)
    
    # Both elements should be present (each has one matching slot)
    assert len(doc.xpath(f'//h2[@{PYXIE_SHOW_ATTR}="toc,sidebar"]')) == 1
    assert len(doc.xpath(f'//p[@{PYXIE_SHOW_ATTR}="related,comments"]')) == 1
    assert "Navigation Elements" in result
    assert "User Content" in result
    
    # Test with none of the slots filled
    result = process_conditional_visibility(html_content, {"other"})
    doc = html.fromstring(result)
    
    # Both elements should be removed
    assert len(doc.xpath(f'//h2[@{PYXIE_SHOW_ATTR}="toc,sidebar"]')) == 0
    assert len(doc.xpath(f'//p[@{PYXIE_SHOW_ATTR}="related,comments"]')) == 0
    assert "Navigation Elements" not in result
    assert "User Content" not in result


def test_process_conditional_visibility_with_existing_style():
    """Test conditional visibility when elements already have style attributes."""
    # HTML with conditional elements that have existing styles
    html_content = f'<div><h2 {PYXIE_SHOW_ATTR}="toc" style="color: blue;">Table of Contents</h2><p {PYXIE_SHOW_ATTR}="sidebar" style="margin-top: 10px;">Sidebar content</p></div>'
    
    # Test with no slots filled
    result = process_conditional_visibility(html_content, set())
    doc = html.fromstring(result)
    
    # Both elements should be removed
    assert len(doc.xpath(f'//h2[@{PYXIE_SHOW_ATTR}="toc"]')) == 0
    assert len(doc.xpath(f'//p[@{PYXIE_SHOW_ATTR}="sidebar"]')) == 0
    assert "Table of Contents" not in result
    assert "Sidebar content" not in result


def test_process_conditional_visibility_error_handling():
    """Test error handling in conditional visibility processing."""
    # Test with invalid HTML
    result = process_conditional_visibility("<div><p>Unclosed tag", {"slot"})
    # Accept either the original HTML or the fixed HTML (since lxml might fix it)
    assert result in ["<div><p>Unclosed tag", "<div><p>Unclosed tag</p></div>\n"]
    
    # Test with error in processing
    def mock_process_that_raises():
        raise Exception("test error")
    
    original_fromstring = html.fromstring
    html.fromstring = mock_process_that_raises
    try:
        result = process_conditional_visibility("<div>Test</div>", {"slot"})
        assert result == "<div>Test</div>"  # Should return original HTML on error
    finally:
        html.fromstring = original_fromstring


def test_process_conditional_visibility_negation():
    """Test conditional visibility with negation operator."""
    # HTML with negation condition
    html_content = f'<div><p {PYXIE_SHOW_ATTR}="!optional">Show when optional is not present</p><p {PYXIE_SHOW_ATTR}="required">Show when required is present</p></div>'
    
    # Test when optional slot is NOT present (negation condition should show)
    filled_slots = {"required"}
    result = process_conditional_visibility(html_content, filled_slots)
    doc = html.fromstring(result)
    
    # Both elements should be present
    assert len(doc.xpath(f'//p[@{PYXIE_SHOW_ATTR}="!optional"]')) == 1
    assert len(doc.xpath(f'//p[@{PYXIE_SHOW_ATTR}="required"]')) == 1
    assert "Show when optional is not present" in result
    assert "Show when required is present" in result
    
    # Test when optional slot IS present (negation condition should hide)
    filled_slots = {"required", "optional"}
    result = process_conditional_visibility(html_content, filled_slots)
    doc = html.fromstring(result)
    
    # Only required element should be present
    assert len(doc.xpath(f'//p[@{PYXIE_SHOW_ATTR}="!optional"]')) == 0
    assert len(doc.xpath(f'//p[@{PYXIE_SHOW_ATTR}="required"]')) == 1
    assert "Show when optional is not present" not in result
    assert "Show when required is present" in result


def test_process_conditional_visibility_complex_conditions():
    """Test conditional visibility with complex conditions."""
    # HTML with complex conditions
    html_content = f'<div><p {PYXIE_SHOW_ATTR}="!optional,required">Show with complex condition</p></div>'
    
    # Test with required filled but optional not (should show)
    result = process_conditional_visibility(html_content, {"required"})
    assert "Show with complex condition" in result
    
    # Test with both filled (should hide due to !optional)
    result = process_conditional_visibility(html_content, {"required", "optional"})
    assert "Show with complex condition" not in result
    
    # Test with neither filled (should hide due to required not present)
    result = process_conditional_visibility(html_content, set())
    assert "Show with complex condition" not in result


def test_process_conditional_visibility_whitespace_handling():
    """Test conditional visibility with whitespace and complex formatting in attributes."""
    # HTML with spaces and varied formatting in the data-pyxie-show attributes
    html_content = f'<div><h2 {PYXIE_SHOW_ATTR}=" toc , sidebar ">Spaced values</h2><p {PYXIE_SHOW_ATTR}="  !featured_image  ,   related  ">Mixed negation with spaces</p><div {PYXIE_SHOW_ATTR}="header,  !footer,  content  ">Multiple conditions with varied spacing</div></div>'
    
    # Test with specific slots filled
    filled_slots = {"toc", "related", "content"}
    result = process_conditional_visibility(html_content, filled_slots)
    doc = html.fromstring(result)
    
    # All elements should be present since their conditions are met
    assert len(doc.xpath(f'//h2[@{PYXIE_SHOW_ATTR}=" toc , sidebar "]')) == 1
    assert len(doc.xpath(f'//p[@{PYXIE_SHOW_ATTR}="  !featured_image  ,   related  "]')) == 1
    assert len(doc.xpath(f'//div[@{PYXIE_SHOW_ATTR}="header,  !footer,  content  "]')) == 1
    assert "Spaced values" in result
    assert "Mixed negation with spaces" in result
    assert "Multiple conditions with varied spacing" in result
    
    # Test with different slots filled that should trigger some hiding
    filled_slots = {"sidebar", "featured_image", "footer"}
    result = process_conditional_visibility(html_content, filled_slots)
    doc = html.fromstring(result)
    
    # First element should be present (sidebar is filled)
    assert len(doc.xpath(f'//h2[@{PYXIE_SHOW_ATTR}=" toc , sidebar "]')) == 1
    assert "Spaced values" in result
    
    # Second element should be removed (featured_image negates !featured_image, and related is not filled)
    assert len(doc.xpath(f'//p[@{PYXIE_SHOW_ATTR}="  !featured_image  ,   related  "]')) == 0
    assert "Mixed negation with spaces" not in result
    
    # Third element should be removed (footer negates !footer, and neither header nor content is filled)
    assert len(doc.xpath(f'//div[@{PYXIE_SHOW_ATTR}="header,  !footer,  content  "]')) == 0
    assert "Multiple conditions with varied spacing" not in result 