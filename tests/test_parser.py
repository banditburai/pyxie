"""Tests for the parser module."""

import pytest
import logging
from typing import Dict, List, Optional, Any
from pyxie.parser import parse, iter_blocks, parse_frontmatter, ContentBlock, ParsedContent
from pyxie.errors import ParseError, FrontmatterError, BlockError

# Test fixtures
@pytest.fixture
def sample_markdown() -> str:
    """Sample markdown with frontmatter and content blocks."""
    return """---
title: Test Document
author: Test Author
date: 2024-01-01
tags: [test, sample]
---

# Introduction

This is a test document with multiple content blocks.

<content>
This is the main content of the document.
With multiple paragraphs.

- List item 1
- List item 2
</content>

<example>
```python
def hello_world():
    print("Hello, world!")
```
</example>

<sidebar>
Additional information can go here.
</sidebar>
"""

@pytest.fixture
def minimal_markdown() -> str:
    """Minimal markdown with just frontmatter."""
    return """---
title: Minimal Document
---

Just some plain markdown without any XML blocks.
"""

@pytest.fixture
def empty_frontmatter_markdown() -> str:
    """Markdown with empty frontmatter."""
    return """---
---

Content without any metadata.
"""

# Test parsing of frontmatter
def test_frontmatter_parsing(sample_markdown: str) -> None:
    """Test that frontmatter is correctly parsed."""
    metadata, content = parse_frontmatter(sample_markdown)
    
    assert metadata["title"] == "Test Document"
    assert metadata["author"] == "Test Author"
    assert str(metadata["date"]).startswith("2024-01-01")
    assert isinstance(metadata["tags"], list)
    assert "test" in metadata["tags"]
    assert "sample" in metadata["tags"]
    assert "# Introduction" in content

def test_empty_frontmatter(empty_frontmatter_markdown: str) -> None:
    """Test handling of empty frontmatter."""
    metadata, content = parse_frontmatter(empty_frontmatter_markdown)
    
    assert metadata == {}
    assert "Content without any metadata" in content

def test_no_frontmatter() -> None:
    """Test handling of content without frontmatter."""
    content = "# Document\n\nNo frontmatter here."
    metadata, remaining = parse_frontmatter(content)
    
    assert metadata == {}
    assert remaining == content

# Test content block extraction
def test_content_block_extraction(sample_markdown: str) -> None:
    """Test extraction of content blocks from markdown."""
    _, content = parse_frontmatter(sample_markdown)
    blocks = list(iter_blocks(content))
    
    assert len(blocks) == 3
    
    # Check block names
    block_names = [block.name for block in blocks]
    assert "content" in block_names
    assert "example" in block_names
    assert "sidebar" in block_names
    
    # Check block content
    content_block = next(block for block in blocks if block.name == "content")
    assert "main content" in content_block.content
    assert "List item" in content_block.content
    
    example_block = next(block for block in blocks if block.name == "example")
    assert "python" in example_block.content
    assert "hello_world" in example_block.content

def test_minimal_block_extraction(minimal_markdown: str) -> None:
    """Test handling of markdown without explicit blocks."""
    _, content = parse_frontmatter(minimal_markdown)
    blocks = list(iter_blocks(content))
    
    # Should not extract any blocks since there are no XML tags
    assert len(blocks) == 0

# Test complete parsing
def test_complete_parsing(sample_markdown: str) -> None:
    """Test the complete parsing process."""
    parsed = parse(sample_markdown)
    
    # Check metadata
    assert parsed.metadata["title"] == "Test Document"
    assert set(parsed.metadata["tags"]) == set(["test", "sample"])
    
    # Check blocks
    assert "content" in parsed.blocks
    assert "example" in parsed.blocks
    assert "sidebar" in parsed.blocks
    
    # Check accessing blocks
    content_block = parsed.get_block("content")
    assert content_block is not None
    assert "main content" in content_block.content
    
    # Check accessing by index
    sidebar_blocks = parsed.get_blocks("sidebar")
    assert len(sidebar_blocks) == 1
    assert "Additional information" in sidebar_blocks[0].content

# Test error handling
def test_malformed_frontmatter() -> None:
    """Test handling of malformed frontmatter."""
    bad_frontmatter = """---
title: Broken
author: # Missing value
---

Content
"""
    # The parser is now more lenient and will try to parse malformed frontmatter
    # without raising an exception
    metadata, content = parse_frontmatter(bad_frontmatter)
    
    # It should still extract valid keys
    assert "title" in metadata
    assert metadata["title"] == "Broken"
    
    # And the content should be preserved
    assert "Content" in content

def test_malformed_blocks() -> None:
    """Test handling of malformed XML blocks."""
    bad_blocks = """---
title: Test
---

<content>
Unclosed content block
"""
    # This should not raise an exception because the parser is now more lenient
    parsed = parse(bad_blocks)
    # No blocks should be found because the XML tag pattern requires closing tags
    assert len(parsed.blocks) == 0 

def test_line_number_tracking_in_errors():
    """Test that malformed blocks are skipped without raising errors."""
    content = """---
title: Test
---

Some content

<block>
Content in block
</block>

<malformed>
Malformed block without end tag

<nested>
<deeper>
Content in deeper block
</deeper>
</nested>

<unclosed>
This block is not properly closed
"""
    
    # This should not raise an exception because the parser is lenient
    parsed = parse(content)
    
    # Check all blocks that should be found
    assert "block" in parsed.blocks
    assert "deeper" in parsed.blocks
    
    # The malformed and unclosed blocks should be skipped
    assert "malformed" not in parsed.blocks
    assert "unclosed" not in parsed.blocks

def test_line_number_in_nested_block_errors():
    """Test handling of unclosed nested blocks."""
    content = """---
title: Test
---

<outer>
Content in outer block
<inner>
Content in inner block
# Missing end tag for inner block
</outer>
"""
    
    # This should not raise an exception because the parser is lenient
    parsed = parse(content)
    
    # The outer tag should be skipped since it has an unclosed inner tag
    assert len(parsed.blocks) == 0
    assert "outer" not in parsed.blocks
    assert "inner" not in parsed.blocks

def test_malformed_frontmatter_skipping():
    """Test that invalid YAML in frontmatter is handled gracefully."""
    content = """---
title: Test
invalid yaml: : value
---

Content
"""
    
    # This should not raise an exception with the updated parser
    metadata, content = parse_frontmatter(content)
    
    # It should still extract valid keys and ignore the invalid ones
    assert "title" in metadata
    assert "invalid yaml" not in metadata
    
    # The content should be preserved
    assert "Content" in content 

def test_line_number_tracking_in_warnings(caplog):
    """Test that the parser tracks line numbers and reports them in warnings."""
    content = """---
title: Test
---

Some content

<block>
Content in block
</block>

<malformed>
Malformed block without end tag

<nested>
<deeper>
Content in deeper block
</deeper>
</nested>

<unclosed>
This block is not properly closed
"""
    
    # Capture logs to verify warnings
    with caplog.at_level(logging.WARNING):
        parsed = parse(content)

        # Check logs for warnings about unclosed tags
        assert "Unclosed block <malformed>" in caplog.text
        assert "Unclosed block <unclosed>" in caplog.text
        assert "line 7" in caplog.text  # Actual line number for malformed
        assert "line 16" in caplog.text  # Actual line number for unclosed

    # Check that the proper blocks are found
    assert "block" in parsed.blocks
    assert "deeper" in parsed.blocks
    
    # The malformed and unclosed blocks should be skipped
    assert "malformed" not in parsed.blocks
    assert "unclosed" not in parsed.blocks

def test_nested_block_warnings(caplog):
    """Test that the parser warns about unclosed nested blocks."""
    content = """---
title: Test
---

<outer>
Content in outer block
<inner>
Content in inner block
# Missing end tag for inner block
</outer>
"""
    
    # Capture logs to verify warnings about unclosed inner tags
    with caplog.at_level(logging.WARNING):
        parsed = parse(content)

        # Check logs for warnings about unclosed inner tags
        assert "Unclosed inner tag <inner>" in caplog.text
        assert "line 2" in caplog.text  # Actual line number for inner tag (relative to block content)
        assert "block starting at line 1" in caplog.text  # Line number of outer block (relative to content after frontmatter)

    # The outer tag should be skipped because it has an unclosed inner tag
    assert "outer" not in parsed.blocks
    assert len(parsed.blocks) == 0

def test_malformed_frontmatter_handling(caplog):
    """Test that the parser properly handles malformed frontmatter with helpful warning messages."""
    content = """---
title: Test
invalid yaml: : value
---

Content
"""
    
    # Capture logs to verify warnings about malformed frontmatter
    with caplog.at_level(logging.WARNING):
        metadata, content_without_frontmatter = parse_frontmatter(content)

        # The parser should log a warning with line number information
        assert "Malformed YAML in frontmatter" in caplog.text
        assert "line 3" in caplog.text  # Line with the malformed YAML
        
        # It should extract valid keys if possible
        assert metadata.get("title") == "Test"
        
        # The content should be returned correctly
        assert "Content" in content_without_frontmatter

def test_valid_frontmatter():
    """Test handling of valid frontmatter."""
    # Valid frontmatter that should not raise exceptions
    content = """---
title: Test
author: John Doe  # This is fine
tags: [a, b, c]   # This is also fine
---

Content
"""
    
    # This should not raise an exception
    metadata, remaining = parse_frontmatter(content)
    
    # Metadata should be correctly parsed
    assert metadata["title"] == "Test"
    assert metadata["author"] == "John Doe"
    assert "tags" in metadata
    
    # Content should be preserved
    assert "Content" in remaining

def test_line_numbers_in_found_blocks():
    """Test that the parser correctly identifies line numbers for blocks."""
    from pyxie.parser import find_tag_line_number
    
    content = """---
title: Test
---

First paragraph

<block1>
Block 1 content
</block1>

<block2>
Block 2 content
</block2>
"""
    
    # Check line numbers for various blocks
    assert find_tag_line_number(content, "block1") == 7
    assert find_tag_line_number(content, "block2") == 11
    
    # Test with starting position
    assert find_tag_line_number(content, "block2", 
                               content.find("</block1>")) == 11 

def test_tags_in_code_blocks():
    """Test that XML tags inside code blocks are not treated as content blocks."""
    content = """---
title: Test Document with Code Blocks
---

Regular content with a <example>This is a real section</example> tag.

<content>
Here is some content.
</content>

```python
# This is a code block
def test_function():
    # This comment has a <sample> tag that should be ignored
    print("<example>This should also be ignored</example>")
```

And some inline code with a tag: `<inline>` that should be ignored.

Let's also verify HTML entities: &lt;tag&gt; should not be interpreted as a section.

<final>
This should be interpreted as a section block.
</final>
"""
    
    parsed = parse(content)
    
    # Check that tags in regular content are treated as section blocks
    assert "content" in parsed.blocks
    assert "example" in parsed.blocks
    assert "final" in parsed.blocks
    
    # Check the content of the example block to make sure it's the right one
    example_block = parsed.get_block("example")
    assert example_block is not None
    assert "This is a real section" in example_block.content
    
    # Check that tags in code blocks, inline code, and HTML entities are ignored
    assert "sample" not in parsed.blocks  # From the code block comment
    assert "inline" not in parsed.blocks  # From the inline code
    assert "tag" not in parsed.blocks  # From the HTML entity &lt;tag&gt; 