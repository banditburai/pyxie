"""Test slot filling behavior in isolation."""

import pytest
from lxml import html
from typing import Dict, List, Set, Tuple, Any
from src.pyxie.slots import (
    process_slots_and_visibility,
    fill_slots,
    process_single_slot,
    process_conditional_visibility,
    check_visibility_condition
)

def test_slot_filling_basic():
    """Test basic slot filling functionality."""
    # Test layout with a single slot
    layout = """
    <div class="container">
        <div data-slot="content"></div>
    </div>
    """
    
    # Test content
    content = "<p>Welcome to Pyxie</p>"
    
    # Process slots
    result = process_slots_and_visibility(layout, {"content": content})
    
    # Verify result
    assert result.was_filled
    assert "Welcome to Pyxie" in result.element

def test_slot_filling_with_classes():
    """Test slot filling with class attributes."""
    # Test layout with class attributes
    layout = """
    <div class="container">
        <div data-slot="content" class="prose"></div>
    </div>
    """
    
    # Test content with its own classes
    content = """
    <div class="content-wrapper">
        <h2>Welcome</h2>
        <p>This is a test of slot filling.</p>
    </div>
    """
    
    # Process slots
    result = process_slots_and_visibility(layout, {"content": content})
    
    # Verify result
    assert result.was_filled
    assert "prose" in result.element
    assert "content-wrapper" in result.element

def test_conditional_visibility():
    """Test conditional visibility with data-pyxie-show attributes."""
    # Test layout with conditional visibility
    layout = """
    <div class="container">
        <div data-pyxie-show="header">
            <h1>Header</h1>
        </div>
        <div data-slot="content"></div>
        <div data-pyxie-show="!header">
            <p>No header content</p>
        </div>
    </div>
    """
    
    # Test content
    content = "<p>Main content</p>"
    
    # Test with header visibility enabled
    result_with_header = process_slots_and_visibility(layout, {
        "content": content,
        "header": True  # Use True to indicate header should be shown
    })
    assert "Header" in result_with_header.element
    assert "No header content" not in result_with_header.element
    
    # Test without header visibility
    result_without_header = process_slots_and_visibility(layout, {
        "content": content
        # header not included, so elements with data-pyxie-show="header" should be hidden
    })
    assert "Header" not in result_without_header.element
    assert "No header content" in result_without_header.element

def test_multiple_slots():
    """Test filling multiple slots in a layout."""
    # Test layout with multiple slots
    layout = """
    <div class="container">
        <div data-slot="header"></div>
        <div data-slot="content"></div>
        <div data-slot="footer"></div>
    </div>
    """
    
    # Test content for multiple slots
    slots = {
        "header": "<h1>Welcome</h1>",
        "content": "<p>Main content</p>",
        "footer": "<p>Footer content</p>"
    }
    
    # Process slots
    result = process_slots_and_visibility(layout, slots)
    
    # Verify result
    assert result.was_filled
    assert "Welcome" in result.element
    assert "Main content" in result.element
    assert "Footer content" in result.element

def test_slot_filling_with_html():
    """Test slot filling with complex HTML content."""
    # Test layout
    layout = """
    <div class="container">
        <div data-slot="content" class="prose"></div>
    </div>
    """
    
    # Test content with complex HTML
    content = """
    <div class="content-wrapper">
        <h2>Welcome</h2>
        <p>This is a test of slot filling.</p>
        <div class="nested">
            <h3>Nested Heading</h3>
            <p>Nested content with <strong>bold</strong> and <em>italic</em> text.</p>
        </div>
    </div>
    """
    
    # Process slots
    result = process_slots_and_visibility(layout, {"content": content})
    
    # Verify result
    assert result.was_filled
    assert "Welcome" in result.element
    assert "Nested Heading" in result.element
    assert "<strong>bold</strong>" in result.element
    assert "<em>italic</em>" in result.element
    assert "prose" in result.element
    assert "content-wrapper" in result.element
    assert "nested" in result.element

def test_empty_slots():
    """Test handling of empty slots."""
    # Test layout with multiple slots
    layout = """
    <div class="container">
        <div data-slot="header"></div>
        <div data-slot="content"></div>
        <div data-slot="footer"></div>
    </div>
    """
    
    # Test with some slots empty
    slots = {
        "header": "",  # Empty header
        "content": "<p>Main content</p>",
        "footer": ""  # Empty footer
    }
    
    # Process slots
    result = process_slots_and_visibility(layout, slots)
    
    # Verify result
    assert result.was_filled
    assert "Main content" in result.element
    assert "data-slot" not in result.element  # Empty slots should be removed

def test_missing_slots():
    """Test handling of missing slot content."""
    # Test layout with multiple slots
    layout = """
    <div class="container">
        <div data-slot="header"></div>
        <div data-slot="content"></div>
        <div data-slot="footer"></div>
    </div>
    """
    
    # Test with missing slot content
    slots = {
        "content": "<p>Main content</p>"
        # header and footer slots not provided
    }
    
    # Process slots
    result = process_slots_and_visibility(layout, slots)
    
    # Verify result
    assert result.was_filled
    assert "Main content" in result.element
    assert "data-slot" not in result.element  # Missing slots should be removed

def test_slot_with_attributes():
    """Test slot filling with various HTML attributes."""
    # Test layout with slots that have various attributes
    layout = """
    <div class="container">
        <div data-slot="content" class="prose" id="main-content" data-test="value"></div>
    </div>
    """
    
    # Test content with its own attributes
    content = """
    <div class="content-wrapper">
        <h2>Welcome</h2>
        <p>This is a test of slot filling.</p>
    </div>
    """
    
    # Process slots
    result = process_slots_and_visibility(layout, {"content": content})
    
    # Verify result
    assert result.was_filled
    assert "prose" in result.element
    assert "content-wrapper" in result.element
    assert "id=\"main-content\"" in result.element
    assert "data-test=\"value\"" in result.element 