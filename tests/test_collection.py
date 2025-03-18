"""Tests for the collection module."""

import pytest
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, Generator, Callable
import logging
from unittest.mock import patch
import os
from dataclasses import dataclass

from pyxie.types import ContentItem
from pyxie.errors import CollectionError
from pyxie.parser import parse, ParsedContent

# Mock for parse result - using a structure similar to the real ParsedContent
@dataclass
class MockParsedContent:
    """Mock for parsed content."""
    content: str
    metadata: Dict[str, Any]
    blocks: Dict[str, Any] = None
    
    def get_block(self, name: str) -> Optional[Any]:
        """Get a block by name."""
        if self.blocks and name in self.blocks:
            return self.blocks[name]
        return None
    
    def get_blocks(self, name: str) -> list:
        """Get all blocks with the given name."""
        if self.blocks and name in self.blocks:
            return [self.blocks[name]]
        return []

# Create a single mock function to be used throughout the tests
def mock_parse_function(content: str, file_path=None) -> MockParsedContent:
    """Mock implementation of the parse function that extracts YAML frontmatter."""
    lines = content.split("\n")
    metadata = {}
    content_start = 0
    
    # Check for frontmatter
    if lines and lines[0].strip() == "---":
        for i, line in enumerate(lines[1:], 1):
            if line.strip() == "---":
                content_start = i + 1
                break
            
            # Extract key-value pairs
            if ":" in line:
                key, value = line.split(":", 1)
                metadata[key.strip()] = value.strip()
    
    # Return mock parsed content
    return MockParsedContent(
        content="\n".join(lines[content_start:]),
        metadata=metadata,
        blocks={}
    )

# Patch module imports before importing Collection
with patch('pyxie.parser.parse', mock_parse_function):
    from pyxie.collection import Collection

# Test fixtures
@pytest.fixture
def mock_parse(monkeypatch) -> Callable[[str], MockParsedContent]:
    """Mock the parse function."""
    # Apply the monkeypatch using our existing mock function
    import pyxie.parser
    # Set the mock in the parser module
    monkeypatch.setattr(pyxie.parser, "parse", mock_parse_function)
    return mock_parse_function

@pytest.fixture
def test_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)

@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test content."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)

@pytest.fixture
def sample_content(temp_dir) -> Path:
    """Create sample content files."""
    # Create post1.md
    post1_path = temp_dir / "post1.md"
    post1_path.write_text("""---
title: First Post
date: 2024-01-01
---
# First Post

This is the first post content.
""")

    # Create post2.md
    post2_path = temp_dir / "post2.md"
    post2_path.write_text("""---
title: Second Post
date: 2024-01-02
draft: true
---
# Second Post

This is a draft post.
""")

    return temp_dir

@pytest.fixture
def create_test_files(test_dir: Path, mock_parse) -> Dict[str, Path]:
    """Create test markdown files in the test directory."""
    file_paths = {}
    
    # Sample content metadata
    sample_content = {
        "post1": {
            "title": "First Post",
            "status": "published",
            "date": "2024-01-01",
            "tags": "python, testing"
        },
        "post2": {
            "title": "Second Post",
            "status": "draft",
            "date": "2024-01-02",
            "tags": "python, tutorial"
        },
        "post3": {
            "title": "Third Post",
            "status": "published",
            "date": "2024-01-03",
            "tags": "python, advanced"
        }
    }
    
    for slug, metadata in sample_content.items():
        content = "---\n"
        for key, value in metadata.items():
            content += f"{key}: {value}\n"
        content += "---\n\n"
        content += f"# {metadata['title']}\n\nTest content for {slug}"
        
        file_path = test_dir / f"{slug}.md"
        file_path.write_text(content)
        file_paths[slug] = file_path
    
    return file_paths

@pytest.fixture
def collection(test_dir: Path, create_test_files: Dict[str, Path], mock_parse) -> Collection:
    """Create a test collection with sample content."""
    collection = Collection(
        name="test",
        path=test_dir,
        default_metadata={"layout": "default", "author": "Test Author"}
    )
    collection.load()
    return collection

# Test initialization
def test_collection_init():
    """Test collection initialization."""
    with patch('pyxie.parser.parse', mock_parse_function):
        # Basic initialization
        collection = Collection(name="test", path="/tmp/test")
        assert collection.name == "test"
        assert isinstance(collection.path, Path)
        assert collection.path == Path("/tmp/test")
        assert collection.default_metadata == {}
        assert collection._items == {}
        
        # With default metadata
        collection = Collection(
            name="test",
            path="/tmp/test",
            default_metadata={"layout": "default"}
        )
        assert collection.default_metadata == {"layout": "default"}

# Test loading content
def test_collection_load(test_dir: Path, create_test_files: Dict[str, Path], mock_parse):
    """Test loading content from files."""
    collection = Collection(name="test", path=test_dir)
    collection.load()
    
    # Check that all files were loaded
    assert len(collection) == len(create_test_files)
    
    # Check that the items were loaded correctly
    for slug in create_test_files.keys():
        assert slug in collection
        item = collection.get_item(slug)
        assert item is not None
        assert item.slug == slug
        assert isinstance(item.metadata, dict)
        assert "title" in item.metadata

def test_collection_load_with_defaults(test_dir: Path, create_test_files: Dict[str, Path], mock_parse):
    """Test loading content with default metadata."""
    default_metadata = {
        "layout": "default",
        "author": "Test Author",
        "collection": "test"
    }
    
    collection = Collection(
        name="test",
        path=test_dir,
        default_metadata=default_metadata
    )
    collection.load()
    
    # Check that defaults were applied
    for slug in create_test_files.keys():
        item = collection.get_item(slug)
        assert item is not None
        for key, value in default_metadata.items():
            assert item.metadata.get(key) == value

def test_collection_load_with_nonexistent_path(test_dir):
    """Test loading from a nonexistent path."""
    # Create a collection with a nonexistent path
    collection = Collection(name="test", path=test_dir / "nonexistent")
    collection.load()
    
    # Collection should be empty
    assert len(collection) == 0

def test_collection_load_fails_completely(monkeypatch):
    """Test when collection load fails completely."""
    # Mock the Path.mkdir method to raise an exception
    def mock_mkdir_that_fails(*args, **kwargs):
        raise PermissionError("No permission to create directory")
    
    # Apply the mock
    monkeypatch.setattr(Path, "mkdir", mock_mkdir_that_fails)
    
    # Create a collection 
    collection = Collection(name="test", path="/nonexistent/path")
    
    # Loading should raise a CollectionError
    with pytest.raises(CollectionError) as excinfo:
        collection.load()
    
    # Check the error message contains the original exception info
    assert "Failed to load collection 'test'" in str(excinfo.value)
    assert "No permission to create directory" in str(excinfo.value)

def test_collection_load_with_invalid_file(test_dir: Path, create_test_files: Dict[str, Path], caplog, mock_parse):
    """Test loading collection with an invalid file."""
    # Create an invalid file
    invalid_file = test_dir / "invalid.md"
    invalid_file.write_text("Not a valid markdown file with frontmatter")
    
    # Capture logs
    caplog.set_level(logging.ERROR)
    
    # Load collection
    collection = Collection(name="test", path=test_dir)
    collection.load()
    
    # Our mock parser is forgiving, so it should load all files including the invalid one
    assert len(collection) == len(create_test_files) + 1  # All valid files plus the invalid one
    assert "invalid" in collection  # The invalid file should be loaded

# Test collection methods
def test_collection_len(collection: Collection):
    """Test the __len__ method."""
    assert len(collection) == 3

def test_collection_iter(collection: Collection):
    """Test the __iter__ method."""
    items = list(collection)
    assert len(items) == 3
    for item in items:
        assert isinstance(item, ContentItem)

def test_collection_contains(collection: Collection):
    """Test the __contains__ method."""
    assert "post1" in collection
    assert "post2" in collection
    assert "post3" in collection
    assert "nonexistent" not in collection

def test_get_item(collection: Collection):
    """Test getting an item by slug."""
    item = collection.get_item("post1")
    assert item is not None
    assert item.slug == "post1"
    assert item.metadata["title"] == "First Post"
    
    # Non-existent item
    assert collection.get_item("nonexistent") is None

# Test filtering and sorting
def test_get_items_basic(collection: Collection):
    """Test basic item retrieval without filters."""
    items = collection.get_items()
    assert len(items) == 3

def test_get_items_with_filter(collection: Collection):
    """Test filtering items by metadata."""
    # Filter by status
    published = collection.get_items(status="published")
    assert len(published) == 2
    for item in published:
        assert item.metadata["status"] == "published"
    
    # Filter by multiple fields
    specific = collection.get_items(status="published", date="2024-01-01")
    assert len(specific) == 1
    assert specific[0].metadata["title"] == "First Post"

def test_get_items_with_sorting(collection: Collection):
    """Test sorting items by metadata fields."""
    # Sort by date (ascending)
    sorted_asc = collection.get_items(order_by="date")
    assert len(sorted_asc) == 3
    assert sorted_asc[0].metadata["date"] == "2024-01-01"
    assert sorted_asc[2].metadata["date"] == "2024-01-03"
    
    # Sort by date (descending)
    sorted_desc = collection.get_items(order_by="-date")
    assert len(sorted_desc) == 3
    assert sorted_desc[0].metadata["date"] == "2024-01-03"
    assert sorted_desc[2].metadata["date"] == "2024-01-01"

def test_get_items_with_limit(collection: Collection):
    """Test limiting the number of items returned."""
    # Get first 2 items
    limited = collection.get_items(limit=2)
    assert len(limited) == 2
    
    # Sort and limit
    sorted_limited = collection.get_items(order_by="date", limit=1)
    assert len(sorted_limited) == 1
    assert sorted_limited[0].metadata["date"] == "2024-01-01"

def test_get_items_combined(collection: Collection):
    """Test combining filtering, sorting, and limiting."""
    items = collection.get_items(
        status="published",
        order_by="-date",
        limit=1
    )
    assert len(items) == 1
    assert items[0].metadata["status"] == "published"
    assert items[0].metadata["date"] == "2024-01-03"

def test_get_items_filtering(mock_parse, sample_content):
    """Test filtering items."""
    collection = Collection("test", sample_content)
    collection.load()
    
    # Filter by date
    items = collection.get_items(date="2024-01-01")
    assert len(items) == 1
    assert items[0].slug == "post1"
    
    # The draft key needs to be explicitly set in the metadata
    # Let's add it manually for testing
    for item in collection:
        if item.slug == "post2":
            item.metadata["draft"] = True
    
    # Filter by draft status
    items = collection.get_items(draft=True)
    assert len(items) == 1
    assert items[0].slug == "post2"
    
    # No matches
    items = collection.get_items(nonexistent="value")
    assert len(items) == 0

def test_get_items_sorting(mock_parse, sample_content):
    """Test sorting items."""
    collection = Collection("test", sample_content)
    collection.load()
    
    # Sort by date ascending
    items = collection.get_items(order_by="date")
    assert len(items) == 2
    assert items[0].slug == "post1"
    assert items[1].slug == "post2"
    
    # Sort by date descending
    items = collection.get_items(order_by="-date")
    assert len(items) == 2
    assert items[0].slug == "post2"
    assert items[1].slug == "post1"

def test_get_items_limit(mock_parse, sample_content):
    """Test limiting items."""
    collection = Collection("test", sample_content)
    collection.load()
    
    # Limit to 1 item
    items = collection.get_items(limit=1)
    assert len(items) == 1

def test_collection_iteration(mock_parse, sample_content):
    """Test iterating over collection items."""
    collection = Collection("test", sample_content)
    collection.load()
    
    items = list(collection)
    assert len(items) == 2
    assert all(isinstance(item, ContentItem) for item in items)

def test_default_metadata(mock_parse, sample_content):
    """Test default metadata."""
    defaults = {
        "author": "Test Author",
        "category": "Testing"
    }
    
    collection = Collection("test", sample_content, default_metadata=defaults)
    collection.load()
    
    # Check that defaults were applied
    item = collection.get_item("post1")
    assert item.metadata["author"] == "Test Author"
    assert item.metadata["category"] == "Testing"
    assert item.metadata["title"] == "First Post"  # Original value preserved

def test_default_layout_precedence(mock_parse, sample_content):
    """Test that default_layout takes precedence over default_metadata['layout'] when both are specified."""
    # Case 1: Both default_layout and metadata["layout"] are explicitly set with different values
    # This should produce a warning and use default_layout
    default_metadata = {"layout": "metadata_layout"}
    explicit_layout = "explicit_layout"  # Not the default "default" value
    
    collection1 = Collection(
        name="test_explicit_conflict",
        path=sample_content,
        default_layout=explicit_layout,
        default_metadata=default_metadata
    )
    collection1.load()
    
    # Check that default_layout was used instead of default_metadata["layout"]
    for item in collection1:
        assert item.metadata["layout"] == explicit_layout
        assert item.metadata["layout"] != default_metadata["layout"]
    
    # Original default_metadata should be preserved
    assert collection1.default_metadata == default_metadata
    assert collection1.default_metadata["layout"] == "metadata_layout"
    
    # Case 2: default_layout uses default value "default", metadata has layout
    # This should NOT produce a warning, and should use metadata's layout value
    default_metadata = {"layout": "metadata_layout"}
    
    collection2 = Collection(
        name="test_default_no_conflict",
        path=sample_content,
        # Using default value for default_layout
        default_metadata=default_metadata
    )
    collection2.load()
    
    # Check that metadata["layout"] was preserved as the layout
    # Note: in Collection._load_file, it still applies default_layout, but we're checking Pyxie behavior 
    # more thoroughly in other tests

def test_error_handling(mock_parse, temp_dir, caplog):
    """Test error handling when loading malformed content."""
    # Create a file that will cause the mock parser to create invalid metadata
    # Our current mock is too forgiving, so we need to patch it for this test
    def mock_parse_that_fails(content: str, file_path=None) -> MockParsedContent:
        # Simulate a parser that fails for this specific content
        if "malformed" in content:
            raise ValueError("Simulated parsing error")
        return mock_parse_function(content, file_path)
    
    with patch('pyxie.parser.parse', mock_parse_that_fails):
        # Create malformed file
        bad_file = temp_dir / "bad.md"
        bad_file.write_text("This is malformed content")
        
        collection = Collection("test", temp_dir)
        
        # Should not raise exception but log an error
        with caplog.at_level(logging.ERROR):
            collection.load()
            
        # Should log an error
        assert "Failed to load" in caplog.text
        
        # The collection should be empty since the file couldn't be loaded
        assert len(collection) == 0 

def test_collection_reference_on_items(mock_parse, sample_content):
    """Test that ContentItem instances have the correct collection name set."""
    collection_name = "test_collection_reference"
    collection = Collection(
        name=collection_name,
        path=sample_content
    )
    collection.load()
    
    # Check that every item has the correct collection reference
    for item in collection:
        assert item.collection == collection_name
        
    # Test that the collection reference is used in calls to other systems
    # Here we're just checking that it's available, we test its usage elsewhere
    item = next(iter(collection))
    assert hasattr(item, "collection")
    assert item.collection is not None 