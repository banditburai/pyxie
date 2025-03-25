#!/usr/bin/env python3

"""Test for counter component example from the user."""

import pytest
from pathlib import Path
from pyxie.renderer import render_content
from pyxie.types import ContentBlock, ContentItem

def test_counter_component_in_code_block():
    """Test that counter component example in code blocks is properly escaped."""
    markdown = """
# 3. Interactive Components

Here's a simple counter component:

```python
from components import IconifyIcon

def Counter(initial: int = 0): 
    \"\"\"A counter component with increment/decrement buttons and interactivity.\"\"\"
    return Div(
        Button(
            IconifyIcon(icon="lucide:minus", cls="w-4 h-4"),
            cls="px-2 py-1 bg-red-100 dark:bg-red-900 text-red-600 dark:text-red-300 rounded-l-lg",
            onclick="this.nextElementSibling.textContent = parseInt(this.nextElementSibling.textContent) - 1"
        ),
        Div(
            str(initial),
            cls="px-4 py-1 bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 font-mono"
        ),
        Button(
            IconifyIcon(icon="lucide:plus", cls="w-4 h-4"),
            cls="px-2 py-1 bg-green-100 dark:bg-green-900 text-green-600 dark:text-green-300 rounded-r-lg",
            onclick="this.previousElementSibling.textContent = parseInt(this.previousElementSibling.textContent) + 1"
        ),
        cls="inline-flex items-center"
    )
```

Use show() to render the counter component

```python
show(Counter(5))
```
    """
    
    # Create content item
    block = ContentBlock(tag_name="content", content=markdown, attrs_str="")
    item = ContentItem(
        source_path=Path("test.md"),
        metadata={},  # Empty metadata, no layout
        blocks={"content": [block]}
    )
    
    # Render the content
    html = render_content(item)
    
    # Check that counter component code is properly escaped and not executed
    assert "IconifyIcon" in html
    assert "Counter" in html
    assert "show(Counter(5))" in html
    
    # Check that the code tags are properly preserved
    assert '<pre><code class="language-python">' in html
    
    # Ensure no actual executed component is in the output
    assert "inline-flex items-center" in html
    assert '<div class="inline-flex items-center">' not in html

def test_counter_component_outside_code_block():
    """Test that counter component outside code blocks is executed."""
    # Note: Since we don't have the actual components module, we'll use a simplified version
    markdown = """
# Test Counter Component

Here's a regular FastHTML component:

<ft>
def Counter(initial=5):
    return f"<div class='counter'>Count: {initial}</div>"

show(Counter())
</ft>
    """
    
    # Create content item
    block = ContentBlock(tag_name="content", content=markdown, attrs_str="")
    item = ContentItem(
        source_path=Path("test.md"),
        metadata={},  # Empty metadata, no layout
        blocks={"content": [block]}
    )
    
    # Render the content
    html = render_content(item)
    
    # Check that the component was executed
    assert "<div class='counter'>Count: 5</div>" in html
    
    # Make sure the original source code is not in the output
    assert "def Counter" not in html
    assert "show(Counter())" not in html 