"""Tests for the cache module."""

import pytest

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

def test_cache_connection_error(tmp_path):
    """Test handling of database connection errors."""
    cache_dir = tmp_path / "cache"
    cache = Cache(cache_dir)
    
    # Make the database read-only to force errors
    (cache_dir / "cache.db").chmod(0o444)
    
    # Test store failure
    result = cache.store("test", tmp_path / "test.md", "<p>test</p>", "default")
    assert not result
    
    # Test get failure
    result = cache.get("test", tmp_path / "test.md", "default")
    assert result is None
    
    # Test invalidate failure
    result = cache.invalidate("test")
    assert not result

def test_cache_hash_failure(tmp_path):
    """Test handling of file hash failures."""
    cache = Cache(tmp_path)
    
    # Test with non-existent file
    result = cache.store("test", tmp_path / "nonexistent.md", "<p>test</p>", "default")
    assert not result
    
    result = cache.get("test", tmp_path / "nonexistent.md", "default")
    assert result is None

def test_cache_template_invalidation(tmp_path):
    """Test cache invalidation when template changes."""
    cache = Cache(tmp_path)
    test_file = tmp_path / "test.md"
    test_file.write_text("test content")
    
    # Store with initial template
    cache.store("test", test_file, "<p>test</p>", "template1")
    
    # Get with different template should return None
    result = cache.get("test", test_file, "template2")
    assert result is None

def test_cache_source_invalidation(tmp_path):
    """Test cache invalidation when source changes."""
    cache = Cache(tmp_path)
    test_file = tmp_path / "test.md"
    test_file.write_text("initial content")
    
    # Store initial content
    cache.store("test", test_file, "<p>initial</p>", "default")
    
    # Change file content
    test_file.write_text("modified content")
    
    # Get should return None due to hash mismatch
    result = cache.get("test", test_file, "default")
    assert result is None

def test_cache_selective_invalidation(tmp_path):
    """Test selective cache invalidation."""
    cache = Cache(tmp_path)
    file1 = tmp_path / "test1.md"
    file2 = tmp_path / "test2.md"
    file1.write_text("test1")
    file2.write_text("test2")
    
    # Store both files
    cache.store("test", file1, "<p>test1</p>", "default")
    cache.store("test", file2, "<p>test2</p>", "default")
    
    # Invalidate only file1
    cache.invalidate("test", file1)
    
    # file1 should be invalidated but file2 should still be cached
    assert cache.get("test", file1, "default") is None
    assert cache.get("test", file2, "default") is not None 