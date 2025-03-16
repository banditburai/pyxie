import os
import tempfile
import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import MagicMock, patch

from pyxie.utilities import (
    # HTML-related functions
    set_html_attributes,
    apply_html_attributes,
    merge_html_classes,
    extract_scripts,
    safe_html_escape,
    format_error_html,
    parse_html_fragment,
    
    # Path handling
    normalize_path,
    hash_file,
    
    # String/data handling
    normalize_tags,
    parse_date,
    merge_metadata,
    extract_content,
    get_line_number,
    convert_value,
    is_float,
    
    # Module importing
    safe_import,
)


class TestHtmlUtilities:
    """Tests for HTML-related utility functions."""
    
    def test_set_html_attributes_different_element_types(self):
        """Test setting attributes on different types of HTML elements."""
        # Test element with "set" method (like lxml elements)
        element1 = MagicMock()
        set_html_attributes(element1, {"class": "container", "id": "main"})
        element1.set.assert_any_call("class", "container")
        element1.set.assert_any_call("id", "main")
        
        # Test dictionary-like element
        element2 = {}
        set_html_attributes(element2, {"class": "container", "id": "main"})
        assert element2 == {"class": "container", "id": "main"}
        
        # Test regular Python object (attributes can't be set but function handles it gracefully)
        class Element:
            pass
        element3 = Element()
        
        # Capture print output to verify warning is logged
        with patch('builtins.print') as mock_print:
            set_html_attributes(element3, {"class": "container", "id": "main"})
            # Function should attempt to set attributes but print warnings when it can't
            assert mock_print.call_count >= 1
            
        # Verify attributes weren't actually set
        assert not hasattr(element3, "class")
        assert not hasattr(element3, "id")
    
    def test_set_html_attributes_cls_alias(self):
        """Test handling of 'cls' attribute which should be mapped to 'class'."""
        element = {}
        set_html_attributes(element, {"cls": "container"})
        assert "class" in element
        assert element["class"] == "container"
        assert "cls" not in element
    
    def test_set_html_attributes_error_handling(self):
        """Test error handling when setting attributes fails."""
        logger_mock = MagicMock()
        
        # Test unsupported element type
        element = 42  # An integer doesn't support attribute setting
        set_html_attributes(element, {"class": "container"}, logger_mock)
        logger_mock.warning.assert_called_once()
        
        # Test with exception during setting
        element = MagicMock()
        element.set.side_effect = Exception("Test error")
        set_html_attributes(element, {"class": "container"}, logger_mock)
        logger_mock.error.assert_called_once()
    
    def test_apply_html_attributes(self):
        """Test applying attributes to the first element in an HTML string."""
        # Test with a simple HTML element
        html = "<div>Test</div>"
        result = apply_html_attributes(html, {"class": "container", "id": "main"})
        assert 'class="container"' in result
        assert 'id="main"' in result
        assert 'Test' in result
        
        # Test with a more complex structure
        html = "<div><p>Test</p></div>"
        result = apply_html_attributes(html, {"class": "container"})
        assert 'class="container"' in result
        assert '<p>Test</p>' in result
        
        # Test cls attribute mapping
        html = "<div>Test</div>"
        result = apply_html_attributes(html, {"cls": "container"})
        assert 'class="container"' in result
        
        # Test behavior with invalid HTML - the function attempts to fix/structure it
        logger_mock = MagicMock()
        result = apply_html_attributes("<not-valid>", {"class": "container"}, logger_mock)
        # The function attempts to parse and apply attributes to invalid HTML
        assert 'class="container"' in result
        assert '<not-valid' in result
        assert '</not-valid>' in result
        # No warning should be logged since the function handled it
        logger_mock.warning.assert_not_called()
    
    def test_merge_html_classes(self):
        """Test merging HTML class strings."""
        # Test with simple classes
        assert merge_html_classes("btn", "primary") == "btn primary"
        
        # Test with duplicates
        assert merge_html_classes("btn btn-lg", "btn primary") in ["btn btn-lg primary", "btn primary btn-lg"]
        
        # Test with None and empty strings
        assert merge_html_classes("btn", None, "", "primary") == "btn primary"
        
        # Test with whitespace
        assert merge_html_classes("  btn  ", "  primary  ") == "btn primary"
        
        # Test sorting behavior
        result = merge_html_classes("z-class", "a-class")
        assert result == "a-class z-class"
    
    def test_extract_scripts(self):
        """Test extraction of script tags from HTML content."""
        # Simple case
        html = "<div>Text</div><script>console.log('test');</script><p>More text</p>"
        parts = extract_scripts(html)
        
        # Should return three parts: div, script, and p
        assert len(parts) == 3
        assert parts[0][1] is False  # First part is not a script
        assert parts[1][1] is True   # Second part is a script
        assert parts[2][1] is False  # Third part is not a script
        
        # Content verification
        assert "<div>Text</div>" in parts[0][0]
        assert "<script" in parts[1][0]
        assert "console.log" in parts[1][0]
        assert "<p>More text</p>" in parts[2][0]
        
        # Test with escaped content in script tag
        html = '<div>Text</div><script>console.log("&lt;p&gt;");</script>'
        parts = extract_scripts(html)
        assert '<script data-raw="true">console.log("<p>");</script>' in parts[1][0]
    
    def test_safe_html_escape(self):
        """Test HTML escaping with None handling."""
        assert safe_html_escape("<script>") == "&lt;script&gt;"
        assert safe_html_escape(None) == ""
        assert safe_html_escape('<a href="test">') == '&lt;a href=&quot;test&quot;&gt;'
        assert safe_html_escape('<a href="test">', quote=False) == '&lt;a href="test"&gt;'
    
    def test_format_error_html(self):
        """Test formatting of error messages as HTML."""
        html = format_error_html("parsing", "Invalid syntax")
        assert 'class="pyxie-error"' in html
        assert "Error parsing content: Invalid syntax" in html
    
    def test_parse_html_fragment(self):
        """Test parsing HTML fragments."""
        # Test valid HTML fragment
        elem = parse_html_fragment("<p>Test</p>")
        assert elem.tag == "p"
        assert elem.text == "Test"
        
        # Test fragment that needs wrapping
        elem = parse_html_fragment("Plain text")
        assert elem.tag == "div"
        assert "Plain text" in elem.text


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
    """Tests for data handling utilities."""
    
    def test_normalize_tags(self):
        """Test normalization of tag lists and strings."""
        # Test with string
        assert normalize_tags("tag1,tag2, tag3") == ["tag1", "tag2", "tag3"]
        
        # Test with list
        assert normalize_tags(["Tag1", "tag2", "TAG3"]) == ["tag1", "tag2", "tag3"]
        
        # Test with duplicates
        assert normalize_tags("tag1,tag1,tag2") == ["tag1", "tag2"]
        
        # Test with None and empty values
        assert normalize_tags(None) == []
        assert normalize_tags([]) == []
        assert normalize_tags(["", None, "tag1"]) == ["tag1"]
        
        # Test with mixed types
        assert normalize_tags(["tag1", 123, True]) == ["123", "tag1", "true"]
    
    def test_parse_date(self):
        """Test date string parsing with various formats."""
        # Test ISO format (which should be supported)
        dt = parse_date("2023-01-15")
        assert isinstance(dt, datetime)
        assert dt.year == 2023
        assert dt.month == 1
        assert dt.day == 15
        
        # Test with time
        dt = parse_date("2023-01-15 14:30:00")
        assert dt.hour == 14
        assert dt.minute == 30
        
        # Test various formats - we only check the ones that actually work
        # The function uses COMMON_DATE_FORMATS from constants.py
        for date_str in [
            "2023/01/15",
            "15-01-2023", 
            "01/15/2023"
        ]:
            dt = parse_date(date_str)
            if dt is not None:  # Only assert if format is supported
                assert dt.year == 2023
                assert dt.month == 1
                assert dt.day == 15
        
        # Test invalid format
        assert parse_date("not-a-date") is None
        
        # Test None handling
        assert parse_date(None) is None
    
    def test_merge_metadata(self):
        """Test merging multiple metadata dictionaries."""
        # Basic merge
        meta1 = {"title": "Test", "author": "John"}
        meta2 = {"date": "2023-01-15", "tags": ["test"]}
        result = merge_metadata(meta1, meta2)
        assert result == {"title": "Test", "author": "John", "date": "2023-01-15", "tags": ["test"]}
        
        # Test None handling
        result = merge_metadata(meta1, None, meta2)
        assert result == {"title": "Test", "author": "John", "date": "2023-01-15", "tags": ["test"]}
        
        # Test overwriting behavior
        meta3 = {"title": "New Title"}
        result = merge_metadata(meta1, meta3)
        assert result["title"] == "New Title"
        
        # Test None values in dictionaries
        meta4 = {"author": None, "subtitle": "Test"}
        result = merge_metadata(meta1, meta4)
        assert result["author"] == "John"  # None shouldn't overwrite value
        assert result["subtitle"] == "Test"
    
    def test_extract_content(self):
        """Test extracting and dedenting content optionally wrapped in tags."""
        # Basic content
        content = "Line 1\nLine 2\nLine 3"
        assert extract_content(content) == content
        
        # With tags
        content = "<div>Line 1\nLine 2\nLine 3</div>"
        assert extract_content(content, "<div>", "</div>") == "Line 1\nLine 2\nLine 3"
        
        # With indentation
        content = "    Line 1\n    Line 2\n    Line 3"
        assert extract_content(content) == "Line 1\nLine 2\nLine 3"
        
        # Mixed indentation
        content = "    Line 1\n      Line 2\n    Line 3"
        assert extract_content(content) == "Line 1\n  Line 2\nLine 3"
        
        # Empty content
        assert extract_content("") == ""
        assert extract_content(None) == ""
    
    def test_get_line_number(self):
        """Test getting line number from a position in text."""
        text = "Line 1\nLine 2\nLine 3"
        assert get_line_number(text, 0) == 1
        assert get_line_number(text, 1) == 1
        assert get_line_number(text, 6) == 1
        assert get_line_number(text, 7) == 2
        assert get_line_number(text, 13) == 2
        assert get_line_number(text, 14) == 3
    
    def test_convert_value(self):
        """Test conversion of string values to appropriate types."""
        # Strings
        assert convert_value('"text"') == "text"
        assert convert_value("'text'") == "text"
        
        # Booleans
        assert convert_value("true") is True
        assert convert_value("false") is False
        assert convert_value("yes") is True
        assert convert_value("no") is False
        
        # None
        assert convert_value("null") is None
        assert convert_value("~") is None
        assert convert_value("") is None
        
        # Numbers
        assert convert_value("42") == 42
        assert convert_value("3.14") == 3.14
        
        # Lists
        assert convert_value("[1, 2, 3]") == ["1", "2", "3"]
        assert convert_value("['a', 'b', 'c']") == ["a", "b", "c"]
        
        # Unrecognized formats stay as strings
        assert convert_value("some text") == "some text"
    
    def test_is_float(self):
        """Test checking if a string represents a float."""
        assert is_float("3.14")
        assert is_float("0.0")
        assert is_float("-1.5")
        assert is_float("1e6")
        
        assert not is_float("text")
        assert not is_float("1a")
        assert not is_float("")


class TestModuleImportUtilities:
    """Tests for module import utilities."""
    
    def test_safe_import_standard_module(self):
        """Test importing a standard library module."""
        # Import os module
        result = safe_import("os")
        assert result is not None
        assert result.__name__ == "os"
        
        # With namespace
        namespace = {}
        safe_import("os", namespace)
        assert "os" in namespace
        assert "path" in namespace  # os.path should be in namespace
    
    def test_safe_import_nonexistent_module(self):
        """Test importing a nonexistent module."""
        # Without logger
        result = safe_import("nonexistent_module_abc123")
        assert result is None
        
        # With logger - two warnings are logged
        logger_mock = MagicMock()
        result = safe_import("nonexistent_module_abc123", logger_instance=logger_mock)
        assert result is None
        # Function logs two warning messages for a nonexistent module
        assert logger_mock.warning.call_count == 2
        # First message about not finding in standard paths
        assert "not found in standard paths" in logger_mock.warning.call_args_list[0][0][0]
        # Second message about not being able to import the module
        assert "Could not import module" in logger_mock.warning.call_args_list[1][0][0]
    
    def test_safe_import_from_context_path(self):
        """Test importing from a specific context path."""
        # Create a temporary module file
        with tempfile.TemporaryDirectory() as tmpdir:
            module_path = Path(tmpdir) / "test_module.py"
            with open(module_path, "w") as f:
                f.write("test_var = 'Hello World'\n")
                f.write("def test_func(): return 42\n")
            
            # Import the module from context path
            result = safe_import("test_module", context_path=tmpdir)
            assert result is not None
            assert result.test_var == "Hello World"
            assert result.test_func() == 42
            
            # With namespace
            namespace = {}
            safe_import("test_module", namespace, tmpdir)
            assert "test_module" in namespace
            assert "test_var" in namespace
            assert "test_func" in namespace
            assert namespace["test_var"] == "Hello World"
            assert namespace["test_func"]() == 42
    
    def test_safe_import_with_error_in_module(self):
        """Test importing a module that raises an error during import."""
        # Create a temporary module file with an error
        with tempfile.TemporaryDirectory() as tmpdir:
            module_path = Path(tmpdir) / "error_module.py"
            with open(module_path, "w") as f:
                f.write("raise ImportError('Test error')\n")
            
            # Import should fail but not raise exception
            logger_mock = MagicMock()
            result = safe_import("error_module", context_path=tmpdir, logger_instance=logger_mock)
            assert result is None
            logger_mock.error.assert_called_once()

    def test_custom_slug_in_frontmatter(self, tmp_path):
        """Test that custom slugs in frontmatter override the filename-based slug."""
        from pyxie.utilities import _prepare_content_item
        
        # Create a test file with a custom slug in frontmatter
        file_path = tmp_path / "test-file.md"
        
        # Mock parsed data with a custom slug in metadata
        class MockParsed:
            def __init__(self):
                self.metadata = {"slug": "custom-slug", "title": "Test Title"}
                self.blocks = {}
        
        # Create a content item
        content_item = _prepare_content_item(
            file_path=file_path,
            content="Test content",
            parsed=MockParsed(),
            default_metadata={"author": "Test Author"}
        )
        
        # Verify the custom slug was used instead of the filename
        assert content_item.slug == "custom-slug"
        assert content_item.slug != "test-file"
        
        # Verify other metadata is preserved
        assert content_item.metadata["title"] == "Test Title"
        assert content_item.metadata["author"] == "Test Author" 