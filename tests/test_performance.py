"""Performance tests for Pyxie components.

These tests measure the performance of key components like the parser,
renderer, and slot filling operations with different sizes of input.
"""

import pytest
import time
import tempfile
from pyxie.parser import parse
from pyxie.slots import fill_slots
from fastcore.xml import Div, P, FT

def time_execution(func, *args, **kwargs):
    """Time the execution of a function."""
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
    
    for i in range(blocks):
        content += f"\n<block{i}>\n"
        # Generate block content
        for j in range(block_size // 10):
            content += f"This is sample content for block {i}, line {j}.\n"
        content += f"</block{i}>\n"
    
    return content

@pytest.mark.parametrize("content_size", ["small", "medium", "large"])
def test_parser_performance(content_size: str):
    """Test parser performance with different content sizes."""
    content = generate_test_content(content_size)
    
    # Measure parsing time
    result, parse_time = time_execution(parse, content)
    
    # Print performance statistics
    print(f"\nParser performance with {content_size} content:")
    print(f"  Time: {parse_time:.4f}s")
    
    # Basic verification that parsing succeeded
    assert result is not None
    assert result.metadata["title"] == "Test Content"
    
    # Verify blocks were parsed
    if content_size == "small":
        assert len(result.blocks) == 5
    elif content_size == "medium":
        assert len(result.blocks) == 20
    elif content_size == "large":
        assert len(result.blocks) == 50

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
    content = generate_test_content("medium")
    
    # Create a temporary file with the content
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".md") as temp_file:
        temp_file.write(content)
        temp_file.flush()
        
        # Function to measure - only use the parser part for now
        def parse_content():
            return parse(content)
        
        # Measure parsing time
        result, parse_time = time_execution(parse_content)
        
        # Print performance statistics
        print("\nParsing performance:")
        print(f"  Time: {parse_time:.4f}s")
        
        # Basic verification
        assert result is not None
        assert result.metadata["title"] == "Test Content"
        assert len(result.blocks) > 0 