"""Tests to ensure FastHTML tags in code blocks are properly escaped."""

import pytest
from mistletoe import Document
from pyxie.renderer import PyxieHTMLRenderer, render_markdown, render_block
from pyxie.parser import parse
from pyxie.types import ContentBlock
from pyxie.fasthtml import process_multiple_fasthtml_tags
import re

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

def test_documentation_example_with_missing_component():
    """Test that FastHTML tags in documentation examples aren't executed."""
    # This simulates the exact error case from the user query where
    # FastHTML in documentation examples tries to import non-existent components
    content = """
## Writing Content

```markdown
<!-- Use FastHTML for dynamic content -->
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

# Use show() to render FastHTML components
show(Greeting())
</fasthtml>
```

In this example, we're importing a Button component that wouldn't exist 
in the documentation environment, but that's fine since this is just example code.
"""
    
    # Render the markdown
    html = render_markdown(content)
    
    # Check that FastHTML tags in code examples are escaped
    assert "&lt;fasthtml&gt;" in html
    assert "&lt;/fasthtml&gt;" in html
    assert "from components import Button" in html
    assert "show(Greeting())" in html
    
    # Verify the code isn't actually executed
    # If it was executed, it would try to import the non-existent Button component
    # and fail, but we want to make sure it's treated as example code
    assert "ImportError" not in html 

def test_documentation_example_with_nonexistent_import():
    """Test that FastHTML tags in documentation examples are not executed."""
    # This simulates documentation showing how to use components that don't exist
    # The FastHTML code should not be executed because it's in a code block
    content = '''
# Documentation Example

Here's how to use components:

```markdown
<content>
# Welcome to My Site

<!-- Use FastHTML for dynamic content -->
<fasthtml>
# This should not be executed since it's in a code block
from components import Button  # This import doesn't exist

def Greeting():
    return Div(
        H1("Hello, World!"),
        Button(text="Click me!")
    )

show(Greeting())
</fasthtml>
</content>
```

The above should be displayed as code, not executed.
'''

    # Parse and render the content directly
    from pyxie.parser import parse
    from pyxie.renderer import render_markdown
    
    # Render the content directly without trying to access blocks
    html = render_markdown(content)
    
    # Check that the FastHTML code was not executed (no error div)
    assert "fasthtml-error" not in html
    # Check that the code is properly escaped and displayed
    assert "&lt;fasthtml" in html or "<code>" in html 

def test_full_quickstart_guide_integration():
    """
    Full integration test using the actual Quick Start Guide markdown.
    This test simulates the complete pipeline as experienced in production.
    """
    # This is a simplified version of the content with the FastHTML example
    content = '''---
title: "FastHTML Escaping Test"
layout: basic
---

<content>
# FastHTML Escaping Test

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

The above FastHTML tags should be escaped and not executed when inside a code block.
</content>'''

    # 1. Parse the content
    from pyxie.parser import parse
    from pyxie.renderer import render_markdown, render_block

    parsed = parse(content)
    
    # Blocks is a dictionary of lists where the key is the tag name
    assert "content" in parsed.blocks, "Content block not found in parsed results"
    content_blocks = parsed.blocks["content"]
    assert len(content_blocks) > 0, "No content blocks found"
    content_block = content_blocks[0]
    
    # 2. Test that the FastHTML tags in the code block are properly identified and not executed
    # First, check the FastHTML content in the markdown code block
    import re
    code_blocks = re.findall(r'```markdown(.*?)```', content_block.content, re.DOTALL)
    assert len(code_blocks) > 0, "No markdown code blocks found"
    
    # There should be FastHTML tags in the code block
    fasthtml_block = None
    for block in code_blocks:
        if "<fasthtml>" in block:
            fasthtml_block = block
            break
            
    assert fasthtml_block is not None, "No FastHTML block found in code examples"
    
    # 3. Verify the FastHTML tags in the code block are correctly detected as being in a code block
    from pyxie.fasthtml import process_multiple_fasthtml_tags
    
    # Print the content we're trying to process
    print("\n\nFastHTML Block:\n", repr(fasthtml_block))
    
    # When we process this through the FastHTML processor
    # Our implementation should detect it's a code block and not execute it
    result = process_multiple_fasthtml_tags(fasthtml_block)
    
    # Print the result for debugging
    print("\n\nResult Content:\n", repr(result.content))
    
    # Confirm the block was not processed as actual FastHTML
    # (if it was, it would try to import the Button component and fail)
    assert "ImportError:" not in result.content
    assert "Button" in result.content, f"Button not found in result: {result.content}"
    
    # 4. Render the full markdown and check that the FastHTML tags in code blocks are not executed
    rendered_markdown = render_markdown(content_block.content)
    
    # The rendered output should contain the escaped FastHTML tags
    assert "&lt;fasthtml&gt;" in rendered_markdown or "<code>" in rendered_markdown
    assert "Button" in rendered_markdown
    
    # It should NOT contain FastHTML error messages
    assert "ImportError:" not in rendered_markdown
    assert "fasthtml-error" not in rendered_markdown
    
    # 5. Test the entire rendering pipeline
    render_result = render_block(content_block)
    assert render_result.success, f"Block rendering failed: {render_result.error}"
    full_rendered = render_result.content
    
    # Print for debugging
    print("\n\nFull Rendered Output:\n", repr(full_rendered))
    
    # The full rendered output should properly handle all FastHTML content
    assert "Button" in full_rendered
    assert "import" in full_rendered
    assert "ImportError:" not in full_rendered
    
    # 6. Additional check: Make sure we can find code blocks with our Button component
    # The markdown ```markdown is converted to <pre><code class="language-markdown"> in HTML
    assert '<code class="language-markdown">' in full_rendered

def test_direct_fasthtml_code_block_detection():
    """
    Test the end-to-end flow of processing FastHTML in code blocks.
    This verifies the correct behavior when FastHTML tags appear in code examples.
    """
    # The correct way to handle code blocks is through the parser
    from pyxie.parser import parse
    from pyxie.renderer import render_block
    
    # Create content with FastHTML in a code block
    content = '''<content>
    # Example
    
    ```markdown
    <fasthtml>
    from components import Button
    show(Button(text='Click me!'))
    </fasthtml>
    ```
    </content>'''
    
    # Parse the content - parser should detect code blocks
    parsed = parse(content)
    content_block = parsed.blocks["content"][0]
    
    # Render the block - FastHTML should not be executed
    result = render_block(content_block)
    assert result.success, f"Block rendering failed: {result.error}"
    rendered = result.content
    
    # Should contain Button but not execution errors
    assert "Button" in rendered
    assert "components" in rendered
    assert "ImportError:" not in rendered
    assert "ModuleNotFoundError" not in rendered
    
    # Code should be rendered properly
    assert "```" in rendered or "<code" in rendered 