"""
Tests for advanced FastHTML functionality.

These tests focus on complex component structures, error handling,
and advanced content manipulation features.
"""

import logging
import time
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
def test_module_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for test modules."""
    return tmp_path

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

class TestContentManipulation:
    """Tests for content manipulation in FastHTML."""
    
    def test_script_tag_rendering(self, create_test_item):
        """Test that script tags are rendered correctly in the final HTML."""
        content = """
<fasthtml>
def Component():
    return Div(
        P("Hello from FastHTML"),
        Script('''
            function test() {
                return document.querySelector('div > p');
            }
        ''')
    )
show(Component())
</fasthtml>"""
        
        result = render_test_block('fasthtml', content, create_test_item)
        assert '<script>' in result

    def test_complex_nested_components(self, create_test_item):
        """Test rendering of deeply nested component structures."""
        content = """
<fasthtml>
def Card(title, content, footer=None):
    components = [
        Div(title, cls="card-title"),
        Div(content, cls="card-content")
    ]

    if footer:
        components.append(Div(footer, cls="card-footer"))

    return Div(*components, cls="card")

def ListItem(content, index):
    return Div(f"{index + 1}. {content}", cls=f"list-item item-{index}")

app = Div(
    Card(
        title="Complex Component",
        content=Div(
            *[ListItem(f"Item {i}", i) for i in range(3)],
            cls="items-list"
        ),
        footer=Div("Card Footer", cls="footer-content")
    ),
    cls="app-container"
)

show(app)
</fasthtml>"""
        
        result = render_test_block('fasthtml', content, create_test_item)
        assert '<div class="app-container">' in result

    def test_component_with_props(self, create_test_item):
        """Test component with props in FastHTML."""
        content = """
<fasthtml>
def Button(text, cls="btn", **props):
    props_str = ' '.join([f'{k}="{v}"' for k, v in props.items() if k != "disabled"])
    disabled = 'disabled' if props.get('disabled') else ''
    return f'<button class="{cls}" {props_str} {disabled}>{text}</button>'

show(Button("Click me", cls="btn-primary", id="submit-btn", disabled="true"))
</fasthtml>"""
        
        result = render_test_block('fasthtml', content, create_test_item)
        assert '<button class="btn-primary"' in result

class TestComplexRendering:
    """Tests for complex rendering scenarios."""
    
    def test_conditional_rendering(self, create_test_item):
        """Test conditional rendering in FastHTML components."""
        content = """
<fasthtml>
def ConditionalComponent(condition):
    if condition:
        return Div("Condition is True", cls="true-condition")
    else:
        return Div("Condition is False", cls="false-condition")

show(ConditionalComponent(True))
show(ConditionalComponent(False))
</fasthtml>"""
        
        result = render_test_block('fasthtml', content, create_test_item)
        assert '<div class="true-condition">Condition is True</div>' in result
        assert '<div class="false-condition">Condition is False</div>' in result

    def test_component_with_javascript(self, create_test_item):
        """Test components with JavaScript in FastHTML."""
        content = """
<fasthtml>
def PageWithJS(title):
    return Div(
        Div(title, cls="title"),
        Div(
            Div("Page content goes here", cls="content"),
            Div(
                Script("document.addEventListener('DOMContentLoaded', function() { console.log('Page loaded!'); });"),
                cls="scripts"
            ),
            cls="body"
        ),
        cls="page"
    )

show(PageWithJS("Example Page"))
</fasthtml>"""
        
        result = render_test_block('fasthtml', content, create_test_item)
        assert '<div class="page">' in result

    def test_external_module_component(self, create_test_item, test_module_dir: Path):
        """Test importing and using components from external modules."""
        # Create a test module
        module_path = test_module_dir / "test_components.py"
        with open(module_path, 'w') as f:
            f.write("""
def CustomComponent(title, content):
    return f'<div class="custom-component"><h2>{title}</h2><p>{content}</p></div>'
""")
        
        # Allow time for the file to be saved
        time.sleep(0.1)
        
        content = f"""
<fasthtml>
import sys
sys.path.insert(0, r'{test_module_dir}')

import test_components
custom = test_components.CustomComponent("Test Title", "This is the content")
show(custom)
</fasthtml>"""
        
        result = render_test_block('fasthtml', content, create_test_item)
        assert '<div class="custom-component">' in result

    def test_dynamic_components(self, create_test_item):
        """Test dynamic component generation in FastHTML."""
        content = """
<fasthtml>
def create_components(count):
    return [Div(f"Component {i}", cls=f"component-{i}") for i in range(count)]

container = Div(*create_components(3), cls="container")
show(container)
</fasthtml>"""
        
        result = render_test_block('fasthtml', content, create_test_item)
        assert '<div class="container">' in result

class TestErrorHandling:
    """Tests for error handling in FastHTML."""
    
    def test_syntax_error(self, create_test_item):
        """Test that syntax errors are caught and reported properly."""
        content = """
<fasthtml>
def broken_function(
    # Missing closing parenthesis
    return "This will never execute"
</fasthtml>"""
        result = render_test_block('fasthtml', content, create_test_item)
        assert "error" in result.lower()

    def test_runtime_error(self, create_test_item):
        """Test that runtime errors are caught and reported properly."""
        content = """
<fasthtml>
def div_by_zero():
    return 1 / 0

show(div_by_zero())
</fasthtml>"""
        result = render_test_block('fasthtml', content, create_test_item)
        assert "error" in result.lower()

    def test_component_error(self, create_test_item):
        """Test that component errors are caught and reported properly."""
        content = """
<fasthtml>
show(UndefinedComponent())
</fasthtml>"""
        result = render_test_block('fasthtml', content, create_test_item)
        assert "error" in result.lower()

    def test_non_executable_content_not_executed(self, create_test_item):
        """Test that FastHTML content is executed when wrapped in fasthtml tags."""
        content = """
<fasthtml>
# This will be executed
x = 'test content'
show(x)
</fasthtml>"""
        
        result = render_test_block('fasthtml', content, create_test_item)
        assert "test content" in result

    def test_non_executable_content_safety(self, create_test_item):
        """Verify that content is only executed when wrapped in fasthtml tags."""
        # Content without fasthtml tags should not execute
        content_without_tags = """
# This should not execute
x = 'test content preserved'
show(x)
"""
        
        result = render_test_block('fasthtml', content_without_tags, create_test_item)
        # Should succeed and preserve the content
        assert "show(x)" in result 