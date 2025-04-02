"""Test cache-related functionality in the Pyxie class."""

import pytest
from pathlib import Path
from pyxie import Pyxie
from pyxie.cache import Cache
from pyxie.types import ContentItem

@pytest.fixture
def temp_content_dir(tmp_path):
    """Create a temporary content directory."""
    content_dir = tmp_path / "content"
    content_dir.mkdir()
    return content_dir

@pytest.fixture
def temp_cache_dir(tmp_path):
    """Create a temporary cache directory."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    return cache_dir

def test_cache_initialization(temp_content_dir, temp_cache_dir):
    """Test cache initialization with various scenarios."""
    # Test with valid cache dir
    pyxie = Pyxie(temp_content_dir, cache_dir=temp_cache_dir)
    assert pyxie.cache is not None
    assert isinstance(pyxie.cache, Cache)

    # Test without cache dir
    pyxie = Pyxie(temp_content_dir)
    assert pyxie.cache is None

    # Test with non-existent cache dir (should create it)
    new_cache_dir = temp_cache_dir / "new"
    pyxie = Pyxie(temp_content_dir, cache_dir=new_cache_dir)
    assert pyxie.cache is not None
    assert new_cache_dir.exists()

def test_cache_invalidation_error_handling(temp_content_dir, temp_cache_dir, monkeypatch):
    """Test error handling during cache invalidation."""
    pyxie = Pyxie(temp_content_dir, cache_dir=temp_cache_dir)
    
    # Add a test collection
    collection_dir = temp_content_dir / "blog"
    collection_dir.mkdir()
    pyxie.add_collection("blog", collection_dir)

    # Create a test markdown file
    post = collection_dir / "test.md"
    post.write_text("""---
title: Test Post
slug: test-post
---
Test content
""")

    # Force content reload to ensure test-post is loaded
    pyxie.rebuild_content()
    
    # Test global cache invalidation with IOError
    def mock_invalidate_global(*args):
        if not args:  # Global invalidation (no args)
            raise IOError("Test error")
        return None

    monkeypatch.setattr(pyxie.cache, "invalidate", mock_invalidate_global)
    
    # Error should be caught and logged, not raised
    pyxie.invalidate_cache()  # Should not raise
    
    # Test collection cache invalidation with OSError
    def mock_invalidate_collection(*args):
        if len(args) == 1:  # Collection invalidation (one arg)
            raise OSError("Test error")
        return None

    monkeypatch.setattr(pyxie.cache, "invalidate", mock_invalidate_collection)
    
    # Error should be caught and logged, not raised
    pyxie.invalidate_cache(collection="blog")  # Should not raise
    
    # Test item cache invalidation with OSError (not ValueError)
    def mock_invalidate_item(*args):
        if len(args) >= 2:  # Item invalidation (two or more args)
            raise OSError("Test error")
        return None

    monkeypatch.setattr(pyxie.cache, "invalidate", mock_invalidate_item)
    
    # Error should be caught and logged, not raised 
    pyxie.invalidate_cache(collection="blog", slug="test-post")  # Should not raise

def test_cache_interaction_with_content_items(temp_content_dir, temp_cache_dir):
    """Test how content items interact with cache."""
    pyxie = Pyxie(temp_content_dir, cache_dir=temp_cache_dir)
    
    # Add a test collection
    collection_dir = temp_content_dir / "blog"
    collection_dir.mkdir()
    pyxie.add_collection("blog", collection_dir)

    # Create a test markdown file
    post = collection_dir / "test.md"
    post.write_text("""---
title: Test Post
slug: test
---
Test content
""")

    # Force content reload
    pyxie.rebuild_content()

    # Get items to trigger content loading
    items = pyxie.get_items("blog").items
    assert len(items) == 1
    
    # Verify item has cache reference
    item = items[0]
    assert item._cache is pyxie.cache

    # Test cache invalidation for specific item
    pyxie.invalidate_cache("blog", item.slug)
    
    # Test cache invalidation for collection
    pyxie.invalidate_cache("blog")
    
    # Test cache invalidation for all
    pyxie.invalidate_cache()

def test_collection_stats_error_handling(temp_content_dir):
    """Test error handling in collection stats calculation."""
    pyxie = Pyxie(temp_content_dir)
    
    # Add a collection but manipulate its _items to test error handling
    collection_dir = temp_content_dir / "blog"
    collection_dir.mkdir()
    pyxie.add_collection("blog", collection_dir)
    
    # Test with None _items
    pyxie._collections["blog"]._items = None
    stats = pyxie.collection_stats
    assert stats["blog"] == 0
    
    # Test with invalid _items
    pyxie._collections["blog"]._items = {}  # Empty dict instead of "invalid"
    stats = pyxie.collection_stats
    assert stats["blog"] == 0 