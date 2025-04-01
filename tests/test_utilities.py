"""Tests for utility functions."""

import os
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import MagicMock, patch
import pytest
import logging
from typing import List, Dict, Any
from io import StringIO

from pyxie.utilities import (
    normalize_path,
    hash_file,
    normalize_tags,
    resolve_default_layout,
    safe_import,
    load_content_file,
    build_pagination_urls
)

logger = logging.getLogger(__name__)

class TestPathUtilities:
    """Tests for path handling utilities."""
    
    def test_normalize_path(self):
        """Test normalizing Path objects and strings to string paths."""
        # Test with Path object
        path_obj = Path("/tmp/test")
        normalized = normalize_path(path_obj)
        assert isinstance(normalized, str)
        assert normalized == str(path_obj.resolve())
        
        # Test with string
        path_str = "/tmp/test"
        normalized = normalize_path(path_str)
        assert isinstance(normalized, str)
        assert normalized == str(Path(path_str).resolve())
    
    def test_hash_file(self):
        """Test generating hashes and timestamps for files."""
        # Create a temp file for testing
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"test content")
            tmp_path = tmp.name
        
        try:
            # Test with use_mtime=True (default)
            result = hash_file(tmp_path)
            assert result is not None
            # Timestamp is returned as a float string (e.g., "1741971433.7431777")
            assert '.' in result  # Contains decimal point
            float_result = float(result)  # Should convert to float without error
            assert float_result > 0
            
            # Test with use_mtime=False (md5 hash)
            result = hash_file(tmp_path, use_mtime=False)
            assert result is not None
            assert len(result) == 32  # MD5 hash length
            
            # Test with nonexistent file
            assert hash_file("/path/does/not/exist") is None
            
            # Test error handling
            with patch("builtins.open", side_effect=Exception("Test error")):
                assert hash_file(tmp_path, use_mtime=False) is None
        finally:
            # Clean up
            os.unlink(tmp_path)

class TestDataUtilities:
    """Tests for data transformation utilities."""
    
    def test_normalize_tags(self):
        """Test tag normalization."""
        # Test with string input
        assert normalize_tags("python, testing, Django") == ["django", "python", "testing"]
        
        # Test with list input
        assert normalize_tags(["Python", "TESTING", "django"]) == ["django", "python", "testing"]
        
        # Test with mixed case and duplicates
        assert normalize_tags(["Python", "python", "PYTHON"]) == ["python"]
        
        # Test with empty input
        assert normalize_tags([]) == []
        assert normalize_tags("") == []
        assert normalize_tags(None) == []
    
    def test_resolve_default_layout(self):
        """Test layout resolution."""
        # Test with default layout and no metadata layout
        assert resolve_default_layout("default", {}, "test") == "default"
        
        # Test with default layout and metadata layout
        assert resolve_default_layout("default", {"layout": "custom"}, "test") == "custom"
        
        # Test with explicit layout and no metadata layout
        assert resolve_default_layout("explicit", {}, "test") == "explicit"
        
        # Test with explicit layout and different metadata layout
        logger_mock = MagicMock()
        assert resolve_default_layout("explicit", {"layout": "custom"}, "test", logger_mock) == "explicit"
        logger_mock.warning.assert_called_once()

class TestModuleImportUtilities:
    """Tests for module import utilities."""
    
    def test_safe_import_standard_module(self):
        """Test importing standard Python modules."""
        # Test importing a standard module
        module = safe_import("os")
        assert module is not None
        assert module.__name__ == "os"
        
        # Test with namespace
        namespace = {}
        safe_import("os", namespace)
        assert "os" in namespace
    
    def test_safe_import_nonexistent_module(self):
        """Test importing a nonexistent module."""
        logger_mock = MagicMock()
        
        # Test without context path
        module = safe_import("nonexistent_module", logger_instance=logger_mock)
        assert module is None
        logger_mock.warning.assert_called()
        
        # Test with context path
        with tempfile.TemporaryDirectory() as tmp_dir:
            module = safe_import("nonexistent_module", context_path=tmp_dir, logger_instance=logger_mock)
            assert module is None
    
    def test_safe_import_from_context_path(self, tmp_path):
        """Test importing from a context path."""
        # Create a test module
        module_path = tmp_path / "test_module.py"
        module_path.write_text("TEST_VALUE = 42")
        
        # Test importing the module
        module = safe_import("test_module", context_path=tmp_path)
        assert module is not None
        assert module.TEST_VALUE == 42
        
        # Test with namespace
        namespace = {}
        safe_import("test_module", namespace, context_path=tmp_path)
        assert "test_module" in namespace
        assert "TEST_VALUE" in namespace
        assert namespace["TEST_VALUE"] == 42
    
    def test_safe_import_with_error_in_module(self, tmp_path):
        """Test importing a module that raises an error."""
        # Create a module with an error
        module_path = tmp_path / "error_module.py"
        module_path.write_text("raise ValueError('Test error')")
        
        logger_mock = MagicMock()
        module = safe_import("error_module", context_path=tmp_path, logger_instance=logger_mock)
        assert module is None
        logger_mock.error.assert_called()

class TestContentLoading:
    """Tests for content loading utilities."""
    
    def test_load_content_file(self, tmp_path):
        """Test loading content files."""
        # Create a test file
        test_file = tmp_path / "test.md"
        test_file.write_text("""---
title: Test Post
tags: python, testing
---
Test content""")
        
        # Test loading with default metadata
        default_metadata = {"layout": "default", "author": "Test Author"}
        item = load_content_file(test_file, default_metadata)
        
        assert item is not None
        assert item.title == "Test Post"
        assert item.tags == ["python", "testing"]
        assert item.layout == "default"
        assert item.author == "Test Author"
        assert item.content.strip() == "Test content"
        
        # Test loading with invalid file
        logger_mock = MagicMock()
        invalid_file = tmp_path / "invalid.md"
        invalid_file.write_text("Invalid frontmatter")
        
        item = load_content_file(invalid_file, logger_instance=logger_mock)
        assert item is not None  # Item is created even with invalid frontmatter
        assert item.content == "Invalid frontmatter"  # Content is preserved
        assert item.title == "Invalid"  # Title is derived from filename

class TestPaginationUtilities:
    """Tests for pagination utilities."""
    
    def test_build_pagination_urls(self):
        """Test building pagination URLs."""
        # Mock pagination object
        class MockPagination:
            def __init__(self):
                self.total_pages = 3
                self.current_page = 2
                self.next_page = 3
                self.previous_page = 1
            
            def page_range(self):
                return range(1, self.total_pages + 1)
        
        pagination = MockPagination()
        
        # Test basic pagination
        urls = build_pagination_urls("/blog", pagination)
        assert "page=2" in urls["current"]
        assert urls["current"].startswith("/blog?")
        assert "page=3" in urls["next"]
        assert urls["next"].startswith("/blog?")
        assert urls["prev"] == "/blog"  # First page doesn't have page parameter
        assert urls["first"] == "/blog"
        assert "page=3" in urls["last"]
        assert urls["last"].startswith("/blog?")
        
        # Test with tag
        urls = build_pagination_urls("/blog", pagination, tag="python")
        assert all(param in urls["current"] for param in ["page=2", "tag=python"])
        assert urls["current"].startswith("/blog?")
        assert all(param in urls["next"] for param in ["page=3", "tag=python"])
        assert urls["next"].startswith("/blog?")
        assert urls["prev"] == "/blog?tag=python"  # First page doesn't have page parameter
        
        # Test with additional params
        urls = build_pagination_urls("/blog", pagination, params={"category": "tech"})
        assert all(param in urls["current"] for param in ["page=2", "category=tech"])
        assert urls["current"].startswith("/blog?")
        assert all(param in urls["next"] for param in ["page=3", "category=tech"])
        assert urls["next"].startswith("/blog?")
        assert urls["prev"] == "/blog?category=tech"  # First page doesn't have page parameter
        
        # Test single page
        pagination.total_pages = 1
        urls = build_pagination_urls("/blog", pagination)
        assert urls == {"current": "/blog"} 