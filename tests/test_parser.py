"""Test the parser module."""

import pytest
import mistletoe
import logging
from datetime import date
from pathlib import Path
from typing import Dict, Any
from mistletoe import Document
from mistletoe import block_token as mistletoe_block_token
from mistletoe import span_token as mistletoe_span_token
from mistletoe.block_token import Heading, Paragraph, List, ListItem, HtmlBlock, CodeFence
from mistletoe.span_token import Emphasis, Strong, RawText, HTMLSpan, InlineCode
from fastcore.xml import FT, Div

from pyxie.parser import parse_frontmatter, RawBlockToken, NestedContentToken
from pyxie.constants import DEFAULT_METADATA

logger = logging.getLogger(__name__)

@pytest.fixture(autouse=True)
def setup_and_teardown():
    """Fixture to set up and tear down custom tokens for testing."""
    # Save original token types
    from mistletoe.block_token import _token_types as mistletoe_block_token
    from mistletoe.span_token import _token_types as mistletoe_span_token
    original_block_tokens = mistletoe_block_token.copy()
    original_span_tokens = mistletoe_span_token.copy()

    # Remove HtmlBlock and HtmlSpan to prevent special handling of HTML tags
    if HtmlBlock in mistletoe_block_token:
        mistletoe_block_token.remove(HtmlBlock)
    if HTMLSpan in mistletoe_span_token:
        mistletoe_span_token.remove(HTMLSpan)

    # Register our custom tokens with high priority
    logger.debug("Custom tokens registered for test.")
    mistletoe_block_token.insert(0, RawBlockToken)
    mistletoe_block_token.insert(1, NestedContentToken)

    yield

    # Restore original token types
    mistletoe_block_token.clear()
    mistletoe_block_token.extend(original_block_tokens)
    mistletoe_span_token.clear()
    mistletoe_span_token.extend(original_span_tokens)
    logger.debug("Tokens reset after test.")

# Define token types for testing
TOKEN_TYPES = [NestedContentToken, RawBlockToken]

@pytest.fixture
def sample_markdown() -> str:
    """Create a sample markdown document with frontmatter and content."""
    return '''---
title: Test Document
author: Test Author
date: 2024-01-01
tags: [test, sample]
---

# Introduction

This is a test document with various content types.

<fasthtml>
show(Div("Hello from FastHTML"))
</fasthtml>

<script>
console.log("Hello from script");
</script>

<content>
This is a content block
</content>
'''

def test_frontmatter_parsing(sample_markdown: str) -> None:
    """Test that frontmatter is correctly parsed."""
    metadata, content = parse_frontmatter(sample_markdown)
    
    # Check metadata fields
    assert metadata['title'] == 'Test Document'
    assert metadata['author'] == 'Test Author'
    assert metadata['date'] == date(2024, 1, 1)  # Date is parsed as datetime.date
    assert metadata['tags'] == ['test', 'sample']
    
    # Check content
    assert '# Introduction' in content
    assert 'This is a test document with various content types.' in content

def test_empty_frontmatter() -> None:
    """Test handling of empty frontmatter."""
    content = '''---
---
# Content after empty frontmatter'''
    
    metadata, remaining_content = parse_frontmatter(content)    
    assert metadata == {}  # Empty frontmatter returns empty dict
    assert '# Content after empty frontmatter' in remaining_content

def test_no_frontmatter() -> None:
    """Test handling of content without frontmatter."""
    content = '# Content without frontmatter'
    
    metadata, remaining_content = parse_frontmatter(content)
    assert metadata == {}  # No frontmatter returns empty dict
    assert content == remaining_content

def test_custom_block_parsing() -> None:
    """Test parsing of custom blocks."""
    content = """<custom class="test">
    This is a custom block with **bold** text.
</custom>"""
    
    doc = Document(content.splitlines())
    
    assert len(doc.children) == 1
    token = doc.children[0]
    assert isinstance(token, NestedContentToken)
    assert token.tag_name == "custom"
    assert token.attrs == {"class": "test"}
    assert "**bold**" in token.content

def test_nested_block_parsing() -> None:
    """Test parsing of nested blocks."""
    content = """<custom>
    Outer content
    <nested>
        Inner content with [link](https://example.com)
    </nested>
</custom>"""
    
    doc = Document(content.splitlines())
    
    assert len(doc.children) == 1
    token = doc.children[0]
    assert isinstance(token, NestedContentToken)
    assert token.tag_name == "custom"
    assert "Outer content" in token.content
    assert "<nested>" in token.content
    assert "[link](https://example.com)" in token.content

def test_fasthtml_block_parsing() -> None:
    """Test parsing of FastHTML blocks."""
    content = """<fasthtml>
    show(Div("Test", cls="test"))
</fasthtml>"""
    
    doc = Document(content.splitlines())
    
    assert len(doc.children) == 1
    token = doc.children[0]
    assert isinstance(token, RawBlockToken)
    assert token.tag_name == "fasthtml"
    assert 'show(Div("Test", cls="test"))' in token.content.strip()

def test_script_block_parsing() -> None:
    """Test parsing of script blocks."""
    content = """<script>
    console.log("Test");
</script>"""
    
    doc = Document(content.splitlines())
    
    assert len(doc.children) == 1
    token = doc.children[0]
    assert isinstance(token, RawBlockToken)
    assert token.tag_name == "script"
    assert 'console.log("Test");' in token.content.strip()

def test_mixed_block_parsing() -> None:
    """Test parsing of mixed block types."""
    content = """<custom>
    Regular markdown with **bold**
    <nested>
        Nested content
    </nested>
    <fasthtml>
        show(Div("Test"))
    </fasthtml>
    <script>
        console.log("Test");
    </script>
</custom>"""
    
    doc = Document(content.splitlines())
    
    assert len(doc.children) == 1
    token = doc.children[0]
    assert isinstance(token, NestedContentToken)
    assert token.tag_name == "custom"
    assert "**bold**" in token.content
    assert "<nested>" in token.content
    assert "<fasthtml>" in token.content
    assert "<script>" in token.content 