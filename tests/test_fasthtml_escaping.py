"""Tests to ensure FastHTML tags in code blocks are properly escaped."""

import pytest
from mistletoe import Document
from pyxie.renderer import PyxieHTMLRenderer, render_markdown, render_block
from pyxie.parser import parse
from pyxie.types import ContentBlock
from pyxie.fasthtml import process_fasthtml_in_content

def test_fasthtml_escaping_in_code_blocks():
    """Test that FastHTML tags in code blocks are escaped correctly."""
    # Test markdown with code blocks containing FastHTML tags
    markdown = """
# Test FastHTML Escaping

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
    html = render_markdown(markdown)
    
    # Check that FastHTML tags are properly escaped in the code blocks
    assert "&lt;fasthtml&gt;" in html
    assert "&lt;/fasthtml&gt;" in html
    assert "<fasthtml>" not in html
    assert "</fasthtml>" not in html
    
    # Check specifically that the code blocks contain the escaped tags
    assert '<pre><code class="language-python">' in html
    assert '<code>&lt;fasthtml&gt;test&lt;/fasthtml&gt;</code>' in html
    assert 'show(Component())' in html

def test_fasthtml_escaping_in_quick_start_guide():
    """Test that FastHTML tags in the quick start guide's code blocks are escaped correctly."""
    # Create a test content block with markdown that includes FastHTML in code blocks
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
    
    # Create a ContentBlock and render it
    block = ContentBlock(
        name="example",
        content=content,
        params={},
        content_type="markdown",
        index=0
    )
    
    # Parse using the parser (to verify code blocks are detected)
    parsed = parse(content)
    
    # The content shouldn't have any actual blocks, just the markdown
    assert len(parsed.blocks) == 0
    
    # Render the markdown directly
    html = render_markdown(content)
    
    # Check that FastHTML tags in code examples are escaped
    assert "&lt;fasthtml&gt;" in html
    assert "&lt;/fasthtml&gt;" in html
    assert "show(TimeDisplay())" in html
    
    # Make sure the actual tags aren't present in their raw form
    assert "<fasthtml>" not in html
    assert "</fasthtml>" not in html

def test_nested_fasthtml_in_code_blocks():
    """Test handling of nested FastHTML tags in code blocks."""
    markdown = """
# Nested Tags Example

```python
def Component():
    return Div(
        H1("Title"),
        P("<fasthtml><ft>Nested tags</ft></fasthtml>")
    )
```
"""
    
    html = render_markdown(markdown)
    
    # Check for escaped nested tags
    assert "&lt;fasthtml&gt;&lt;ft&gt;Nested tags&lt;/ft&gt;&lt;/fasthtml&gt;" in html
    assert "<fasthtml><ft>" not in html

def test_mixed_fasthtml_content():
    """Test that FastHTML tags in code blocks are properly escaped."""
    # Mixed content with both actual FastHTML to execute and example FastHTML in code blocks
    content = """
# Mixed FastHTML Example

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
    
    # First render the markdown to HTML
    html = render_markdown(content)
    
    # Verify code blocks have escaped FastHTML
    assert "&lt;fasthtml&gt;" in html
    assert "This should not be executed" in html
    assert "ExampleComponent" in html
    
    # Verify the escaped tags remain in the final output
    assert "&lt;fasthtml&gt;" in html
    assert "def ExampleComponent()" in html
    assert "show(ExampleComponent())" in html 