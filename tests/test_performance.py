"""Tests for performance benchmarks."""

import pytest
import time
from pathlib import Path
from typing import Dict, Any
from mistletoe.block_token import add_token
from pyxie.parser import parse_frontmatter, FastHTMLToken, ScriptToken, ContentBlockToken
from pyxie.types import ContentItem, ContentBlock
from pyxie.renderer import render_content
from pyxie.layouts import layout
from fasthtml.common import *

# Register content block tokens
add_token(FastHTMLToken)
add_token(ScriptToken)
add_token(ContentBlockToken)

@pytest.fixture
def test_content(request) -> str:
    """Generate test content of different sizes."""
    size = request.param
    if size == "small":
        return """---
title: Small Test
date: 2024-03-20
---

<content>
# Small Test

This is a small test document.
</content>
"""
    elif size == "medium":
        return """---
title: Medium Test
date: 2024-03-20
---

<content>
# Medium Test

This is a medium test document with multiple sections.

## Section 1

Content for section 1.

## Section 2

Content for section 2.

## Section 3

Content for section 3.
</content>
"""
    else:  # large
        return """---
title: Large Test
date: 2024-03-20
---

<content>
# Large Test

This is a large test document with multiple sections and complex content.

## Section 1

Content for section 1 with lists:

- Item 1
- Item 2
- Item 3

## Section 2

Content for section 2 with code:

```python
def test_function():
    return "Hello, World!"
```

## Section 3

Content for section 3 with FastHTML:

<ft>
def Greeting(name="World"):
    return Div(
        H1(f"Hello, {name}!"),
        P("Welcome to my site.")
    )

show(Greeting())
</ft>

## Section 4

Content for section 4 with tables:

| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Row 1    | Data     | Data     |
| Row 2    | Data     | Data     |
| Row 3    | Data     | Data     |

## Section 5

Final section with more content.
</content>
"""

@pytest.mark.parametrize("test_content", ["small", "medium", "large"], indirect=True)
def test_parser_performance(test_content: str):
    """Test parser performance with different content sizes."""
    start_time = time.time()
    
    # Parse content multiple times
    iterations = 100
    for _ in range(iterations):
        metadata, content = parse_frontmatter(test_content)
    
    end_time = time.time()
    duration = end_time - start_time
    
    # Calculate average time per parse
    avg_time = duration / iterations
    print(f"\nParser performance for {len(test_content)} bytes:")
    print(f"Total time: {duration:.4f} seconds")
    print(f"Average time: {avg_time:.4f} seconds per parse")
    
    # Assert reasonable performance
    assert avg_time < 0.01, f"Parsing took too long: {avg_time:.4f} seconds per parse"

def test_slot_filling_performance():
    """Test slot filling performance."""
    # Create a complex layout with multiple slots
    @layout("test")
    def test_layout(title: str = "") -> FT:
        return Div(
            H1(title),
            Div(None, data_slot="header"),
            Div(None, data_slot="nav"),
            Div(None, data_slot="sidebar"),
            Div(None, data_slot="content"),
            Div(None, data_slot="footer"),
            cls="layout"
        )
    
    # Create content blocks
    blocks = {
        "header": [ContentBlock(
            tag_name="header",
            content="# Site Header",
            attrs_str=""
        )],
        "nav": [ContentBlock(
            tag_name="nav",
            content="- [Home](#)\n- [About](#)\n- [Contact](#)",
            attrs_str=""
        )],
        "sidebar": [ContentBlock(
            tag_name="sidebar",
            content="## Categories\n- Category 1\n- Category 2\n- Category 3",
            attrs_str=""
        )],
        "content": [ContentBlock(
            tag_name="content",
            content="# Main Content\n\nThis is the main content area.",
            attrs_str=""
        )],
        "footer": [ContentBlock(
            tag_name="footer",
            content="© 2024 Test Site",
            attrs_str=""
        )]
    }
    
    # Create content item
    item = ContentItem(
        source_path=Path("test.md"),
        metadata={"layout": "test", "title": "Test Page"},
        blocks=blocks
    )
    
    start_time = time.time()
    
    # Render content multiple times
    iterations = 100
    for _ in range(iterations):
        html = render_content(item)
    
    end_time = time.time()
    duration = end_time - start_time
    
    # Calculate average time per render
    avg_time = duration / iterations
    print(f"\nSlot filling performance:")
    print(f"Total time: {duration:.4f} seconds")
    print(f"Average time: {avg_time:.4f} seconds per render")
    
    # Assert reasonable performance
    assert avg_time < 0.01, f"Slot filling took too long: {avg_time:.4f} seconds per render"

def test_rendering_performance():
    """Test rendering performance with a complex document."""
    # Create a complex document with various content types
    content = """---
title: Performance Test
date: 2024-03-20
layout: test
---

<content>
# Performance Test

## Markdown Content

This is a test of rendering performance with various content types:

- Lists
- Code blocks
- Tables
- FastHTML components

### Code Example

```python
def test_function():
    return "Hello, World!"
```

### Table Example

| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Data 1   | Data 2   | Data 3   |
| Data 4   | Data 5   | Data 6   |

### FastHTML Example

<ft>
def TestComponent():
    return Div(
        H1("Test Component"),
        P("This is a test component.")
    )

show(TestComponent())
</ft>

### Script Example

<script>
console.log("Performance test");
</script>
</content>
"""
    
    # Register test layout
    @layout("test")
    def test_layout(title: str = "") -> FT:
        return Div(
            H1(title),
            Div(None, data_slot="content"),
            cls="test-layout"
        )
    
    # Parse content
    metadata, content = parse_frontmatter(content)
    
    # Create content blocks
    blocks = {
        "content": [ContentBlock(
            tag_name="content",
            content=content,
            attrs_str=""
        )]
    }
    
    # Create content item
    item = ContentItem(
        source_path=Path("test.md"),
        metadata=metadata,
        blocks=blocks
    )
    
    start_time = time.time()
    
    # Render content multiple times
    iterations = 50
    for _ in range(iterations):
        html = render_content(item)
    
    end_time = time.time()
    duration = end_time - start_time
    
    # Calculate average time per render
    avg_time = duration / iterations
    print(f"\nRendering performance:")
    print(f"Total time: {duration:.4f} seconds")
    print(f"Average time: {avg_time:.4f} seconds per render")
    
    # Assert reasonable performance
    assert avg_time < 0.02, f"Rendering took too long: {avg_time:.4f} seconds per render" 