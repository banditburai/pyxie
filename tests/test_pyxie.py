"""Test Pyxie class functionality."""

import pytest
from pathlib import Path
from typing import Dict
from dataclasses import dataclass

from pyxie.pyxie import Pyxie
from pyxie.layouts import registry
from pyxie.types import ContentItem

@dataclass
class ContentHelper:
    """Helper for creating test content."""
    content: str
    template: str = "test"
    metadata: Dict[str, str] = None

# Test utilities
def create_test_post(test_dir: Path, name: str, content: str) -> Path:
    """Create a test post file."""
    post_dir = test_dir / "content"
    post_dir.mkdir(exist_ok=True)
    post_file = post_dir / f"{name}.md"
    post_file.write_text(content)
    return post_file

@dataclass
class ContentFixture:
    """Helper for creating test content."""
    content: str
    template: str = "test"
    metadata: Dict[str, str] = None
    
    def write_to(self, path: Path) -> None:
        """Write content to a file."""
        content = "---\n"
        content += f"layout: {self.template}\n"
        if self.metadata:
            for key, value in self.metadata.items():
                content += f"{key}: {value}\n"
        content += "status: published\n"  # Add status for filtering
        content += "---\n"
        content += self.content
        path.write_text(content)

# Fixtures
@pytest.fixture
def test_paths(tmp_path):
    """Create test directory structure."""
    content_dir = tmp_path / "content"
    cache_dir = tmp_path / "cache"
    content_dir.mkdir()
    cache_dir.mkdir()
    return {
        "app_root": tmp_path,
        "content": content_dir,
        "cache": cache_dir
    }

@pytest.fixture
def pyxie(test_paths):
    """Create a Pyxie instance for testing."""
    return Pyxie(
        content_dir=test_paths["content"],
        cache_dir=test_paths["cache"]
    )

@pytest.fixture
def test_content():
    """Create test content."""
    return ContentHelper(
        content="Test content",
        metadata={"title": "Test"}
    )

# Test cases
def test_initialization(pyxie: Pyxie) -> None:
    """Test Pyxie initialization."""
    assert pyxie.content_dir is not None
    assert pyxie.cache is not None
    assert pyxie.default_metadata is not None
    assert pyxie.default_layout is not None

def test_add_collection(pyxie: Pyxie) -> None:
    """Test adding content collections."""
    # Add test collection
    pyxie.add_collection(
        name="test",
        path=pyxie.content_dir / "test",
        default_layout="default"
    )
    
    assert "test" in pyxie._collections
    assert pyxie._collections["test"].name == "test"
    assert pyxie._collections["test"].default_layout == "default"

def test_content_loading(pyxie: Pyxie) -> None:
    """Test loading content from collections."""
    # Create test collection
    test_dir = pyxie.content_dir / "test"
    test_dir.mkdir()
    
    # Add test content
    test_content = ContentFixture(
        content="# Test Content",
        metadata={"title": "Test Page"}
    )
    test_content.write_to(test_dir / "test.md")
    
    # Add collection and verify content
    pyxie.add_collection("test", test_dir)
    item, error = pyxie.get_item("test", collection="test")
    assert error is None
    assert item is not None
    assert item.metadata["title"] == "Test Page"

def test_error_handling(pyxie: Pyxie, monkeypatch) -> None:
    """Test error handling during content loading."""
    # Create a collection with invalid content
    test_dir = pyxie.content_dir / "error_test"
    test_dir.mkdir()
    
    # Create invalid markdown file
    invalid_file = test_dir / "invalid.md"
    invalid_file.write_text("---\nbroken yaml\n: :\n---\nContent")
    
    # This should log an error but not raise an exception
    pyxie.add_collection("error_test", test_dir)
    
    # Test nonexistent collection
    items = pyxie.get_items(collection="nonexistent")
    assert len(items) == 0

def test_collection_metadata(pyxie: Pyxie) -> None:
    """Test collection metadata handling."""
    # Add collection with metadata
    metadata = {"author": "Test Author", "category": "test"}
    pyxie.add_collection(
        name="test",
        path=pyxie.content_dir / "test",
        default_metadata=metadata
    )
    
    assert "author" in pyxie._collections["test"].default_metadata
    assert pyxie._collections["test"].default_metadata["author"] == "Test Author"

@pytest.mark.parametrize("has_cache", [True, False])
def test_query_items(pyxie: Pyxie, has_cache: bool, test_paths: Dict[str, Path]) -> None:
    """Test querying content items."""
    # Create test instance with or without cache
    if not has_cache:
        pyxie = Pyxie(content_dir=test_paths['content'])
    
    # Create test directory
    test_dir = pyxie.content_dir / "test"
    test_dir.mkdir()
    
    # Add test content with different tags
    for i in range(5):
        content = ContentFixture(
            content=f"# Test Content {i}",
            metadata={
                "title": f"Test Page {i}",
                "tags": f"tag{i}, common"
            }
        )
        content.write_to(test_dir / f"test{i}.md")
    
    # Add collection
    pyxie.add_collection("test", test_dir)
    
    # Test basic query
    all_items = pyxie.get_items()
    assert len(all_items) == 5
    
    # Test filtering
    filtered = pyxie.get_items(tags__contains=["tag1"])
    assert len(filtered) == 1
    
    common = pyxie.get_items(tags__contains=["common"])
    assert len(common) == 5

def test_initialization_with_auto_discover(test_paths: Dict[str, Path]) -> None:
    """Test initialization with auto_discover_layouts parameter."""
    # Create a test layout file
    layouts_dir = test_paths['content'].parent / "layouts"
    layouts_dir.mkdir(exist_ok=True)
    
    # Create a layout file
    layout_file = layouts_dir / "test_layout.py"
    layout_content = """
from pyxie.layouts import layout
from fastcore.xml import Div, H1, FT

@layout("auto_test_layout")
def auto_test_layout(title="Auto Test") -> FT:
    return Div(H1(title), cls="auto-test")
"""
    layout_file.write_text(layout_content)
    
    # Save current registry state
    saved_layouts = registry._layouts.copy()
    
    try:
        # Clear registry
        registry._layouts.clear()
        
        # Test with auto-discovery enabled (default)
        Pyxie(
            content_dir=test_paths['content'],
            cache_dir=test_paths['cache']
        )
        
        assert "auto_test_layout" in registry._layouts
        
        # Clear registry again
        registry._layouts.clear()
        
        # Test with auto-discovery disabled
        Pyxie(
            content_dir=test_paths['content'],
            cache_dir=test_paths['cache'],
            auto_discover_layouts=False
        )
        
        assert "auto_test_layout" not in registry._layouts
        
    finally:
        # Restore registry
        registry._layouts.clear()
        registry._layouts.update(saved_layouts)

def test_initialization_with_layout_paths(test_paths: Dict[str, Path]) -> None:
    """Test initialization with custom layout_paths parameter."""
    # Create a custom layout directory
    custom_dir = test_paths['content'].parent / "custom_layouts"
    custom_dir.mkdir(exist_ok=True)
    
    # Create a layout file in the custom directory
    layout_file = custom_dir / "custom_layout.py"
    layout_content = """
from pyxie.layouts import layout
from fastcore.xml import Div, H1, FT

@layout("custom_path_layout")
def custom_path_layout(title="Custom Path") -> FT:
    return Div(H1(title), cls="custom-path")
"""
    layout_file.write_text(layout_content)
    
    # Save current registry state
    saved_layouts = registry._layouts.copy()
    
    try:
        # Clear registry
        registry._layouts.clear()
        
        # Test with custom layout path
        Pyxie(
            content_dir=test_paths['content'],
            cache_dir=test_paths['cache'],
            layout_paths=[custom_dir]
        )
        
        assert "custom_path_layout" in registry._layouts
        
    finally:
        # Restore registry
        registry._layouts.clear()
        registry._layouts.update(saved_layouts)

def test_custom_slug_support(pyxie: Pyxie) -> None:
    """Test support for custom slugs in frontmatter."""
    # Create test collection
    test_dir = pyxie.content_dir / "slug_test"
    test_dir.mkdir()
    
    # Add file with default slug (from filename)
    default_content = ContentFixture(
        content="# Default Slug Test",
        metadata={"title": "Default Slug Post"}
    )
    default_content.write_to(test_dir / "default-slug.md")
    
    # Add file with custom slug in frontmatter
    custom_content = ContentFixture(
        content="# Custom Slug Test",
        metadata={"title": "Custom Slug Post", "slug": "custom-url-path"}
    )
    custom_content.write_to(test_dir / "filename-ignored.md")
    
    # Add collection and verify content
    pyxie.add_collection("slug_test", test_dir)
    
    # Test default slug behavior (from filename)
    default_item, _ = pyxie.get_item("default-slug", collection="slug_test")
    assert default_item is not None
    assert default_item.slug == "default-slug"
    assert default_item.metadata["title"] == "Default Slug Post"
    
    # Test custom slug behavior (from frontmatter)
    custom_item, _ = pyxie.get_item("custom-url-path", collection="slug_test")
    assert custom_item is not None
    assert custom_item.slug == "custom-url-path"
    assert custom_item.metadata["title"] == "Custom Slug Post"
    
    # Original filename should not be accessible
    nonexistent_item, error = pyxie.get_item("filename-ignored", collection="slug_test")
    assert nonexistent_item is None
    assert error is not None

def test_default_layout_from_metadata(test_paths: Dict[str, Path]) -> None:
    """Test that Pyxie correctly uses layout from default_metadata when default_layout is not explicitly set."""
    # Test when layout is in default_metadata and default_layout is left as default
    metadata_with_layout = {"layout": "metadata_layout", "other_key": "value"}
    
    pyxie1 = Pyxie(
        content_dir=test_paths['content'],
        cache_dir=test_paths['cache'],
        default_metadata=metadata_with_layout
    )
    
    # Pyxie should use the layout specified in metadata
    assert pyxie1.default_layout == "metadata_layout"
    
    # Test when both are set with different values - should warn and use default_layout
    pyxie2 = Pyxie(
        content_dir=test_paths['content'],
        cache_dir=test_paths['cache'],
        default_layout="explicit_layout",
        default_metadata=metadata_with_layout
    )
    
    # Should use the explicit default_layout
    assert pyxie2.default_layout == "explicit_layout"
    
    # Test when both are the same - no warning needed
    metadata_with_matching_layout = {"layout": "same_layout", "other_key": "value"}
    
    pyxie3 = Pyxie(
        content_dir=test_paths['content'],
        cache_dir=test_paths['cache'],
        default_layout="same_layout",
        default_metadata=metadata_with_matching_layout
    )
    
    # Should use the common layout value
    assert pyxie3.default_layout == "same_layout"

@pytest.mark.asyncio
async def test_watcher_initialization(test_paths: Dict[str, Path], monkeypatch) -> None:
    """Test watcher initialization without watchfiles installed."""
    # Mock watchfiles import to fail
    def mock_import(*args):
        raise ImportError("watchfiles not installed")
    monkeypatch.setattr("builtins.__import__", mock_import)
    
    # Create a Pyxie instance with reload=True but without watchfiles
    pyxie = Pyxie(
        content_dir=test_paths["content"],
        cache_dir=test_paths["cache"],
        reload=True
    )
    
    # Watcher should not be active since watchfiles is not installed
    assert pyxie._watcher_task is None

@pytest.mark.asyncio
async def test_watcher_functionality(test_paths: Dict[str, Path], monkeypatch) -> None:
    """Test watcher functionality with mocked watchfiles."""
    import asyncio
    from unittest.mock import MagicMock

    # Create a mock async iterator
    class MockAsyncIterator:
        def __init__(self):
            self.called = False

        def __aiter__(self):
            return self

        async def __anext__(self):
            if not self.called:
                self.called = True
                return {('modified', str(test_paths["content"] / "test.md"))}
            await asyncio.sleep(0.1)  # Keep running
            return {('modified', str(test_paths["content"] / "test.md"))}

        async def close(self):
            pass

    # Mock watchfiles.awatch
    mock_awatch = MagicMock()
    mock_awatch.return_value = MockAsyncIterator()
    monkeypatch.setattr("watchfiles.awatch", mock_awatch)

    # Create a Pyxie instance with reload=True
    pyxie = Pyxie(
        content_dir=test_paths["content"],
        cache_dir=test_paths["cache"],
        reload=False  # Don't auto-start watching
    )

    # Start watching
    await pyxie.start_watching()
    assert pyxie._watcher_task is not None
    assert not pyxie._watcher_task.done()

    # Wait a bit for the watcher to start
    await asyncio.sleep(0.1)

    # Stop watching
    await pyxie.stop_watching()
    assert pyxie._watcher_task is None

    # Verify mock was called with correct directory
    mock_awatch.assert_called_once_with(str(test_paths["content"]))

@pytest.mark.asyncio
async def test_watcher_error_handling(test_paths: Dict[str, Path], monkeypatch) -> None:
    """Test error handling in watcher."""
    import asyncio
    from unittest.mock import MagicMock

    # Create a mock async iterator that raises an exception
    class MockErrorIterator:
        def __aiter__(self):
            return self

        async def __anext__(self):
            raise RuntimeError("Test error")

        async def close(self):
            pass

    # Mock watchfiles.awatch
    mock_awatch = MagicMock()
    mock_awatch.return_value = MockErrorIterator()
    monkeypatch.setattr("watchfiles.awatch", mock_awatch)

    # Create a Pyxie instance with reload=True
    pyxie = Pyxie(
        content_dir=test_paths["content"],
        cache_dir=test_paths["cache"],
        reload=False  # Don't auto-start watching
    )

    # Start watching
    await pyxie.start_watching()
    assert pyxie._watcher_task is not None

    # Wait for the error to be handled
    await asyncio.sleep(0.1)
    assert pyxie._watcher_task is None

@pytest.mark.asyncio
async def test_watcher_restart_on_completion(test_paths: Dict[str, Path], monkeypatch) -> None:
    """Test that watcher restarts if task completes unexpectedly."""
    import asyncio
    from unittest.mock import MagicMock

    # Create a mock async iterator that completes after one iteration
    class MockCompletingIterator:
        def __init__(self):
            self.iteration = 0

        def __aiter__(self):
            return self

        async def __anext__(self):
            if self.iteration == 0:
                self.iteration += 1
                return {('modified', str(test_paths["content"] / "test.md"))}
            raise StopAsyncIteration

        async def close(self):
            pass

    # Mock watchfiles.awatch
    mock_awatch = MagicMock()
    mock_awatch.return_value = MockCompletingIterator()
    monkeypatch.setattr("watchfiles.awatch", mock_awatch)

    # Create a Pyxie instance with reload=True
    pyxie = Pyxie(
        content_dir=test_paths["content"],
        cache_dir=test_paths["cache"],
        reload=True  # Enable auto-restart
    )

    # Start watching
    await pyxie.start_watching()
    assert pyxie._watcher_task is not None

    # Wait for the first watcher to complete and restart
    for _ in range(10):  # Try up to 10 times
        await asyncio.sleep(0.1)
        if pyxie._watcher_task and not pyxie._watcher_task.done():
            break
    else:
        assert False, "Watcher task did not restart"

    # Stop watching
    await pyxie.stop_watching()
    assert pyxie._watcher_task is None