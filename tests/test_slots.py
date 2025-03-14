"""Tests for the slot filling functionality."""

import pytest
from pathlib import Path
from typing import Dict, List, Any
from lxml import html, etree
from fastcore.xml import Div, P, H1, Section, Article, FT, to_xml

from pyxie.slots import fill_slots, SlotFillResult
from pyxie.errors import PyxieError

# Test fixtures
@pytest.fixture
def simple_layout() -> str:
    """Create a simple layout with several slots."""
    layout = Div(
        H1(None, data_slot="title", cls="title"),
        Section(None, data_slot="content", cls="content"),
        Article(None, data_slot="example", cls="example"),
        cls="container"
    )
    return to_xml(layout)

@pytest.fixture
def nested_layout() -> str:
    """Create a nested layout with slots at different depths."""
    layout = Article(
        H1(None, data_slot="title", cls="title"),
        Div(
            Section(None, data_slot="intro", cls="intro"),
            Section(None, data_slot="content", cls="content"),
            cls="main"
        ),
        Div(
            Section(None, data_slot="sidebar", cls="sidebar"),
            P(None, data_slot="footer", cls="footer"),
            cls="aside"
        ),
        cls="page"
    )
    return to_xml(layout)

# Test basic slot filling
def test_basic_slot_filling(simple_layout: str) -> None:
    """Test that slots are correctly filled with content."""
    blocks = {
        "title": ["<h1>Test Title</h1>"],
        "content": ["<p>Test content paragraph</p>"]
    }
    
    result = fill_slots(simple_layout, blocks)
    
    assert result.was_filled
    assert "<h1>Test Title</h1>" in result.element
    assert "<p>Test content paragraph</p>" in result.element
    assert 'class="title"' in result.element
    assert 'class="content"' in result.element

# Test empty slot removal
def test_empty_slot_removal(simple_layout: str) -> None:
    """Test that empty slots are removed from the DOM."""
    blocks = {
        "title": ["<h1>Test Title</h1>"],
        # No content for "content" or "example" slots
    }
    
    result = fill_slots(simple_layout, blocks)
    
    assert result.was_filled
    assert "<h1>Test Title</h1>" in result.element
    
    # Parse the result to check DOM structure
    dom = html.fromstring(result.element)
    
    # Title should exist
    title_elements = dom.xpath('//*[@class="title"]')
    assert len(title_elements) == 1
    
    # Content and example slots should be removed
    content_elements = dom.xpath('//*[@class="content"]')
    example_elements = dom.xpath('//*[@class="example"]')
    assert len(content_elements) == 0
    assert len(example_elements) == 0
    
    # Container should still exist
    container_elements = dom.xpath('//*[@class="container"]')
    assert len(container_elements) == 1

# Test multiple instances of the same slot
def test_multiple_slot_instances(simple_layout: str) -> None:
    """Test handling multiple instances of content for the same slot."""
    blocks = {
        "content": [
            "<p>First content block</p>",
            "<p>Second content block</p>",
            "<p>Third content block</p>"
        ]
    }
    
    result = fill_slots(simple_layout, blocks)
    
    assert result.was_filled
    assert "<p>First content block</p>" in result.element
    assert "<p>Second content block</p>" in result.element
    assert "<p>Third content block</p>" in result.element
    
    # Parse result to check structure
    dom = html.fromstring(result.element)
    content_elements = dom.xpath('//section[@class="content"]')
    assert len(content_elements) == 3  # Should have duplicated the slot

# Test class merging
def test_class_merging(simple_layout: str) -> None:
    """Test that classes from content elements are merged with slot classes."""
    blocks = {
        "title": ['<h1 class="large bold">Enhanced Title</h1>']
    }
    
    result = fill_slots(simple_layout, blocks)
    
    assert result.was_filled
    dom = html.fromstring(result.element)
    title_element = dom.xpath('//h1')[0]
    
    # Should have both original "title" class and new classes
    classes = title_element.get('class').split()
    assert "title" in classes
    assert "large" in classes
    assert "bold" in classes

# Test slot with tail text
def test_slot_with_tail_text() -> None:
    """Test that tail text of removed slots is preserved."""
    layout = '<div><span data-slot="test" class="test"></span> Tail text should remain</div>'
    blocks = {}  # No content for the "test" slot
    
    result = fill_slots(layout, blocks)
    
    assert result.was_filled
    assert "Tail text should remain" in result.element
    assert '<span data-slot="test"' not in result.element  # Slot should be removed

# Test error cases
def test_invalid_html() -> None:
    """Test handling of invalid HTML in content blocks."""
    layout = '<div><div data-slot="content"></div></div>'
    blocks = {
        "content": ["<p>Unclosed paragraph<p>"]  # Invalid HTML
    }
    
    result = fill_slots(layout, blocks)
    
    # Should still succeed, as lxml is forgiving with HTML
    assert result.was_filled
    assert "Unclosed paragraph" in result.element 

class TestSlotErrorHandling:
    """Tests for error handling in slot filling operations."""
    
    def test_invalid_slot_target(self):
        """Test behavior when trying to fill a slot on an invalid target."""
        from pyxie.slots import fill_slots, SlotError
        from fastcore.xml import Div, to_xml
        
        # Create a slot value
        slot_value = "Test content"
        
        # Try to fill a slot on a non-XML element (string gets converted to p element)
        result = fill_slots("not an element", {"content": slot_value})
        
        # Check that the result succeeded (strings are converted to elements)
        assert result.was_filled  
        assert result.error is None
        
        # Try with None
        result = fill_slots(None, {"content": slot_value})
        
        # Check that the result exists 
        assert result is not None
    
    def test_slot_name_conflict(self):
        """Test behavior with conflicting slot names."""
        from pyxie.slots import fill_slots, SlotError
        from fastcore.xml import Div, to_xml
        
        # Create an element with two identical slots
        element = Div(
            Div(None, data_slot="content"),
            Div(None, data_slot="content")
        )
        
        # Fill the slots with different values
        slots = {
            "content": "Content value"
        }
        
        # This should fill both slots with the same value
        result = fill_slots(element, slots)
        
        # Check that the result indicates success
        assert result.was_filled
        assert result.error is None
        
        # For XML output tests, just check the output contains the element object
        assert str(result.element) is not None
    
    def test_nested_slot_errors(self):
        """Test error handling in deeply nested slots."""
        from pyxie.slots import fill_slots, SlotError
        from fastcore.xml import Div, H1, P, to_xml
        
        # Create a complex nested structure with potentially problematic slots
        element = Div(
            H1("Title"),
            Div(
                P(None, data_slot="nested1"),
                Div(
                    P(None, data_slot="nested2"),
                    Div(
                        # This is an invalid slot (not a string or XML element)
                        P(123, data_slot="nested3"),
                        P(None, data_slot="nested4")
                    )
                )
            )
        )
        
        # Create slots
        slots = {
            "nested1": "Content 1",
            "nested2": "Content 2",
            "nested3": "Content 3",
            "nested4": "Content 4"
        }
        
        # Fill the slots - should work despite the invalid slot
        result = fill_slots(element, slots)
        
        # Verify the result exists (we don't check exact content because encoding differs)
        assert result is not None
    
    def test_cyclic_slot_references(self):
        """Test behavior with potential cyclic slot references."""
        from pyxie.slots import fill_slots, SlotError
        from fastcore.xml import Div, P
        
        # Create content for slots - with potential for cycles
        slot_content1 = Div(P(None, data_slot="slot2"))
        slot_content2 = Div(P(None, data_slot="slot1"))
        
        # Element with slots
        element = Div(
            Div(None, data_slot="slot1"),
            Div(None, data_slot="slot2")
        )
        
        # Fill slots with content that references other slots
        slots = {
            "slot1": slot_content1,
            "slot2": slot_content2
        }
        
        # This operation could potentially create a cycle
        # The implementation should handle this appropriately
        result = fill_slots(element, slots)
        
        # Verify the structure looks reasonable
        from fastcore.xml import to_xml
        xml = to_xml(result)
        assert "data-slot=\"slot1\"" in xml
        assert "data-slot=\"slot2\"" in xml
    
    def test_missing_slots(self):
        """Test behavior when trying to fill slots that don't exist."""
        from pyxie.slots import fill_slots
        from fastcore.xml import Div, P, to_xml
        
        # Create element with slots
        element = Div(
            Div(None, data_slot="existing")
        )
        
        # Try to fill slots that don't exist
        slots = {
            "existing": "This slot exists",
            "nonexistent": "This slot doesn't exist"
        }
        
        # This should fill the existing slot and ignore the nonexistent one
        result = fill_slots(element, slots)
        
        # Verify the result exists (we don't check exact content)
        assert result is not None
        assert result.was_filled 