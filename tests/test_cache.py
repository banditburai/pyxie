"""Tests for the cache module."""

import pytest
from pathlib import Path
from typing import Dict, Any

from pyxie.cache import Cache

@pytest.fixture
def cache_dir(tmp_path):
    """Create a temporary cache directory."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    return cache_dir

@pytest.fixture
def test_file(tmp_path):
    """Create a test file with content."""
    test_file = tmp_path / "test.md"
    test_file.write_text("# Test\nContent")
    return test_file

@pytest.fixture
def test_layout(tmp_path):
    """Create a test layout file."""
    layout_file = tmp_path / "layout.py"
    layout_file.write_text("def layout(): pass")
    return layout_file

@pytest.fixture
def cache(cache_dir):
    """Create a cache instance."""
    return Cache(cache_dir)

def test_cache_initialization(tmp_path):
    """Test cache initialization."""
    # Test with explicit directory
    cache = Cache(tmp_path / "cache")
    assert cache.db_path.exists()
    assert cache.db_path.parent == tmp_path / "cache"

def test_cache_storage_and_retrieval(cache, test_file):
    """Test storing and retrieving from cache."""
    # Store entry
    collection = "test"
    template_name = "default"
    html = "<div>test</div>"
    
    assert cache.store(collection, test_file, html, template_name)
    
    # Get entry
    cached_html = cache.get(collection, test_file, template_name)
    assert cached_html == html

def test_invalidation(cache, test_file):
    """Test cache invalidation."""
    # Store some entries
    collection1 = "test1"
    collection2 = "test2"
    template_name = "default"
    
    cache.store(collection1, test_file, "<div>1</div>", template_name)
    cache.store(collection2, test_file, "<div>2</div>", template_name)
    
    # Invalidate specific entry
    assert cache.invalidate(collection1, test_file)
    assert cache.get(collection1, test_file, template_name) is None
    assert cache.get(collection2, test_file, template_name) is not None
    
    # Invalidate by collection
    assert cache.invalidate(collection2)
    assert cache.get(collection2, test_file, template_name) is None
    
    # Invalidate all
    cache.store("test3", test_file, "<div>3</div>", template_name)
    assert cache.invalidate()
    assert cache.get("test3", test_file, template_name) is None 