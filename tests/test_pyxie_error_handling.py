"""Test error handling in the Pyxie class."""

import pytest
from pathlib import Path
from pyxie import Pyxie
from pyxie.types import ContentItem
from pyxie.errors import PyxieError

def test_init_error_handling(tmp_path):
    """Test error handling in __init__ when event loop is not running."""
    # Create a Pyxie instance with reload=True but no running event loop
    pyxie = Pyxie(
        content_dir=tmp_path,
        reload=True
    )
    assert pyxie.reload is True  # Should still set reload flag even if watcher can't start
    assert pyxie._watcher_task is None  # Watcher task should not be created when no event loop is running

def test_process_content_item_error_handling(tmp_path):
    """Test error handling in _process_content_item."""
    pyxie = Pyxie(content_dir=tmp_path)
    
    # Test with None item
    pyxie._process_content_item(None, 0, pyxie._collections["content"])
    assert len(pyxie._items) == 0  # Should not add None items

def test_collection_stats_error_handling(tmp_path):
    """Test error handling in collection_stats."""
    pyxie = Pyxie(content_dir=tmp_path)
    
    # Create a collection that will raise an error when accessing items
    class ErrorCollection:
        def __init__(self):
            self._items = None  # This will raise AttributeError when len() is called
            
    pyxie._collections["error"] = ErrorCollection()
    
    # Should handle the error and return stats for valid collections
    stats = pyxie.collection_stats
    assert "error" in stats
    assert stats["error"] == 0  # Should return 0 for collections with no items

def test_get_raw_content_error_handling(tmp_path):
    """Test error handling in get_raw_content."""
    pyxie = Pyxie(content_dir=tmp_path)
    
    # Test with nonexistent slug
    content = pyxie.get_raw_content("nonexistent")
    assert content is None

def test_load_collection_error_handling(tmp_path):
    """Test error handling in _load_collection."""
    pyxie = Pyxie(content_dir=tmp_path)
    
    # Create an invalid markdown file
    invalid_md = tmp_path / "invalid.md"
    invalid_md.write_text("---\ninvalid yaml:\n---\nInvalid content")
    
    # Should load the file with default metadata
    pyxie._load_collection(pyxie._collections["content"])
    assert len(pyxie._items) == 1
    assert "invalid" in pyxie._items
    assert pyxie._items["invalid"].metadata["title"] == "Invalid"
    assert pyxie._items["invalid"].metadata["collection"] == "content"

def test_get_items_error_handling(tmp_path):
    """Test error handling in get_items."""
    pyxie = Pyxie(content_dir=tmp_path)
    
    # Test with nonexistent collection
    result = pyxie.get_items(collection="nonexistent")
    assert len(result) == 0

def test_invalidate_cache_error_handling(tmp_path):
    """Test error handling in invalidate_cache."""
    pyxie = Pyxie(
        content_dir=tmp_path,
        cache_dir=tmp_path / "cache"
    )
    
    # Test with nonexistent collection
    pyxie.invalidate_cache(collection="nonexistent")
    
    # Test with nonexistent slug
    pyxie.invalidate_cache(slug="nonexistent")
    
    # Test with both nonexistent collection and slug
    pyxie.invalidate_cache(collection="nonexistent", slug="nonexistent")
    
    # Test with valid collection but nonexistent slug
    pyxie.invalidate_cache(collection="content", slug="nonexistent") 