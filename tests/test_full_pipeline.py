"""Test the full rendering pipeline."""

import pytest
from src.pyxie.types import ContentItem
from src.pyxie.renderer import render_content
from src.pyxie.layouts import layout
from src.pyxie.parser import custom_tokenize_block, FastHTMLToken, ScriptToken, NestedContentToken
from mistletoe import Document
from fastcore.xml import Div
from textwrap import dedent

# Test layout
@layout("test")
def _test_page_layout(metadata):
    """Test layout using regular HTML."""
    title = metadata.get('title', 'Untitled Page')
    return Div(
        Div(
            Div(
                Div(title, cls="title"),
                Div(None, data_slot="content"),
                cls="content"
            ),
            cls="content"
        ),
        cls="test-layout"
    )

def test_full_pipeline():
    """Test the full rendering pipeline."""
    # Test content with nested markdown - using dedent to handle indentation
    content = dedent("""
        # Welcome to Pyxie

        This is a test of the full pipeline.

        <custom>
        This is a custom block with **bold** and *italic* text.

        <nested>
        This is a nested block with a [link](https://example.com).
        </nested>
        </custom>

        <fasthtml>
        show(Div('Hello, World!', cls='greeting'))
        </fasthtml>

        <script>
        console.log("Test script");
        </script>
    """).strip()
    
    # Create a content item
    item = ContentItem(
        content=content,
        source_path="test_page.md",
        metadata={
            "title": "Test Page",
            "layout": "test"
        }
    )
    
    # Debug tokenization
    print("\nDEBUG: Tokenization:")
    doc = Document('')
    doc.children = list(custom_tokenize_block(item.content, [FastHTMLToken, ScriptToken, NestedContentToken]))
    for token in doc.children:
        print(f"\nToken type: {type(token).__name__}")
        if isinstance(token, NestedContentToken):
            print(f"Tag name: {token.tag_name}")
            print("Content:")
            print(token.content)
            print("Children:")
            for child in token.children:
                print(f"  Child type: {type(child).__name__}")
                if isinstance(child, NestedContentToken):
                    print(f"  Child tag: {child.tag_name}")
                    print("  Child content:")
                    print(child.content)
    
    # Render the content
    result = render_content(item)
    print("\nDEBUG: Rendered HTML:")
    print(result)
    print("\nDEBUG: Looking for these tags:")
    print("<custom>")
    print("<nested>")
    
    # Basic assertions
    assert '<div class="title">Test Page</div>' in result
    assert "Welcome to Pyxie" in result
    assert "This is a test of the full pipeline" in result
    
    # Check custom block rendering - tags should be preserved
    assert "<custom>" in result
    assert "<nested>" in result
    assert "<strong>bold</strong>" in result
    assert "<em>italic</em>" in result
    assert '<a href="https://example.com">link</a>' in result
    
    # Check FastHTML block
    assert '<div class="greeting">Hello, World!</div>' in result
    
    # Check script block
    assert '<script>' in result
    assert 'console.log("Test script");' in result
    
    # Check layout structure
    assert '<div class="test-layout"' in result
    assert '<div class="content"' in result 