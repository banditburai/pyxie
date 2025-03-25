"""Test the parser module."""

import pytest
from datetime import date
from pathlib import Path
from typing import Dict, Any
from mistletoe import Document
from fastcore.xml import FT, Div

from pyxie.parser import parse
from pyxie.types import MarkdownDocument
from pyxie.constants import DEFAULT_METADATA

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
    parsed = parse(sample_markdown)
    
    # Check metadata fields
    assert parsed.metadata['title'] == 'Test Document'
    assert parsed.metadata['author'] == 'Test Author'
    assert parsed.metadata['date'] == date(2024, 1, 1)  # Date is parsed as datetime.date
    assert parsed.metadata['tags'] == ['test', 'sample']

def test_empty_frontmatter() -> None:
    """Test handling of empty frontmatter."""
    content = '''---
---
# Content after empty frontmatter'''
    
    parsed = parse(content)
    assert isinstance(parsed, MarkdownDocument)
    assert parsed.metadata == DEFAULT_METADATA  # Empty frontmatter uses defaults
    assert '# Content after empty frontmatter' in parsed.raw_content

def test_no_frontmatter() -> None:
    """Test handling of content without frontmatter."""
    content = '# Content without frontmatter'
    
    parsed = parse(content)
    assert isinstance(parsed, MarkdownDocument)
    assert parsed.metadata == DEFAULT_METADATA  # No frontmatter uses defaults
    assert content == parsed.raw_content 