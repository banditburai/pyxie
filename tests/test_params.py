"""Tests for parameter parsing functionality."""

import pytest
from typing import Dict, Any

from pyxie.params import parse_params, normalize_class_attr, format_params

# Test fixtures
@pytest.fixture
def simple_params() -> Dict[str, str]:
    """Simple parameter dictionary for testing."""
    return {
        "class": "container",
        "id": "main",
        "data-attr": "value"
    }

# Test cases for normalize_class_attr
@pytest.mark.parametrize("input_params, expected", [
    ({"cls": "container"}, {"class": "container"}),
    ({"class": "container"}, {"class": "container"}),
    ({"cls": "container", "id": "main"}, {"class": "container", "id": "main"}),
    ({"cls": "container", "class": "override"}, {"class": "override", "cls": "container"}),
    ({}, {}),
    ({"id": "main"}, {"id": "main"})
])
def test_normalize_class_attr(input_params: Dict[str, str], expected: Dict[str, str]):
    """Test normalizing class attributes."""
    result = normalize_class_attr(input_params)
    assert result == expected
    
    # The function should not modify the original dictionary if cls is not present
    if "cls" not in input_params:
        assert input_params == result

# Test cases for parse_params
@pytest.mark.parametrize("params_str, expected", [
    # Basic cases
    ('class="container"', {"class": "container"}),
    ('id=main', {"id": "main"}),
    ('class="container" id=main', {"class": "container", "id": "main"}),
    
    # Different quote types
    ('class="container" title=\'Page Title\'', {"class": "container", "title": "Page Title"}),
    ('desc=\'Single quotes\' msg="Double quotes"', {"desc": "Single quotes", "msg": "Double quotes"}),
    
    # Normalize cls to class
    ('cls="container"', {"class": "container"}),
    
    # Hyphenated attributes
    ('data-attr="value"', {"data-attr": "value"}),
    ('data-value=42', {"data-value": "42"}),
    
    # Empty cases
    ('', {}),
    (None, {}),
    
    # Multiple spaces
    ('  class="spaced"    id=test  ', {"class": "spaced", "id": "test"}),
    
    # Edge cases
    ('class="value with spaces"', {"class": "value with spaces"}),
    ('class="value" id="test" disabled', {"class": "value", "id": "test"}),  # incomplete param is ignored
])
def test_parse_params(params_str: str, expected: Dict[str, str]):
    """Test parsing parameters from strings."""
    result = parse_params(params_str)
    assert result == expected

def test_parse_params_complex():
    """Test parsing more complex parameter strings."""
    # Complex parameter string with various formats
    params_str = 'class="container mx-auto" id=main data-attr="value with spaces" aria-label=\'Accessible label\' data-index=42'
    
    result = parse_params(params_str)
    
    assert len(result) == 5
    assert result["class"] == "container mx-auto"
    assert result["id"] == "main"
    assert result["data-attr"] == "value with spaces"
    assert result["aria-label"] == "Accessible label"
    assert result["data-index"] == "42"

def test_parse_params_invalid():
    """Test parsing invalid parameter strings."""
    # Invalid parameter strings
    invalid_cases = [
        'class=',                  # Missing value
        'class="unclosed',         # Unclosed quote
        '=value',                  # Missing key
        'class="value" =42',       # Missing key for second param
    ]
    
    for invalid in invalid_cases:
        result = parse_params(invalid)
        # Should return empty dict or partial results without raising exceptions
        assert isinstance(result, dict)
    
    # Test non-string input separately
    with pytest.raises(AttributeError):
        parse_params(42)  # Will raise AttributeError since int has no strip method

# Test cases for format_params
@pytest.mark.parametrize("params, expected", [
    # Basic cases
    ({"class": "container"}, 'class=container'),
    ({"id": "main"}, 'id=main'),
    ({"class": "container", "id": "main"}, 'class=container id=main'),
    
    # Normalize cls to class
    ({"cls": "container"}, 'class=container'),
    
    # Values with spaces
    ({"title": "Page Title"}, 'title="Page Title"'),
    
    # Empty cases
    ({}, ''),
    
    # None values
    ({"class": "container", "disabled": None}, 'class=container'),
    
    # Non-string values
    ({"data-index": 42}, 'data-index=42'),
    ({"data-active": True}, 'data-active=True'),
])
def test_format_params(params: Dict[str, Any], expected: str):
    """Test formatting parameters as strings."""
    result = format_params(params)
    assert result == expected

def test_format_params_sort_order():
    """Test that parameters are sorted alphabetically."""
    params = {
        "z-index": 1,
        "class": "container",
        "id": "main",
        "aria-label": "test"
    }
    
    result = format_params(params)
    
    # Split the result into parts
    parts = result.split()
    
    # Check that the parts are sorted alphabetically by key
    assert parts[0].startswith('aria-label=')
    assert parts[1].startswith('class=')
    assert parts[2].startswith('id=')
    assert parts[3].startswith('z-index=')

def test_format_params_special_chars():
    """Test formatting with special characters."""
    params = {
        "data-value": "value with \"quotes\"",
        "title": "Title with 'single' quotes",
        "description": "Line 1\nLine 2"
    }
    
    result = format_params(params)
    
    # Should properly handle special characters
    assert 'data-value="value with "quotes""' in result
    assert 'title="Title with \'single\' quotes"' in result
    assert 'description="Line 1\nLine 2"' in result

def test_format_params_complex():
    """Test formatting complex parameters."""
    params = {
        "class": "container mx-auto",
        "id": "main-content",
        "data-attr": "test-value",
        "aria-label": "Content section",
        "style": "margin: 0; padding: 10px;",
        "hidden": True
    }
    
    result = format_params(params)
    
    # Check that all parameters are included
    assert 'class="container mx-auto"' in result
    assert 'id=main-content' in result
    assert 'data-attr=test-value' in result
    assert 'aria-label="Content section"' in result
    assert 'style="margin: 0; padding: 10px;"' in result
    assert 'hidden=True' in result

def test_round_trip():
    """Test round-trip parsing and formatting."""
    original = 'class="container" id=main data-value="test" aria-hidden=true'
    
    # Parse the parameters
    parsed = parse_params(original)
    
    # Format them back to string
    formatted = format_params(parsed)
    
    # The formatted string might have different order or quoting, but parsing it again should give the same result
    reparsed = parse_params(formatted)
    
    assert parsed == reparsed 