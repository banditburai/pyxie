"""Shared test fixtures for Pyxie tests."""

import pytest
import logging
from pathlib import Path
from typing import Dict, Any
from pyxie.pyxie import Pyxie
import os
import sys
from mistletoe.block_token import _token_types as mistletoe_block_token
from mistletoe.span_token import _token_types as mistletoe_span_token
from mistletoe.block_token import HtmlBlock
from pyxie.parser import RawBlockToken, NestedContentToken
from pyxie.slots import process_layout, CONDITION_ATTR, SLOT_ATTR

# Add the project root directory to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

logger = logging.getLogger(__name__)

@pytest.fixture
def setup_mistletoe_tokens():
    """Fixture to set up and tear down custom tokens for testing.
    
    This fixture handles:
    - Saving original Mistletoe token types
    - Removing HtmlBlock to prevent special handling of HTML tags
    - Registering custom tokens with high priority
    - Restoring original token types after test
    
    Use this fixture for tests that directly use Mistletoe's Document class.
    Tests using render_content() don't need this fixture as token registration
    is handled internally.
    """
    from mistletoe.block_token import _token_types

    # Save original token types
    original_block_tokens = list(_token_types)

    # Clear existing tokens
    _token_types.clear()

    # Add our custom tokens first (highest priority)
    _token_types.extend([RawBlockToken, NestedContentToken])

    # Add back original tokens except HtmlBlock
    for token in original_block_tokens:
        if token != HtmlBlock and token not in [RawBlockToken, NestedContentToken]:
            _token_types.append(token)

    logger.debug("Custom tokens registered for test.")

    yield

    # Restore original token types
    _token_types.clear()
    _token_types.extend(original_block_tokens)
    logger.debug("Original tokens restored after test.")

@pytest.fixture
def test_paths(tmp_path: Path) -> Dict[str, Path]:
    """Create test directory structure.
    
    Returns:
        Dict with paths for:
        - layouts: Directory for layout files
        - content: Directory for content files
        - cache: Directory for cache files
    """
    return {
        'layouts': tmp_path / "layouts",
        'content': tmp_path / "content",
        'cache': tmp_path / "cache"
    }

@pytest.fixture
def pyxie_instance(test_paths):
    """Create a Pyxie instance for testing."""
    instance = Pyxie(
        content_dir=test_paths['content'],
        cache_dir=test_paths['cache']
    )
    assert "content" in instance.collections
    collection = instance._collections["content"]
    assert collection.path == test_paths['content']
    return instance

@pytest.fixture
def test_layout_html() -> str:
    """Create a test layout HTML with various slots and conditional elements."""
    return f'''
    <div class="layout">
        <div class="header">
            <page-title {SLOT_ATTR}="page_title" class="title">Default Title</page-title>
            <navigation {SLOT_ATTR}="navigation" class="nav"></navigation>
        </div>
        <div class="main">
            <main-content {SLOT_ATTR}="main_content" class="content"></main-content>
            <side-panel {SLOT_ATTR}="side_panel" class="sidebar" {CONDITION_ATTR}="side_panel">Sidebar content</side-panel>
        </div>
        <div class="footer">
            <page-footer {SLOT_ATTR}="page_footer" class="footer" {CONDITION_ATTR}="!hide_footer">Footer content</page-footer>
        </div>
    </div>
    '''

@pytest.fixture
def test_slots_content() -> str:
    """Create test slot content for testing.
    
    Returns an HTML string containing fragments with proper slot attributes.
    Each fragment will be matched with its corresponding slot in the layout.
    """
    return f'''
    <page-title {SLOT_ATTR}="page_title" class="title">Test Title</page-title>
    <navigation {SLOT_ATTR}="navigation" class="nav"><a href='/'>Home</a></navigation>
    <main-content {SLOT_ATTR}="main_content" class="content">Main content here</main-content>
    <side-panel {SLOT_ATTR}="side_panel" class="sidebar">Sidebar content</side-panel>
    <page-footer {SLOT_ATTR}="page_footer" class="footer">Footer content</page-footer>
    '''

@pytest.fixture
def test_context() -> Dict[str, Any]:
    """Create test context for conditional visibility."""
    return {
        "sidebar": True,
        "hide_footer": False,
        "show_extra": True
    }

@pytest.fixture
def process_test_layout(test_layout_html, test_slots_content, test_context):
    """Process a test layout with slots and conditionals."""
    return process_layout(test_layout_html, test_slots_content, test_context)

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "needs_mistletoe_tokens: mark test as needing Mistletoe token setup"
    ) 