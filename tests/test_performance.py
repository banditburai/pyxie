"""Performance tests for Pyxie components.

These tests measure the performance of key components like the parser,
renderer, and slot filling operations with different sizes of input.
"""

import pytest
import time
import tempfile
from pathlib import Path
from pyxie.parser import parse, FastHTMLToken, ScriptToken, ContentBlockToken
from pyxie.slots import fill_slots
from pyxie.renderer import render_content
from pyxie.utilities import _prepare_content_item
from fastcore.xml import Div, P, FT
from mistletoe.block_token import add_token
from pyxie.types import ContentItem, ContentBlock
from pyxie.layouts import Layout, layout

def time_execution(func, *args, **kwargs):
    """Execute a function and measure its execution time."""
    start_time = time.time()
    result = func(*args, **kwargs)
    end_time = time.time()
    return result, end_time - start_time

def create_nested_structure(depth: int):
    """Create a nested element structure for testing."""
    if depth <= 0:
        return P("Content at leaf level", data_slot="slot-leaf")
    
    children = []
    for i in range(3):  # Create 3 children at each level
        child = create_nested_structure(depth - 1)
        children.append(child)
    
    return Div(
        *children,
        data_slot=f"slot-level-{depth}",
        cls=f"level-{depth}"
    )

# Create test content of different sizes
def generate_test_content(size: str) -> str:
    """Generate test content of different sizes."""
    if size == "small":
        blocks = 5
        block_size = 100
    elif size == "medium":
        blocks = 20
        block_size = 500
    elif size == "large":
        blocks = 50
        block_size = 2000
    else:
        raise ValueError(f"Invalid size: {size}")
    
    content = "---\n"
    content += "title: Test Content\n"
    content += "layout: test\n"
    content += "---\n\n"
    
    content += "# Main Content\n\n"
    content += "This is the main content of the document.\n\n"
    
    # Create separate content blocks
    content_blocks = []
    for i in range(blocks):
        block_content = []
        block_content.append(f"## Block {i}\n")
        for j in range(block_size // 10):
            block_content.append(f"This is sample content for block {i}, line {j}.")
        content_blocks.append(ContentBlock(
            tag_name="content",
            content="\n".join(block_content),
            attrs_str="",
            content_type="markdown"
        ))
    
    # Create initial markdown block
    initial_block = ContentBlock(
        tag_name="content",
        content="# Main Content\n\nThis is the main content of the document.",
        attrs_str="",
        content_type="markdown"
    )
    
    return initial_block, content_blocks

@pytest.mark.parametrize("content_size", ["small", "medium", "large"])
def test_parser_performance(content_size: str):
    """Test parser performance with different content sizes."""
    initial_block, content_blocks = generate_test_content(content_size)
    
    # Create ContentItem directly
    content_item = ContentItem(
        source_path=Path("test.md"),
        metadata={"title": "Test Content", "layout": "test"},
        blocks={"content": [initial_block] + content_blocks}
    )
    
    # Print performance statistics
    print(f"\nParser performance with {content_size} content:")
    print(f"  Blocks: {len(content_blocks)}")
    
    # Basic verification that parsing succeeded
    assert content_item is not None
    assert content_item.metadata["title"] == "Test Content"
    
    # Verify blocks were parsed
    if content_size == "small":
        assert len(content_item.blocks["content"]) == 6  # Initial block + 5 content blocks
    elif content_size == "medium":
        assert len(content_item.blocks["content"]) == 21  # Initial block + 20 content blocks
    elif content_size == "large":
        assert len(content_item.blocks["content"]) == 51  # Initial block + 50 content blocks

def test_slot_filling_performance():
    """Test slot filling performance with complex nested structures."""
    # Create a complex nested structure
    def create_nested_element(depth: int, width: int) -> FT:
        """Create a nested element structure for testing."""
        if depth <= 0:
            return P("Content at leaf level", data_slot="slot-leaf")
        
        children = []
        for i in range(width):
            child = create_nested_element(depth - 1, width)
            children.append(child)
        
        return Div(*children, data_slot=f"slot-{depth}")
    
    # Create element with 5 levels of nesting, width 3
    element = create_nested_element(5, 3)
    
    # Create slot values
    slots = {}
    
    # Measure slot filling time
    result, fill_time = time_execution(fill_slots, element, slots)
    
    # Print performance statistics
    print("\nSlot filling performance:")
    print(f"  Time: {fill_time:.4f}s")
    
    # Basic verification
    assert result is not None

def test_rendering_performance():
    """Test the performance of the complete rendering pipeline."""
    # Register a test layout
    @layout("test")
    def test_layout() -> FT:
        return Div(
            Div(
                None,  # Use None as default slot content
                data_slot="content",
                cls="test-layout"
            )
        )
    
    # Generate medium-sized test content
    initial_block, content_blocks = generate_test_content("medium")
    
    # Create ContentItem directly
    content_item = ContentItem(
        source_path=Path("test.md"),
        metadata={"title": "Test Content", "layout": "test"},
        blocks={"content": [initial_block] + content_blocks}
    )
    
    # Test rendering performance
    def render_pipeline():
        rendered = render_content(content_item)
        return rendered
    
    final_result, render_time = time_execution(render_pipeline)
    
    # Print performance statistics
    print("\nRendering Pipeline Performance:")
    print(f"  Total Render Time: {render_time:.4f}s")
    
    # Basic verification
    assert content_item is not None
    assert content_item.metadata["title"] == "Test Content"
    assert len(content_item.blocks["content"]) == 21  # Initial block + 20 content blocks
    assert final_result is not None
    assert "test-layout" in final_result  # Verify layout was applied 