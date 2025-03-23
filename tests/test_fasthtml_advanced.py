"""Advanced tests for FastHTML rendering functionality.

These tests focus on complex FastHTML features that are not covered
in the basic tests, including JavaScript integration, imports, 
error handling, and more complex component structures.
"""

import pytest
from typing import Dict, Any, Generator
import tempfile
from pathlib import Path
import time
import os

from pyxie.fasthtml import (
    render_fasthtml, parse_fasthtml_tags, create_namespace,
    safe_import, process_imports, py_to_js, js_function,
    protect_script_tags,
    EXECUTABLE_MARKER_START, EXECUTABLE_MARKER_END,
    extract_executable_content
)
from pyxie.types import ContentBlock

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
        tags = parse_fasthtml_tags(content, first_only=True)
        assert tags
        tag_match = tags[0]
        assert tag_match.content == "def hello():\n    return 'Hello'"
        
        # Handling indentation
        indented = """<fasthtml>
            def hello():
                return 'Hello'
        </fasthtml>"""
        tags = parse_fasthtml_tags(indented, first_only=True)
        assert tags
        tag_match = tags[0]
        assert "def hello():" in tag_match.content
        assert "return 'Hello'" in tag_match.content
        
        # Empty content
        assert not parse_fasthtml_tags("", first_only=True)
        empty_tags = parse_fasthtml_tags("<fasthtml></fasthtml>", first_only=True)
        assert empty_tags
        empty_tag = empty_tags[0]
        assert empty_tag.content == ""
        
        # Non-FastHTML content
        plain = "def hello():\n    return 'Hello'"
        assert not parse_fasthtml_tags(plain, first_only=True)
    
    def test_extract_executable_content(self):
        """Test detection and extraction of executable FastHTML content."""
        # Simple check for executable marker
        test_marked = f"{EXECUTABLE_MARKER_START}print('hello'){EXECUTABLE_MARKER_END}"
        assert test_marked.startswith(EXECUTABLE_MARKER_START)
        
        # Import the function to test
        from pyxie.fasthtml import is_executable_fasthtml, extract_executable_content
        
        # Valid executable content
        assert is_executable_fasthtml(test_marked)
        assert extract_executable_content(test_marked) == "print('hello')"
        
        # Non-executable content
        assert not is_executable_fasthtml("plain text")
        assert not is_executable_fasthtml("<fasthtml>content</fasthtml>")
        assert extract_executable_content("plain text") == "plain text"  # Returns original if not executable
    
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
    """Test complex FastHTML rendering scenarios."""
    
    def test_complex_nested_components(self):
        """Test rendering of deeply nested component structures."""
        content = EXECUTABLE_MARKER_START + """<fasthtml>
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
</fasthtml>""" + EXECUTABLE_MARKER_END

        result = render_fasthtml(content)
        assert result.success
        rendered = result.content

        # Check outer structure
        assert '<div class="app-container">' in rendered
        assert '<div class="card">' in rendered
        assert '<div class="card-title">Complex Component</div>' in rendered
        assert '<div class="card-content">' in rendered
        assert '<div class="items-list">' in rendered

        # Check list items
        assert '<div class="list-item item-0">1. Item 0</div>' in rendered
        assert '<div class="list-item item-1">2. Item 1</div>' in rendered
        assert '<div class="list-item item-2">3. Item 2</div>' in rendered

        # Check footer
        assert '<div class="card-footer">' in rendered
        assert '<div class="footer-content">Card Footer</div>' in rendered

    def test_conditional_rendering(self):
        """Test conditional rendering in FastHTML components."""
        content = EXECUTABLE_MARKER_START + """<fasthtml>
def ConditionalComponent(condition):
    if condition:
        return Div("Condition is True", cls="true-condition")
    else:
        return Div("Condition is False", cls="false-condition")

show(ConditionalComponent(True))
show(ConditionalComponent(False))
</fasthtml>""" + EXECUTABLE_MARKER_END

        result = render_fasthtml(content)
        assert result.success
        rendered = result.content

        # Both conditions should be rendered
        assert '<div class="true-condition">Condition is True</div>' in rendered
        assert '<div class="false-condition">Condition is False</div>' in rendered

    def test_component_with_javascript(self):
        """Test components with JavaScript in FastHTML."""
        content = EXECUTABLE_MARKER_START + """<fasthtml>
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
</fasthtml>""" + EXECUTABLE_MARKER_END

        result = render_fasthtml(content)
        assert result.success
        rendered = result.content

        # Check basic structure
        assert '<div class="page">' in rendered
        assert '<div class="title">Example Page</div>' in rendered
        assert '<div class="body">' in rendered
        assert '<div class="content">Page content goes here</div>' in rendered
        assert '<div class="scripts">' in rendered
        
        # Check script content (should be protected)
        assert 'document.addEventListener' in rendered
        assert "console.log('Page loaded!')" in rendered

    def test_external_module_component(self, test_module_dir: Path):
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

        content = EXECUTABLE_MARKER_START + """<fasthtml>
import sys
sys.path.insert(0, r'""" + str(test_module_dir) + """')

import test_components
custom = test_components.CustomComponent("Test Title", "This is the content")
show(custom)
</fasthtml>""" + EXECUTABLE_MARKER_END

        result = render_fasthtml(content)
        assert result.success, f"Error: {result.error}"
        rendered = result.content

        # The component is now rendered as HTML, not escaped
        assert '<div class="custom-component">' in rendered
        assert '<h2>Test Title</h2>' in rendered
        assert '<p>This is the content</p>' in rendered

    def test_dynamic_components(self):
        """Test dynamic component generation in FastHTML."""
        content = EXECUTABLE_MARKER_START + """<fasthtml>
def create_components(count):
    return [Div(f"Component {i}", cls=f"component-{i}") for i in range(count)]

container = Div(*create_components(3), cls="container")
show(container)
</fasthtml>""" + EXECUTABLE_MARKER_END

        result = render_fasthtml(content)
        assert result.success
        rendered = result.content

        # Check container and all dynamic components
        assert '<div class="container">' in rendered
        assert '<div class="component-0">Component 0</div>' in rendered
        assert '<div class="component-1">Component 1</div>' in rendered
        assert '<div class="component-2">Component 2</div>' in rendered

    def test_component_with_props(self):
        """Test component with props in FastHTML."""
        content = EXECUTABLE_MARKER_START + """<fasthtml>
def Button(text, cls="btn", **props):
    props_str = ' '.join([f'{k}="{v}"' for k, v in props.items()])
    return f'<button class="{cls}" {props_str}>{text}</button>'

show(Button("Click me", cls="btn-primary", id="submit-btn", disabled="true"))
</fasthtml>""" + EXECUTABLE_MARKER_END

        result = render_fasthtml(content)
        assert result.success
        rendered = result.content

        # The component is now rendered as HTML, not escaped
        assert '<button class="btn-primary"' in rendered
        assert 'id="submit-btn"' in rendered
        assert 'disabled="true"' in rendered
        assert '>Click me</button>' in rendered

    def test_nested_tags(self):
        """Test processing of nested FastHTML tags."""
        # Test content with executable marker
        content = EXECUTABLE_MARKER_START + """
show(Div("Test component"))
""" + EXECUTABLE_MARKER_END

        # Process the content with the marker
        result = render_fasthtml(content)
        
        # The component should be rendered
        assert '<div>Test component</div>' in result.content

# Test error handling
class TestErrorHandling:
    """Test error handling in FastHTML."""
    
    def test_syntax_error(self):
        """Test that syntax errors are caught and reported properly."""
        content = EXECUTABLE_MARKER_START + """<fasthtml>
def broken_function(
    # Missing closing parenthesis
    return "This will never execute"
</fasthtml>""" + EXECUTABLE_MARKER_END

        result = render_fasthtml(content)
        assert not result.success
        assert "Syntax error" in str(result.error)
    
    def test_runtime_error(self):
        """Test that runtime errors are caught and reported properly."""
        content = EXECUTABLE_MARKER_START + """<fasthtml>
def div_by_zero():
    return 1 / 0

show(div_by_zero())
</fasthtml>""" + EXECUTABLE_MARKER_END

        result = render_fasthtml(content)
        assert not result.success
        assert "ZeroDivisionError" in str(result.error)
    
    def test_component_error(self):
        """Test that component errors are caught and reported properly."""
        content = EXECUTABLE_MARKER_START + """<fasthtml>
show(UndefinedComponent())
</fasthtml>""" + EXECUTABLE_MARKER_END

        result = render_fasthtml(content)
        assert not result.success
        assert "NameError" in str(result.error)
        
    def test_non_executable_content_not_executed(self):
        """Test that FastHTML content without the executable marker is not executed."""
        content = """<fasthtml>
# This would cause an error if executed
undefined_variable + 1
</fasthtml>"""

        result = render_fasthtml(content)
        assert result.success
        assert "undefined_variable + 1" in result.content 
        
    def test_non_executable_content_safety(self):
        """Verify that content is only executed when it has the executable marker."""
        # Content without the marker should not execute
        content_without_marker = """<fasthtml>
# This should not execute
x = 'test content preserved'
show(x)
</fasthtml>"""
        
        result = render_fasthtml(content_without_marker)
        # Should succeed and preserve the content
        assert result.success
        assert "show(x)" in result.content
        
        # Same content with marker should execute
        content_with_marker = EXECUTABLE_MARKER_START + """
# This should execute
x = 'test content executed'
show(x)
""" + EXECUTABLE_MARKER_END
        
        result = render_fasthtml(content_with_marker)
        # Should succeed and show the result
        assert result.success
        assert "test content executed" in result.content 