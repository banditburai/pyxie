"""Tests for FastHTML core functionality."""

import pytest
from textwrap import dedent
from fastcore.xml import FT, XML, Div
from pyxie.fasthtml import render_fasthtml, FastHTMLRenderer, FastHTMLExecutor, PyxieXML

def test_simple_div():
    """Test rendering a simple div."""
    result = render_fasthtml('show(Div("Hello World"))')
    assert result.content == '<div>Hello World</div>'
    assert not result.error

def test_div_with_class():
    """Test rendering a div with a class attribute."""
    result = render_fasthtml('show(Div("Hello World", cls="test-class"))')
    assert result.content == '<div class="test-class">Hello World</div>'
    assert not result.error

def test_nested_components():
    """Test rendering nested components."""
    code = dedent("""
    outer = Div(
        Div("Inner content", cls="inner"),
        cls="outer"
    )
    show(outer)
    """)
    result = render_fasthtml(code)
    assert '<div class="outer">' in result.content
    assert '<div class="inner">Inner content</div>' in result.content
    assert not result.error

def test_component_function():
    """Test rendering a component function."""
    code = dedent("""
    def MyComponent(text):
        return Div(text, cls="custom")
    
    show(MyComponent("Hello from function"))
    """)
    result = render_fasthtml(code)
    assert result.content == '<div class="custom">Hello from function</div>'
    assert not result.error

def test_multiple_components():
    """Test rendering multiple components."""
    code = dedent("""
    show(Div("First"))
    show(Div("Second", cls="second"))
    """)
    result = render_fasthtml(code)
    assert '<div>First</div>' in result.content
    assert '<div class="second">Second</div>' in result.content
    assert not result.error

def test_error_handling():
    """Test error handling in FastHTML rendering."""
    result = render_fasthtml('show(undefined_variable)')
    assert result.error is not None
    assert 'undefined_variable' in result.error

def test_xml_object_rendering():
    """Test direct rendering of XML objects."""
    xml = PyxieXML('div', 'Test content', cls='test')
    result = FastHTMLRenderer._render_component(xml)
    assert result == '<div class="test">Test content</div>'

def test_empty_content():
    """Test rendering empty content."""
    result = render_fasthtml('')
    assert result.content == ''
    assert not result.error

def test_namespace_setup():
    """Test that the namespace is set up correctly."""
    with FastHTMLExecutor() as executor:
        namespace = executor.namespace
        assert 'Div' in namespace
        assert 'show' in namespace
        assert callable(namespace['show'])
        
        # Test that a basic component works
        code = 'show(Div("Test"))'
        results = executor.execute(code)
        assert len(results) == 1
        assert isinstance(results[0], FT) 