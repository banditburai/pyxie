"""Tests for the renderer module."""

import pytest
from pathlib import Path
from bs4 import BeautifulSoup
from fastcore.xml import Div, H1, Article, Aside, FT
from typing import Optional, Callable, Any, List, Dict, TypeVar, Protocol
from dataclasses import dataclass

from pyxie.renderer import render_block, render_blocks, RenderError, render_content, process_fasthtml
from pyxie.parser import ContentBlock
from pyxie.layouts import layout, registry
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

def test_process_fasthtml() -> None:
    """Test processing of FastHTML blocks, including error handling."""
    from pyxie.renderer import process_fasthtml
    
    # Test with valid HTML content inside fasthtml tags (should be passed through)
    valid_html_content = '<p>Text</p><fasthtml><div id="test">Direct HTML content</div></fasthtml>'
    result = process_fasthtml(valid_html_content)
    assert "<p>Text</p>" in result
    assert '<div id="test">Direct HTML content</div>' in result
    
    # Test with invalid content that triggers error handling
    invalid_content = '<p>Text</p><fasthtml>invalid syntax</fasthtml>'
    result = process_fasthtml(invalid_content)
    assert "<p>Text</p>" in result
    assert "Error" in result # Should show an error message
    assert "FastHTMLExecutionError" in result # The specific error

class MockCache:
    """Mock cache for testing."""
    
    def __init__(self):
        self.cache = {}
        self.get_called = False
        self.store_called = False
    
    def get(self, collection, path, layout):
        self.get_called = True
        key = f"{collection}:{path}:{layout}"
        return self.cache.get(key)
    
    def store(self, collection, path, content, layout):
        self.store_called = True
        key = f"{collection}:{path}:{layout}"
        self.cache[key] = content

def test_render_content_with_cache() -> None:
    """Test rendering content with cache."""
    from pyxie.types import ContentItem
    from pyxie.renderer import render_content
    from pyxie.layouts import layout, registry
    from fastcore.xml import Div, H1
    
    # Register test layout using the decorator pattern
    @layout("cache-test")
    def test_layout(metadata=None):
        return Div(H1("Test Title"), cls="test-layout")
    
    # Create test item
    item = ContentItem(
        slug="test-item",
        content="# Test\nThis is a test.",
        source_path=Path("test/test-item.md"),
        metadata={"layout": "cache-test"}
    )
    
    # Create mock cache
    mock_cache = MockCache()
    
    # First render should store in cache
    result = render_content(item, mock_cache)
    assert mock_cache.store_called
    assert "test-layout" in result
    assert "<h1>Test Title</h1>" in result
    
    # Reset mock
    mock_cache.store_called = False
    
    # Second render should retrieve from cache
    second_result = render_content(item, mock_cache)
    assert not mock_cache.store_called
    assert second_result == result

def test_content_item_render_method() -> None:
    """Test the render() method on ContentItem."""
    from pyxie.types import ContentItem
    from fasthtml.common import NotStr
    from pyxie.layouts import layout
    from fastcore.xml import Div, H1
    
    # Register test layout
    @layout("render-test")
    def test_layout(metadata=None):
        return Div(H1("Rendered Title"), cls="render-test")
    
    # Create test item with layout
    item = ContentItem(
        slug="render-test-item",
        content="Test content for render method",
        source_path=Path("test/render-test-item.md"),
        metadata={"layout": "render-test"}
    )
    
    # Access the html property to trigger rendering
    html_content = item.html
    assert "<h1>Rendered Title</h1>" in html_content
    
    # Test the render method
    rendered = item.render()
    
    # Verify it returns a NotStr
    assert isinstance(rendered, NotStr)
    
    # Verify the content matches the html property
    assert str(rendered) == html_content

def test_handle_slot_filling_errors() -> None:
    """Test handling of slot filling errors."""
    from pyxie.renderer import handle_slot_filling
    from pyxie.slots import SlotFillResult
    from lxml import etree
    import io
    
    # This test needs to create situations where fill_slots returns was_filled=False
    
    # Case 1: Test with malformed component (not an FT or string)
    # This should cause an error in extract_layout_root
    html, error = handle_slot_filling(42, {"content": ["<p>Test</p>"]}, "test-slug")
    assert html is None
    assert error is not None
    assert "Failed to fill slots" in error
    
    # Case 2: Test with valid XML but slots not filled
    # Our slots system might auto-repair some types of malformed HTML,
    # so let's create a scenario where slots definitely can't be filled
    valid_xml = '<!DOCTYPE html><html><body><div data-slot="missing-slot"></div></body></html>'
    html, error = handle_slot_filling(valid_xml, {"different-slot": ["<p>Test</p>"]}, "test-slug")
    # The HTML should be returned with empty slots - it doesn't consider this an error
    assert html is not None
    assert "<p>Test</p>" not in html
    
    # Case 3: Valid case - slots are filled correctly
    valid_xml = '<!DOCTYPE html><html><body><div data-slot="content"></div></body></html>'
    html, error = handle_slot_filling(valid_xml, {"content": ["<p>Test</p>"]}, "test-slug")
    assert html is not None
    assert error is None
    assert "<p>Test</p>" in html 