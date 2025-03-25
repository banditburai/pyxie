"""Debug script to investigate content processing issues in render_content."""

import logging
from pathlib import Path
from pyxie.types import ContentBlock, ContentItem
from pyxie.renderer import render_content
from pyxie.layouts import layout, registry
from fastcore.xml import FT, Div
import fasthtml.common as ft_common
from pyxie.fasthtml import render_fasthtml

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def normalize_html(html: str) -> str:
    """Normalize HTML string by removing extra whitespace."""
    return ' '.join(html.split())

def setup_test_layout():
    """Set up a test layout."""
    registry._layouts.clear()
    
    @layout("default")
    def default_layout(content: str = "") -> ft_common.FT:
        """Default layout that just renders the content directly."""
        return Div(content, data_slot="content")

def create_test_item(content: str, content_type: str = "ft") -> ContentItem:
    """Create a test ContentItem with the given content."""
    if content_type == "ft":
        blocks = {"content": [ContentBlock(
            tag_name="fasthtml",
            content=f"<ft>\n{content}\n</ft>",
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

def test_content_type_preservation():
    """Test if content type is preserved through the rendering pipeline."""
    logger.info("\n=== Testing Content Type Preservation ===")
    
    # Test FastHTML content
    ft_content = 'show(Div("FastHTML content", cls="ft-test"))'
    
    # First test direct FastHTML rendering
    direct_result = render_fasthtml(ft_content)
    logger.info("Direct FastHTML rendering result:\n%s", direct_result)
    
    # Then test through render_content
    ft_item = create_test_item(ft_content, content_type="ft")
    render_result = render_content(ft_item)
    logger.info("Render content result:\n%s", render_result)
    
    # Compare the results - normalize strings before comparison
    assert normalize_html(direct_result.content) == normalize_html(render_result), \
        f"Content type not preserved\nExpected: {direct_result.content}\nGot: {render_result}"

def test_component_definition_and_usage():
    """Test how component definitions are handled and preserved."""
    logger.info("\n=== Testing Component Definition and Usage ===")
    
    # First test direct FastHTML execution
    component_def = """
def MyComponent(text):
    return Div(text, cls="custom")

show(MyComponent("Test"))
"""
    direct_result = render_fasthtml(component_def)
    logger.info("Direct component definition result:\n%s", direct_result)
    
    # Then test through render_content
    ft_item = create_test_item(component_def, content_type="ft")
    render_result = render_content(ft_item)
    logger.info("Render content component result:\n%s", render_result)
    
    # Compare the results - normalize strings before comparison
    assert normalize_html(direct_result.content) == normalize_html(render_result), \
        f"Component definition not preserved\nExpected: {direct_result.content}\nGot: {render_result}"

def test_layout_content_processing():
    """Test how content is processed within layouts."""
    logger.info("\n=== Testing Layout Content Processing ===")
    
    @layout("custom")
    def custom_layout(content: str = "") -> ft_common.FT:
        return Div(
            Div("Header", cls="header"),
            Div(content, data_slot="content"),
            Div("Footer", cls="footer")
        )
    
    # Test FastHTML content in layout
    ft_content = 'show(Div("FastHTML in layout", cls="ft-test"))'
    
    # First test direct FastHTML rendering
    direct_result = render_fasthtml(ft_content)
    logger.info("Direct FastHTML rendering result:\n%s", direct_result)
    
    # Then test through layout
    custom_item = ContentItem(
        source_path=Path("test.md"),
        metadata={"layout": "custom"},
        blocks={"content": [ContentBlock(
            tag_name="fasthtml",
            content=f"<ft>\n{ft_content}\n</ft>",
            attrs_str="",
            content_type="ft"
        )]}
    )
    layout_result = render_content(custom_item)
    logger.info("Layout rendering result:\n%s", layout_result)
    
    # Check if FastHTML was properly processed within layout
    assert 'class="ft-test"' in layout_result, "FastHTML not properly processed in layout"

def test_content_block_processing():
    """Test how content blocks are processed individually."""
    logger.info("\n=== Testing Content Block Processing ===")
    
    # Test a FastHTML block
    ft_block = ContentBlock(
        tag_name="fasthtml",
        content='<ft>\nshow(Div("FastHTML block", cls="ft"))\n</ft>',
        attrs_str="",
        content_type="ft"
    )
    
    # Test a markdown block
    md_block = ContentBlock(
        tag_name="content",
        content="# Markdown block\n\nThis is markdown content.",
        attrs_str="",
        content_type="markdown"
    )
    
    # Process each block individually
    ft_item = ContentItem(
        source_path=Path("test.md"),
        metadata={"layout": "default"},
        blocks={"content": [ft_block]}
    )
    ft_result = render_content(ft_item)
    logger.info("FastHTML block result:\n%s", ft_result)
    
    md_item = ContentItem(
        source_path=Path("test.md"),
        metadata={"layout": "default"},
        blocks={"content": [md_block]}
    )
    md_result = render_content(md_item)
    logger.info("Markdown block result:\n%s", md_result)

if __name__ == "__main__":
    setup_test_layout()
    
    test_content_type_preservation()
    test_component_definition_and_usage()
    test_layout_content_processing()
    test_content_block_processing() 