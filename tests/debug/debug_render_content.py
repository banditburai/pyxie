"""Debug script to test render_content assumptions and behavior."""

import logging
from pathlib import Path
from typing import Dict, Any
from pyxie.types import ContentBlock, ContentItem
from pyxie.renderer import render_content
from pyxie.layouts import layout, registry
from fastcore.xml import FT, Div
import fasthtml.common as ft_common

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def setup_test_layout():
    """Set up a test layout."""
    registry._layouts.clear()
    
    @layout("default")
    def default_layout(content: str = "") -> ft_common.FT:
        """Default layout that just renders the content directly."""
        return Div(content, data_slot="content")

def create_test_item(content: str) -> ContentItem:
    """Create a test ContentItem with the given content."""
    
    blocks = {"content": [ContentBlock(
        tag_name="fasthtml",
        content=f"<ft>\n{content}\n</ft>",  # Wrap content in <ft> tags
        attrs_str=""
    )]}
    
    return ContentItem(
        source_path=Path("test.md"),
        metadata={"layout": "default"},
        blocks=blocks
    )

def test_content_type_handling():
    """Test how render_content handles different content types."""
    logger.info("\n=== Testing Content Type Handling ===")
    
    # Test FastHTML content
    ft_content = """
show(Div("FastHTML content", cls="ft-test"))
"""
    ft_item = create_test_item(ft_content)
    ft_result = render_content(ft_item)
    logger.info("FastHTML content result:\n%s", ft_result)
    
    # Test markdown content
    md_content = """
# Markdown Content

This is regular markdown content.
"""
    md_item = create_test_item(md_content)
    md_result = render_content(md_item)
    logger.info("Markdown content result:\n%s", md_result)

def test_fasthtml_block_processing():
    """Test how render_content processes FastHTML blocks."""
    logger.info("\n=== Testing FastHTML Block Processing ===")
    
    # Test simple FastHTML block
    simple_content = 'show(Div("Simple block", cls="simple"))'
    simple_item = create_test_item(simple_content)
    simple_result = render_content(simple_item)
    logger.info("Simple FastHTML block result:\n%s", simple_result)
    
    # Test complex FastHTML block with function
    complex_content = """
def MyComponent(text):
    return Div(text, cls="custom")

show(MyComponent("Complex block"))
"""
    complex_item = create_test_item(complex_content)
    complex_result = render_content(complex_item)
    logger.info("Complex FastHTML block result:\n%s", complex_result)

def test_layout_interaction():
    """Test how render_content interacts with layouts."""
    logger.info("\n=== Testing Layout Interaction ===")
    
    # Test with default layout
    default_content = 'show(Div("Default layout", cls="default"))'
    default_item = create_test_item(default_content)
    default_result = render_content(default_item)
    logger.info("Default layout result:\n%s", default_result)
    
    # Test with custom layout
    @layout("custom")
    def custom_layout(content: str = "") -> ft_common.FT:
        return Div(
            Div("Header", cls="header"),
            Div(content, data_slot="content"),
            Div("Footer", cls="footer")
        )
    
    custom_item = ContentItem(
        source_path=Path("test.md"),
        metadata={"layout": "custom"},
        blocks={"content": [ContentBlock(
            tag_name="fasthtml",
            content='<ft>\nshow(Div("Custom layout", cls="custom"))\n</ft>',
            attrs_str=""
        )]}
    )
    custom_result = render_content(custom_item)
    logger.info("Custom layout result:\n%s", custom_result)

def test_multiple_blocks():
    """Test how render_content handles multiple blocks."""
    logger.info("\n=== Testing Multiple Blocks ===")
    
    # Create multiple blocks
    blocks = {
        "content": [
            ContentBlock(
                tag_name="fasthtml",
                content='<ft>\nshow(Div("First block", cls="first"))\n</ft>',
                attrs_str=""
            ),
            ContentBlock(
                tag_name="content",
                content="Some markdown content",
                attrs_str=""
            ),
            ContentBlock(
                tag_name="fasthtml",
                content='<ft>\nshow(Div("Second block", cls="second"))\n</ft>',
                attrs_str=""
            )
        ]
    }
    
    multi_item = ContentItem(
        source_path=Path("test.md"),
        metadata={"layout": "default"},
        blocks=blocks
    )
    
    multi_result = render_content(multi_item)
    logger.info("Multiple blocks result:\n%s", multi_result)

def test_error_handling():
    """Test how render_content handles errors."""
    logger.info("\n=== Testing Error Handling ===")
    
    # Test invalid Python syntax
    invalid_content = """
show(Div("Invalid syntax"
"""
    invalid_item = create_test_item(invalid_content)
    invalid_result = render_content(invalid_item)
    logger.info("Invalid syntax result:\n%s", invalid_result)
    
    # Test undefined variable
    undefined_content = """
show(undefined_component)
"""
    undefined_item = create_test_item(undefined_content)
    undefined_result = render_content(undefined_item)
    logger.info("Undefined variable result:\n%s", undefined_result)

if __name__ == "__main__":
    setup_test_layout()
    
    test_content_type_handling()
    test_fasthtml_block_processing()
    test_layout_interaction()
    test_multiple_blocks()
    test_error_handling() 