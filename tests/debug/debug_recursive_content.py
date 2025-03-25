"""Debug script to test recursive content processing."""

import logging
from pathlib import Path
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

def create_test_item(content: str, content_type: str = "markdown") -> ContentItem:
    """Create a test ContentItem with the given content."""
    return ContentItem(
        source_path=Path("test.md"),
        metadata={"layout": "default"},
        blocks={"content": [ContentBlock(
            tag_name="content",
            content=content,
            attrs_str="",
            content_type=content_type
        )]}
    )

def test_fasthtml_in_markdown():
    """Test FastHTML blocks inside markdown content."""
    logger.info("\n=== Testing FastHTML in Markdown ===")
    
    content = """
# Main Content

Here's a FastHTML component:

<ft>
def MyComponent():
    return Div(
        H1("Component Title"),
        P("Component content"),
        show(Div("Nested content"))
    )

show(MyComponent())
</ft>

More markdown content.
"""
    
    item = create_test_item(content, content_type="markdown")
    result = render_content(item)
    logger.info("FastHTML in markdown result:\n%s", result)
    
    # Check that both markdown and FastHTML were processed
    assert '<h1 id="main-content">Main Content</h1>' in result, "Top-level markdown not processed"
    assert '<h1>Component Title</h1>' in result, "FastHTML component not processed"
    assert '<p>Component content</p>' in result, "Component content not processed"
    assert '<div>Nested content</div>' in result, "Nested content not processed"

def test_multiple_fasthtml_blocks():
    """Test multiple FastHTML blocks in markdown."""
    logger.info("\n=== Testing Multiple FastHTML Blocks ===")
    
    content = """
# Multiple Components

First component:

<ft>
show(Div("First component content"))
</ft>

Second component:

<ft>
def SecondComponent():
    return Div(
        P("Second component content"),
        show(Div("Nested in second"))
    )

show(SecondComponent())
</ft>

End of content.
"""
    
    item = create_test_item(content, content_type="markdown")
    result = render_content(item)
    logger.info("Multiple FastHTML blocks result:\n%s", result)
    
    # Check that all components were processed
    assert '<h1 id="multiple-components">Multiple Components</h1>' in result, "Markdown not processed"
    assert '<div>First component content</div>' in result, "First component not processed"
    assert '<p>Second component content</p>' in result, "Second component not processed"
    assert '<div>Nested in second</div>' in result, "Nested content not processed"

def test_component_reuse():
    """Test reusing components in FastHTML."""
    logger.info("\n=== Testing Component Reuse ===")
    
    content = """
# Component Reuse

<ft>
def ReusableComponent(text):
    return Div(
        P(text),
        Div("Common nested content")
    )

# Show components individually
show(ReusableComponent("First usage"))
show(ReusableComponent("Second usage"))
</ft>

End of content.
"""
    
    item = create_test_item(content, content_type="markdown")
    result = render_content(item)
    logger.info("Component reuse result:\n%s", result)
    
    # Check component reuse
    assert '<h1 id="component-reuse">Component Reuse</h1>' in result, "Markdown not processed"
    assert '<p>First usage</p>' in result, "First component usage not processed"
    assert '<p>Second usage</p>' in result, "Second component usage not processed"
    assert result.count('Common nested content') == 2, "Nested content not reused"

if __name__ == "__main__":
    setup_test_layout()
    test_fasthtml_in_markdown()
    test_multiple_fasthtml_blocks()
    test_component_reuse() 