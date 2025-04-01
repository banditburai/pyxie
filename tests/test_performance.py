"""Tests for performance benchmarks."""

import pytest
import time
import logging
from pathlib import Path
from typing import Dict, Any
from mistletoe import Document
from mistletoe.block_token import Heading, Paragraph, List, HtmlBlock
from mistletoe.block_token import add_token
from pyxie.parser import RawBlockToken, NestedContentToken, parse_frontmatter
from pyxie.types import ContentItem
from pyxie.renderer import render_content, PyxieRenderer
from pyxie.layouts import layout
from fasthtml.common import *

logger = logging.getLogger(__name__)

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
    
    # Create content with multiple sections
    content = """<header>
# Site Header
</header>

<nav>
- [Home](#)
- [About](#)
- [Contact](#)
</nav>

<sidebar>
## Categories
- Category 1
- Category 2
- Category 3
</sidebar>

<content>
# Main Content

This is the main content area.
</content>

<footer>
© 2024 Test Site
</footer>
"""
    
    # Create content item
    item = ContentItem(
        source_path=Path("test.md"),
        metadata={"layout": "test", "title": "Test Page"},
        content=content
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
</content>
"""
    
    # Create content item
    item = ContentItem(
        source_path=Path("test.md"),
        metadata={"layout": "test", "title": "Test Page"},
        content=content
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
    print(f"\nRendering performance:")
    print(f"Total time: {duration:.4f} seconds")
    print(f"Average time: {avg_time:.4f} seconds per render")
    
    # Assert reasonable performance
    assert avg_time < 0.01, f"Rendering took too long: {avg_time:.4f} seconds per render" 