"""Test the Pyxie renderer functionality."""

import pytest
from pathlib import Path
from pyxie.types import ContentItem, RenderResult
from pyxie.renderer import render_content, NestedRenderer
from pyxie.layouts import layout, registry
from fastcore.xml import FT, Div, H1, P, Span
from tests.utils import ComponentFinder
from typing import List
from pyxie.parser import parse_frontmatter, FastHTMLToken, ScriptToken, NestedContentToken
from io import StringIO
from mistletoe import Document
from mistletoe.block_token import add_token

@pytest.fixture(autouse=True)
def setup_test_layout():
    """Set up test layout for all tests."""
    # Clear any existing layouts
    registry._layouts.clear()
    
    @layout("default")
    def default_layout(content: str = "") -> FT:
        """Default layout that just renders the content directly."""
        return Div(data_slot="content")

    @layout("page")
    def page_layout(content: str = "") -> FT:
        """Page layout with header and footer."""
        return Div(
            Div("Header", cls="header"),
            Div(data_slot="content", cls="content"),
            Div("Footer", cls="footer")
        )

@pytest.mark.parametrize("markdown,expected_html", [
    ("# Title\nContent", ['<h1 id="title">Title</h1>', "<p>Content</p>"]),
    ("[Link](https://example.com)\n![Image](image.jpg)",
     ['<a href="https://example.com">Link</a>', '<img src="image.jpg"']),
    ("```python\ndef test(): pass\n```\nInline `code`",
     ["<pre><code", "def test(): pass", "<code>code</code>"])
])
def test_markdown_variations(markdown: str, expected_html: List[str]) -> None:
    """Test various markdown rendering cases."""
    item = ContentItem(
        source_path=Path("test.md"),
        metadata={},
        content=markdown
    )
    
    with NestedRenderer() as renderer:
        rendered = renderer.render(Document(StringIO(item.content)))
        
    for expected in expected_html:
        assert expected in rendered

def test_complex_layout_integration():
    """Test integration of rendered markdown with complex layout."""
    @layout("complex")
    def complex_layout(content: str = "") -> FT:
        return Div(
            Div(None, data_slot="content", cls="content"),
            cls="complex-layout"
        )
    
    content = """# Welcome

<custom>
    **Main** content with *formatting*
    
    <nested>
        - Item 1
        - Item 2
    </nested>
</custom>
"""
    item = ContentItem(
        source_path=Path("test.md"),
        metadata={"layout": "complex"},
        content=content
    )
    
    rendered = render_content(item)
    
    assert '<h1 id="welcome">Welcome</h1>' in rendered
    assert "<strong>Main</strong>" in rendered
    assert "<em>formatting</em>" in rendered
    assert "<nested>" in rendered
    assert "Item 1" in rendered
    assert "Item 2" in rendered

def test_complex_nested_content():
    """Test rendering of complex nested content."""
    content = """# Section 1
## Subsection
- List item 1
  - Nested item
    ```python
    def test():
        return "nested"
    ```
- List item 2
"""
    item = ContentItem(
        source_path=Path("test.md"),
        metadata={},
        content=content
    )
    
    rendered = render_content(item)
    
    assert "<h1" in rendered
    assert "<h2" in rendered
    assert "<li>" in rendered
    assert "<pre><code" in rendered
    assert "def test():" in rendered

def test_content_handling():
    """Test various content handling cases including empty content and HTML preservation."""
    # Test empty content
    item = ContentItem(
        source_path=Path("test.md"),
        metadata={},
        content=""
    )
    rendered = render_content(item)
    assert rendered == ""  # Empty content returns empty string
    
    # Test custom block preservation
    item = ContentItem(
        source_path=Path("test.md"),
        metadata={},
        content="""<custom class="test">
    This is a **custom** block
</custom>"""
    )
    rendered = render_content(item)
    assert '<custom class="test">' in rendered
    assert '<strong>custom</strong>' in rendered

def test_markdown_rendering():
    """Test that markdown content is rendered correctly."""
    content = """
# Test Header

## Another Header

This is a paragraph with **bold** and *italic* text.

- List item 1
- List item 2

1. Numbered item 1
2. Numbered item 2

> Blockquote

`inline code`

```python
def hello():
    print("Hello, World!")
```
"""
    item = ContentItem(
        source_path=Path("test.md"),
        metadata={},
        content=content
    )
    
    rendered = render_content(item)
    
    assert "<h1" in rendered
    assert "<h2" in rendered
    assert "<strong>bold</strong>" in rendered
    assert "<em>italic</em>" in rendered
    assert "<li>List item" in rendered
    assert "<li>Numbered item" in rendered
    assert "<blockquote>" in rendered
    assert "<code>inline code</code>" in rendered
    assert "<pre><code" in rendered
    assert "def hello():" in rendered

def test_fasthtml_rendering():
    """Test that FastHTML blocks are rendered correctly."""
    content = """<fasthtml>
    show(Div("Hello World", cls="test-class"))
</fasthtml>"""
    
    item = ContentItem(
        source_path=Path("test.md"),
        metadata={},
        content=content
    )
    
    rendered = render_content(item)
    assert '<div class="test-class">' in rendered
    assert "Hello World" in rendered

def test_script_tag_rendering():
    """Test that script tags are rendered correctly."""
    content = """
<fasthtml>
show(Script('console.log("Hello World");'))
</fasthtml>
"""
    item = ContentItem(
        source_path=Path("test.md"),
        metadata={},
        content=content
    )
    
    rendered = render_content(item)
    assert "<script" in rendered
    assert 'console.log("Hello World");' in rendered

def test_header_anchor_ids():
    """Test that headers get unique anchor IDs."""
    content = """# First Header
## Second Header
# First Header
### Third Header with *emphasis*"""
    
    item = ContentItem(
        source_path=Path("test.md"),
        metadata={},
        content=content
    )
    
    rendered = render_content(item)
    
    # Check that headers have unique IDs
    assert '<h1 id="first-header">' in rendered
    assert '<h2 id="second-header">' in rendered
    assert '<h1 id="first-header-1">' in rendered  # Second occurrence gets -1
    assert '<h3 id="third-header-with-emphasis">' in rendered

def test_mixed_content():
    """Test rendering of mixed content types."""
    content = """
# Title

<fasthtml>
show(Div("FastHTML content"))
</fasthtml>

<fasthtml>
show(Script('console.log("Script content");'))
</fasthtml>

## Subtitle

Regular markdown content.
"""
    item = ContentItem(
        source_path=Path("test.md"),
        metadata={},
        content=content
    )
    
    rendered = render_content(item)
    
    assert "<h1" in rendered
    assert "<h2" in rendered
    assert "<div" in rendered
    assert "<script" in rendered
    assert "FastHTML content" in rendered
    assert 'console.log("Script content");' in rendered
    assert "Regular markdown content" in rendered

def test_error_handling():
    """Test that rendering errors are handled gracefully."""
    content = """<fasthtml>
    show(UndefinedComponent())
</fasthtml>"""
    
    item = ContentItem(
        source_path=Path("test.md"),
        metadata={},
        content=content
    )
    
    rendered = render_content(item)
    assert '<div class="error">' in rendered
    assert "UndefinedComponent" in rendered

def test_layout_rendering():
    """Test that content with layouts is rendered correctly."""
    content = """
# Content Title
Regular content
"""
    item = ContentItem(
        source_path=Path("test.md"),
        metadata={"layout": "page", "title": "Test Page"},
        content=content
    )
    
    rendered = render_content(item)
    assert "Content Title" in rendered
    assert "Regular content" in rendered

def test_conditional_rendering():
    """Test that conditional rendering works correctly."""
    content = """
<fasthtml>
if True:
    show(Div("Visible content"))
else:
    show(Div("Hidden content"))
</fasthtml>
"""
    item = ContentItem(
        source_path=Path("test.md"),
        metadata={},
        content=content
    )
    
    rendered = render_content(item)
    assert "Visible content" in rendered
    assert "Hidden content" not in rendered 