"""Test FastHTML rendering functionality."""

import pytest
from pathlib import Path
from pyxie.types import ContentItem
from pyxie.renderer import render_content
from pyxie.layouts import layout, registry
from fastcore.xml import FT, Div, H1, H2, P
from pyxie.fasthtml import render_fasthtml
import fasthtml.common as ft_common

@pytest.fixture(autouse=True)
def setup_test_layout():
    """Set up test layout for all tests."""
    registry._layouts.clear()
    
    @layout("default")
    def default_layout(content: str = "") -> FT:
        """Default layout that just renders the content directly."""
        return Div(content, data_slot="content")

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
<ft>
show(Div("Hello World", cls="test-class"))
</ft>
"""
    item = create_test_item(content)
    html = render_content(item)
    assert '<div class="test-class">Hello World</div>' in html

def test_nested_components():
    """Test rendering of nested components."""
    content = """
<ft>
component = Div(
    Div("Inner content", cls="inner"),
    cls="outer"
)
show(component)
</ft>
"""
    item = create_test_item(content)
    html = render_content(item)
    assert '<div class="outer">' in html
    assert '<div class="inner">Inner content</div>' in html

def test_component_function():
    """Test rendering of component functions."""
    content = """
<ft>
def MyComponent(text):
    return Div(text, cls="custom")

show(MyComponent("Hello from function"))
</ft>
"""
    item = create_test_item(content)
    html = render_content(item)
    assert '<div class="custom">Hello from function</div>' in html

def test_script_block():
    """Test that script blocks are properly rendered."""
    content = """
<script>
console.log("Hello World");
</script>
"""
    item = create_test_item(content)
    html = render_content(item)
    assert 'console.log("Hello World");' in html
    assert html.strip().startswith('<script>')
    assert html.strip().endswith('</script>')

def test_multiple_blocks():
    """Test that multiple blocks are properly rendered."""
    content = """
<ft>
show(Div('First block'))
</ft>

<script>
console.log('Second block');
</script>

This is markdown content.
"""
    item = create_test_item(content)
    html = render_content(item)
    assert '<div>First block</div>' in html
    assert "console.log('Second block');" in html
    assert '<script>' in html and '</script>' in html
    assert '<p>This is markdown content.</p>' in html

def test_mixed_content():
    """Test rendering of mixed content types."""
    content = """
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
"""
    item = create_test_item(content)
    html = render_content(item)
    assert '<div>FastHTML content</div>' in html
    assert 'console.log("Script content");' in html
    assert '<script>' in html and '</script>' in html
    assert '<p>Regular markdown content.</p>' in html
    assert '<div>More FastHTML content</div>' in html 

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
    
    result = render_fasthtml(content)
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
    result = render_fasthtml(content)
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
    result = render_fasthtml(content)
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
    result = render_fasthtml(content)
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
    result = render_fasthtml(content)
    assert not result.success
    assert "undefined_var" in result.error.lower()
    
    # Test syntax error
    content = "show(Div('Unclosed string)"
    result = render_fasthtml(content)
    assert not result.success
    assert "unterminated string literal" in result.error.lower()
    
    # Test type error
    content = "show(Div(123 + 'string'))"
    result = render_fasthtml(content)
    assert not result.success
    assert "type" in result.error.lower() 

def test_complex_nested_content():
    """Test rendering of complex nested FastHTML content."""
    content = """
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
"""
    item = create_test_item(content)
    html = render_content(item)
    assert '<div class="complex">' in html
    assert '<h1>Main Title</h1>' in html
    assert '<div class="nested">' in html
    assert '<h2>Nested Section</h2>' in html
    assert '<div class="inner">' in html
    assert '<div class="deep">Even deeper</div>' in html
    assert '<div class="footer">Footer</div>' in html

def test_render_block_integration():
    """Test integration between render_content and FastHTML."""
    content = """
<ft>
def TestComponent():
    return Div(
        H1("Test Title"),
        P("Test content"),
        cls="test-component"
    )

show(TestComponent())
</ft>
"""
    item = create_test_item(content)
    html = render_content(item)
    assert '<div class="test-component">' in html
    assert '<h1>Test Title</h1>' in html
    assert '<p>Test content</p>' in html

def test_comprehensive_error_handling():
    """Test comprehensive error handling in FastHTML."""
    # Test syntax error
    content = """def broken_function():
return "This will never execute"
"""
    result = render_fasthtml(content)
    assert not result.success
    assert "expected an indented block" in result.error.lower()
    
    # Test runtime error
    content = """def div_by_zero():
    x = 1/0
    return x
show(div_by_zero())
"""
    result = render_fasthtml(content)
    assert not result.success
    assert "division by zero" in result.error.lower()
    
    # Test undefined component
    content = """show(NonexistentComponent())
"""
    result = render_fasthtml(content)
    assert not result.success
    assert "nonexistentcomponent" in result.error.lower()
    
    # Test invalid show() call
    content = """show(Div("Test"), invalid="param")
"""
    result = render_fasthtml(content)
    assert not result.success
    assert "unexpected keyword argument" in result.error.lower()

