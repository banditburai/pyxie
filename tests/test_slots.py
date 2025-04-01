"""Tests for the slot filling functionality."""

import pytest
from lxml import html, etree
from fastcore.xml import Div, P, H1, Section, Article, to_xml

from pyxie.slots import (
    process_layout, SLOT_ATTR, CONDITION_ATTR, parse_html, merge_classes,
    extract_slots, fill_slot, check_condition
)
from pyxie.errors import SlotError

# Test fixtures
@pytest.fixture
def simple_layout() -> str:
    """Create a simple layout with several slots."""
    layout = Div(
        H1(None, data_slot="page_title", cls="title"),
        Section(None, data_slot="main_content", cls="content"),
        Article(None, data_slot="side_content", cls="example"),
        cls="container"
    )
    return to_xml(layout)

@pytest.fixture
def nested_layout() -> str:
    """Create a nested layout with slots at different depths."""
    layout = Article(
        H1(None, data_slot="page_title", cls="title"),
        Div(
            Section(None, data_slot="intro_content", cls="intro"),
            Section(None, data_slot="main_content", cls="content"),
            cls="main"
        ),
        Div(
            Section(None, data_slot="side_content", cls="sidebar"),
            P(None, data_slot="page_footer", cls="footer"),
            cls="aside"
        ),
        cls="page"
    )
    return to_xml(layout)

# Test parse_html function
def test_parse_html():
    """Test HTML parsing functionality."""
    # Test valid HTML
    html_str = "<div>Test content</div>"
    result = parse_html(html_str)
    assert result.tag == "div"
    assert result.text_content().strip() == "Test content"

    # Test empty HTML - should create an empty div
    result = parse_html("")
    assert result.tag == "div"
    assert not result.text
    assert len(result) == 0

    # Test with create_parent=False
    result = parse_html(html_str, create_parent=False)
    assert result.tag == "div"
    assert result.text_content().strip() == "Test content"

    # Test HTML fragment with multiple elements
    html_str = "<p>First</p><p>Second</p>"
    result = parse_html(html_str)
    assert result.tag == "div"  # Should create parent div
    assert len(result) == 2  # Should have two p elements
    assert result[0].text == "First"
    assert result[1].text == "Second"

# Test merge_classes function
def test_merge_classes():
    """Test class merging functionality."""
    # Test basic merging
    assert merge_classes("class1 class2", "class2 class3") == "class1 class2 class3"

    # Test with None values
    assert merge_classes("class1", None, "class2") == "class1 class2"

    # Test with empty strings
    assert merge_classes("class1", "", "class2") == "class1 class2"

    # Test with whitespace
    assert merge_classes(" class1 ", " class2 ") == "class1 class2"

    # Test with duplicates
    assert merge_classes("class1 class1", "class1") == "class1"

# Test extract_slots function
def test_extract_slots():
    """Test slot extraction functionality."""
    # Test with valid slots
    html_str = "<div data-slot='header'>Header content</div><p>Main content</p><div data-slot='footer'>Footer content</div>"
    result = extract_slots(html_str)
    assert result.slots["header"] == '<div data-slot="header">Header content</div>'
    assert result.slots["footer"] == '<div data-slot="footer">Footer content</div>'
    assert "Main content" in result.main_content

    # Test with empty content
    result = extract_slots("")
    assert result.slots == {}
    assert result.main_content == ""

    # Test with no slots
    result = extract_slots("<p>Just content</p>")
    assert result.slots == {}
    assert "Just content" in result.main_content

# Test fill_slot function
def test_fill_slot():
    """Test slot filling functionality."""
    # Create a parent element to hold the placeholder
    parent = html.Element("div")
    placeholder = etree.SubElement(parent, "div", attrib={"data-slot": "test", "class": "original"})
    placeholder.text = "Default content"
    
    # Test filling with content
    fill_slot(placeholder, '<div class="new">New content</div>')
    assert placeholder.get('class') == "original new"
    assert placeholder.text_content().strip() == "New content"

    # Test filling with empty content and no default content
    parent = html.Element("div")
    placeholder = etree.SubElement(parent, "div", attrib={"data-slot": "test", "class": "original"})
    fill_slot(placeholder, "")
    assert placeholder.getparent() is None  # Should be removed

    # Test filling with text-only content
    parent = html.Element("div")
    placeholder = etree.SubElement(parent, "div", attrib={"data-slot": "test", "class": "original"})
    placeholder.text = "Default content"
    fill_slot(placeholder, "Just text")
    assert placeholder.get('class') == "original"
    assert placeholder.text_content().strip() == "Just text"

# Test check_condition function
def test_check_condition():
    """Test condition checking functionality."""
    slots = {"header": "content", "footer": ""}
    context = {"published": True, "draft": False}

    # Test with metadata context
    assert check_condition("published", slots, context) is True
    assert check_condition("!published", slots, context) is False
    assert check_condition("draft", slots, context) is False
    assert check_condition("!draft", slots, context) is True

    # Test with slot content
    assert check_condition("header", slots, context) is True
    assert check_condition("!header", slots, context) is False
    assert check_condition("footer", slots, context) is False
    assert check_condition("!footer", slots, context) is True

    # Test with empty condition
    assert check_condition("", slots, context) is False

    # Test with nonexistent key
    assert check_condition("nonexistent", slots, context) is False
    assert check_condition("!nonexistent", slots, context) is True

# Test basic slot filling
def test_basic_slot_filling(simple_layout: str) -> None:
    """Test that slots are correctly filled with content."""
    rendered_html = """
    <h1 data-slot="page_title">Test Title</h1>
    <p data-slot="main_content">Test content paragraph</p>
    """
    
    result = process_layout(simple_layout, rendered_html, {})
    
    assert "Test Title" in result
    assert "Test content paragraph" in result
    assert 'class="title"' in result
    assert 'class="content"' in result

# Test empty slot removal
def test_empty_slot_removal(simple_layout: str) -> None:
    """Test that empty slots are removed if they have no default content."""
    rendered_html = """
    <h1 data-slot="page_title">Test Title</h1>
    <section data-slot="main_content"></section>
    """

    result = process_layout(simple_layout, rendered_html, {})

    # Parse the result to check DOM structure
    dom = html.fromstring(result)

    # Title should exist with filled content
    title_elements = dom.xpath('//*[@class="title"]')
    assert len(title_elements) == 1
    assert title_elements[0].text == "Test Title"

    # Empty slots without default content should be removed
    content_elements = dom.xpath('//*[@class="content"]')
    example_elements = dom.xpath('//*[@class="example"]')
    assert len(content_elements) == 0  # No default content, should be removed
    assert len(example_elements) == 0  # No default content, should be removed

def test_empty_slot_with_default(nested_layout: str) -> None:
    """Test that empty slots preserve their default content when available."""
    # Create layout with default content
    layout = """
    <div class="container">
        <h1 data-slot="page_title" class="title">Default Title</h1>
        <section data-slot="main_content" class="content">Default Content</section>
        <article data-slot="side_content" class="example"></article>
    </div>
    """

    # Provide empty content for some slots
    rendered_html = """
    <h1 data-slot="page_title"></h1>
    <section data-slot="main_content"></section>
    """

    result = process_layout(layout, rendered_html, {})

    # Parse result to check structure
    dom = html.fromstring(result)

    # Elements with default content should be preserved with their defaults
    title = dom.xpath('//*[@class="title"]')[0]
    content = dom.xpath('//*[@class="content"]')[0]
    assert title.text == "Default Title"
    assert content.text == "Default Content"

    # Empty elements without default should still be removed
    example_elements = dom.xpath('//*[@class="example"]')
    assert len(example_elements) == 0

# Test multiple instances of the same slot
def test_multiple_slot_instances(simple_layout: str) -> None:
    """Test handling multiple instances of content for the same slot."""
    rendered_html = """
    <div data-slot="main_content">
        <p>First content block</p>
        <p>Second content block</p>
        <p>Third content block</p>
    </div>
    """
    
    result = process_layout(simple_layout, rendered_html, {})
    
    # Parse result to check structure
    dom = html.fromstring(result)
    content_elements = dom.xpath('//*[@class="content"]')
    assert len(content_elements) == 1  # Should have one content section with all blocks
    
    # Verify all content blocks are present
    paragraphs = content_elements[0].xpath('.//p')
    assert len(paragraphs) == 3
    assert "First content block" in paragraphs[0].text
    assert "Second content block" in paragraphs[1].text
    assert "Third content block" in paragraphs[2].text

# Test class merging and preservation
def test_class_merging_and_preservation(simple_layout: str) -> None:
    """Test that classes are properly merged and preserved at all levels."""
    rendered_html = """
    <h1 data-slot="page_title" class="large bold">
        <span class="highlight">Enhanced Title</span>
    </h1>
    <div data-slot="main_content" class="custom-content">
        <p class="intro">First paragraph</p>
        <p class="body">Second paragraph</p>
    </div>
    """
    
    result = process_layout(simple_layout, rendered_html, {})
    dom = html.fromstring(result)
    
    # Check title element classes
    title_element = dom.xpath('//h1')[0]
    title_classes = set(title_element.get('class').split())
    assert title_classes == {"title", "large", "bold"}
    
    # Check that span class is preserved
    span = dom.xpath('//span')[0]
    assert span.get('class') == "highlight"
    
    # Check content element classes
    content_element = dom.xpath('//*[@class="content custom-content"]')[0]
    paragraphs = content_element.xpath('.//p')
    assert paragraphs[0].get('class') == "intro"
    assert paragraphs[1].get('class') == "body"

# Test conditional visibility
def test_conditional_visibility(simple_layout: str) -> None:
    """Test conditional visibility based on slot presence."""
    layout_with_conditions = """
    <div class="container">
        <div data-slot="page_title" data-pyxie-show="page_title">Title Section</div>
        <div data-slot="main_content">Main Content</div>
        <div data-slot="side_content" data-pyxie-show="!main_content">Side Content</div>
        <div data-slot="optional_content" data-pyxie-show="main_content">Optional Content</div>
    </div>
    """

    # Test with only title
    rendered_html = '<div data-slot="page_title">Test Title</div>'
    result = process_layout(layout_with_conditions, rendered_html, {})
    assert "Test Title" in result
    assert "Side Content" in result  # Should show because main_content is not present
    assert "Optional Content" not in result  # Should not show because main_content is not present

    # Test with main content
    rendered_html = '<div data-slot="main_content">Main Content</div>'
    result = process_layout(layout_with_conditions, rendered_html, {})
    assert "Main Content" in result
    assert "Side Content" not in result  # Should not show because main_content is present
    assert "Optional Content" in result  # Should show because main_content is present

# Test slot with tail text
def test_slot_with_tail_text() -> None:
    """Test that tail text of removed slots is preserved."""
    layout = '<div><span data-slot="test_slot" class="test"></span> Tail text should remain</div>'
    rendered_html = ""  # No content for the test slot
    
    result = process_layout(layout, rendered_html, {})
    assert "Tail text should remain" in result
    assert '<span data-slot="test_slot"' not in result  # Slot should be removed

# Test error cases
def test_invalid_html() -> None:
    """Test handling of invalid HTML in content blocks."""
    layout = '<div><div data-slot="test_content"></div></div>'
    rendered_html = '<p data-slot="test_content">Unclosed paragraph<p>'  # Invalid HTML
    
    result = process_layout(layout, rendered_html, {})
    
    # Should still succeed, as lxml is forgiving with HTML
    assert "Unclosed paragraph" in result

class TestSlotErrorHandling:
    """Tests for error handling in slot filling operations."""
    
    def test_invalid_slot_target(self):
        """Test behavior when trying to fill a slot on an invalid target."""
        rendered_html = '<p data-slot="test_content">Test content</p>'
        
        # Try to fill a slot on a non-XML element (string gets converted to p element)
        with pytest.raises(SlotError) as exc_info:
            process_layout("not an element", rendered_html, {})
        
        # Verify the error message
        assert "Layout must contain at least one slot" in str(exc_info.value)
        
        # Try with None
        with pytest.raises(SlotError):
            process_layout(None, rendered_html, {})
    
    def test_slot_name_conflict(self):
        """Test behavior with conflicting slot names."""
        # Create an element with two identical slots
        element = Div(
            Div(None, data_slot="test_content"),
            Div(None, data_slot="test_content")
        )
        
        # Fill the slots with content
        rendered_html = """
        <div data-slot="test_content">Content value</div>
        """
        
        # This should fill both slots with the same value
        result = process_layout(to_xml(element), rendered_html, {})
        assert "Content value" in result
    
    def test_nested_slot_errors(self):
        """Test error handling in deeply nested slots."""
        # Create a complex nested structure with potentially problematic slots
        element = Div(
            H1("Title"),
            Div(
                P(None, data_slot="nested_slot1"),
                Div(
                    P(None, data_slot="nested_slot2"),
                    Div(
                        P(123, data_slot="nested_slot3"),  # Invalid content
                        P(None, data_slot="nested_slot4")
                    )
                )
            )
        )
        
        rendered_html = """
        <p data-slot="nested_slot1">Content 1</p>
        <p data-slot="nested_slot2">Content 2</p>
        <p data-slot="nested_slot3">Content 3</p>
        <p data-slot="nested_slot4">Content 4</p>
        """
        
        # Should still work despite the invalid slot
        result = process_layout(to_xml(element), rendered_html, {})
        assert "Content 1" in result
        assert "Content 2" in result
        assert "Content 3" in result
        assert "Content 4" in result 