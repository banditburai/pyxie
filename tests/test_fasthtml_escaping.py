"""Tests to ensure FastHTML in code blocks is handled correctly."""

import pytest
from mistletoe import Document
from pyxie.renderer import render_content
from pyxie.parser import parse
from pyxie.types import ContentBlock, ContentItem
from pyxie.layouts import layout, registry
from pyxie.fasthtml import render_fasthtml
from fastcore.xml import FT, Div
from pathlib import Path
import re

@pytest.fixture(autouse=True)
def setup_test_layout():
    """Set up test layout for all tests."""
    # Clear any existing layouts
    registry._layouts.clear()
    
    @layout("default")
    def default_layout(content: str = "") -> FT:
        """Default layout that just renders the content directly."""
        return Div(data_slot="content")
        
    @layout("basic")
    def basic_layout(content: str = "") -> FT:
        """Basic layout that just renders the content directly."""
        return Div(data_slot="content")

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

def test_fasthtml_in_code_blocks():
    """Test that FastHTML in code blocks is treated as literal text."""
    markdown = """
# Test FastHTML in Code Blocks

Regular paragraph with text.

```python
# Here's some Python code with FastHTML
from fasthtml.common import *

def Component():
    return Div(
        H1("Title"),
        P("This is <fasthtml>not</fasthtml> executed")
    )

# This should be displayed as text
show(Component())
```

Inline code with FastHTML tag: `<fasthtml>test</fasthtml>`

Another code block:

```markdown
This is markdown with <fasthtml> tags that should not be executed
but displayed as text in the rendered HTML.
```
"""
    
    # Render the markdown
    html = render_content(create_test_item(markdown))
    
    # Check that code blocks are properly rendered
    assert '<pre><code class="language-python">' in html
    assert '<pre><code class="language-markdown">' in html
    
    # Check that FastHTML content appears as literal text
    assert "This is &lt;fasthtml&gt;not&lt;/fasthtml&gt; executed" in html  # In code block
    assert "show(Component())" in html  # Code appears as text
    
    # Check that inline code is properly rendered
    assert '<code>&lt;fasthtml&gt;test&lt;/fasthtml&gt;</code>' in html

def test_fasthtml_in_documentation():
    """Test that FastHTML in documentation code blocks is treated as literal text."""
    content = """
## Writing Content

Here's an example of markdown with FastHTML:

```markdown
---
title: "Example Post"
---

<content>
# My Content

<!-- Use FastHTML for dynamic content -->
<fasthtml>
from datetime import datetime

def TimeDisplay():
    return P(f"Current time: {datetime.now().strftime('%H:%M')}")

show(TimeDisplay())
</fasthtml>

Back to markdown.
</content>
```
"""
    
    # Render the content
    html = render_content(create_test_item(content))
    
    # Check that FastHTML appears as literal text in code block
    assert '<pre><code class="language-markdown">' in html
    assert "def TimeDisplay()" in html
    assert "show(TimeDisplay())" in html
    
    # Verify the code isn't actually executed (no rendered output)
    assert '<p>Current time:' not in html.lower()

def test_mixed_content_handling():
    """Test that FastHTML in code blocks is not executed."""
    content = """
# Mixed Content Example

Here's a regular paragraph.

And here's an example of FastHTML code in a code block:

```python
# Example FastHTML code
<fasthtml>
def ExampleComponent():
    return Div(
        H2("This should not be executed"),
        P("This is just an example")
    )

show(ExampleComponent())
</fasthtml>
```
"""
    
    # Render the content
    html = render_content(create_test_item(content))
    
    # Verify code block content appears as literal text
    assert '<pre><code class="language-python">' in html
    assert "def ExampleComponent()" in html
    assert "show(ExampleComponent())" in html
    
    # Verify the code isn't executed (no rendered components)
    assert '<h2>This should not be executed</h2>' not in html
    assert '<p>This is just an example</p>' not in html

def test_documentation_with_imports():
    """Test that FastHTML with imports in documentation is not executed."""
    content = """
## Component Usage

```markdown
<fasthtml>
# Import components from your app
from components import Button
from datetime import datetime

def Greeting():
    return Div(
        H1("Hello, World!", cls="text-3xl font-bold"),
        P(f"The time is: {datetime.now().strftime('%H:%M')}"),
        Button(text="Click me!", onclick="alert('Hello!')")
    )

show(Greeting())
</fasthtml>
```
"""

    # Render the content
    html = render_content(create_test_item(content))
    
    # Check that code appears as literal text in code block
    assert '<pre><code class="language-markdown">' in html
    assert "from components import Button" in html
    assert "show(Greeting())" in html
    
    # Verify the code isn't executed (no rendered components)
    assert '<h1 class="text-3xl font-bold">' not in html
    assert '<button' not in html.lower()

def test_quickstart_guide():
    """Test that FastHTML in quickstart guide code blocks is treated as literal text."""
    content = '''---
title: "FastHTML Guide"
layout: basic
---

<content>
# FastHTML Guide

Here's an example of FastHTML in a code block:

```markdown
<content>
# Welcome to My Site

<fasthtml>
from components import Button

def Greeting(name="World"):
    return Div(
        H1(f"Hello, {name}!"),
        Button(text="Click me!")
    )

show(Greeting())
</fasthtml>
</content>
```

The above FastHTML should appear as literal text.
</content>'''

    # Render the content
    rendered_html = render_content(create_test_item(content))
    
    # Verify that the markdown is rendered correctly
    assert "FastHTML Guide" in rendered_html
    assert "example of FastHTML in a code block" in rendered_html
    
    # Verify code block content appears as literal text
    assert '<pre><code class="language-markdown">' in rendered_html
    assert "def Greeting" in rendered_html
    assert "show(Greeting())" in rendered_html
    
    # Verify the code isn't executed (no rendered components)
    assert '<h1>Hello, World!</h1>' not in rendered_html
    assert '<button' not in rendered_html.lower()

def test_code_block_detection():
    """Test that FastHTML in code blocks is properly detected and not executed."""
    content = '''<content>
# Example

```markdown
<fasthtml>
from components import Button
show(Button(text='Click me!'))
</fasthtml>
```
</content>'''

    # Render the content
    rendered = render_content(create_test_item(content))
    
    # Verify code block content appears as literal text
    assert '<pre><code class="language-markdown">' in rendered
    assert "from components import Button" in rendered
    assert "show(Button" in rendered
    
    # Verify we don't have rendered components
    assert '<button' not in rendered.lower()