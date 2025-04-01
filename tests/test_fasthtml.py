"""Test FastHTML rendering functionality."""

import pytest
from pathlib import Path
from pyxie.types import ContentItem
from pyxie.renderer import render_content
from pyxie.layouts import layout, registry
from fastcore.xml import FT, Div, H1, H2, P
from pyxie.fasthtml import execute_fasthtml
import fasthtml.common as ft_common

@pytest.fixture(autouse=True)
def setup_test_layout():
    """Set up test layout for all tests."""
    registry._layouts.clear()
    
    @layout("default")
    def default_layout(content: str = "") -> FT:
        """Default layout that just renders the content directly."""
        return Div(content, data_slot="main_content")

def create_test_item(content: str) -> ContentItem:
    """Create a test ContentItem with the given content."""
    return ContentItem(
        source_path=Path("test.md"),
        metadata={"layout": "default"},
        content=content
    )

def test_simple_component():
    """Test rendering of a simple component."""
    content = """
<main_content>
<ft>
show(Div("Hello World", cls="test-class"))
</ft>
</main_content>
"""
    item = create_test_item(content)
    html = render_content(item)
    assert '<div>\n<div class="test-class">Hello World</div>\n</div>' in html

def test_nested_components():
    """Test rendering of nested components."""
    content = """
<main_content>
<ft>
component = Div(
    Div("Inner content", cls="inner"),
    cls="outer"
)
show(component)
</ft>
</main_content>
"""
    item = create_test_item(content)
    html = render_content(item)
    assert '<div>\n<div class="outer">' in html
    assert '<div class="inner">Inner content</div>' in html

def test_component_function():
    """Test rendering of component functions."""
    content = """
<main_content>
<ft>
def MyComponent(text):
    return Div(text, cls="custom")

show(MyComponent("Hello from function"))
</ft>
</main_content>
"""
    item = create_test_item(content)
    html = render_content(item)
    assert '<div>\n<div class="custom">Hello from function</div>\n</div>' in html

def test_script_block():
    """Test that script blocks are properly rendered."""
    content = """
<main_content>
<script>
console.log("Hello World");
</script>
</main_content>
"""
    item = create_test_item(content)
    html = render_content(item)
    assert '<script>\nconsole.log("Hello World");\n</script>' in html

def test_multiple_blocks():
    """Test that multiple blocks are properly rendered."""
    content = """
<main_content>
<ft>
show(Div('First block'))
</ft>

<script>
console.log('Second block');
</script>

This is markdown content.
</main_content>
"""
    item = create_test_item(content)
    html = render_content(item)
    assert '<div>\n<div>First block</div>\n</div>' in html
    assert '<script>\nconsole.log(\'Second block\');\n</script>' in html
    assert '<p>This is markdown content.</p>' in html

def test_mixed_content():
    """Test rendering of mixed content types."""
    content = """
<main_content>
<ft>
show(Div("FastHTML content"))
</ft>

<script>
console.log("Script content");
</script>

Regular markdown content.

<ft>
show(Div("More FastHTML content"))
</ft>
</main_content>
"""
    item = create_test_item(content)
    html = render_content(item)
    assert '<div>\n<div>FastHTML content</div>\n</div>' in html
    assert '<script>\nconsole.log("Script content");\n</script>' in html
    assert '<p>Regular markdown content.</p>' in html
    assert '<div>\n<div>More FastHTML content</div>\n</div>' in html

def test_process_fasthtml():
    """Test FastHTML function creation and execution."""
    # Import components for test
    Div = ft_common.Div
    
    # Test function definition and execution
    content = """
def Greeting(name):
    return Div(f"Hello, {name}!", cls="greeting")
show(Greeting("World"))
"""
    
    result = execute_fasthtml(content)
    assert result.success, f"Rendering failed: {result.error}"
    assert "<div class=\"greeting\">Hello, World!</div>" in result.content

def test_fasthtml_function_with_multiple_args():
    """Test FastHTML function with multiple arguments."""
    content = """
def Card(title, content, footer=None):
    return Div(
        Div(title, cls="card-title"),
        Div(content, cls="card-content"),
        Div(footer, cls="card-footer") if footer else None,
        cls="card"
    )
show(Card("Hello", "This is content", "Footer text"))
"""
    result = execute_fasthtml(content)
    assert result.success, f"Rendering failed: {result.error}"
    assert '<div class="card">' in result.content
    assert '<div class="card-title">Hello</div>' in result.content
    assert '<div class="card-content">This is content</div>' in result.content
    assert '<div class="card-footer">Footer text</div>' in result.content

def test_fasthtml_function_reuse():
    """Test that FastHTML functions can be reused."""
    content = """
def Button(text, cls=""):
    return Div(text, cls=f"button {cls}".strip())

show(Button("Click me"))
show(Button("Submit", cls="primary"))
"""
    result = execute_fasthtml(content)
    assert result.success, f"Rendering failed: {result.error}"
    assert '<div class="button">Click me</div>' in result.content
    assert '<div class="button primary">Submit</div>' in result.content

def test_fasthtml_conditional_logic():
    """Test FastHTML conditional logic."""
    content = """
items = ["A", "B", "C"]
for item in items:
    show(Div(f"Item {item}"))

if len(items) > 2:
    show(Div("More than 2 items"))
else:
    show(Div("2 or fewer items"))
"""
    result = execute_fasthtml(content)
    assert result.success, f"Rendering failed: {result.error}"
    assert "Item A" in result.content
    assert "Item B" in result.content
    assert "Item C" in result.content
    assert "More than 2 items" in result.content
    assert "2 or fewer items" not in result.content

def test_fasthtml_error_handling():
    """Test FastHTML error handling."""
    # Test undefined variable
    content = "show(undefined_var)"
    result = execute_fasthtml(content)
    assert not result.success
    assert "undefined_var" in result.error.lower()
    
    # Test syntax error
    content = "show(Div('Unclosed string)"
    result = execute_fasthtml(content)
    assert not result.success
    assert "unterminated string literal" in result.error.lower()
    
    # Test type error
    content = "show(Div(123 + 'string'))"
    result = execute_fasthtml(content)
    assert not result.success
    assert "type" in result.error.lower() 

def test_complex_nested_content():
    """Test rendering of complex nested FastHTML content."""
    content = """
<main_content>
<ft>
def ComplexComponent():
    return Div([
        H1("Main Title"),
        Div([
            H2("Nested Section"),
            P("Some text"),
            Div([
                "Deep nested content",
                Div("Even deeper", cls="deep")
            ], cls="inner")
        ], cls="nested"),
        Div("Footer", cls="footer")
    ], cls="complex")

show(ComplexComponent())
</ft>
</main_content>
"""
    item = create_test_item(content)
    html = render_content(item)
    assert '<div>\n<div class="complex">' in html
    assert '<h1>Main Title</h1>' in html
    assert '<div class="nested">' in html
    assert '<h2>Nested Section</h2>' in html
    assert '<div class="inner">' in html
    assert '<div class="deep">Even deeper</div>' in html
    assert '<div class="footer">Footer</div>' in html

def test_render_block_integration():
    """Test integration between render_content and FastHTML."""
    content = """
<main_content>
<ft>
def TestComponent():
    return Div(
        H1("Test Title"),
        P("Test content"),
        cls="test-component"
    )

show(TestComponent())
</ft>
</main_content>
"""
    item = create_test_item(content)
    html = render_content(item)
    assert '<div>\n<div class="test-component">' in html
    assert '<h1>Test Title</h1>' in html
    assert '<p>Test content</p>' in html

def test_comprehensive_error_handling():
    """Test comprehensive error handling in FastHTML."""
    # Test syntax error
    content = """def broken_function():
return "This will never execute"
"""
    result = execute_fasthtml(content)
    assert not result.success
    assert "expected an indented block" in result.error.lower()
    
    # Test runtime error
    content = """def div_by_zero():
    x = 1/0
    return x
show(div_by_zero())
"""
    result = execute_fasthtml(content)
    assert not result.success
    assert "division by zero" in result.error.lower()
    
    # Test undefined component
    content = """show(NonexistentComponent())
"""
    result = execute_fasthtml(content)
    assert not result.success
    assert "nonexistentcomponent" in result.error.lower()
    
    # Test invalid show() call
    content = """show(Div("Test"), invalid="param")
"""
    result = execute_fasthtml(content)
    assert not result.success
    assert "unexpected keyword argument" in result.error.lower()

def test_py_to_js_conversion():
    """Test Python to JavaScript conversion."""
    from pyxie.fasthtml import py_to_js
    
    # Test basic types
    assert py_to_js(None) == "null"
    assert py_to_js(True) == "true"
    assert py_to_js(42) == "42"
    assert py_to_js(3.14) == "3.14"
    
    # Test string escaping
    assert py_to_js('test"quote"') == '"test\\"quote\\""'
    assert py_to_js('line\nbreak') == '"line\\nbreak"'
    
    # Test function conversion
    assert py_to_js("__FUNCTION__function() { return 42; }") == "function() { return 42; }"
    
    # Test collections
    assert py_to_js([1, 2, 3], indent=0) == "[\n  1,\n  2,\n  3\n]"
    assert py_to_js({"a": 1, "b": 2}, indent=0) == "{\n  \"a\": 1,\n  \"b\": 2\n}"
    
    # Test callable
    def test_func(): pass
    assert "function test_func(index)" in py_to_js(test_func)
    
    # Test error handling
    class CustomObj:
        def __str__(self): raise ValueError("test error")
    
    try:
        py_to_js(CustomObj())
        assert False, "Expected ValueError"
    except ValueError as e:
        assert str(e) == "test error"

def test_pyxie_xml_advanced():
    """Test advanced PyxieXML functionality."""
    from pyxie.fasthtml import PyxieXML
    
    # Test script tag handling
    script = PyxieXML("script", "console.log('test')", type="text/javascript")
    assert str(script) == '<script type="text/javascript">console.log(\'test\')</script>'
    
    # Test void elements
    img = PyxieXML("img", src="test.jpg", alt="Test")
    assert str(img) == '<img src="test.jpg" alt="Test">'
    
    # Test boolean attributes
    checkbox = PyxieXML("input", type="checkbox", checked=True, disabled=False)
    assert str(checkbox) == '<input type="checkbox" checked>'
    
    # Test nested children
    div = PyxieXML("div", "Parent", 
                   PyxieXML("span", "Child 1"),
                   PyxieXML("span", "Child 2"))
    assert "Parent" in str(div)
    assert "Child 1" in str(div)
    assert "Child 2" in str(div)

def test_fasthtml_executor_context():
    """Test FastHTMLExecutor context management."""
    from pyxie.fasthtml import FastHTMLExecutor
    
    # Test context manager
    with FastHTMLExecutor() as executor:
        assert executor.namespace is not None
        results = executor.execute("show('test')")
        assert results == ['test']
    assert executor.namespace is None
    
    # Test without context manager
    executor = FastHTMLExecutor()
    assert executor.namespace is None
    results = executor.execute("show('test')")
    assert results == ['test']
    assert executor.namespace is not None

def test_fasthtml_renderer_edge_cases():
    """Test FastHTMLRenderer edge cases."""
    from pyxie.fasthtml import FastHTMLRenderer
    
    # Test empty results
    assert FastHTMLRenderer.to_xml([]) == ""
    
    # Test None values
    assert FastHTMLRenderer.to_xml([None]) == ""
    
    # Test mixed content types
    from fastcore.xml import FT
    class Div(FT): 
        def __init__(self, children=None):
            children = children or []
            super().__init__("div", tuple(children))
    
    mixed = [
        "text",
        42,
        True,
        Div(children=["child"]),
        ["nested", "list"],
        None
    ]
    result = FastHTMLRenderer.to_xml(mixed)
    assert "text" in result
    assert "42" in result
    assert "True" in result
    assert "<div>child</div>" in result
    assert "nested list" in result

def test_execute_fasthtml_error_handling():
    """Test error handling in execute_fasthtml."""
    from pyxie.fasthtml import execute_fasthtml
    
    # Test empty content
    result = execute_fasthtml("")
    assert result.content == ""
    assert result.error is None
    
    # Test syntax error
    result = execute_fasthtml("invalid python code :")
    assert result.error is not None
    assert "invalid syntax" in result.error.lower()
    
    # Test runtime error
    result = execute_fasthtml("1/0")
    assert result.error is not None
    assert "division by zero" in result.error.lower()
    
    # Test import error
    result = execute_fasthtml("from nonexistent_module import something")
    assert result.error is not None
    assert "no module named" in result.error.lower()

