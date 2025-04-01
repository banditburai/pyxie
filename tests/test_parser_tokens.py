"""Test custom token parsing with Mistletoe's token registration system."""

import pytest
import logging
from mistletoe import Document
from mistletoe.block_token import Heading, Paragraph, List, ListItem, CodeFence
from mistletoe.span_token import Emphasis, Strong, RawText, InlineCode
from pyxie.parser import RawBlockToken, NestedContentToken
from pyxie.renderer import PyxieRenderer

logger = logging.getLogger(__name__)

@pytest.mark.needs_mistletoe_tokens
def test_nested_content_parsing(setup_mistletoe_tokens):
    """Test parsing of nested content blocks with inner Markdown."""
    markdown_input = """
<my-content class="test">
# Heading Inside
Some **bold** text.
</my-content>
"""
    # The fixture setup_mistletoe_tokens will have already registered our custom tokens
    # and removed HtmlBlock from Mistletoe's token types
    doc = Document(markdown_input.strip().splitlines())

    # Assertions
    assert len(doc.children) == 1
    token = doc.children[0]
    assert isinstance(token, NestedContentToken)
    assert token.tag_name == 'my-content'
    assert token.attrs == {'class': 'test'}
    # Check that inner content was parsed into children by Mistletoe
    assert len(token.children) == 2  # Heading and Paragraph
    assert isinstance(token.children[0], Heading)  # Check Heading type
    assert isinstance(token.children[1], Paragraph)  # Check Paragraph type

@pytest.mark.needs_mistletoe_tokens
def test_raw_block_token(setup_mistletoe_tokens):
    """Test parsing of raw block tokens (no inner parsing)."""
    markdown_input = """
<script type="text/javascript">
  let x = 1; // Raw content
</script>
"""
    doc = Document(markdown_input.strip().splitlines())

    # Assertions
    assert len(doc.children) == 1
    token = doc.children[0]
    assert isinstance(token, RawBlockToken)
    assert token.tag_name == 'script'
    assert token.attrs == {'type': 'text/javascript'}
    assert token.content.strip() == 'let x = 1; // Raw content'
    assert token.children == []  # Raw tokens have no parsed children

@pytest.mark.needs_mistletoe_tokens
def test_custom_span_token(setup_mistletoe_tokens):
    """Test that custom span-like tags are treated as raw text."""
    markdown_input = "Some text <my-span id=1>with *italic* content</my-span> here."
    doc = Document(markdown_input.strip().splitlines())

    # Assertions (Paragraph -> RawText, Emphasis, RawText)
    assert len(doc.children) == 1
    para = doc.children[0]
    assert isinstance(para, Paragraph)
    assert len(para.children) == 3
    assert isinstance(para.children[0], RawText)
    assert para.children[0].content == "Some text <my-span id=1>with "
    assert isinstance(para.children[1], Emphasis)
    assert len(para.children[1].children) == 1
    assert para.children[1].children[0].content == "italic"
    assert isinstance(para.children[2], RawText)
    assert para.children[2].content == " content</my-span> here."

@pytest.mark.needs_mistletoe_tokens
def test_nested_custom_blocks(setup_mistletoe_tokens):
    """Test parsing of nested custom blocks with proper nesting level tracking."""
    markdown_input = """
<outer>
  <inner>
    <deepest>
      Content here
    </deepest>
  </inner>
</outer>
"""
    doc = Document(markdown_input.strip().splitlines())

    # Assertions
    assert len(doc.children) == 1
    outer = doc.children[0]
    assert isinstance(outer, NestedContentToken)
    assert outer.tag_name == 'outer'
    assert len(outer.children) == 1

    inner = outer.children[0]
    assert isinstance(inner, NestedContentToken)
    assert inner.tag_name == 'inner'
    assert len(inner.children) == 1

    deepest = inner.children[0]
    assert isinstance(deepest, NestedContentToken)
    assert deepest.tag_name == 'deepest'
    assert len(deepest.children) == 1

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
    # The inner content should be a single paragraph containing both the span and regular text
    assert len(custom_block.children) == 1
    assert isinstance(custom_block.children[0], Paragraph)
    paragraph = custom_block.children[0]
    assert len(paragraph.children) == 7  # span + text + formatting

@pytest.mark.needs_mistletoe_tokens
def test_void_elements(setup_mistletoe_tokens):
    """Test parsing of void elements (self-closing tags)."""
    markdown_input = """
<custom-void />
<custom-void attr="value" />
"""
    doc = Document(markdown_input.strip().splitlines())

    # Assertions
    assert len(doc.children) == 2
    for token in doc.children:
        assert isinstance(token, NestedContentToken)
        assert token.tag_name == 'custom-void'
        assert token.children == []  # Void elements have no children
        assert token.content == ''  # Void elements have no content

@pytest.mark.needs_mistletoe_tokens
def test_attributes_parsing(setup_mistletoe_tokens):
    """Test parsing of various attribute formats."""
    markdown_input = """
<custom key="value" bool-key no-value="" single='quote' />
"""
    doc = Document(markdown_input.strip().splitlines())

    # Assertions
    assert len(doc.children) == 1
    token = doc.children[0]
    assert isinstance(token, NestedContentToken)
    assert token.tag_name == 'custom'
    assert token.attrs == {
        'key': 'value',
        'bool-key': True,
        'no-value': '',
        'single': 'quote'
    } 

@pytest.mark.needs_mistletoe_tokens
def test_empty_nested_content(setup_mistletoe_tokens):
    """Test parsing of empty nested content blocks."""
    content = "<my-content></my-content>"
    doc = Document(content.splitlines())
    assert len(doc.children) == 1
    custom_block = doc.children[0]
    assert isinstance(custom_block, NestedContentToken)
    assert custom_block.tag_name == "my-content"
    assert len(custom_block.children) == 0  # Should have no children after parsing empty content

@pytest.mark.needs_mistletoe_tokens
def test_empty_span(setup_mistletoe_tokens):
    """Test that empty custom spans are treated as raw text."""
    content = "Text <my-span></my-span> more."
    doc = Document(content.splitlines())
    assert len(doc.children) == 1
    paragraph = doc.children[0]
    assert isinstance(paragraph, Paragraph)
    assert len(paragraph.children) == 1
    assert isinstance(paragraph.children[0], RawText)
    assert paragraph.children[0].content == content

@pytest.mark.needs_mistletoe_tokens
def test_raw_content_with_closing_tag(setup_mistletoe_tokens):
    """Test raw block content containing closing tag substring."""
    content = '<script>var x = "</script>";</script>'
    doc = Document(content.splitlines())
    assert len(doc.children) == 1
    script = doc.children[0]
    assert isinstance(script, RawBlockToken)
    assert script.tag_name == "script"
    assert script.content == 'var x = "</script>";'  # Should capture full content including closing tag

@pytest.mark.needs_mistletoe_tokens
def test_standard_html_inside_nested(setup_mistletoe_tokens):
    """Test standard HTML blocks inside nested content."""
    content = "<my-content><div>DIV</div></my-content>"
    doc = Document(content.splitlines())
    assert len(doc.children) == 1
    custom_block = doc.children[0]
    assert isinstance(custom_block, NestedContentToken)
    assert custom_block.tag_name == "my-content"
    assert len(custom_block.children) == 1
    # Mistletoe should parse <div> as a Paragraph since it's not a registered block token
    assert isinstance(custom_block.children[0], Paragraph)
    assert len(custom_block.children[0].children) == 1
    assert isinstance(custom_block.children[0].children[0], RawText)
    assert custom_block.children[0].children[0].content == '<div>DIV</div>'

@pytest.mark.needs_mistletoe_tokens
def test_standard_list_inside_nested(setup_mistletoe_tokens):
    """Test standard Markdown list inside nested content."""
    content = """<my-content>
* Item 1
* Item 2
</my-content>"""
    doc = Document(content.splitlines())
    assert len(doc.children) == 1
    custom_block = doc.children[0]
    assert isinstance(custom_block, NestedContentToken)
    assert custom_block.tag_name == "my-content"
    assert len(custom_block.children) == 1
    assert isinstance(custom_block.children[0], List)
    list_items = custom_block.children[0].children
    assert len(list_items) == 2
    assert isinstance(list_items[0], ListItem)
    assert isinstance(list_items[1], ListItem)
    assert list_items[0].children[0].children[0].content == "Item 1"
    assert list_items[1].children[0].children[0].content == "Item 2" 

@pytest.mark.needs_mistletoe_tokens
def test_custom_tags_in_code_fence(setup_mistletoe_tokens):
    """Test that custom tags inside code fences are treated as literal text."""
    markdown_input = """
```html
<fasthtml>
  <script>console.log("test");</script>
  <my-content>Some content</my-content>
</fasthtml>
```
"""
    doc = Document(markdown_input.strip().splitlines())
    
    # Assertions
    assert len(doc.children) == 1
    code_fence = doc.children[0]
    assert isinstance(code_fence, CodeFence)
    assert code_fence.language == "html"
    # The content should be treated as literal text, not parsed as tokens
    assert "<fasthtml>" in code_fence.content
    assert "<script>console.log(\"test\");</script>" in code_fence.content
    assert "<my-content>Some content</my-content>" in code_fence.content
    assert "</fasthtml>" in code_fence.content 