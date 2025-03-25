"""Debug script for testing nested content handling."""

import logging
from pathlib import Path
from mistletoe import Document
from mistletoe.block_token import add_token
from pyxie.parser import FastHTMLToken, ContentBlockToken
from pyxie.renderer import PyxieHTMLRenderer
from pyxie.types import ContentBlock, ContentItem
from pyxie.renderer import render_content
from pyxie.layouts import layout, registry
import fasthtml.common as ft_common

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def setup_test_layout():
    """Set up a test layout."""
    registry._layouts.clear()
    
    @layout("default")
    def default_layout(content: str = "") -> ft_common.FT:
        """Default layout that just renders the content directly."""
        return ft_common.Div(content, data_slot="content")

def create_test_item(content: str) -> ContentItem:
    """Create a test ContentItem with the given content."""
    return ContentItem(
        source_path=Path("test.md"),
        metadata={"layout": "default"},
        blocks={"content": [ContentBlock(
            tag_name="content",
            content=content,
            attrs_str="",            
        )]}
    )

def test_nested_content():
    """Test handling of nested content with FastHTML and markdown."""
    # Test case 1: Markdown with FastHTML blocks
    content1 = """
# Main Heading

This is a paragraph with **bold** text.

<ft>
show(Div("FastHTML content"))
</ft>

## Subheading

More markdown content with `code`.
"""
    logger.info("Testing markdown with FastHTML blocks...")
    result1 = render_content(create_test_item(content1))
    logger.info(f"Result 1:\n{result1}")
    
    # Test case 2: FastHTML with components
    content2 = """
<ft>
def MyComponent():
    return Div(
        "This is FastHTML content",
        P("With a paragraph"),
        Ul(
            Li("List item 1"),
            Li("List item 2")
        )
    )

show(MyComponent())
</ft>
"""
    logger.info("\nTesting FastHTML with components...")
    result2 = render_content(create_test_item(content2))
    logger.info(f"Result 2:\n{result2}")
    
    # Test case 3: Complex nesting
    content3 = """
<content>
# Top Level

<ft>
def NestedComponent():
    return Div(
        "Nested FastHTML content",
        P("With a paragraph"),
        show(Div("Deeply nested FastHTML"))  # Direct show() call for nested content
    )

show(NestedComponent())
</ft>

## Bottom Level

More markdown content.
</content>
"""
    logger.info("\nTesting complex nesting...")
    result3 = render_content(create_test_item(content3))
    logger.info(f"Result 3:\n{result3}")

if __name__ == "__main__":
    setup_test_layout()
    test_nested_content() 