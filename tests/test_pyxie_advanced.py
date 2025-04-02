"""Test advanced functionality in pyxie.py."""

import pytest
import asyncio
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, patch, AsyncMock
from pyxie import Pyxie
from pyxie.types import ContentItem
from pyxie.errors import LayoutError
from pyxie.collection import Collection

@pytest.fixture
def pyxie_instance(tmp_path):
    """Create a Pyxie instance with test directories."""
    content_dir = tmp_path / "content"
    cache_dir = tmp_path / "cache"
    content_dir.mkdir()
    cache_dir.mkdir()
    
    return Pyxie(
        content_dir=content_dir,
        cache_dir=cache_dir,
        default_metadata={"test": True}
    )

@pytest.fixture
def test_collection(pyxie_instance, tmp_path):
    """Create a test collection with content."""
    collection_path = tmp_path / "test_collection"
    collection_path.mkdir()
    
    # Create test content
    (collection_path / "test1.md").write_text("""---
title: Test 1
tags: [test]
---
Content 1
""")
    
    (collection_path / "test2.md").write_text("""---
title: Test 2
tags: [test]
---
Content 2
""")
    
    pyxie_instance.add_collection("test", collection_path)
    return collection_path

def test_collection_stats_error_handling(pyxie_instance, test_collection):
    """Test error handling in collection stats calculation."""
    # Test with invalid _items
    pyxie_instance._collections["test"]._items = None
    stats = pyxie_instance.collection_stats
    assert stats["test"] == 0

def test_process_content_item_error_handling(pyxie_instance, test_collection):
    """Test error handling in content item processing."""
    # Test with None item
    initial_count = len(pyxie_instance._items)
    pyxie_instance._process_content_item(None, 0, pyxie_instance._collections["test"])
    assert len(pyxie_instance._items) == initial_count  # No items should be added

    # Test with invalid item
    invalid_item = Mock(spec=ContentItem)
    invalid_item.slug = "invalid"
    pyxie_instance._process_content_item(invalid_item, 0, pyxie_instance._collections["test"])
    assert len(pyxie_instance._items) == initial_count + 1  # Valid item should be added

def test_load_collection_error_handling(pyxie_instance, test_collection):
    """Test error handling in collection loading."""
    # Test with invalid file
    (test_collection / "invalid.md").write_text("invalid: [")
    initial_count = len(pyxie_instance._items)
    pyxie_instance._load_collection(pyxie_instance._collections["test"])
    assert len(pyxie_instance._items) == initial_count + 1  # Valid files should be loaded

def test_get_items_error_handling(pyxie_instance, test_collection):
    """Test error handling in get_items."""
    # Test with invalid collection
    items = pyxie_instance.get_items("nonexistent")
    assert len(items.items) == 0
    assert items.total == 0

    # Test with invalid filters
    items = pyxie_instance.get_items("test", invalid_filter="value")
    assert len(items.items) == 0  # Invalid filters should return empty result

def test_invalidate_cache_error_handling(pyxie_instance, test_collection):
    """Test error handling in cache invalidation."""
    # Test with IOError
    with patch.object(pyxie_instance.cache, 'invalidate', side_effect=IOError("Test error")):
        # The error should be caught and logged, not raised
        pyxie_instance.invalidate_cache()
        # Test with specific collection
        pyxie_instance.invalidate_cache(collection="content")
        # No exception should be raised

def test_get_raw_content_error_handling(pyxie_instance, test_collection):
    """Test error handling in get_raw_content."""
    # Test with nonexistent item
    content = pyxie_instance.get_raw_content("nonexistent")
    assert content is None
    
    # Test with invalid file
    with patch('pathlib.Path.read_text', side_effect=Exception("Test error")):
        content = pyxie_instance.get_raw_content("test1")
        assert content is None

@pytest.mark.asyncio
async def test_start_watching_error_handling(pyxie_instance, test_collection):
    """Test error handling in start_watching."""
    # Test without watchfiles
    with patch.dict('sys.modules', {'watchfiles': None}):
        await pyxie_instance.start_watching()
        assert pyxie_instance._watcher_task is None

@pytest.mark.asyncio
async def test_stop_watching_error_handling(pyxie_instance, test_collection):
    """Test error handling in stop_watching."""
    # Create a mock coroutine
    async def mock_coro():
        return None

    # Test with CancelledError
    mock_task = asyncio.create_task(mock_coro())
    mock_task.cancel = Mock()
    mock_task.done = Mock(return_value=False)
    pyxie_instance._watcher_task = mock_task

    await pyxie_instance.stop_watching()
    assert mock_task.cancel.called

def test_rebuild_content_error_handling(pyxie_instance, test_collection):
    """Test error handling in rebuild_content."""
    # Test with invalid file touch
    with patch('os.utime', side_effect=Exception("Test error")):
        pyxie_instance.rebuild_content()
        # Should not raise exception

    # Test with invalid collection
    invalid_collection = Collection(name="invalid", path=test_collection)
    pyxie_instance._collections["invalid"] = invalid_collection
    pyxie_instance.rebuild_content()
    # Should not raise exception

def test_serve_md_middleware(pyxie_instance, test_collection):
    """Test markdown serving middleware."""
    middleware = pyxie_instance.serve_md()
    assert middleware is not None

    # Test middleware class
    from starlette.middleware import Middleware
    assert isinstance(middleware, Middleware)

def test_pagination_edge_cases(pyxie_instance, test_collection):
    """Test pagination edge cases."""
    # Test cursor pagination
    items = pyxie_instance.get_items(
        "test",
        cursor_field="title",
        cursor_value="Test 1",
        cursor_limit=1
    )
    assert len(items.items) == 1
    
    # Test offset pagination
    items = pyxie_instance.get_items("test", offset=1, limit=1)
    assert len(items.items) == 1
    
    # Test page pagination
    items = pyxie_instance.get_items("test", page=1, per_page=1)
    assert len(items.items) == 1

def test_sorting_edge_cases(pyxie_instance, test_collection):
    """Test sorting edge cases."""
    # Test single field sorting
    items = pyxie_instance.get_items("test", order_by="title")
    assert len(items.items) == 2
    
    # Test multiple field sorting
    items = pyxie_instance.get_items("test", order_by=["title", "tags"])
    assert len(items.items) == 2
    
    # Test invalid sorting
    items = pyxie_instance.get_items("test", order_by=None)
    assert len(items.items) == 2  # Should still return items without sorting 