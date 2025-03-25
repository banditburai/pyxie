"""Debug script to investigate multiple blocks handling in render_content."""

import logging
from pathlib import Path
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

def create_test_item(blocks: list) -> ContentItem:
    """Create a test ContentItem with the given blocks."""
    return ContentItem(
        source_path=Path("test.md"),
        metadata={"layout": "default"},
        blocks={"content": blocks}
    )

def test_sequential_blocks():
    """Test sequential FastHTML blocks."""
    logger.info("\n=== Testing Sequential FastHTML Blocks ===")
    
    blocks = [
        ContentBlock(
            tag_name="fasthtml",
            content='<ft>\nshow(Div("First block", cls="first"))\n</ft>',
            attrs_str="",
            content_type="ft"
        ),
        ContentBlock(
            tag_name="fasthtml",
            content='<ft>\nshow(Div("Second block", cls="second"))\n</ft>',
            attrs_str="",
            content_type="ft"
        )
    ]
    
    item = create_test_item(blocks)
    result = render_content(item)
    logger.info("Sequential blocks result:\n%s", result)

def test_mixed_content_blocks():
    """Test mixed content type blocks."""
    logger.info("\n=== Testing Mixed Content Type Blocks ===")
    
    blocks = [
        ContentBlock(
            tag_name="fasthtml",
            content='<ft>\nshow(Div("FastHTML block", cls="ft"))\n</ft>',
            attrs_str="",
            content_type="ft"
        ),
        ContentBlock(
            tag_name="content",
            content="# Markdown block\n\nThis is markdown content.",
            attrs_str="",
            content_type="markdown"
        )
    ]
    
    item = create_test_item(blocks)
    result = render_content(item)
    logger.info("Mixed content blocks result:\n%s", result)

def test_block_with_variables():
    """Test blocks that share variables."""
    logger.info("\n=== Testing Blocks with Shared Variables ===")
    
    blocks = [
        ContentBlock(
            tag_name="fasthtml",
            content='<ft>\ndef MyComponent(text):\n    return Div(text, cls="custom")\n</ft>',
            attrs_str="",
            content_type="ft"
        ),
        ContentBlock(
            tag_name="fasthtml",
            content='<ft>\nshow(MyComponent("Using shared component"))\n</ft>',
            attrs_str="",
            content_type="ft"
        )
    ]
    
    item = create_test_item(blocks)
    result = render_content(item)
    logger.info("Blocks with shared variables result:\n%s", result)

def test_block_with_layout():
    """Test blocks with a custom layout."""
    logger.info("\n=== Testing Blocks with Custom Layout ===")
    
    @layout("custom")
    def custom_layout(content: str = "") -> ft_common.FT:
        return Div(
            Div("Header", cls="header"),
            Div(content, data_slot="content"),
            Div("Footer", cls="footer")
        )
    
    blocks = [
        ContentBlock(
            tag_name="fasthtml",
            content='<ft>\nshow(Div("First in layout", cls="first"))\n</ft>',
            attrs_str="",
            content_type="ft"
        ),
        ContentBlock(
            tag_name="fasthtml",
            content='<ft>\nshow(Div("Second in layout", cls="second"))\n</ft>',
            attrs_str="",
            content_type="ft"
        )
    ]
    
    item = ContentItem(
        source_path=Path("test.md"),
        metadata={"layout": "custom"},
        blocks={"content": blocks}
    )
    
    result = render_content(item)
    logger.info("Blocks with custom layout result:\n%s", result)

if __name__ == "__main__":
    setup_test_layout()
    
    test_sequential_blocks()
    test_mixed_content_blocks()
    test_block_with_variables()
    test_block_with_layout() 