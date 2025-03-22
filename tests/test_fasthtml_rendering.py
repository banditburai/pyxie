"""
Tests for FastHTML rendering functionality.

These tests focus on verifying that FastHTML components render correctly to XML,
especially for complex nested component structures.
"""

import logging

from pyxie.fasthtml import render_fasthtml, EXECUTABLE_MARKER, RenderResult
import fasthtml.common as ft_common
from pyxie.parser import find_content_blocks, find_code_blocks
from pyxie.renderer import render_block
from pyxie.layouts import registry

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
    result = render_fasthtml(content)
    assert hasattr(result, 'success'), "Result object doesn't have a success attribute"
    assert result.success
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
    result = render_fasthtml(content)
    assert hasattr(result, 'success'), "Result object doesn't have a success attribute"
    assert result.success
    assert "<div class=\"outer\">" in result.content
    assert "<div class=\"inner\">Inner content</div>" in result.content


def test_component_function():
    """Test rendering of a component function."""
    content = EXECUTABLE_MARKER + """<fasthtml>
def MyComponent(text):
    return Div(text, cls="custom")
    
show(MyComponent("Hello from function"))
</fasthtml>"""
    result = render_fasthtml(content)
    assert hasattr(result, 'success'), "Result object doesn't have a success attribute"
    assert result.success
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
    result = render_fasthtml(content)
    assert hasattr(result, 'success'), "Result object doesn't have a success attribute"
    assert result.success
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
    result = render_fasthtml(content)
    assert hasattr(result, 'success'), "Result object doesn't have a success attribute"
    assert result.success
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
    result = render_fasthtml(content)
    assert hasattr(result, 'success'), "Result object doesn't have a success attribute"
    assert result.success
    assert "<div class=\"chart\">" in result.content
    assert "<div class=\"bar-container\">" in result.content
    assert "<div class=\"bar\" style=\"width: 50.0%\"></div>" in result.content


def test_fasthtml_execution_in_content():
    """Test that FastHTML blocks are properly executed and rendered in content."""
    # Create test content with FastHTML - using the components already imported
    test_content = EXECUTABLE_MARKER + """<fasthtml>
# Use Button component that's already imported in this test file
show(Button("Click me", cls="test-button"))
</fasthtml>"""
    
    # Render the block
    result = render_fasthtml(test_content)
    
    # The rendered content should be successful
    assert hasattr(result, 'success'), "Result object doesn't have a success attribute"
    assert result.success, f"Rendering failed: {result.error}"
    
    # The rendered content should contain the button but not the show() function call
    assert 'class="test-button"' in result.content, "Button not rendered"
    assert '<button' in result.content, "Button element not found"
    assert 'show(' not in result.content, "Raw show() function call found in output"


def test_multiple_fasthtml_blocks_execution():
    """Test execution of multiple FastHTML blocks in a single content."""
    # Test with properly formatted content for a single block first
    from pyxie.parser import find_content_blocks, find_code_blocks
    from pyxie.renderer import render_block
    
    # Create markdown content with two FastHTML blocks
    markdown_content = """
# Test Page with Multiple FastHTML Blocks

<fasthtml>
show(Div("First component", cls="first"))
</fasthtml>

Some regular markdown content in between the blocks.

<fasthtml>
show(Div("Second component", cls="second"))
</fasthtml>
"""
    
    # Find code blocks first (required for the parser)
    code_blocks = find_code_blocks(markdown_content)
    
    # Parse the content to find blocks
    blocks = find_content_blocks(markdown_content, warn_unclosed=False)
    fasthtml_blocks = blocks.get('fasthtml', [])
    
    # There should be two fasthtml blocks
    assert len(fasthtml_blocks) == 2, f"Expected 2 FastHTML blocks, found {len(fasthtml_blocks)}"
    
    # Render each block and check the output
    for i, block in enumerate(fasthtml_blocks):
        result = render_block(block)
        assert result.success, f"Failed to render block {i}: {result.error}"
        assert 'show(' not in result.content, f"Block {i} contains raw show() call"
        
        # Check for specific content in each block
        if i == 0:
            assert 'class="first"' in result.content, "First component not rendered"
        elif i == 1:
            assert 'class="second"' in result.content, "Second component not rendered"


def test_fasthtml_with_content_type_ft():
    """Test that FastHTML blocks with content_type='ft' are still properly executed."""
    from pyxie.types import ContentBlock
    from pyxie.renderer import render_block
    
    # Create a FastHTML block with content_type="ft"
    content = EXECUTABLE_MARKER + """<fasthtml>
show(Div("This should execute even with ft content type", cls="test-ft-div"))
</fasthtml>"""
    
    # Create the content block with content_type="ft"
    block = ContentBlock(
        name="fasthtml",
        content=content,
        content_type="ft",  # This is the key part - setting content_type to "ft"
        params={},
        index=0
    )
    
    # Render the block
    result = render_block(block)
    
    # Check that it executed properly despite the content_type
    assert result.success, f"Rendering failed: {result.error}"
    assert '<div class="test-ft-div">' in result.content, "Div not rendered correctly"
    assert 'show(' not in result.content, "Raw show() function call found in output"


def test_integrated_fasthtml_parsing_and_rendering():
    """Test the full integration path from parsing markdown to rendering FastHTML."""
    from pyxie.parser import find_content_blocks, find_code_blocks
    from pyxie.types import ContentBlock
    from pyxie.renderer import render_block
    from pyxie.fasthtml import EXECUTABLE_MARKER

    # Create a FastHTML block with executable marker
    fasthtml_content = EXECUTABLE_MARKER + """<fasthtml>
show(Div("This is a FastHTML component in content", cls="integration-test"))
</fasthtml>"""

    # Create a ContentBlock directly
    block = ContentBlock(
        name="fasthtml",
        content=fasthtml_content,
        content_type="markdown",  # Use markdown content type
        params={},
        index=0
    )
    
    # Render the block directly
    result = render_block(block)
    
    # Verify the rendering was successful
    assert result.success, f"FastHTML block rendering failed: {result.error}"
    
    # Check that it rendered the component correctly
    assert '<div class="integration-test">' in result.content, "FastHTML component not found in rendered output"
    assert 'show(' not in result.content, "Raw FastHTML code found in rendered output"


def test_content_block_type_rendering():
    """Test how different content_type values affect FastHTML execution."""
    from pyxie.types import ContentBlock
    from pyxie.renderer import render_block
    
    # Get a basic executable FastHTML content block
    base_content = EXECUTABLE_MARKER + """<fasthtml>
show(Div("This is test content", cls="test-type-div"))
</fasthtml>"""
    
    # Test various content_type values that might be set during parsing
    content_types = ["", None, "md", "markdown", "html", "ft"]
    
    for ct in content_types:
        # Create a block with each content type
        block = ContentBlock(
            name="fasthtml",
            content=base_content,
            content_type=ct,
            params={},
            index=0
        )
        
        # Render the block and check the result
        result = render_block(block)
        assert result.success, f"Rendering failed with content_type={ct}: {result.error}"
        assert '<div class="test-type-div">' in result.content, f"Div not rendered correctly with content_type={ct}"
        assert 'show(' not in result.content, f"Raw show() call found in output with content_type={ct}"


def test_problematic_fasthtml_formats():
    """Test handling of problematic FastHTML formats that might occur in real-world usage."""
    from pyxie.fasthtml import render_fasthtml, EXECUTABLE_MARKER
    
    # Test case 1: Content with the marker but without proper <fasthtml> tags
    # This simulates a case where the parser added the marker but tags were altered
    content1 = EXECUTABLE_MARKER + """
show(Div("This should still execute even without proper tags", cls="test-problematic"))
"""
    
    result1 = render_fasthtml(content1)
    assert hasattr(result1, 'success'), "Result object doesn't have a success attribute"
    assert result1.success, f"Failed to process content without tags: {result1.error}"
    assert '<div class="test-problematic">' in result1.content, "Component not rendered correctly"
    
    # Test case 2: Content with the marker and malformed tags
    content2 = EXECUTABLE_MARKER + """<fasthtml>
show(Div("This has malformed tags", cls="test-malformed"))
</Fasthtml>"""  # Note the capitalization mismatch
    
    result2 = render_fasthtml(content2)
    assert hasattr(result2, 'success'), "Result object doesn't have a success attribute"
    assert result2.success, f"Failed to process content with malformed tags: {result2.error}"
    assert '<div class="test-malformed">' in result2.content, "Component not rendered with malformed tags"
    
    # Test case 3: Content with extra text outside the tags
    content3 = EXECUTABLE_MARKER + """Some text before
<fasthtml>
show(Div("This has text outside tags", cls="test-outside"))
</fasthtml>
Some text after"""
    
    result3 = render_fasthtml(content3)
    assert hasattr(result3, 'success'), "Result object doesn't have a success attribute"
    assert result3.success, f"Failed to process content with text outside tags: {result3.error}"
    assert '<div class="test-outside">' in result3.content, "Component not rendered with outside text"


if __name__ == "__main__":
    test_simple_component()
    test_nested_components()
    test_component_function()
    test_list_comprehension()
    test_image_gallery()
    test_bar_chart()
    test_fasthtml_execution_in_content()
    test_multiple_fasthtml_blocks_execution()
    test_fasthtml_with_content_type_ft()
    test_integrated_fasthtml_parsing_and_rendering()
    test_content_block_type_rendering()
    test_problematic_fasthtml_formats()
    print("All tests passed!") 