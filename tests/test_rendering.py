"""Tests for the renderer module."""

import pytest
from pathlib import Path
from bs4 import BeautifulSoup
from fastcore.xml import Div, H1, Article, Aside, FT
from typing import Optional, Callable, Any, List, Dict, TypeVar, Protocol
from dataclasses import dataclass

from pyxie.renderer import render_block, render_blocks, RenderError, render_content
from pyxie.parser import ContentBlock
from pyxie.layouts import layout
from pyxie.pyxie import Pyxie

T = TypeVar('T', bound=FT)

class TreePredicate(Protocol):
    """Protocol for tree predicates."""
    def __call__(self, node: Any) -> bool: ...

# Test utilities
@dataclass
class ComponentFinder:
    """Helper for finding components in FastHTML trees."""
    
    @staticmethod
    def find_first(root: FT, predicate: TreePredicate) -> Optional[FT]:
        """Find first component matching predicate in tree."""
        if predicate(root):
            return root
        
        if hasattr(root, 'children'):
            for child in root.children:
                if isinstance(child, FT):
                    if result := ComponentFinder.find_first(child, predicate):
                        return result
        return None
    
    @staticmethod
    def find_all(root: FT, predicate: TreePredicate) -> List[FT]:
        """Find all components matching predicate in tree."""
        results: List[FT] = []
        
        if predicate(root):
            results.append(root)
        
        if hasattr(root, 'children'):
            for child in root.children:
                if isinstance(child, FT):
                    results.extend(ComponentFinder.find_all(child, predicate))
        return results
    
    @staticmethod
    def is_type(obj: Any, type_name: str) -> bool:
        """Check if object is of a given type by name."""
        return obj.__class__.__name__ == type_name

    @staticmethod
    def find_element(html: str, selector: str) -> Optional[BeautifulSoup]:
        """Find an element in HTML using a CSS selector."""
        soup = BeautifulSoup(html, 'html.parser')
        return soup.select_one(selector)

# Fixtures
@pytest.fixture
def test_paths(tmp_path: Path) -> Dict[str, Path]:
    """Create test directory structure."""
    return {
        'layouts': tmp_path / "layouts",
        'content': tmp_path / "content",
        'cache': tmp_path / "cache"
    }

@pytest.fixture
def pyxie(test_paths: Dict[str, Path]) -> Pyxie:
    """Create a Pyxie instance with test paths."""
    for path in test_paths.values():
        path.mkdir(exist_ok=True)
    
    return Pyxie(
        content_dir=test_paths['content'],
        cache_dir=test_paths['cache']
    )

# Test cases
@pytest.mark.parametrize("markdown,expected_html", [
    ("# Title\nContent", ["<h1>Title</h1>", "<p>Content</p>"]),
    ("[Link](https://example.com)\n![Image](image.jpg)", 
     ['<a href="https://example.com">Link</a>', '<img src="image.jpg" alt="Image"']),
    ("```python\ndef test(): pass\n```\nInline `code`",
     ["<pre><code", "def test(): pass", "<code>code</code>"])
])
def test_markdown_rendering(markdown: str, expected_html: List[str]) -> None:
    """Test various markdown rendering cases."""
    block = ContentBlock(name="content", content=markdown, params={})
    result = render_block(block)
    for html in expected_html:
        assert html in result

def test_integration_with_layout(pyxie: Pyxie) -> None:
    """Test integration of rendered markdown with layout."""
    # Register test layout
    @layout("test")
    def test_layout(metadata=None):
        return Div(
            H1(None, data_slot="title"),
            Article(None, data_slot="content"),
            Aside(None, data_slot="sidebar"),
            cls="test-layout"
        )

    # Create test content
    content_file = pyxie.content_dir / "test.md"
    content_file.write_text("""---
layout: test
title: Test Page
status: published
---

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
""")

    # Add the content to the pyxie instance
    pyxie.add_collection("test", pyxie.content_dir)
    pyxie._load_collection(pyxie._collections["test"])
    
    # Get the content item
    item, error = pyxie.get_item("test", collection="test")
    assert error is None
    
    # Render and verify
    result = render_content(item)
    assert "test-layout" in result
    assert "Welcome" in result
    assert "Main" in result
    assert "Item 1" in result
    assert "Item 2" in result

@pytest.mark.parametrize("error_case", [
    "empty_content",
    "invalid_layout",
    "malformed_html"
])
def test_error_handling(pyxie: Pyxie, error_case: str) -> None:
    """Test various error handling cases."""
    if error_case == "empty_content":
        block = ContentBlock(name="content", content="", params={})
        try:
            render_block(block)
            assert False, "Expected RenderError but none was raised"
        except RenderError:
            # Expected error
            pass
    
    elif error_case == "invalid_layout":
        content_file = pyxie.content_dir / "test.md"
        content_file.write_text("""---
layout: nonexistent
status: published
---
# Test
""")
        pyxie.add_collection("test", pyxie.content_dir)
        pyxie._load_collection(pyxie._collections["test"])
        item, _ = pyxie.get_item("test", collection="test")
        result = render_content(item)
        assert "Error rendering content" in result
    
    elif error_case == "malformed_html":
        block = ContentBlock(name="content", content="<unclosed>test", params={})
        result = render_block(block)
        # The current implementation doesn't sanitize HTML, so the tag is preserved
        assert "<unclosed>" in result

def test_complex_nested_content() -> None:
    """Test rendering of complex nested content."""
    markdown = """# Section 1
## Subsection
- List item 1
  - Nested item
    ```python
    def test():
        return "nested"
    ```
- List item 2
"""
    block = ContentBlock(name="content", content=markdown, params={})
    result = render_block(block)
    
    # Check for content presence rather than exact HTML format
    assert "Section 1" in result
    assert "Subsection" in result
    assert "List item 1" in result
    assert "Nested item" in result
    assert "def test" in result
    
    # Check for "nested" with both straight quotes and HTML entities
    assert ("return \"nested\"" in result or "return &quot;nested&quot;" in result)
    assert "List item 2" in result 