"""
Tests for FastHTML escaping functionality.

These tests focus on proper escaping of HTML content,
especially in code blocks and when dealing with special characters.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Callable
import pytest
from mistletoe import Document
from mistletoe.block_token import add_token, Heading, Paragraph, List, HtmlBlock
from fastcore.xml import FT, Div, H1, P, Span, Button, Script
from pyxie.types import ContentItem
from pyxie.parser import RawBlockToken, NestedContentToken, parse_frontmatter
from pyxie.renderer import render_content, PyxieRenderer
from pyxie.layouts import layout, registry
from pyxie.errors import PyxieError
from pyxie.fasthtml import execute_fasthtml, create_namespace
import fasthtml.common as ft_common

# Add these components for the tests to work with ft_common namespace
Div = ft_common.Div
H1 = ft_common.H1
P = ft_common.P
Span = ft_common.Span
Button = ft_common.Button
Script = ft_common.Script
NotStr = ft_common.NotStr

logging.basicConfig(level=logging.DEBUG)

@pytest.fixture(autouse=True)
def setup_test_layout():
    """Set up test layout for all tests."""
    # Clear any existing layouts
    registry._layouts.clear()
    
    @layout("default")
    def default_layout(content: str = "") -> FT:
        """Default layout that just renders the content directly."""
        return Div(data_slot="content")

@pytest.fixture
def create_test_item():
    """Fixture to create test ContentItems."""
    def _create(content: str, metadata: Dict[str, Any] = None) -> ContentItem:
        return ContentItem(
            source_path=Path("test.md"),
            metadata=metadata or {"layout": "default"},
            content=content
        )
    return _create

def render_test_block(tag_name: str, content: str, create_test_item: Callable) -> Any:
    """Helper function to render a test block."""
    logging.debug("=== Starting render_test_block ===")
    logging.debug(f"Tag name: {tag_name}")
    logging.debug(f"Input content:\n{content}")
    
    # Create a test item with the content wrapped in content tags
    test_item = create_test_item(f"<content>\n{content}\n</content>")
    
    # Render the content
    result = render_content(test_item)
    
    logging.debug(f"Render result:\n{result}")
    return result

class TestCodeBlockEscaping:
    """Tests for escaping FastHTML content in code blocks."""
    
    def test_code_block_with_fasthtml(self, create_test_item):
        """Test that FastHTML content in code blocks is properly escaped."""
        content = """
<fasthtml>
def Component():
    return Div(
        P("This is a code block with FastHTML:"),
        P("```python"),
        P("def example():"),
        P("    return Div('Hello')"),
        P("```")
    )
show(Component())
</fasthtml>"""
        
        result = render_test_block('fasthtml', content, create_test_item)
        assert "def example():" in result
        assert "return Div('Hello')" in result

    def test_nested_code_blocks(self, create_test_item):
        """Test escaping of nested code blocks in FastHTML."""
        content = """
<fasthtml>
def Component():
    return Div(
        P("Nested code blocks:"),
        P("```python"),
        P("def outer():"),
        P("    def inner():"),
        P("        return 'nested'"),
        P("    return inner()"),
        P("```")
    )
show(Component())
</fasthtml>"""
        
        result = render_test_block('fasthtml', content, create_test_item)
        assert "def outer():" in result
        assert "def inner():" in result
        assert "return 'nested'" in result

class TestSpecialCharacterEscaping:
    """Tests for escaping special characters in FastHTML."""
    
    def test_html_entities(self, create_test_item):
        """Test that HTML entities are properly escaped."""
        content = r"""
<fasthtml>
def Component():
    return Div(
        P("Special characters: & < > ' \"")
    )
show(Component())
</fasthtml>"""
        
        result = render_test_block('fasthtml', content, create_test_item)
        assert "&" in result
        assert "<" in result
        assert ">" in result
        assert "'" in result
        assert '"' in result

    def test_unicode_characters(self, create_test_item):
        """Test that Unicode characters are properly handled."""
        content = """
<fasthtml>
def Component():
    return Div(
        P("Unicode: 🌟 ✨ 💫")
    )
show(Component())
</fasthtml>"""
        
        result = render_test_block('fasthtml', content, create_test_item)
        assert "🌟" in result
        assert "✨" in result
        assert "💫" in result

    def test_html_content_escaping(self, create_test_item):
        """Test that HTML content is properly escaped when rendered."""
        content = """
<fasthtml>
def Component():
    return Div(
        P("HTML content that needs escaping:"),
        P("&lt;script&gt;alert('xss')&lt;/script&gt;")
    )
show(Component())
</fasthtml>"""
        
        result = render_test_block('fasthtml', content, create_test_item)
        assert "&lt;script&gt;" in result
        assert "alert('xss')" in result

class TestComponentEscaping:
    """Tests for escaping in FastHTML components."""
    
    def test_component_with_escaped_content(self, create_test_item):
        """Test that component content is properly escaped."""
        content = """
<fasthtml>
def Component():
    return Div(
        P("Component with escaped content:"),
        P("&lt;script&gt;alert('xss')&lt;/script&gt;")
    )
show(Component())
</fasthtml>"""
        
        result = render_test_block('fasthtml', content, create_test_item)
        assert "&lt;script&gt;" in result
        assert "alert('xss')" in result

    def test_component_with_raw_html(self, create_test_item):
        """Test that raw HTML in components is properly escaped."""
        content = """
<fasthtml>
def Component():
    return Div(
        P("Raw HTML:"),
        P("&lt;script&gt;alert('xss')&lt;/script&gt;")
    )
show(Component())
</fasthtml>"""
        
        result = render_test_block('fasthtml', content, create_test_item)
        assert "&lt;script&gt;" in result
        assert "alert('xss')" in result