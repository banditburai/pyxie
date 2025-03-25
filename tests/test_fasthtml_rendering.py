"""
Tests for FastHTML rendering functionality.

These tests focus on verifying that FastHTML components render correctly to XML,
especially for complex nested component structures.
"""

import logging
from typing import Dict, List, Any
import pytest
from pathlib import Path

from pyxie.fasthtml import render_fasthtml, create_namespace
import fasthtml.common as ft_common
from pyxie.types import ContentBlock, ContentItem
from pyxie.renderer import render_content
from pyxie.layouts import layout, registry
from fastcore.xml import FT, Div

# Add these components for the tests to work with ft_common namespace
Div = ft_common.Div
P = ft_common.P
Img = ft_common.Img
Button = ft_common.Button
NotStr = ft_common.NotStr

logging.basicConfig(level=logging.DEBUG)

@pytest.fixture(autouse=True)
def setup_test_layout():
    """Set up test layout for all tests."""
    # Clear any existing layouts
    registry._layouts.clear()
    
    @layout("default")
    def default_layout(content: str = "") -> FT:
        """Default layout that just renders the content directly."""
        return Div(data_slot="content")

def create_test_item(content: str) -> ContentItem:
    """Create a test ContentItem with the given content."""
    return ContentItem(
        source_path=Path("test.md"),
        metadata={"layout": "default"},
        blocks={"content": [ContentBlock(
            tag_name="content",
            content=content,
            attrs_str=""
        )]}
    )

def test_simple_component():
    """Test rendering of a simple component."""
    content = """
<fasthtml>
show(Div("Hello World", cls="test-class"))
</fasthtml>
"""
    result = render_content(create_test_item(content))
    assert "<div class=\"test-class\">Hello World</div>" in result

def test_nested_components():
    """Test rendering of nested components."""
    content = """
<fasthtml>
component = Div(
    Div("Inner content", cls="inner"),
    cls="outer"
)
show(component)
</fasthtml>
"""
    result = render_content(create_test_item(content))
    assert "<div class=\"outer\">" in result
    assert "<div class=\"inner\">Inner content</div>" in result

def test_component_function():
    """Test rendering of a component function."""
    content = """
<fasthtml>
def MyComponent(text):
    return Div(text, cls="custom")
    
show(MyComponent("Hello from function"))
</fasthtml>
"""
    result = render_content(create_test_item(content))
    assert "<div class=\"custom\">Hello from function</div>" in result

def test_list_comprehension():
    """Test rendering of components created with list comprehension."""
    content = """
<fasthtml>
component = Div(
    *[P(f"Item {i}", cls=f"item-{i}") for i in range(3)],
    cls="list-container"
)
show(component)
</fasthtml>
"""
    result = render_content(create_test_item(content))
    assert "<div class=\"list-container\">" in result
    assert "<p class=\"item-0\">Item 0</p>" in result
    assert "<p class=\"item-1\">Item 1</p>" in result
    assert "<p class=\"item-2\">Item 2</p>" in result

def test_image_gallery():
    """Test rendering of an image gallery with multiple nested components."""
    content = """
<fasthtml>
def ImageCard(src, alt=""):
    return Div(
        Img(src=src, alt=alt, cls="img-style"),
        cls="card-style"
    )

gallery = Div(
    ImageCard("image1.jpg", "Image 1"),
    ImageCard("image2.jpg", "Image 2"),
    ImageCard("image3.jpg", "Image 3"),
    cls="gallery"
)
show(gallery)
</fasthtml>
"""
    result = render_content(create_test_item(content))
    assert "<div class=\"gallery\">" in result
    assert "<div class=\"card-style\">" in result
    assert "<img src=\"image1.jpg\" alt=\"Image 1\" class=\"img-style\">" in result
    assert "<img src=\"image2.jpg\" alt=\"Image 2\" class=\"img-style\">" in result
    assert "<img src=\"image3.jpg\" alt=\"Image 3\" class=\"img-style\">" in result

def test_bar_chart():
    """Test rendering of a bar chart with list comprehension in a function."""
    content = """
<fasthtml>
def BarChart(data):
    max_value = max(value for _, value in data)
    
    return Div(
        *[
            Div(
                Div(cls=f"bar", style=f"width: {(value/max_value)*100}%"),
                P(label, cls="label"),
                cls="bar-container"
            )
            for label, value in data
        ],
        cls="chart"
    )

data = [
    ("A", 10),
    ("B", 20),
    ("C", 15)
]

show(BarChart(data))
</fasthtml>
"""
    result = render_content(create_test_item(content))
    assert "<div class=\"chart\">" in result
    assert "<div class=\"bar-container\">" in result
    # Check for the bar div with both class and style attributes, regardless of order
    assert 'class="bar"' in result
    assert 'style="width: 50.0%"' in result
    assert 'style="width: 100.0%"' in result
    assert 'style="width: 75.0%"' in result

def test_fasthtml_execution_in_content():
    """Test that FastHTML blocks are properly executed and rendered in content."""
    content = """
<fasthtml>
show(Button("Click me", cls="test-button"))
</fasthtml>
"""
    result = render_content(create_test_item(content))
    assert 'class="test-button"' in result, "Button not rendered"
    assert '<button' in result, "Button element not found"
    assert 'show(' not in result, "Raw show() function call found in output"

def test_multiple_fasthtml_blocks():
    """Test that multiple FastHTML blocks can be rendered independently."""
    content = """
<fasthtml>
show(Div("First component", cls="first"))
</fasthtml>

Some regular markdown content in between.

<fasthtml>
show(Div("Second component", cls="second"))
</fasthtml>
"""
    result = render_content(create_test_item(content))
    assert '<div class="first">First component</div>' in result, "First component not rendered"
    assert '<div class="second">Second component</div>' in result, "Second component not rendered"
    assert 'Some regular markdown content in between' in result, "Markdown content not preserved"
    assert 'show(' not in result, "Raw show() function call found in output"

def test_problematic_fasthtml_formats():
    """Test handling of problematic FastHTML formats."""
    # Test empty content
    empty_result = render_content(create_test_item("<fasthtml></fasthtml>"))
    assert empty_result.strip() == "<div></div>"
    
    # Test invalid Python syntax
    invalid_content = """
<fasthtml>
show(Div("Invalid syntax"
</fasthtml>
"""
    invalid_result = render_content(create_test_item(invalid_content))
    assert "error" in invalid_result.lower()
    
    # Test undefined variables
    undefined_content = """
<fasthtml>
show(undefined_component)
</fasthtml>
"""
    undefined_result = render_content(create_test_item(undefined_content))
    assert "error" in undefined_result.lower()