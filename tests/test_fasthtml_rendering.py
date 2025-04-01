"""
Tests for FastHTML rendering functionality.

These tests focus on verifying that FastHTML components render correctly to XML,
especially for complex nested component structures.
"""

import logging
from typing import Dict, List, Any
import pytest
from pathlib import Path
from io import StringIO
from mistletoe import Document
from mistletoe.block_token import add_token, Heading, Paragraph, List, HtmlBlock
from fastcore.xml import FT, Div, H1, P, Span, Button
from pyxie.types import ContentItem
from pyxie.parser import RawBlockToken, NestedContentToken, parse_frontmatter
from pyxie.renderer import render_content, PyxieRenderer
from pyxie.layouts import layout, registry
from pyxie.errors import PyxieError
from pyxie.fasthtml import execute_fasthtml, create_namespace
import fasthtml.common as ft_common

# Add these components for the tests to work with ft_common namespace
Div = ft_common.Div
H1 = ft_common.H1
P = ft_common.P
Span = ft_common.Span
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

@pytest.fixture
def create_test_item():
    """Fixture to create test ContentItems."""
    def _create(content: str, metadata: Dict[str, Any] = None) -> ContentItem:
        return ContentItem(
            source_path=Path("test.md"),
            metadata=metadata or {"layout": "default"},
            content=content
        )
    return _create

class TestBasicRendering:
    """Tests for basic FastHTML rendering functionality."""
    
    def test_simple_component(self, create_test_item):
        """Test rendering of a simple component."""
        content = """
<content>
<fasthtml>
show(Div("Hello World", cls="test-class"))
</fasthtml>
</content>
"""
        result = render_content(create_test_item(content))
        assert "<div class=\"test-class\">Hello World</div>" in result

    def test_nested_components(self, create_test_item):
        """Test rendering of nested components."""
        content = """
<content>
<fasthtml>
component = Div(
    Div("Inner content", cls="inner"),
    cls="outer"
)
show(component)
</fasthtml>
</content>
"""
        result = render_content(create_test_item(content))
        assert "<div class=\"outer\">" in result
        assert "<div class=\"inner\">Inner content</div>" in result

    def test_component_function(self, create_test_item):
        """Test rendering of a component function."""
        content = """
<content>
<fasthtml>
def MyComponent(text):
    return Div(text, cls="custom")
    
show(MyComponent("Hello from function"))
</fasthtml>
</content>
"""
        result = render_content(create_test_item(content))
        assert "<div class=\"custom\">Hello from function</div>" in result

class TestComplexRendering:
    """Tests for complex FastHTML rendering scenarios."""
    
    def test_list_comprehension(self, create_test_item):
        """Test rendering of components created with list comprehension."""
        content = """
<content>
<fasthtml>
component = Div(
    *[P(f"Item {i}", cls=f"item-{i}") for i in range(3)],
    cls="list-container"
)
show(component)
</fasthtml>
</content>
"""
        result = render_content(create_test_item(content))
        assert "<div class=\"list-container\">" in result
        assert "<p class=\"item-0\">Item 0</p>" in result
        assert "<p class=\"item-1\">Item 1</p>" in result
        assert "<p class=\"item-2\">Item 2</p>" in result

    def test_image_gallery(self, create_test_item):
        """Test rendering of an image gallery with multiple nested components."""
        content = """
<content>
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
</content>
"""
        result = render_content(create_test_item(content))
        assert "<div class=\"gallery\">" in result
        assert "<div class=\"card-style\">" in result
        assert "<img src=\"image1.jpg\" alt=\"Image 1\" class=\"img-style\">" in result
        assert "<img src=\"image2.jpg\" alt=\"Image 2\" class=\"img-style\">" in result
        assert "<img src=\"image3.jpg\" alt=\"Image 3\" class=\"img-style\">" in result

    def test_bar_chart(self, create_test_item):
        """Test rendering of a bar chart with list comprehension in a function."""
        content = """
<content>
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
</content>
"""
        result = render_content(create_test_item(content))
        assert "<div class=\"chart\">" in result
        assert "<div class=\"bar-container\">" in result
        assert "<div class=\"bar\"" in result
        assert "<p class=\"label\">A</p>" in result
        assert "<p class=\"label\">B</p>" in result
        assert "<p class=\"label\">C</p>" in result

class TestIntegration:
    """Tests for FastHTML integration with the main renderer."""
    
    def test_fasthtml_execution_in_content(self, create_test_item):
        """Test that FastHTML blocks are properly executed and rendered in content."""
        content = """
<content>
<fasthtml>
show(Button("Click me", cls="test-button"))
</fasthtml>
</content>
"""
        result = render_content(create_test_item(content))
        assert 'class="test-button"' in result, "Button not rendered"

    def test_multiple_fasthtml_blocks(self, create_test_item):
        """Test that multiple FastHTML blocks can be rendered independently."""
        content = """
<content>
<fasthtml>
show(Div("First component", cls="first"))
</fasthtml>

Some regular markdown content in between.

<fasthtml>
show(Div("Second component", cls="second"))
</fasthtml>
</content>
"""
        result = render_content(create_test_item(content))
        assert '<div class="first">First component</div>' in result, "First component not rendered"
        assert '<div class="second">Second component</div>' in result, "Second component not rendered"
        assert "Some regular markdown content in between." in result

    def test_self_closing_tags(self, create_test_item):
        """Test handling of self-closing tags in FastHTML."""
        content = """
<content>
<fasthtml>
show(Img(src="test.jpg", alt="Test Image", cls="test-img"))
</fasthtml>
</content>
"""
        result = render_content(create_test_item(content))
        assert '<img src="test.jpg" alt="Test Image" class="test-img">' in result

class TestErrorHandling:
    """Tests for FastHTML error handling."""
    
    def test_invalid_syntax(self, create_test_item):
        """Test handling of invalid Python syntax."""
        content = """
<content>
<fasthtml>
show(Div("Invalid syntax"
</fasthtml>
</content>
"""
        result = render_content(create_test_item(content))
        assert "error" in result.lower()

    def test_undefined_variables(self, create_test_item):
        """Test handling of undefined variables."""
        content = """
<content>
<fasthtml>
show(undefined_component)
</fasthtml>
</content>
"""
        result = render_content(create_test_item(content))
        assert "error" in result.lower()

    def test_invalid_component_type(self, create_test_item):
        """Test handling of invalid component objects."""
        content = """
<content>
<fasthtml>
class InvalidComponent:
    def __str__(self):
        raise ValueError("Cannot convert to string")

show(InvalidComponent())
</fasthtml>
</content>
"""
        result = render_content(create_test_item(content))
        assert "error" in result.lower()

    def test_direct_value_rendering(self, create_test_item):
        """Test that direct values are rendered as strings."""
        content = """
<content>
<fasthtml>
show(123)  # Numbers should be converted to strings
</fasthtml>
</content>
"""
        result = render_content(create_test_item(content))
        assert "123" in result