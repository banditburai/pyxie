"""Debug script for testing the full FastHTML rendering pipeline."""

import logging
from pathlib import Path
from pyxie.types import ContentBlock, ContentItem
from pyxie.renderer import render_content
from pyxie.parser import parse
from pyxie.layouts import layout, registry
from fastcore.xml import FT, Div
import fasthtml.common as ft_common
import textwrap

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def setup_test_layout():
    """Set up a test layout."""
    registry._layouts.clear()
    
    @layout("default")
    def default_layout(content: str = "") -> ft_common.FT:
        """Default layout that just renders the content directly."""
        return Div(content, data_slot="content")

def create_test_item(content: str, content_type: str = "ft") -> ContentItem:
    """Create a test ContentItem."""
    if content_type == "ft":
        blocks = {"content": [ContentBlock(
            tag_name="fasthtml",
            content=f"<ft>\n{content}\n</ft>",  # Wrap content in <ft> tags
            attrs_str="",
            content_type="ft"
        )]}
    else:
        blocks = {"content": [ContentBlock(
            tag_name="content",
            content=content,
            attrs_str="",
            content_type=content_type
        )]}
    
    return ContentItem(
        source_path=Path("test.md"),
        metadata={"layout": "default"},
        blocks=blocks
    )

def test_simple_component():
    """Test the full pipeline with a simple component."""
    content = """
show(Div("Hello World", cls="test-class"))
"""
    item = create_test_item(content)
    result = render_content(item)
    logger.info(f"Simple component result:\n{result}")

def test_nested_components():
    """Test the full pipeline with nested components."""
    content = """
component = Div(
    Div("Inner content", cls="inner"),
    cls="outer"
)
show(component)
"""
    item = create_test_item(content)
    result = render_content(item)
    logger.info(f"Nested components result:\n{result}")

def test_component_function():
    """Test the full pipeline with a component function."""
    content = """
def MyComponent(text):
    return Div(text, cls="custom")

show(MyComponent("Hello from function"))
"""
    item = create_test_item(content)
    result = render_content(item)
    logger.info(f"Component function result:\n{result}")

def test_multiple_blocks():
    """Test the full pipeline with multiple blocks."""
    content1 = 'show(Div("First component", cls="first"))'
    content2 = 'show(Div("Second component", cls="second"))'
    
    blocks = {"content": [
        ContentBlock(
            tag_name="fasthtml",
            content=f"<ft>\n{content1}\n</ft>",  # Wrap content in <ft> tags
            attrs_str="",
            content_type="ft"
        ),
        ContentBlock(
            tag_name="fasthtml",
            content=f"<ft>\n{content2}\n</ft>",  # Wrap content in <ft> tags
            attrs_str="",
            content_type="ft"
        )
    ]}
    
    item = ContentItem(
        source_path=Path("test.md"),
        metadata={"layout": "default"},
        blocks=blocks
    )
    
    result = render_content(item)
    logger.info(f"Multiple blocks result:\n{result}")

if __name__ == "__main__":
    setup_test_layout()
    
    logger.info("Testing simple component...")
    test_simple_component()
    
    logger.info("\nTesting nested components...")
    test_nested_components()
    
    logger.info("\nTesting component function...")
    test_component_function()
    
    logger.info("\nTesting multiple blocks...")
    test_multiple_blocks() 