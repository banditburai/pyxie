"""Debug tests for parser functionality."""

import pytest
import logging
from mistletoe import Document
from mistletoe.block_token import Heading, Paragraph, List, ListItem, CodeFence
from mistletoe.span_token import Emphasis, Strong, RawText, InlineCode
from pyxie.parser import RawBlockToken, NestedContentToken
from pyxie.renderer import PyxieRenderer

logger = logging.getLogger(__name__)

@pytest.mark.needs_mistletoe_tokens
def test_nested_content_token_initialization(setup_mistletoe_tokens):
    """Test how NestedContentToken initializes and processes content."""
    # Test case 1: Simple markdown content
    content = """<custom>
This is **bold** and *italic* content
</custom>"""
    doc = Document(content.splitlines())

    print("\nTest 1: Simple markdown content")
    assert len(doc.children) == 1
    token = doc.children[0]
    assert isinstance(token, NestedContentToken)
    assert token.tag_name == 'custom'
    assert len(token.children) == 1
    assert isinstance(token.children[0], Paragraph)
    assert len(token.children[0].children) == 5
    assert isinstance(token.children[0].children[0], RawText)
    assert token.children[0].children[0].content == "This is "
    assert isinstance(token.children[0].children[1], Strong)
    assert len(token.children[0].children[1].children) == 1
    assert token.children[0].children[1].children[0].content == "bold"
    assert isinstance(token.children[0].children[2], RawText)
    assert token.children[0].children[2].content == " and "
    assert isinstance(token.children[0].children[3], Emphasis)
    assert len(token.children[0].children[3].children) == 1
    assert token.children[0].children[3].children[0].content == "italic"
    assert isinstance(token.children[0].children[4], RawText)
    assert token.children[0].children[4].content == " content"

@pytest.mark.needs_mistletoe_tokens
def test_block_splitting(setup_mistletoe_tokens):
    """Test how content is split into blocks."""
    # Test case 1: Simple markdown content
    content = """<custom>
This is **bold** content
</custom>"""
    doc = Document(content.splitlines())

    print("\nTest 1: Block splitting - Simple content")
    print(f"Original content: {content}")
    assert len(doc.children) == 1
    token = doc.children[0]
    assert isinstance(token, NestedContentToken)
    assert token.tag_name == 'custom'
    assert len(token.children) == 1
    assert isinstance(token.children[0], Paragraph)
    assert len(token.children[0].children) == 3
    assert isinstance(token.children[0].children[0], RawText)
    assert token.children[0].children[0].content == "This is "
    assert isinstance(token.children[0].children[1], Strong)
    assert len(token.children[0].children[1].children) == 1
    assert token.children[0].children[1].children[0].content == "bold"
    assert isinstance(token.children[0].children[2], RawText)
    assert token.children[0].children[2].content == " content"

@pytest.mark.needs_mistletoe_tokens
def test_full_rendering_pipeline(setup_mistletoe_tokens):
    """Test the full rendering pipeline with custom tokens."""
    content = """<custom>
# Heading
Some **bold** content
</custom>"""
    doc = Document(content.splitlines())
    
    with PyxieRenderer() as renderer:
        html = renderer.render(doc)
        assert '<h1 id="heading">Heading</h1>' in html
        assert '<strong>bold</strong>' in html
        assert 'data-slot="custom"' in html 