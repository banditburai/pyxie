"""Test the Pyxie class functionality."""

import pytest
from pathlib import Path
import tempfile
import shutil
from pyxie.pyxie import Pyxie
from pyxie.types import ContentItem
from pyxie.constants import DEFAULT_METADATA
from pyxie.layouts import registry
from pyxie.query import Query
import asyncio

@pytest.fixture
def temp_content_dir():
    """Create a temporary directory for content files."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)

@pytest.fixture
def temp_cache_dir():
    """Create a temporary directory for cache files."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)

@pytest.fixture
def sample_content(temp_content_dir):
    """Create sample content files for testing."""
    # Create a test markdown file
    test_md = temp_content_dir / "test.md"
    test_md.write_text("""---
title: Test Post
tags: [test, sample]
---
# Test Content
This is a test post.""")

    # Create a nested directory with content
    nested_dir = temp_content_dir / "nested"
    nested_dir.mkdir()
    nested_md = nested_dir / "nested.md"
    nested_md.write_text("""---
title: Nested Post
tags: [test, nested]
---
# Nested Content
This is a nested post.""")

    return temp_content_dir

def test_pyxie_initialization():
    """Test basic Pyxie initialization."""
    pyxie = Pyxie()
    assert pyxie.content_dir is None
    assert pyxie.default_metadata == DEFAULT_METADATA
    assert pyxie.default_layout == "default"
    assert pyxie.cache is None
    assert pyxie.collections == []
    assert pyxie.item_count == 0
    assert pyxie.collection_stats == {}

def test_pyxie_with_content_dir(sample_content):
    """Test Pyxie initialization with content directory."""
    pyxie = Pyxie(content_dir=sample_content)
    assert pyxie.content_dir == sample_content
    assert "content" in pyxie.collections
    collection = pyxie._collections["content"]
    assert collection.path == sample_content
    assert pyxie.item_count == 2
    assert pyxie.collection_stats["content"] == 2

def test_pyxie_with_cache(sample_content, temp_cache_dir):
    """Test Pyxie with cache directory."""
    pyxie = Pyxie(content_dir=sample_content, cache_dir=temp_cache_dir)
    assert pyxie.cache is not None
    assert pyxie.cache.cache_dir == temp_cache_dir

def test_add_collection(temp_content_dir):
    """Test adding a collection."""
    pyxie = Pyxie()
    pyxie.add_collection("test", temp_content_dir)
    assert "test" in pyxie.collections
    assert pyxie.collection_stats["test"] == 0

def test_get_items(sample_content):
    """Test getting items from collections."""
    pyxie = Pyxie(content_dir=sample_content)
    
    # Get all items
    items = pyxie.get_items()
    assert len(items) == 2
    
    # Get items with tag filter
    items = pyxie.get_items(tags=["test"])
    assert len(items) == 2
    
    # Get items with multiple tag filter
    items = pyxie.get_items(tags=["nested"])
    assert len(items) == 1

def test_get_item(sample_content):
    """Test getting a single item by slug."""
    pyxie = Pyxie(content_dir=sample_content)
    
    # Get existing item
    item, error = pyxie.get_item("test")
    assert item is not None
    assert error is None
    assert item.title == "Test Post"
    
    # Get non-existent item
    item, error = pyxie.get_item("nonexistent")
    assert item is None
    assert error is not None

def test_get_tags(sample_content):
    """Test getting tags from collections."""
    pyxie = Pyxie(content_dir=sample_content)
    
    # Get all tags
    tags = pyxie.get_tags()
    assert len(tags) == 3
    assert tags["test"] == 2
    assert tags["sample"] == 1
    assert tags["nested"] == 1
    
    # Get tags from specific collection
    tags = pyxie.get_tags("content")
    assert len(tags) == 3

def test_get_all_tags(sample_content):
    """Test getting all unique tags."""
    pyxie = Pyxie(content_dir=sample_content)
    tags = pyxie.get_all_tags()
    assert sorted(tags) == sorted(["test", "sample", "nested"])

def test_custom_metadata(sample_content):
    """Test Pyxie with custom default metadata."""
    custom_metadata = {
        "author": "Test Author",
        "layout": "custom"
    }
    pyxie = Pyxie(
        content_dir=sample_content,
        default_metadata=custom_metadata
    )
    
    item, _ = pyxie.get_item("test")
    assert item is not None
    assert item.metadata["author"] == "Test Author"
    assert item.metadata["layout"] == "custom"

def test_collection_with_custom_metadata(temp_content_dir):
    """Test collection with custom metadata."""
    pyxie = Pyxie()
    custom_metadata = {
        "author": "Collection Author",
        "layout": "collection"
    }
    pyxie.add_collection(
        "custom",
        temp_content_dir,
        default_metadata=custom_metadata
    )
    
    assert pyxie.collections == ["custom"]
    collection = pyxie._collections["custom"]
    assert collection.default_metadata["author"] == "Collection Author"
    assert collection.default_metadata["layout"] == "collection"
    assert collection.default_metadata["collection"] == "custom"

def test_get_raw_content(sample_content):
    """Test getting raw content of an item."""
    pyxie = Pyxie(content_dir=sample_content)
    
    # Get content of existing item
    content = pyxie.get_raw_content("test")
    assert content is not None
    assert "# Test Content" in content
    
    # Get content of non-existent item
    content = pyxie.get_raw_content("nonexistent")
    assert content is None

def test_rebuild_content(sample_content):
    """Test rebuilding content."""
    pyxie = Pyxie(content_dir=sample_content)
    initial_count = pyxie.item_count
    
    # Add a new file
    new_md = sample_content / "new.md"
    new_md.write_text("""---
title: New Post
---
# New Content""")
    
    # Rebuild content
    pyxie.rebuild_content()
    assert pyxie.item_count == initial_count + 1

def test_invalidate_cache(sample_content, temp_cache_dir):
    """Test cache invalidation."""
    pyxie = Pyxie(content_dir=sample_content, cache_dir=temp_cache_dir)
    
    # Invalidate specific item
    pyxie.invalidate_cache(slug="test")
    
    # Invalidate entire collection
    pyxie.invalidate_cache(collection="content")
    
    # Invalidate all
    pyxie.invalidate_cache()

def test_collection_management(pyxie_instance, tmp_path):
    """Test collection management functionality."""
    # Test adding a new collection
    new_collection_path = tmp_path / "new_collection"
    pyxie_instance.add_collection("new_collection", new_collection_path)
    assert "new_collection" in pyxie_instance.collections
    assert pyxie_instance.collection_stats["new_collection"] == 0

    # Test adding collection with custom metadata
    custom_metadata = {"custom_field": "value"}
    pyxie_instance.add_collection(
        "custom_collection",
        tmp_path / "custom_collection",
        default_metadata=custom_metadata
    )
    items = pyxie_instance._get_collection_items("custom_collection")
    assert len(items) == 0  # Empty collection
    assert "custom_collection" in pyxie_instance.collections

def test_cache_interaction(pyxie_instance, tmp_path):
    """Test cache interaction with content items."""
    # Create a content file
    content_file = tmp_path / "content" / "test.md"
    content_file.parent.mkdir(parents=True, exist_ok=True)
    content_file.write_text("---\ntitle: Test\n---\nContent")

    # Add collection with cache
    pyxie_instance.add_collection("test_collection", tmp_path / "content")
    
    # Verify cache is attached to items
    items = pyxie_instance._get_collection_items("test_collection")
    assert len(items) == 1
    assert items[0]._cache == pyxie_instance.cache

def test_layout_discovery(pyxie_instance, tmp_path):
    """Test layout discovery and registration."""
    # Create a custom layout directory
    layout_dir = tmp_path / "layouts"
    layout_dir.mkdir(exist_ok=True)
    (layout_dir / "custom.py").write_text("""
from pyxie.layouts import Layout, layout

@layout("custom")
class CustomLayout(Layout):
    def render(self, item):
        return "Custom rendered content"
    """)

    # Initialize Pyxie with custom layout path
    pyxie_instance = Pyxie(
        content_dir=tmp_path / "content",
        layout_paths=[layout_dir],
        auto_discover_layouts=True
    )

    # Verify custom layout is registered
    assert "custom" in registry._layouts

def test_error_handling(pyxie_instance, tmp_path):
    """Test error handling in content processing."""
    # Create invalid content file
    invalid_file = tmp_path / "content" / "invalid.md"
    invalid_file.parent.mkdir(parents=True, exist_ok=True)
    invalid_file.write_text("---\ninvalid: [\n---\nContent")  # Invalid YAML with unclosed bracket

    # Create valid content file
    valid_file = tmp_path / "content" / "valid.md"
    valid_file.write_text("---\ntitle: Valid\n---\nContent")

    # Add collection and verify graceful handling
    pyxie_instance.add_collection("test_collection", tmp_path / "content")
    items = pyxie_instance._get_collection_items("test_collection")
    
    # Only the valid file should be processed
    assert len(items) == 1
    assert items[0].source_path == valid_file

def test_pagination_edge_cases(pyxie_instance, tmp_path):
    """Test edge cases in pagination methods."""
    # Create test content
    content_dir = tmp_path / "content"
    content_dir.mkdir(parents=True, exist_ok=True)
    for i in range(5):
        (content_dir / f"item_{i}.md").write_text(f"---\ntitle: Item {i}\ndate: 2024-01-{i+1}\n---\nContent")

    # Add collection
    pyxie_instance.add_collection("test_collection", content_dir)

    # Test cursor pagination with invalid cursor
    query = Query(pyxie_instance._get_collection_items("test_collection"))
    result = query.cursor("date", "invalid_date", 2).execute()
    assert len(result) == 0

    # Test offset pagination with invalid parameters
    result = query.offset(-1).limit(2).execute()
    assert len(result) == 0

def test_tag_handling_edge_cases():
    """Test edge cases in tag handling."""
    pyxie = Pyxie(content_dir="tests/fixtures/content")
    
    # Test with empty tags
    items = pyxie.get_items(tags=[])
    assert len(items) == 0
    
    # Test with invalid tag format
    items = pyxie.get_items(tags=["invalid/tag"])
    assert len(items) == 0
    
    # Test with duplicate tags
    items = pyxie.get_items(tags=["test", "test"])
    assert len(items) == len(pyxie.get_items(tags=["test"]))

def test_file_watching(tmp_path):
    """Test file watching functionality."""
    content_dir = tmp_path / "content"
    content_dir.mkdir()

    # Create a test file
    test_file = content_dir / "test.md"
    test_file.write_text("""---
title: Test Post
---
Test content
""")

    async def run_test():
        pyxie = Pyxie(content_dir, reload=True)
        
        # Test starting watcher
        await pyxie.start_watching()
        assert pyxie._watcher_task is not None
        
        # Test checking content
        await pyxie.check_content()
        
        # Test stopping watcher
        await pyxie.stop_watching()
        assert pyxie._watcher_task is None

    # Run everything in a single event loop
    asyncio.run(run_test())

def test_cache_invalidation_edge_cases(tmp_path):
    """Test cache invalidation edge cases."""
    content_dir = tmp_path / "content"
    content_dir.mkdir()
    cache_dir = tmp_path / "cache"
    
    pyxie = Pyxie(content_dir, cache_dir=cache_dir)
    
    # Test invalidating non-existent collection
    pyxie.invalidate_cache("nonexistent")
    
    # Test invalidating non-existent slug
    pyxie.invalidate_cache("content", "nonexistent")
    
    # Test invalidating with no cache
    pyxie_no_cache = Pyxie(content_dir)
    pyxie_no_cache.invalidate_cache()

def test_content_rebuilding_with_reload(tmp_path):
    """Test content rebuilding with reload enabled."""
    content_dir = tmp_path / "content"
    content_dir.mkdir()

    # Create initial content
    post = content_dir / "post.md"
    post.write_text("""---
title: Initial Post
---
Initial content
""")

    async def run_test():
        pyxie = Pyxie(content_dir, reload=True)
        assert len(pyxie._items) == 1
        
        # Modify content
        post.write_text("""---
title: Updated Post
---
Updated content
""")
        
        # Rebuild content
        pyxie.rebuild_content()
        assert len(pyxie._items) == 1
        assert next(iter(pyxie._items.values())).title == "Updated Post"

    # Run everything in a single event loop
    asyncio.run(run_test())

def test_markdown_serving_middleware(tmp_path):
    """Test markdown serving middleware."""
    content_dir = tmp_path / "content"
    content_dir.mkdir()
    
    # Create a test post
    post = content_dir / "test.md"
    post.write_text("""---
title: Test Post
---
Test content
""")
    
    pyxie = Pyxie(content_dir)
    middleware = pyxie.serve_md()
    
    # Test middleware class creation
    assert middleware.cls.__name__ == "MarkdownMiddleware"

def test_error_handling_in_content_processing(tmp_path):
    """Test error handling in content processing."""
    content_dir = tmp_path / "content"
    content_dir.mkdir()
    
    # Create an invalid markdown file with invalid YAML frontmatter
    invalid_file = content_dir / "invalid.md"
    invalid_file.write_text("""---
title: Invalid
tags: [test
---
Invalid content""")  # Invalid YAML with unclosed bracket
    
    pyxie = Pyxie(content_dir)
    assert len(pyxie._items) == 0  # Invalid file should be skipped
    
    # Test getting raw content for non-existent item
    assert pyxie.get_raw_content("nonexistent") is None
    
    # Test getting raw content for invalid file
    invalid_file.write_text("---\ntitle: Invalid\n---\n{% invalid template %}")
    pyxie = Pyxie(content_dir)
    assert pyxie.get_raw_content("invalid") is not None  # Should return raw content even if invalid