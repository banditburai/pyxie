"""Test the parser module."""

import pytest
from datetime import date
from pathlib import Path
from typing import Dict, Any
from mistletoe import Document
from fastcore.xml import FT, Div

from pyxie.parser import parse_frontmatter, custom_tokenize_block, NestedContentToken, FastHTMLToken, ScriptToken
from pyxie.constants import DEFAULT_METADATA

# Define token types for testing
TOKEN_TYPES = [NestedContentToken, FastHTMLToken, ScriptToken]

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
    
    tokens = list(custom_tokenize_block(content, TOKEN_TYPES))
    
    assert len(tokens) == 1
    token = tokens[0]
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
    
    tokens = list(custom_tokenize_block(content, TOKEN_TYPES))
    
    assert len(tokens) == 1
    token = tokens[0]
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
    
    tokens = list(custom_tokenize_block(content, TOKEN_TYPES))
    
    assert len(tokens) == 1
    token = tokens[0]
    assert isinstance(token, FastHTMLToken)
    assert 'show(Div("Test", cls="test"))' in token.content.strip()

def test_script_block_parsing() -> None:
    """Test parsing of script blocks."""
    content = """<script>
    console.log("Test");
</script>"""
    
    tokens = list(custom_tokenize_block(content, TOKEN_TYPES))
    
    assert len(tokens) == 1
    token = tokens[0]
    assert isinstance(token, ScriptToken)
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
    
    tokens = list(custom_tokenize_block(content, TOKEN_TYPES))
    
    assert len(tokens) == 1
    token = tokens[0]
    assert isinstance(token, NestedContentToken)
    assert token.tag_name == "custom"
    assert "**bold**" in token.content
    assert "<nested>" in token.content
    assert "<fasthtml>" in token.content
    assert "<script>" in token.content 