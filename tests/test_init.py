"""Test the functionality in __init__.py."""

import pytest
from pathlib import Path
from pyxie.types import ContentItem
from pyxie.renderer import render_content
from fasthtml.common import NotStr
from pyxie.layouts import LayoutRegistry, layout
from pyxie.__init__ import _get_html

@pytest.fixture
def default_layout():
    """Create a default layout."""
    @layout("default")
    def _default_layout(content=None, **kwargs):
        return f'<div data-slot="content">{content or ""}</div>'
    return _default_layout

@pytest.fixture
def test_layout():
    """Create a test layout."""
    @layout("test")
    def _test_layout(content=None, **kwargs):
        return f'<div data-slot="content">{content or ""}</div>'
    return _test_layout

def test_content_item_html_property(tmp_path, test_layout, default_layout):
    """Test the html property of ContentItem."""
    # Create a test content item
    source_path = tmp_path / "test.md"
    content = ContentItem(
        source_path=source_path,
        metadata={"title": "Test"},  # No layout specified
        content='<div data-slot="content">Test content</div>'
    )
    
    # Test that html property returns rendered content
    html = content.html
    assert isinstance(html, str)
    assert "Test content" in html
    
    # Test error handling
    content.metadata["layout"] = "nonexistent"
    html = content.html
    assert "ERROR: LAYOUT LOADING: Layout 'nonexistent' not found" in html

def test_content_item_render_method(tmp_path, test_layout, default_layout):
    """Test the render method of ContentItem."""
    # Create a test content item
    source_path = tmp_path / "test.md"
    content = ContentItem(
        source_path=source_path,
        metadata={"title": "Test"},  # No layout specified
        content='<div data-slot="content">Test content</div>'
    )
    
    # Test that render returns NotStr when html is available
    result = content.render()
    assert isinstance(result, NotStr)
    assert "Test content" in str(result)
    
    # Test that render returns None when html is not available
    delattr(ContentItem, 'html')  # Remove html property from class
    result = content.render()
    assert result is None
    
    # Restore html property for subsequent tests
    ContentItem.html = property(_get_html)  # This will regenerate the html property

def test_content_item_html_property_error_handling(tmp_path, test_layout, default_layout):
    """Test error handling in the html property when render_content raises an exception."""
    # Create a test content item with invalid content that will cause render_content to fail
    source_path = tmp_path / "test.md"
    content = ContentItem(
        source_path=source_path,
        metadata={"title": "Test"},
        content='<div data-slot="content">Test content</div>'
    )
    
    # Mock render_content to raise an exception
    def mock_render_content(*args, **kwargs):
        raise Exception("Test error")
    
    # Temporarily replace render_content in both modules
    original_render_content = render_content
    try:
        import pyxie.__init__ as pyxie_init
        import pyxie.renderer as renderer
        
        # Replace render_content in both modules
        pyxie_init.render_content = mock_render_content
        renderer.render_content = mock_render_content
        
        # Test that html property returns error message when render_content fails
        html = content.html
        assert isinstance(html, str)
        assert "Error: Test error" in html
    finally:
        # Restore original render_content in both modules
        pyxie_init.render_content = original_render_content
        renderer.render_content = original_render_content 