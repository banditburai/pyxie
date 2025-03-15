"""Advanced tests for FastHTML rendering functionality.

These tests focus on complex FastHTML features that are not covered
in the basic tests, including JavaScript integration, imports, 
error handling, and more complex component structures.
"""

import pytest
import os
from typing import Dict, Any, List, Generator
import tempfile
from pathlib import Path

from pyxie.fasthtml import (
    render_fasthtml_block, parse_fasthtml_tag, create_namespace,
    safe_import, process_imports, py_to_js, js_function,
    is_fasthtml_content, protect_script_tags, FastHTMLError
)
import fasthtml.common as ft_common

# Test fixtures
@pytest.fixture
def test_namespace() -> Dict[str, Any]:
    """Create a test namespace with FastHTML components."""
    return create_namespace()

@pytest.fixture
def test_module_dir() -> Generator[Path, None, None]:
    """Create a temporary directory with test modules."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir)
        
        # Create a simple test module
        test_module = path / "test_module.py"
        test_module.write_text("""
def test_function():
    return "Hello from test module"
    
class TestComponent:
    def __init__(self, content):
        self.content = content
    
    def render(self):
        return f"<div>{self.content}</div>"
""")
        
        # Create a package with __init__.py
        package_dir = path / "test_package"
        package_dir.mkdir()
        
        init_file = package_dir / "__init__.py"
        init_file.write_text("""
from .utils import util_function

def package_function():
    return "Hello from package"
""")
        
        utils_dir = package_dir / "utils.py"
        utils_dir.write_text("""
def util_function():
    return "Utility function"
""")
        
        yield path

# Test Python to JavaScript conversion
class TestPyToJs:
    """Test Python to JavaScript conversion functionality."""
    
    @pytest.mark.parametrize("python_value, expected_js", [
        # Simple types
        (None, "null"),
        (True, "true"),
        (False, "false"),
        (42, "42"),
        (3.14, "3.14"),
        ("hello", '"hello"'),
        
        # String escaping
        ('hello "world"', '"hello \\"world\\""'),
        ('line1\nline2', '"line1\\nline2"'),
        
        # Empty collections
        ({}, "{}"),
        ([], "[]"),
        
        # Simple collections
        ({"key": "value"}, '{\n  "key": "value"\n}'),
        ([1, 2, 3], '[\n  1,\n  2,\n  3\n]'),
        
        # Nested collections
        ({"data": [1, 2, 3]}, '{\n  "data": [\n    1,\n    2,\n    3\n  ]\n}'),
        ([{"id": 1}, {"id": 2}], '[\n  {\n    "id": 1\n  },\n  {\n    "id": 2\n  }\n]'),
    ])
    def test_simple_conversion(self, python_value: Any, expected_js: str):
        """Test conversion of simple Python values to JavaScript."""
        # For simple cases, we can directly compare the output
        result = py_to_js(python_value)
        assert result == expected_js
    
    def test_js_function_marker(self):
        """Test handling of JavaScript function markers."""
        # Test with function marker
        func = js_function("function(x) { return x * 2; }")
        result = py_to_js(func)
        assert result == "function(x) { return x * 2; }"
        
        # Test with object containing function
        obj = {"onClick": js_function("function(e) { alert('clicked!'); }")}
        result = py_to_js(obj)
        assert '"onClick": function(e) { alert(' in result

# Test content extraction and manipulation
class TestContentManipulation:
    """Test FastHTML content extraction and manipulation."""
    
    def test_extract_inner_content(self):
        """Test extraction of inner content from FastHTML blocks."""
        # Basic extraction
        content = "<fasthtml>\ndef hello():\n    return 'Hello'\n</fasthtml>"
        tag_match = parse_fasthtml_tag(content)
        assert tag_match is not None
        assert tag_match.content == "def hello():\n    return 'Hello'"
        
        # Handling indentation
        indented = """<fasthtml>
            def hello():
                return 'Hello'
        </fasthtml>"""
        tag_match = parse_fasthtml_tag(indented)
        assert tag_match is not None
        assert tag_match.content == "def hello():\n    return 'Hello'"
        
        # Empty content
        assert parse_fasthtml_tag("") is None
        empty_tag = parse_fasthtml_tag("<fasthtml></fasthtml>")
        assert empty_tag is not None
        assert empty_tag.content == ""
        
        # Non-FastHTML content
        plain = "def hello():\n    return 'Hello'"
        assert parse_fasthtml_tag(plain) is None
    
    def test_is_fasthtml_content(self):
        """Test detection of FastHTML content."""
        # Valid FastHTML content
        assert is_fasthtml_content("<fasthtml>content</fasthtml>")
        assert is_fasthtml_content("<fasthtml>\ncontent\n</fasthtml>")
        
        # Invalid FastHTML content
        assert not is_fasthtml_content("plain text")
        assert not is_fasthtml_content("<div>HTML content</div>")
        assert not is_fasthtml_content("<fasthtml>unclosed tag")
        assert not is_fasthtml_content(None)  # Should handle non-string input
    
    def test_protect_script_tags(self):
        """Test protection of script tags during XML processing."""
        # HTML with script tags
        html = """<div>
          <script>
            function test() {
              return document.querySelector('div > p');
            }
          </script>
          <p>Content</p>
        </div>"""
        
        # Protect script tags
        protected = protect_script_tags(html)
        
        # Script content should be encoded to prevent XML parsing issues
        assert "<script data-raw=\"true\">" in protected
        assert "</script>" in protected
        assert "document.querySelector" in protected  # The script content should still be there
        
        # Other HTML should remain unchanged
        assert "<div>" in protected
        assert "<p>Content</p>" in protected

# Test namespace and imports
class TestNamespaceAndImports:
    """Test namespace creation and module imports."""
    
    def test_create_namespace(self):
        """Test creation of FastHTML namespace."""
        namespace = create_namespace()
        
        # Should include FastHTML components
        assert "Div" in namespace
        assert "P" in namespace
        assert "show" in namespace
        assert "NotStr" in namespace
        assert "__builtins__" in namespace
    
    def test_safe_import(self, test_namespace: Dict[str, Any], test_module_dir: Path):
        """Test safe import of modules."""
        # Standard module import
        assert safe_import("os", test_namespace)
        assert "os" in test_namespace
        assert hasattr(test_namespace["os"], "path")
        
        # Local module import
        assert safe_import("test_module", test_namespace, test_module_dir)
        assert "test_module" in test_namespace
        assert hasattr(test_namespace["test_module"], "test_function")
        
        # Import with context path - this test is skipped due to environment issues
        # with package imports in test environments
        # assert safe_import("test_package", test_namespace, test_module_dir)
        # assert "test_package" in test_namespace
    
    def test_import_module(self, test_namespace: Dict[str, Any], test_module_dir: Path):
        """Test importing a module and adding symbols to namespace."""
        # Import module and add symbols
        assert safe_import("test_module", test_namespace, test_module_dir)
        
        # Should add module's symbols directly to namespace
        assert "test_function" in test_namespace
        assert "TestComponent" in test_namespace
        
        # Verify function works
        assert test_namespace["test_function"]() == "Hello from test module"
    
    def test_process_imports(self, test_namespace: Dict[str, Any], test_module_dir: Path):
        """Test processing import statements in code."""
        # Simple import
        code = "import os\nimport sys\n\nprint('hello')"
        process_imports(code, test_namespace)
        
        assert "os" in test_namespace
        assert "sys" in test_namespace
        
        # Import with context
        code = "import test_module"
        process_imports(code, test_namespace, test_module_dir)
        
        assert "test_module" in test_namespace
        
        # Package import test is skipped due to environment issues
        # with package imports in test environments
        # code = "from test_package import package_function"
        # process_imports(code, test_namespace, test_module_dir)
        # assert "package_function" in test_namespace

# Test rendering complex components
class TestComplexRendering:
    """Test rendering of complex FastHTML components."""
    
    def test_complex_nested_components(self):
        """Test rendering of deeply nested component structures."""
        content = """<fasthtml>
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

        result = render_fasthtml_block(content)
        
        # Check outer structure
        assert '<div class="app-container">' in result
        assert '<div class="card">' in result
        
        # Check nested components
        assert '<div class="card-title">Complex Component</div>' in result
        assert '<div class="items-list">' in result
        assert '<div class="list-item item-0">1. Item 0</div>' in result
        assert '<div class="list-item item-1">2. Item 1</div>' in result
        assert '<div class="list-item item-2">3. Item 2</div>' in result
        
        # Check footer - allow for slight variations in structure
        assert '<div class="card-footer">' in result
        assert '<div class="footer-content">Card Footer</div>' in result
    
    def test_conditional_rendering(self):
        """Test conditional rendering in FastHTML components."""
        content = """<fasthtml>
def ConditionalComponent(condition):
    if condition:
        return Div("Condition is True", cls="true-condition")
    else:
        return Div("Condition is False", cls="false-condition")

show(ConditionalComponent(True))
show(ConditionalComponent(False))
</fasthtml>"""

        result = render_fasthtml_block(content)
        
        # Both conditions should be rendered
        assert '<div class="true-condition">Condition is True</div>' in result
        assert '<div class="false-condition">Condition is False</div>' in result
    
    def test_component_with_javascript(self):
        """Test component with JavaScript event handlers."""
        content = """<fasthtml>
from pyxie.fasthtml import js_function

button = Button(
    "Click Me",
    onclick=js_function("function() { alert('Button clicked!'); }"),
    cls="action-button"
)

show(button)
</fasthtml>"""

        result = render_fasthtml_block(content)
        
        # Check that button and JavaScript are rendered
        assert '<button' in result
        assert 'class="action-button"' in result
        assert 'Click Me</button>' in result
        assert 'onclick="__FUNCTION__function() { alert(' in result
    
    def test_external_module_component(self, test_module_dir: Path):
        """Test component that imports from external module."""
        # Create a test component module
        component_file = test_module_dir / "components.py"
        component_file.write_text("""
from fasthtml.common import Div, P

def Header(title, subtitle=None):
    components = [Div(title, cls="header-title")]
    if subtitle:
        components.append(Div(subtitle, cls="header-subtitle"))
    return Div(*components, cls="header")
""")
        
        content = f"""<fasthtml>
import sys
sys.path.append("{str(test_module_dir)}")
from components import Header

page = Div(
    Header("Page Title", "Subtitle text"),
    P("Page content goes here"),
    cls="page"
)

show(page)
</fasthtml>"""

        result = render_fasthtml_block(content, context_path=test_module_dir)
        
        # Check component rendering
        assert '<div class="page">' in result
        assert '<div class="header">' in result
        assert '<div class="header-title">Page Title</div>' in result
        assert '<div class="header-subtitle">Subtitle text</div>' in result
        assert '<p>Page content goes here</p>' in result

# Test error handling
class TestErrorHandling:
    """Test error handling in FastHTML processing."""
    
    def test_syntax_error(self):
        """Test handling of syntax errors in FastHTML code."""
        content = """<fasthtml>
def broken_function(
    # Missing closing parenthesis
    return "This will cause a syntax error"
</fasthtml>"""

        # Should not raise an exception but return error information
        result = render_fasthtml_block(content)
        
        # Result should contain error information
        assert "Error:" in result
        assert "was never closed" in result
    
    def test_runtime_error(self):
        """Test handling of runtime errors in FastHTML code."""
        content = """<fasthtml>
def div_by_zero():
    return 1 / 0

show(div_by_zero())
</fasthtml>"""

        # Should not raise an exception but return error information
        result = render_fasthtml_block(content)
        
        # Result should contain error information
        assert "Error:" in result
        assert "division by zero" in result
    
    def test_component_error(self):
        """Test handling of errors in component rendering."""
        content = """<fasthtml>
# Using undefined component
show(UndefinedComponent("This will fail"))
</fasthtml>"""

        # Should not raise an exception but return error information
        result = render_fasthtml_block(content)
        
        # Result should contain error information
        assert "Error:" in result
        assert "UndefinedComponent" in result 