"""Test conditional visibility in layouts."""

import pytest
from src.pyxie.slots import process_layout, SlotError

def test_process_conditional_visibility_single_slot():
    """Test conditional visibility with a single slot."""
    layout_html = """
    <div>
        <h1 data-pyxie-show="header">Welcome</h1>
        <div data-slot="header"></div>
    </div>
    """
    rendered_html = """
    <div data-slot="header">My Header</div>
    """
    result = process_layout(layout_html, rendered_html, {})
    assert "My Header" in result
    assert 'data-pyxie-show="header"' not in result  # Attribute should be removed
    assert "Welcome" in result  # Content is preserved when slot is filled

def test_process_conditional_visibility_multiple_slots():
    """Test conditional visibility with multiple slots using OR logic."""
    layout_html = """
    <div>
        <h1 data-pyxie-show="header">Welcome</h1>
        <div data-slot="header"></div>
        <p data-pyxie-show="footer">Goodbye</p>
        <div data-slot="footer"></div>
    </div>
    """
    rendered_html = """
    <div data-slot="header">My Header</div>
    """
    result = process_layout(layout_html, rendered_html, {})
    assert "My Header" in result
    assert 'data-pyxie-show="header"' not in result  # Attribute should be removed
    assert 'data-pyxie-show="footer"' not in result  # Attribute should be removed
    assert "Welcome" in result  # Content is preserved when slot is filled
    assert "Goodbye" not in result  # Content is removed when slot is empty

def test_process_conditional_visibility_with_existing_style():
    """Test conditional visibility with elements that already have style attributes."""
    layout_html = """
    <div>
        <h1 data-pyxie-show="header">Welcome</h1>
        <div data-slot="header" style="color: blue;"></div>
    </div>
    """
    rendered_html = """
    <div data-slot="header">My Header</div>
    """
    result = process_layout(layout_html, rendered_html, {})
    assert "My Header" in result
    assert "color: blue" in result
    assert 'data-pyxie-show="header"' not in result  # Attribute should be removed
    assert "Welcome" in result  # Content is preserved when slot is filled

def test_process_conditional_visibility_error_handling():
    """Test error handling for invalid HTML input."""
    with pytest.raises(SlotError):
        process_layout("<invalid>", "", {})

def test_process_conditional_visibility_negation():
    """Test negation conditions."""
    layout_html = """
    <div>
        <h1 data-pyxie-show="!footer">No Footer</h1>
        <div data-slot="header"></div>
    </div>
    """
    rendered_html = """
    <div data-slot="header">My Header</div>
    """
    result = process_layout(layout_html, rendered_html, {})
    assert "My Header" in result
    assert 'data-pyxie-show="!footer"' not in result  # Attribute should be removed
    assert "No Footer" in result  # Content is preserved when condition is met

def test_process_conditional_visibility_complex_conditions():
    """Test complex conditional visibility scenarios."""
    layout_html = """
    <div>
        <h1 data-pyxie-show="header">Welcome</h1>
        <div data-slot="header"></div>
        <nav data-pyxie-show="sidebar">Navigation</nav>
        <div data-slot="sidebar"></div>
        <p data-pyxie-show="footer">Goodbye</p>
        <div data-slot="footer"></div>
    </div>
    """
    rendered_html = """
    <div data-slot="header">My Header</div>
    <div data-slot="sidebar">My Sidebar</div>
    """
    result = process_layout(layout_html, rendered_html, {})
    assert "My Header" in result
    assert "My Sidebar" in result
    assert 'data-pyxie-show="header"' not in result  # Attribute should be removed
    assert 'data-pyxie-show="sidebar"' not in result  # Attribute should be removed
    assert 'data-pyxie-show="footer"' not in result  # Attribute should be removed
    assert "Welcome" in result  # Content is preserved when slot is filled
    assert "Navigation" in result  # Content is preserved when slot is filled
    assert "Goodbye" not in result  # Content is removed when slot is empty

def test_process_conditional_visibility_whitespace_handling():
    """Test whitespace handling in conditional attributes."""
    layout_html = """
    <div>
        <h1 data-pyxie-show=" header ">Welcome</h1>
        <div data-slot="header"></div>
    </div>
    """
    rendered_html = """
    <div data-slot="header">My Header</div>
    """
    result = process_layout(layout_html, rendered_html, {})
    assert "My Header" in result
    assert 'data-pyxie-show=" header "' not in result  # Attribute should be removed
    assert "Welcome" in result  # Content is preserved when slot is filled

def test_layout_with_fixtures():
    """Test layout processing with test fixtures."""
    layout_html = """
    <div>
        <h1 data-pyxie-show="header">Welcome</h1>
        <div data-slot="header"></div>
    </div>
    """
    rendered_html = """
    <div data-slot="header">My Header</div>
    """
    result = process_layout(layout_html, rendered_html, {})
    assert "My Header" in result
    assert 'data-pyxie-show="header"' not in result  # Attribute should be removed
    assert "Welcome" in result  # Content is preserved when slot is filled

def test_layout_with_modified_context():
    """Test layout processing with different context values."""
    layout_html = """
    <div>
        <h1 data-pyxie-show="show_header">Welcome</h1>
        <div data-slot="header"></div>
    </div>
    """
    rendered_html = """
    <div data-slot="header">My Header</div>
    """
    result = process_layout(layout_html, rendered_html, {"show_header": True})
    assert "My Header" in result
    assert 'data-pyxie-show="show_header"' not in result  # Attribute should be removed
    assert "Welcome" in result  # Content is preserved when condition is met

def test_layout_with_empty_slots():
    """Test layout processing with empty slots."""
    layout_html = """
    <div>
        <h1 data-pyxie-show="header">Welcome</h1>
        <div data-slot="header"></div>
    </div>
    """
    rendered_html = ""
    result = process_layout(layout_html, rendered_html, {})
    assert 'data-pyxie-show="header"' not in result  # Attribute should be removed
    assert "Welcome" not in result  # Content is removed when slot is empty 