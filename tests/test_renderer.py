"""Test the PyxieRenderer implementation."""

import pytest
import logging
from mistletoe import Document
from mistletoe.block_token import BlockToken, Heading, Paragraph, List, HtmlBlock
from pyxie.renderer import PyxieRenderer
from pyxie.parser import RawBlockToken, NestedContentToken
from pyxie.layouts import LayoutNotFoundError

logger = logging.getLogger(__name__)

@pytest.fixture
def clear_layouts():
    """Clear all registered layouts before running tests."""
    from pyxie.layouts import registry
    registry._layouts.clear()
    yield
    registry._layouts.clear()

@pytest.mark.needs_mistletoe_tokens
def test_raw_block_rendering(setup_mistletoe_tokens):
    """Test rendering of raw block tokens."""
    # Test script block
    script_input = """
<script type="text/javascript">
let x = 1;
console.log(x);
</script>
"""
    with PyxieRenderer() as renderer:
        doc = Document(script_input.strip().splitlines())
        html = renderer.render(doc)
        assert '<script type="text/javascript">' in html
        assert 'let x = 1;' in html
        assert 'console.log(x);' in html
        assert '</script>' in html

    # Test style block
    style_input = """
<style type="text/css">
body { color: red; }
</style>
"""
    with PyxieRenderer() as renderer:
        doc = Document(style_input.strip().splitlines())
        html = renderer.render(doc)
        assert '<style type="text/css">' in html
        assert 'body { color: red; }' in html
        assert '</style>' in html

    # Test FastHTML block
    fasthtml_input = """
<fasthtml>
show(Div("Hello World"))
</fasthtml>
"""
    with PyxieRenderer() as renderer:
        doc = Document(fasthtml_input.strip().splitlines())
        html = renderer.render(doc)
        assert '<div>' in html
        assert 'Hello World' in html
        assert '</div>' in html

    # Test FastHTML block with error
    error_fasthtml_input = """
<fasthtml>
{{ invalid syntax }}
</fasthtml>
"""
    with PyxieRenderer() as renderer:
        doc = Document(error_fasthtml_input.strip().splitlines())
        html = renderer.render(doc)
        assert '<div class="error">' in html
        assert 'Error:' in html

    # Test pre block (default raw block)
    pre_input = """
<pre>
def hello():
    print("Hello")
</pre>
"""
    with PyxieRenderer() as renderer:
        doc = Document(pre_input.strip().splitlines())
        html = renderer.render(doc)
        assert '<pre>' in html
        assert 'def hello():' in html
        assert '    print("Hello")' in html
        assert '</pre>' in html

    # Test raw block with attributes
    raw_with_attrs_input = """
<pre class="code" data-lang="python">
print("Hello")
</pre>
"""
    with PyxieRenderer() as renderer:
        doc = Document(raw_with_attrs_input.strip().splitlines())
        html = renderer.render(doc)
        assert 'class="code"' in html
        assert 'data-lang="python"' in html
        assert 'print("Hello")' in html

    # Test self-closing raw block
    self_closing_input = '<script src="test.js" />'
    with PyxieRenderer() as renderer:
        doc = Document(self_closing_input.splitlines())
        html = renderer.render(doc)
        assert '<script src="test.js" />' in html

@pytest.mark.needs_mistletoe_tokens
def test_raw_block_error_handling(setup_mistletoe_tokens):
    """Test error handling in raw block rendering."""
    # Test script block with invalid content
    invalid_script = """
<script>
{{ invalid content }}
</script>
"""
    with PyxieRenderer() as renderer:
        doc = Document(invalid_script.strip().splitlines())
        html = renderer.render(doc)
        # Script content is rendered as-is, not as error
        assert '{{ invalid content }}' in html

    # Test style block with invalid content
    invalid_style = """
<style>
{{ invalid content }}
</style>
"""
    with PyxieRenderer() as renderer:
        doc = Document(invalid_style.strip().splitlines())
        html = renderer.render(doc)
        # Style content is rendered as-is, not as error
        assert '{{ invalid content }}' in html

    # Test raw block with invalid attributes
    invalid_attrs = """
<pre class="test" data-invalid="{{ invalid }}">
content
</pre>
"""
    with PyxieRenderer() as renderer:
        doc = Document(invalid_attrs.strip().splitlines())
        html = renderer.render(doc)
        # Invalid attributes are rendered as-is
        assert 'data-invalid="{{ invalid }}"' in html

@pytest.mark.needs_mistletoe_tokens
def test_nested_content_rendering(setup_mistletoe_tokens):
    """Test rendering of nested content tokens with inner Markdown."""
    markdown_input = """
<my-content class="test">
# Heading Inside
Some **bold** text.
</my-content>
"""
    with PyxieRenderer() as renderer:
        doc = Document(markdown_input.strip().splitlines())
        html = renderer.render(doc)
        assert 'class="test"' in html
        assert 'data-slot="my-content"' in html
        assert '<h1 id="heading-inside">Heading Inside</h1>' in html
        assert '<strong>bold</strong>' in html
        assert '</my-content>' in html

@pytest.mark.needs_mistletoe_tokens
def test_void_element_rendering(setup_mistletoe_tokens):
    """Test rendering of void elements."""
    markdown_input = '<img src="test.jpg" alt="Test" />'
    with PyxieRenderer() as renderer:
        doc = Document(markdown_input.strip().splitlines())
        html = renderer.render(doc)
        assert 'src="test.jpg"' in html
        assert 'alt="Test"' in html
        assert html.startswith('<img') and html.rstrip().endswith('/>')

@pytest.mark.needs_mistletoe_tokens
def test_attributes_rendering(setup_mistletoe_tokens):
    """Test rendering of various attribute types."""
    markdown_input = """<my-component string="value" number=42 boolean empty="" special="<>&'\">Content</my-component>"""
    with PyxieRenderer() as renderer:
        doc = Document(markdown_input.strip().splitlines())
        html = renderer.render(doc)
        assert 'string="value"' in html
        assert 'number="42"' in html
        assert 'boolean' in html
        assert 'empty=""' in html
        assert 'special' in html
        assert '<p>&amp;\'"&gt;Content</p>' in html

@pytest.mark.needs_mistletoe_tokens
def test_heading_ids(setup_mistletoe_tokens):
    """Test that headings receive proper anchor IDs."""
    markdown_input = """
# First Heading
# First Heading
## Sub-heading!
### Complex <em>Heading</em> Here
"""
    with PyxieRenderer() as renderer:
        doc = Document(markdown_input.strip().splitlines())
        html = renderer.render(doc)
        assert 'id="first-heading"' in html
        assert 'id="first-heading-1"' in html  # Second identical heading gets incremented
        assert 'id="sub-heading"' in html
        assert 'id="complex-heading-here"' in html  # HTML tags removed from ID

@pytest.mark.needs_mistletoe_tokens
def test_image_rendering(setup_mistletoe_tokens):
    """Test rendering of images with pyxie: URLs."""
    markdown_input = """
![Test](pyxie:nature/800/600)
![Another](test.jpg)
"""
    with PyxieRenderer() as renderer:
        doc = Document(markdown_input.strip().splitlines())
        html = renderer.render(doc)
        assert 'src="https://picsum.photos/seed/nature/800/600"' in html
        assert 'src="test.jpg"' in html

@pytest.mark.needs_mistletoe_tokens
def test_nested_custom_blocks(setup_mistletoe_tokens):
    """Test rendering of nested custom blocks."""
    markdown_input = """
<outer-block>
<inner-block>
# Heading
</inner-block>
</outer-block>
"""
    with PyxieRenderer() as renderer:
        doc = Document(markdown_input.strip().splitlines())
        html = renderer.render(doc)
        assert 'data-slot="outer-block"' in html
        assert 'data-slot="inner-block"' in html
        assert '<h1 id="heading">Heading</h1>' in html
        assert '</inner-block>' in html
        assert '</outer-block>' in html

@pytest.mark.needs_mistletoe_tokens
def test_mixed_content(setup_mistletoe_tokens):
    """Test parsing of mixed content with standard Markdown and custom tokens."""
    markdown_input = """
# Standard Heading

<custom-block>
  <span>**bold** text</span>
  Regular *italic* text
</custom-block>

<script>
  console.log("raw");
</script>
"""
    doc = Document(markdown_input.strip().splitlines())

    # Assertions
    assert len(doc.children) == 3  # Heading, custom block, script
    assert isinstance(doc.children[0], Heading)  # Heading
    assert isinstance(doc.children[1], NestedContentToken)  # custom-block
    assert isinstance(doc.children[2], RawBlockToken)  # script

    # Check custom block contents
    custom_block = doc.children[1]
    # The inner content should be a single paragraph containing both HTML and markdown
    assert len(custom_block.children) == 1
    assert isinstance(custom_block.children[0], Paragraph)
    # The paragraph should contain both HTML and markdown
    assert '<span>**bold** text</span>' in custom_block.content
    assert 'Regular *italic* text' in custom_block.content

@pytest.mark.needs_mistletoe_tokens
def test_empty_blocks(setup_mistletoe_tokens):
    """Test rendering of empty blocks."""
    markdown_input = """
<custom-block></custom-block>
<void-element />
"""
    with PyxieRenderer() as renderer:
        doc = Document(markdown_input.strip().splitlines())
        html = renderer.render(doc)
        assert 'data-slot="custom-block"' in html
        assert '<void-element />' in html

@pytest.mark.needs_mistletoe_tokens
def test_html_inside_nested(setup_mistletoe_tokens):
    """Test rendering of standard HTML inside nested content."""
    markdown_input = """
<my-content>
<div class="inner">
# Heading
</div>
</my-content>
"""
    with PyxieRenderer() as renderer:
        doc = Document(markdown_input.strip().splitlines())
        html = renderer.render(doc)
        assert 'data-slot="my-content"' in html
        assert '<div class="inner">' in html
        # HTML blocks should contain raw markdown, not parsed markdown
        assert '# Heading' in html
        assert '</div>' in html
        assert '</my-content>' in html

@pytest.mark.needs_mistletoe_tokens
def test_list_inside_nested(setup_mistletoe_tokens):
    """Test rendering of Markdown lists inside nested content."""
    markdown_input = """<my-content>
  * Item 1
  * Item 2
    * Nested item
</my-content>"""
    with PyxieRenderer() as renderer:
        doc = Document(markdown_input.strip().splitlines())
        html = renderer.render(doc)
        assert 'data-slot="my-content"' in html
        assert '<ul>' in html
        assert '<li><p>Item 1</p></li>' in html
        assert '<li><p>Item 2</p>\n<ul>' in html
        assert '<li><p>Nested item</p></li>' in html
        assert '</my-content>' in html

@pytest.mark.needs_mistletoe_tokens
def test_tree_structure_code_blocks(setup_mistletoe_tokens):
    """Test rendering of tree structure/ASCII art code blocks."""
    tree_input = """```
my-site/
├── posts/          # Content
├── layouts/        # Layouts
├── static/
│   └── css/       # Styles
└── main.py        # App
```"""
    with PyxieRenderer() as renderer:
        doc = Document(tree_input.splitlines())
        html = renderer.render(doc)
        
        # Verify structure is preserved
        assert '├── posts/' in html
        assert '│   └── css/' in html
        assert '└── main.py' in html
        
        # Verify no double blank lines
        assert '\n\n\n' not in html
        
        # Verify proper code block wrapping
        assert '<pre><code>' in html
        assert '</code></pre>' in html 

@pytest.mark.needs_mistletoe_tokens
def test_table_rendering(setup_mistletoe_tokens):
    """Test rendering of tables with various edge cases."""
    # Test table with header and alignment
    table_content = """
| Left | Center | Right |
|:-----|:------:|------:|
| 1    |   2    |     3 |
| a    |   b    |     c |
"""
    with PyxieRenderer() as renderer:
        doc = Document(table_content.strip().splitlines())
        html = renderer.render(doc)
        assert '<table>' in html
        assert '<thead>' in html
        assert '<tbody>' in html
        assert '<th align="left">Left</th>' in html
        assert '<th align="center">Center</th>' in html
        assert '<th align="right">Right</th>' in html
        assert '<td align="left">1</td>' in html
        assert '<td align="center">2</td>' in html
        assert '<td align="right">3</td>' in html

    # Test table with empty cells
    empty_table = """
| Header 1 |         | Header 3 |
|----------|---------|----------|
| Cell 1   |         | Cell 3   |
|          | Cell 2  |          |
"""
    with PyxieRenderer() as renderer:
        doc = Document(empty_table.strip().splitlines())
        html = renderer.render(doc)
        # Empty cells have align attribute but no content
        assert '<td align="left"></td>' in html
        assert '<td align="left">Cell 2</td>' in html

@pytest.mark.needs_mistletoe_tokens
def test_link_rendering(setup_mistletoe_tokens):
    """Test rendering of various link types."""
    # Test auto links
    auto_links = """
Visit https://example.com or email@example.com
"""
    with PyxieRenderer() as renderer:
        doc = Document(auto_links.strip().splitlines())
        html = renderer.render(doc)
        # Auto links are not automatically converted
        assert 'https://example.com' in html
        assert 'email@example.com' in html

    # Test links with titles
    titled_links = """
[Link with title](https://example.com "Example")
[Link without title](https://example.com)
"""
    with PyxieRenderer() as renderer:
        doc = Document(titled_links.strip().splitlines())
        html = renderer.render(doc)
        assert '<a href="https://example.com" title="Example">Link with title</a>' in html
        assert '<a href="https://example.com">Link without title</a>' in html

@pytest.mark.needs_mistletoe_tokens
def test_code_rendering(setup_mistletoe_tokens):
    """Test rendering of code blocks with various languages and styles."""
    # Test code fence with language
    code_fence = """
```python
def hello():
    print("Hello, world!")
```
"""
    with PyxieRenderer() as renderer:
        doc = Document(code_fence.strip().splitlines())
        html = renderer.render(doc)
        assert '<pre><code class="language-python">' in html
        assert 'def hello():' in html

    # Test code block without language
    code_block = """
```
def hello():
    print("Hello, world!")
```
"""
    with PyxieRenderer() as renderer:
        doc = Document(code_block.strip().splitlines())
        html = renderer.render(doc)
        assert '<pre><code>' in html
        assert 'def hello():' in html

    # Test inline code with special characters
    inline_code = """
Use `<div>` for block elements and `&amp;` for entities.
"""
    with PyxieRenderer() as renderer:
        doc = Document(inline_code.strip().splitlines())
        html = renderer.render(doc)
        assert '<code>&lt;div&gt;</code>' in html
        assert '<code>&amp;amp;</code>' in html

@pytest.mark.needs_mistletoe_tokens
def test_list_rendering(setup_mistletoe_tokens):
    """Test rendering of various list types and structures."""
    # Test ordered list with different markers
    ordered_list = """
1. First item
2. Second item
   1. Sub item 1
   2. Sub item 2
3. Third item
"""
    with PyxieRenderer() as renderer:
        doc = Document(ordered_list.strip().splitlines())
        html = renderer.render(doc)
        assert '<ol>' in html
        assert '<li><p>First item</p></li>' in html
        assert '<ol>' in html  # Nested list
        assert '<li><p>Sub item 1</p></li>' in html

    # Test unordered list with different markers
    unordered_list = """
* First item
+ Second item
  - Sub item 1
  - Sub item 2
* Third item
"""
    with PyxieRenderer() as renderer:
        doc = Document(unordered_list.strip().splitlines())
        html = renderer.render(doc)
        assert '<ul>' in html
        assert '<li><p>First item</p></li>' in html
        assert '<ul>' in html  # Nested list
        assert '<li><p>Sub item 1</p></li>' in html

    # Test list with checkboxes
    checkbox_list = """
- [ ] Unchecked task
- [x] Checked task
  - [ ] Sub task 1
  - [x] Sub task 2
"""
    with PyxieRenderer() as renderer:
        doc = Document(checkbox_list.strip().splitlines())
        html = renderer.render(doc)
        assert '<ul>' in html
        assert '[ ]' in html  # Checkboxes are rendered as text
        assert '[x]' in html

@pytest.mark.needs_mistletoe_tokens
def test_renderer_error_handling(setup_mistletoe_tokens):
    """Test error handling in the renderer."""
    # Test rendering with invalid token type
    invalid_content = """
<invalid-token>
Content
</invalid-token>
"""
    with PyxieRenderer() as renderer:
        doc = Document(invalid_content.strip().splitlines())
        html = renderer.render(doc)
        # Invalid tokens are rendered as paragraphs
        assert '<p>Content</p>' in html

    # Test rendering with malformed content
    malformed_content = """
# Heading with *unclosed emphasis
"""
    with PyxieRenderer() as renderer:
        doc = Document(malformed_content.strip().splitlines())
        html = renderer.render(doc)
        # Unclosed emphasis is rendered as text
        assert '<h1 id="heading-with-unclosed-emphasis">Heading with *unclosed emphasis</h1>' in html

    # Test rendering with nested errors
    nested_errors = """
> Quote with *unclosed emphasis
> - List with *unclosed emphasis
> - Another *unclosed emphasis
"""
    with PyxieRenderer() as renderer:
        doc = Document(nested_errors.strip().splitlines())
        html = renderer.render(doc)
        # Unclosed emphasis in nested structures is rendered as text
        assert '<blockquote>' in html
        assert '<p>Quote with *unclosed emphasis</p>' in html
        assert '<li><p>List with *unclosed emphasis</p></li>' in html
        assert '<li><p>Another *unclosed emphasis</p></li>' in html

@pytest.mark.needs_mistletoe_tokens
def test_renderer_initialization(setup_mistletoe_tokens, caplog):
    """Test renderer initialization and warning logging."""
    # Test with known custom tokens
    with PyxieRenderer(RawBlockToken, NestedContentToken) as renderer:
        # Verify known tokens are registered by checking if they can be rendered
        doc = Document("<raw>test</raw>")
        html = renderer.render(doc)
        assert 'data-slot="raw"' in html
        assert '<p>test</p>' in html
        
        doc = Document("<nested>test</nested>")
        html = renderer.render(doc)
        assert 'data-slot="nested"' in html
        assert '<p>test</p>' in html

@pytest.mark.needs_mistletoe_tokens
def test_render_content_error_handling(setup_mistletoe_tokens):
    """Test error handling in the main render_content function."""
    from pyxie.renderer import render_content
    from pyxie.types import ContentItem
    from pathlib import Path

    # Test with empty content and no layout specified
    empty_item = ContentItem(
        source_path=Path("test.md"),
        content="",
        metadata={"layout": "nonexistent_layout"}  # Explicitly request a nonexistent layout
    )
    result = render_content(empty_item)
    assert "Layout 'nonexistent_layout' not found" in result

@pytest.mark.needs_mistletoe_tokens
def test_math_rendering(setup_mistletoe_tokens):
    """Test rendering of math tokens using KaTeX."""
    # Test inline math
    inline_math = "This is inline math: $x^2 + y^2 = z^2$"
    with PyxieRenderer() as renderer:
        doc = Document(inline_math)
        html = renderer.render(doc)
        assert '<span class="katex-inline"' in html
        assert 'data-tex="x^2 + y^2 = z^2"' in html

    # Test display math
    display_math = """This is display math:
$$
\\sum_{i=1}^n i = \\frac{n(n+1)}{2}
$$"""
    with PyxieRenderer() as renderer:
        doc = Document(display_math)
        html = renderer.render(doc)
        assert '<div class="katex-block"' in html
        assert '\\sum_{i=1}^n i = \\frac{n(n+1)}{2}' in html

@pytest.mark.needs_mistletoe_tokens
def test_raw_block_edge_cases(setup_mistletoe_tokens):
    """Test edge cases in raw block rendering."""
    # Test empty FastHTML block
    empty_fasthtml = "<fasthtml></fasthtml>"
    with PyxieRenderer() as renderer:
        doc = Document(empty_fasthtml)
        html = renderer.render(doc)
        assert html == ''  # Empty FastHTML should return empty string

    # Test FastHTML with only whitespace
    whitespace_fasthtml = "<fasthtml>   \n   </fasthtml>"
    with PyxieRenderer() as renderer:
        doc = Document(whitespace_fasthtml)
        html = renderer.render(doc)
        assert html == ''

    # Test style block with error
    style_with_error = "<style>{invalid css</style>"
    with PyxieRenderer() as renderer:
        doc = Document(style_with_error)
        html = renderer.render(doc)
        assert '<style>' in html
        assert '{invalid css' in html

    # Test script block with error
    script_with_error = "<script>{invalid js</script>"
    with PyxieRenderer() as renderer:
        doc = Document(script_with_error)
        html = renderer.render(doc)
        assert '<script>' in html
        assert '{invalid js' in html

@pytest.mark.needs_mistletoe_tokens
def test_empty_content_handling(setup_mistletoe_tokens):
    """Test handling of empty content in various contexts."""
    # Test empty paragraph
    empty_paragraph = '<p></p>'
    with PyxieRenderer() as renderer:
        doc = Document(empty_paragraph.splitlines())
        html = renderer.render(doc)
        assert '<p></p>' in html

    # Test paragraph with only whitespace
    whitespace_paragraph = '<p>   </p>'
    with PyxieRenderer() as renderer:
        doc = Document(whitespace_paragraph.splitlines())
        html = renderer.render(doc)
        assert '<p>   </p>' in html

    # Test empty nested content
    empty_nested = "<custom-block></custom-block>"
    with PyxieRenderer() as renderer:
        doc = Document(empty_nested)
        html = renderer.render(doc)
        assert 'data-slot="custom-block"' in html
        assert '<custom-block' in html
        assert '</custom-block>' in html

@pytest.mark.needs_mistletoe_tokens
def test_render_content_error_handling_comprehensive(setup_mistletoe_tokens, clear_layouts):
    """Test comprehensive error handling in render_content function."""
    from pyxie.types import ContentItem
    from pathlib import Path
    from pyxie.renderer import render_content

    # Test with invalid layout
    item_invalid_layout = ContentItem(
        content="# Test",
        source_path=Path("test.md"),
        metadata={"layout": "nonexistent_layout"}
    )
    result = render_content(item_invalid_layout)
    assert "Layout 'nonexistent_layout' not found" in result

    # Test with invalid Markdown content
    item_invalid_markdown = ContentItem(
        content="<invalid>markdown</unclosed>",
        source_path=Path("test.md")
    )
    result = render_content(item_invalid_markdown)
    # Should get error about missing default layout
    assert "Layout 'default' not found" in result

    # Test with empty content
    item_empty = ContentItem(
        content="",
        source_path=Path("test.md")
    )
    result = render_content(item_empty)
    # Should get error about missing default layout
    assert "Layout 'default' not found" in result

@pytest.mark.needs_mistletoe_tokens
def test_renderer_initialization_with_unknown_token(setup_mistletoe_tokens, caplog):
    """Test renderer initialization with unknown token types."""
    class UnknownToken(BlockToken):
        """A token type that the renderer doesn't know how to handle."""
        pass

    # The renderer should log a warning and not register unknown tokens
    with PyxieRenderer(UnknownToken) as renderer:
        # Verify warning was logged
        assert any("Token 'UnknownToken' not registered - no render method found." in record.message 
                  for record in caplog.records)
        # Unknown tokens should not be registered
        assert not hasattr(renderer, 'render_unknown_token')
        # Should still have the basic render methods
        assert hasattr(renderer, 'render_raw_block_token')
        assert hasattr(renderer, 'render_nested_content_token')

@pytest.mark.needs_mistletoe_tokens
def test_raw_block_error_handling_comprehensive_extended_2(setup_mistletoe_tokens, clear_layouts):
    """Test error handling in raw block rendering with various scenarios."""
    # Test script error handling with invalid attributes
    script_error = """
<script invalid="'">
throw new Error("Test script error");
</script>
"""
    with PyxieRenderer() as renderer:
        doc = Document(script_error.strip().splitlines())
        html = renderer.render(doc)
        assert '<script invalid="&#x27;">' in html  # Script tags are raw blocks, so quotes are escaped
        assert 'throw new Error("Test script error");' in html

    # Test style error handling with invalid attributes
    style_error = """
<style invalid="'">
@invalid { color: red; }
</style>
"""
    with PyxieRenderer() as renderer:
        doc = Document(style_error.strip().splitlines())
        html = renderer.render(doc)
        assert '<style invalid="&#x27;">' in html  # Style tags are raw blocks, so quotes are escaped
        assert '@invalid { color: red; }' in html

    # Test raw block error handling with invalid attributes
    raw_error = """
<pre invalid="'">
{{ invalid content }}
</pre>
"""
    with PyxieRenderer() as renderer:
        doc = Document(raw_error.strip().splitlines())
        html = renderer.render(doc)
        assert '<pre invalid="\'">' in html  # Pre is a standard HTML tag, so quotes are not escaped
        assert '{{ invalid content }}' in html

    # Test image rendering with invalid pyxie: URL
    invalid_image = """
![Test](pyxie:invalid)
"""
    with PyxieRenderer() as renderer:
        doc = Document(invalid_image.strip().splitlines())
        html = renderer.render(doc)
        assert 'src="pyxie:invalid"' in html
        assert 'alt="Test"' in html

    # Test empty paragraph handling
    empty_paragraph = """

"""
    with PyxieRenderer() as renderer:
        doc = Document(empty_paragraph.strip().splitlines())
        html = renderer.render(doc)
        assert html == ""

    # Test render_content error handling with invalid layout HTML
    from pyxie.types import ContentItem
    from pyxie.renderer import render_content
    from pyxie.layouts import registry

    # Register a layout that will raise an error
    registry.register("error_test", lambda *args, **kwargs: None)

    # Test with layout that returns None
    error_layout_item = ContentItem(
        content="Test content",
        metadata={"layout": "error_test"},
        source_path="test.md"
    )
    result = render_content(error_layout_item)
    # assert "UNEXPECTED ERROR" in result
    assert "ERROR: LAYOUT PROCESSING: LayoutValidationError" in result
    assert "must return a FastHTML component or HTML string" in result

    # Register a valid test layout
    registry.register("test", lambda *args, **kwargs: '<div><div data-slot="content">Test Layout</div></div>')

    # Test with content that will cause a parsing error
    invalid_content_item = ContentItem(
        content="<invalid>markdown</invalid>",
        metadata={"layout": "test"},
        source_path="test.md"
    )
    result = render_content(invalid_content_item)
    assert "Test Layout" in result

@pytest.mark.needs_mistletoe_tokens
def test_raw_block_error_handling_comprehensive_extended_3(setup_mistletoe_tokens, clear_layouts):
    """Test error handling in raw block rendering with actual exceptions."""
    # Test script error handling with invalid token
    from pyxie.parser import RawBlockToken
    class InvalidScriptToken(RawBlockToken):
        def __init__(self):
            self.tag_name = 'script'
            self.content = None
            self.attrs = {}
            self.is_self_closing = True  # Script tags can be self-closing
    
    with PyxieRenderer() as renderer:
        html = renderer.render_raw_block_token(InvalidScriptToken())
        assert '<script />' in html  # For empty script tags, we expect a self-closing tag

    # Test style error handling with invalid token
    class InvalidStyleToken(RawBlockToken):
        def __init__(self):
            self.tag_name = 'style'
            self.content = None
            self.attrs = {}
            self.is_self_closing = True  # Style tags can be self-closing
    
    with PyxieRenderer() as renderer:
        html = renderer.render_raw_block_token(InvalidStyleToken())
        assert '<style />' in html  # For empty style tags, we expect a self-closing tag

    # Test pre error handling with invalid token
    class InvalidPreToken(RawBlockToken):
        def __init__(self):
            self.tag_name = 'pre'
            self.content = None
            self.attrs = {}
            self.is_self_closing = False  # Pre tags should never be self-closing
    
    with PyxieRenderer() as renderer:
        html = renderer.render_raw_block_token(InvalidPreToken())
        assert '<pre>None</pre>' in html  # None is rendered as string since pre is a standard HTML tag

    # Test error handling with missing tag_name
    class InvalidToken(RawBlockToken):
        def __init__(self):
            self.content = "test"
            self.attrs = {}
    
    with PyxieRenderer() as renderer:
        with pytest.raises(AttributeError) as exc_info:
            html = renderer.render_raw_block_token(InvalidToken())
        assert "'InvalidToken' object has no attribute 'tag_name'" in str(exc_info.value)

    # Test error handling with invalid attributes
    class InvalidAttrToken(RawBlockToken):
        def __init__(self):
            self.tag_name = 'script'
            self.content = "test"
            self.attrs = {'onclick': 'alert("test")'}  # Invalid attribute for script tag
    
    with PyxieRenderer() as renderer:
        html = renderer.render_raw_block_token(InvalidAttrToken())
        assert 'onclick="alert(&quot;test&quot;)"' in html  # Attributes should be properly escaped

@pytest.mark.needs_mistletoe_tokens
def test_renderer_edge_cases(setup_mistletoe_tokens):
    """Test various edge cases in the renderer."""
    # Test FastHTML block with empty result
    empty_fasthtml = """
<fasthtml>
show(Div(""))
</fasthtml>
"""
    with PyxieRenderer() as renderer:
        doc = Document(empty_fasthtml.strip().splitlines())
        html = renderer.render(doc)
        assert '<div>' in html
        assert '<div></div>' in html
        assert '</div>' in html

    # Test FastHTML block with error in execution
    error_fasthtml = """
<fasthtml>
raise ValueError("Test error")
</fasthtml>
"""
    with PyxieRenderer() as renderer:
        doc = Document(error_fasthtml.strip().splitlines())
        html = renderer.render(doc)
        assert '<div class="error">Error: Test error</div>' in html

    # Test script block with error in rendering
    error_script = """
<script>
{{ invalid content }}
</script>
"""
    with PyxieRenderer() as renderer:
        doc = Document(error_script.strip().splitlines())
        html = renderer.render(doc)
        assert '<script>' in html
        assert '{{ invalid content }}' in html
        assert '</script>' in html

    # Test style block with error in rendering
    error_style = """
<style>
{{ invalid content }}
</style>
"""
    with PyxieRenderer() as renderer:
        doc = Document(error_style.strip().splitlines())
        html = renderer.render(doc)
        assert '<style>' in html
        assert '{{ invalid content }}' in html
        assert '</style>' in html

    # Test raw block with error in rendering
    error_raw = """
<pre>
{{ invalid content }}
</pre>
"""
    with PyxieRenderer() as renderer:
        doc = Document(error_raw.strip().splitlines())
        html = renderer.render(doc)
        assert '<pre>' in html
        assert '{{ invalid content }}' in html
        assert '</pre>' in html

    # Test nested content with error in rendering
    error_nested = """
<my-content>
{{ invalid content }}
</my-content>
"""
    with PyxieRenderer() as renderer:
        doc = Document(error_nested.strip().splitlines())
        html = renderer.render(doc)
        assert 'data-slot="my-content"' in html
        assert '{{ invalid content }}' in html
        assert '</my-content>' in html

    # Test image with pyxie: URL
    pyxie_image = '![Test](pyxie:test/800/600)'
    with PyxieRenderer() as renderer:
        doc = Document(pyxie_image.splitlines())
        html = renderer.render(doc)
        assert 'src="https://picsum.photos/seed/test/800/600"' in html
        assert 'alt="Test"' in html

    # Test image with title
    image_with_title = '![Test](test.jpg "Image Title")'
    with PyxieRenderer() as renderer:
        doc = Document(image_with_title.splitlines())
        html = renderer.render(doc)
        assert 'title="Image Title"' in html

    # Test empty paragraph
    empty_paragraph = '<p></p>'
    with PyxieRenderer() as renderer:
        doc = Document(empty_paragraph.splitlines())
        html = renderer.render(doc)
        assert '<p></p>' in html

    # Test paragraph with only whitespace
    whitespace_paragraph = '<p>   </p>'
    with PyxieRenderer() as renderer:
        doc = Document(whitespace_paragraph.splitlines())
        html = renderer.render(doc)
        assert '<p>   </p>' in html

    # Test heading with duplicate text
    duplicate_heading = """
# Test Heading
# Test Heading
"""
    with PyxieRenderer() as renderer:
        doc = Document(duplicate_heading.strip().splitlines())
        html = renderer.render(doc)
        assert 'id="test-heading"' in html
        assert 'id="test-heading-1"' in html

    # Test heading with special characters
    special_heading = '# Test & Heading!'
    with PyxieRenderer() as renderer:
        doc = Document(special_heading.splitlines())
        html = renderer.render(doc)
        assert 'id="test-amp-heading"' in html
        assert '>Test &amp; Heading!</h1>' in html

    # Test heading with HTML tags
    html_heading = '# Test <span>Heading</span>'
    with PyxieRenderer() as renderer:
        doc = Document(html_heading.splitlines())
        html = renderer.render(doc)
        assert 'id="test-heading"' in html