"""
Tests for FastHTML rendering functionality.

These tests focus on verifying that FastHTML components render correctly to XML,
especially for complex nested component structures.
"""

import logging

from pyxie.fasthtml import process_single_fasthtml_block, EXECUTABLE_MARKER
import fasthtml.common as ft_common

# Add these components for the tests to work with ft_common namespace
Div = ft_common.Div
P = ft_common.P
Img = ft_common.Img
Button = ft_common.Button
NotStr = ft_common.NotStr

logging.basicConfig(level=logging.DEBUG)

def test_simple_component():
    """Test rendering of a simple component."""
    content = EXECUTABLE_MARKER + """<fasthtml>
show(Div("Hello World", cls="test-class"))
</fasthtml>"""
    result = process_single_fasthtml_block(content)
    assert result.is_success
    assert "<div class=\"test-class\">Hello World</div>" in result.content


def test_nested_components():
    """Test rendering of nested components."""
    content = EXECUTABLE_MARKER + """<fasthtml>
component = Div(
    Div("Inner content", cls="inner"),
    cls="outer"
)
show(component)
</fasthtml>"""
    result = process_single_fasthtml_block(content)
    assert result.is_success
    assert "<div class=\"outer\">" in result.content
    assert "<div class=\"inner\">Inner content</div>" in result.content


def test_component_function():
    """Test rendering of a component function."""
    content = EXECUTABLE_MARKER + """<fasthtml>
def MyComponent(text):
    return Div(text, cls="custom")
    
show(MyComponent("Hello from function"))
</fasthtml>"""
    result = process_single_fasthtml_block(content)
    assert result.is_success
    assert "<div class=\"custom\">Hello from function</div>" in result.content


def test_list_comprehension():
    """Test rendering of components created with list comprehension."""
    content = EXECUTABLE_MARKER + """<fasthtml>
component = Div(
    *[P(f"Item {i}", cls=f"item-{i}") for i in range(3)],
    cls="list-container"
)
show(component)
</fasthtml>"""
    result = process_single_fasthtml_block(content)
    assert result.is_success
    assert "<div class=\"list-container\">" in result.content
    assert "<p class=\"item-0\">Item 0</p>" in result.content
    assert "<p class=\"item-1\">Item 1</p>" in result.content
    assert "<p class=\"item-2\">Item 2</p>" in result.content


def test_image_gallery():
    """Test rendering of an image gallery with multiple nested components."""
    content = EXECUTABLE_MARKER + """<fasthtml>
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
</fasthtml>"""
    result = process_single_fasthtml_block(content)
    assert result.is_success
    assert "<div class=\"gallery\">" in result.content
    assert "<div class=\"card-style\">" in result.content
    assert "<img src=\"image1.jpg\" alt=\"Image 1\" class=\"img-style\">" in result.content
    assert "<img src=\"image2.jpg\" alt=\"Image 2\" class=\"img-style\">" in result.content
    assert "<img src=\"image3.jpg\" alt=\"Image 3\" class=\"img-style\">" in result.content


def test_bar_chart():
    """Test rendering of a bar chart with list comprehension in a function."""
    content = EXECUTABLE_MARKER + """<fasthtml>
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
</fasthtml>"""
    result = process_single_fasthtml_block(content)
    assert result.is_success
    assert "<div class=\"chart\">" in result.content
    assert "<div class=\"bar-container\">" in result.content
    assert "<div class=\"bar\" style=\"width: 50.0%\"></div>" in result.content


if __name__ == "__main__":
    test_simple_component()
    test_nested_components()
    test_component_function()
    test_list_comprehension()
    test_image_gallery()
    test_bar_chart()
    print("All tests passed!") 