"""Tests for slot filling functionality."""

import pytest
from lxml import html

from pyxie.slots import process_layout, SlotError, CONDITION_ATTR

def test_slot_filling_basic():
    """Test basic slot filling functionality."""
    # Test layout
    layout = """
    <div class="container">
        <div data-slot="main_content" class="prose"></div>
    </div>
    """

    # Test content
    rendered_html = """
    <div data-slot="main_content">
        <p>Test content</p>
    </div>
    """

    # Process slots
    result = process_layout(layout, rendered_html, {})

    # Check that content was filled correctly
    assert "Test content" in result
    assert 'class="prose"' in result

def test_slot_filling_with_classes():
    """Test slot filling with class merging."""
    # Test layout
    layout = """
    <div class="container">
        <div data-slot="main_content" class="prose"></div>
    </div>
    """

    # Test content with additional classes
    rendered_html = """
    <div data-slot="main_content" class="content-wrapper">
        <p>Test content</p>
    </div>
    """

    # Process slots
    result = process_layout(layout, rendered_html, {})

    # Check that classes were merged correctly
    assert "Test content" in result
    assert 'class="prose content-wrapper"' in result

def test_conditional_visibility():
    """Test conditional visibility based on slot content."""
    # Test layout
    layout = """
    <div class="container">
        <div data-slot="main_content" class="prose"></div>
        <div data-pyxie-show="main_content">This should be visible</div>
        <div data-pyxie-show="missing_content">This should be hidden</div>
    </div>
    """

    # Test content
    rendered_html = """
    <div data-slot="main_content">
        <p>Test content</p>
    </div>
    """

    # Process slots
    result = process_layout(layout, rendered_html, {})

    # Check visibility
    assert "This should be visible" in result
    assert "This should be hidden" not in result

def test_multiple_slots():
    """Test filling multiple slots."""
    # Test layout
    layout = """
    <div class="container">
        <div data-slot="page_header"></div>
        <div data-slot="main_content"></div>
        <div data-slot="page_footer"></div>
    </div>
    """

    # Test content for multiple slots
    rendered_html = """
    <div data-slot="page_header">Header content</div>
    <div data-slot="main_content">Main content</div>
    <div data-slot="page_footer">Footer content</div>
    """

    # Process slots
    result = process_layout(layout, rendered_html, {})

    # Check that all slots were filled
    assert "Header content" in result
    assert "Main content" in result
    assert "Footer content" in result

def test_slot_filling_with_html():
    """Test slot filling with complex HTML content."""
    # Test layout
    layout = """
    <div class="container">
        <div data-slot="main_content" class="prose"></div>
    </div>
    """

    # Test content with complex HTML
    rendered_html = """
    <div data-slot="main_content" class="content-wrapper">
        <h2>Welcome</h2>
        <p>This is a test of slot filling.</p>
        <div class="nested">
            <h3>Nested Heading</h3>
            <p>Nested content with <strong>bold</strong> and <em>italic</em> text.</p>
        </div>
    </div>
    """

    # Process slots
    result = process_layout(layout, rendered_html, {})

    # Check that complex HTML was preserved
    assert "Welcome" in result
    assert "Nested Heading" in result
    assert "<strong>bold</strong>" in result
    assert "<em>italic</em>" in result
    assert 'class="nested"' in result  # Check that nested class is preserved

def test_empty_slots():
    """Test handling of empty slots."""
    # Test layout with multiple slots
    layout = """
    <div class="container">
        <div data-slot="page_header"></div>
        <div data-slot="main_content"></div>
        <div data-slot="page_footer"></div>
    </div>
    """

    # Test with some slots empty
    rendered_html = """
    <div data-slot="main_content">Main content</div>
    """

    # Process slots
    result = process_layout(layout, rendered_html, {})

    # Check that empty slots were handled correctly
    assert "Main content" in result
    dom = html.fromstring(result)
    assert len(dom.xpath('//*[@data-slot="page_header"]')) == 0
    assert len(dom.xpath('//*[@data-slot="page_footer"]')) == 0

def test_missing_slots():
    """Test handling of missing slot content."""
    # Test layout with multiple slots
    layout = """
    <div class="container">
        <div data-slot="page_header"></div>
        <div data-slot="main_content"></div>
        <div data-slot="page_footer"></div>
    </div>
    """

    # Test with missing slot content
    rendered_html = """
    <div data-slot="main_content">Main content</div>
    """

    # Process slots
    result = process_layout(layout, rendered_html, {})

    # Check that missing slots were handled correctly
    assert "Main content" in result
    dom = html.fromstring(result)
    assert len(dom.xpath('//*[@data-slot="page_header"]')) == 0
    assert len(dom.xpath('//*[@data-slot="page_footer"]')) == 0

def test_slot_with_attributes():
    """Test slot filling with various HTML attributes."""
    # Test layout with slots that have various attributes
    layout = """
    <div class="container">
        <div data-slot="main_content" class="prose" id="main-content" data-test="value"></div>
    </div>
    """

    # Test content with its own attributes
    rendered_html = """
    <div data-slot="main_content" class="content-wrapper" data-custom="test">
        <h2>Welcome</h2>
        <p>This is a test of slot filling.</p>
    </div>
    """

    # Process slots
    result = process_layout(layout, rendered_html, {})

    # Check that attributes were handled correctly
    dom = html.fromstring(result)
    content_div = dom.xpath('//*[@id="main-content"]')[0]
    assert content_div.get('class') == 'prose content-wrapper'
    assert content_div.get('data-test') == 'value'
    assert content_div.get('data-custom') == 'test' 