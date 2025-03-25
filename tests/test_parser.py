"""Test the parser module."""

import pytest
from datetime import date
from pathlib import Path
from typing import Dict, Any
from mistletoe import Document
from fastcore.xml import FT, Div

from pyxie.parser import parse_frontmatter
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