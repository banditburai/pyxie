"""Test the Pyxie renderer functionality."""

import pytest
from pathlib import Path
from pyxie.types import ContentItem, ContentBlock, RenderResult
from pyxie.renderer import render_content
from pyxie.layouts import layout, registry
from fastcore.xml import FT, Div
from tests.utils import ComponentFinder
from typing import List

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
    ("# Title\nContent", ["<h1 id=\"title\">Title</h1>", "<p>Content</p>"]),
    ("[Link](https://example.com)\n![Image](image.jpg)", 
     ['<a href="https://example.com">Link</a>', '<img src="image.jpg" alt="image.jpg"']),
    ("```python\ndef test(): pass\n```\nInline `code`",
     ["<pre><code", "def test(): pass", "<code>code</code>"])
])
def test_markdown_variations(markdown: str, expected_html: List[str]) -> None:
    """Test various markdown rendering cases."""
    block = ContentBlock(tag_name="content", content=markdown, attrs_str="")
    item = ContentItem(
        source_path=Path("test.md"),
        metadata={},
        blocks={"content": [block]}
    )
    html = render_content(item)
    for expected in expected_html:
        assert expected in html

def test_complex_layout_integration():
    """Test integration of rendered markdown with complex layout."""
    @layout("complex")
    def complex_layout(content: str = "") -> FT:
        return Div(
            Div(data_slot="title", cls="title"),
            Div(data_slot="content", cls="content"),
            Div(data_slot="sidebar", cls="sidebar")
        )
    
    content = """
<title>
# Welcome
</title>

<content>
**Main** content with *formatting*
</content>

<sidebar>
- Item 1
- Item 2
</sidebar>
"""
    blocks = {
        "title": [ContentBlock(tag_name="title", content="# Welcome", attrs_str="")],
        "content": [ContentBlock(tag_name="content", content="**Main** content with *formatting*", attrs_str="")],
        "sidebar": [ContentBlock(tag_name="sidebar", content="- Item 1\n- Item 2", attrs_str="")]
    }
    
    item = ContentItem(
        source_path=Path("test.md"),
        metadata={"layout": "complex"},
        blocks=blocks
    )
    html = render_content(item)
    
    # Use ComponentFinder to verify structure
    soup = ComponentFinder.find_element(html, ".title")
    assert soup is not None
    assert "Welcome" in soup.text
    
    soup = ComponentFinder.find_element(html, ".content")
    assert soup is not None
    assert "Main" in soup.text
    assert "formatting" in soup.text
    
    soup = ComponentFinder.find_element(html, ".sidebar")
    assert soup is not None
    assert "Item 1" in soup.text
    assert "Item 2" in soup.text

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
    block = ContentBlock(tag_name="content", content=content, attrs_str="")
    item = ContentItem(
        source_path=Path("test.md"),
        metadata={},
        blocks={"content": [block]}
    )
    html = render_content(item)
    
    # Check for content presence rather than exact HTML format
    assert "Section 1" in html
    assert "Subsection" in html
    assert "List item 1" in html
    assert "Nested item" in html
    assert "def test" in html
    assert ("return \"nested\"" in html or "return &quot;nested&quot;" in html)
    assert "List item 2" in html

def test_comprehensive_error_handling():
    """Test various error handling cases."""
    # Test empty content
    block = ContentBlock(tag_name="content", content="", attrs_str="")
    item = ContentItem(
        source_path=Path("test.md"),
        metadata={},
        blocks={"content": [block]}
    )
    html = render_content(item)
    assert html.strip() == "<div></div>"  # Empty content renders as empty div due to layout
    
    # Test malformed HTML in markdown
    block = ContentBlock(tag_name="content", content="<unclosed>test", attrs_str="")
    item = ContentItem(
        source_path=Path("test.md"),
        metadata={},
        blocks={"content": [block]}
    )
    html = render_content(item)
    assert "&lt;unclosed&gt;" in html  # HTML is properly escaped
    assert "test" in html

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
    block = ContentBlock(tag_name="content", content=content, attrs_str="")
    item = ContentItem(
        source_path=Path("test.md"),
        metadata={},
        blocks={"content": [block]}
    )
    html = render_content(item)
    
    assert '<h1 id="test-header">Test Header</h1>' in html
    assert '<h2 id="another-header">Another Header</h2>' in html
    assert '<strong>bold</strong>' in html
    assert '<em>italic</em>' in html
    assert '<li>List item 1</li>' in html
    assert '<li>Numbered item 1</li>' in html
    assert '<blockquote>' in html
    assert '<code>inline code</code>' in html
    assert '<pre><code class="language-python">' in html

def test_fasthtml_rendering():
    """Test that FastHTML blocks are rendered correctly."""
    content = """
    <fasthtml>
show(Div("Hello World", cls="test-class"))
    </fasthtml>
    """
    block = ContentBlock(tag_name="content", content=content, attrs_str="")
    item = ContentItem(
        source_path=Path("test.md"),
        metadata={},
        blocks={"content": [block]}
    )
    html = render_content(item)
    assert '<div class="test-class">Hello World</div>' in html

def test_script_tag_rendering():
    """Test that script tags are rendered correctly."""
    content = """
<fasthtml>
show(Script('console.log("Hello World");'))
</fasthtml>
"""
    block = ContentBlock(tag_name="content", content=content, attrs_str="")
    item = ContentItem(
        source_path=Path("test.md"),
        metadata={},
        blocks={"content": [block]}
    )
    html = render_content(item)
    assert 'console.log("Hello World");' in html
    assert '<script>' in html
    assert '</script>' in html

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
    block = ContentBlock(tag_name="content", content=content, attrs_str="")
    item = ContentItem(
        source_path=Path("test.md"),
        metadata={},
        blocks={"content": [block]}
    )
    html = render_content(item)
    
    assert '<h1 id="title">Title</h1>' in html
    assert '<div>FastHTML content</div>' in html
    assert 'console.log("Script content");' in html
    assert '<script>' in html
    assert '</script>' in html
    assert '<h2 id="subtitle">Subtitle</h2>' in html
    assert '<p>Regular markdown content.</p>' in html

def test_error_handling():
    """Test that rendering errors are handled gracefully."""
    content = """
<fasthtml>
show(UndefinedComponent())
</fasthtml>
"""
    block = ContentBlock(tag_name="content", content=content, attrs_str="")
    item = ContentItem(
        source_path=Path("test.md"),
        metadata={},
        blocks={"content": [block]}
    )
    html = render_content(item)
    assert 'ERROR: NAME \'UNDEFINEDCOMPONENT\' IS NOT DEFINED' in html.upper()
    assert 'fasthtml-error' in html

def test_layout_rendering():
    """Test that content with layouts is rendered correctly."""
    content = """
# Content Title
Regular content
"""
    block = ContentBlock(tag_name="content", content=content, attrs_str="")
    item = ContentItem(
        source_path=Path("test.md"),
        metadata={"layout": "page", "title": "Test Page"},
        blocks={"content": [block]}
    )
    html = render_content(item)
    assert '<h1 id="content-title">Content Title</h1>' in html
    assert '<p>Regular content</p>' in html
    assert 'Header' in html
    assert 'Footer' in html

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
    block = ContentBlock(tag_name="content", content=content, attrs_str="")
    item = ContentItem(
        source_path=Path("test.md"),
        metadata={},
        blocks={"content": [block]}
    )
    html = render_content(item)
    assert '<div>Visible content</div>' in html
    assert 'Hidden content' not in html 