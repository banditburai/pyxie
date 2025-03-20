"""Tests for content rebuilding functionality."""

from pyxie import Pyxie

def test_rebuild_content(tmp_path):
    """Test that content rebuilding works correctly."""
    # Create test content
    content_dir = tmp_path / "content"
    content_dir.mkdir()
    (content_dir / "test.md").write_text("Test content")
    
    # Initialize Pyxie
    pyxie = Pyxie(content_dir=content_dir)
    
    # Initial content check
    assert len(pyxie.get_items().items) == 1
    
    # Add new content
    (content_dir / "new.md").write_text("New content")
    
    # Rebuild content
    pyxie.rebuild_content()
    
    # Check content was rebuilt
    items = pyxie.get_items().items
    assert len(items) == 2
    
    # Verify content
    content = {item.slug: item.content for item in items}
    assert content["test"] == "Test content"
    assert content["new"] == "New content"

def test_rebuild_content_with_cache(tmp_path):
    """Test content rebuilding with cache enabled."""
    # Create test content
    content_dir = tmp_path / "content"
    content_dir.mkdir()
    (content_dir / "test.md").write_text("Test content")
    
    # Initialize Pyxie with cache
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    pyxie = Pyxie(content_dir=content_dir, cache_dir=cache_dir)
    
    # Initial content check
    assert len(pyxie.get_items().items) == 1
    
    # Add new content
    (content_dir / "new.md").write_text("New content")
    
    # Rebuild content
    pyxie.rebuild_content()
    
    # Check content was rebuilt and cache was invalidated
    items = pyxie.get_items().items
    assert len(items) == 2
    
    # Verify content
    content = {item.slug: item.content for item in items}
    assert content["test"] == "Test content"
    assert content["new"] == "New content" 