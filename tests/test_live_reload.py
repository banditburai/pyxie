"""Tests for content rebuilding functionality."""

from pyxie import Pyxie
import pyxie

def test_rebuild_content(tmp_path):
    """Test that content rebuilding works correctly."""
    # Create test content
    content_dir = tmp_path / "content"
    content_dir.mkdir()
    (content_dir / "test.md").write_text("Test content")
    
    # Initialize Pyxie
    pyxie = Pyxie(content_dir=content_dir)
    assert "content" in pyxie.collections
    collection = pyxie._collections["content"]
    assert collection.path == content_dir
    
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

def test_rebuild_triggers_reload(tmp_path, monkeypatch):
    """Test that rebuild_content triggers reload by touching __init__.py when reload=True."""
    import os
    from pathlib import Path
    
    # Track if utime was called
    utime_called = False
    def mock_utime(path, times):
        nonlocal utime_called
        utime_called = True
    monkeypatch.setattr(os, 'utime', mock_utime)
    
    # Create test content
    content_dir = tmp_path / "content"
    content_dir.mkdir()
    (content_dir / "test.md").write_text("Test content")
    
    # Initialize Pyxie with reload enabled
    pyxie_instance = Pyxie(content_dir=content_dir, reload=True)
    
    # Create a mock __init__.py file
    init_file = Path(pyxie.__file__).parent / "__init__.py"
    init_file.parent.mkdir(parents=True, exist_ok=True)
    init_file.touch()
    
    # Rebuild content
    pyxie_instance.rebuild_content()
    
    # Verify that utime was called to trigger reload
    assert utime_called, "reload should trigger utime on __init__.py" 