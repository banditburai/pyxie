"""Test the render_content function and its interaction with process_layout."""

import pytest
from pathlib import Path
from src.pyxie.types import ContentItem
from src.pyxie.renderer import render_content
from src.pyxie.layouts import layout
from fastcore.xml import Div, H1, to_xml
from src.pyxie.slots import extract_slots
from src.pyxie.layouts import LayoutResult

# Test layout
@layout("test")
def create_test_layout(metadata):
    """Test layout using regular HTML."""
    title = metadata.get('title', 'Untitled Page')
    return Div(
        Div(
            Div(
                Div(title, cls="title"),
                # Header is shown if show_header is true in frontmatter
                Div(None, data_slot="page_header", data_pyxie_show="show_header"),
                # Nav slot - shown if filled, removed if empty
                Div(None, data_slot="page_nav"),
                # Content is always shown
                Div(None, data_slot="main_content"),
                # Footer is shown if show_footer is true in frontmatter
                Div(None, data_slot="page_footer", data_pyxie_show="show_footer"),
                cls="content"
            ),
            cls="content"
        ),
        cls="test-layout"
    )

@pytest.fixture
def default_layout():
    """Create a default layout for testing."""
    @layout("default")
    def create_default_layout(metadata=None):
        return Div(
            Div(None, data_slot="main_content"),
            cls="default-layout"
        )
    return create_default_layout

def test_basic_content_rendering(default_layout):
    """Test basic content rendering without layout."""
    content = """
<main_content>
# Welcome
This is a test with **bold** and *italic*.
</main_content>
"""
    item = ContentItem(
        source_path=Path("test.md"),
        metadata={},
        content=content
    )
    
    result = render_content(item)
    assert "<h1 id=\"welcome\">Welcome</h1>" in result
    assert "<strong>bold</strong>" in result
    assert "<em>italic</em>" in result

def test_content_with_layout():
    """Test content rendering with a layout."""
    content = """
<main_content>
# Welcome
This is a test with **bold** and *italic*.
</main_content>
"""
    item = ContentItem(
        source_path=Path("test.md"),
        metadata={
            "layout": "test",
            "title": "Test Page"
        },
        content=content
    )
    
    result = render_content(item)
    assert "test-layout" in result
    assert "Test Page" in result
    assert "<h1 id=\"welcome\">Welcome</h1>" in result
    assert "<strong>bold</strong>" in result
    assert "<em>italic</em>" in result

def test_content_with_slots():
    """Test content rendering with multiple slots."""
    content = """
<page_header>
# Site Header
</page_header>

<page_nav>
- [Home](#)
- [About](#)
- [Contact](#)
</page_nav>

<main_content>
# Main Content
This is the main content area.
</main_content>

<page_footer>
© 2024 Test Site
</page_footer>
"""
    item = ContentItem(
        source_path=Path("test.md"),
        metadata={
            "layout": "test",
            "title": "Test Page",
            "show_header": True,
            "show_footer": True
        },
        content=content
    )
    
    result = render_content(item)
    assert "test-layout" in result
    assert "Test Page" in result
    assert "<h1 id=\"site-header\">Site Header</h1>" in result
    assert "<a href=\"#\">Home</a>" in result
    assert "<h1 id=\"main-content\">Main Content</h1>" in result
    assert "© 2024 Test Site" in result

def test_content_with_conditional_visibility():
    """Test content rendering with conditional visibility."""
    content = """
<page_header>
# Site Header
</page_header>

<page_nav>
- [Home](#)
- [About](#)
- [Contact](#)
</page_nav>

<main_content>
# Main Content
This is the main content area.
</main_content>

<page_footer>
© 2024 Test Site
</page_footer>
"""
    # Test with show_header=True and show_footer=False
    item = ContentItem(
        source_path=Path("test.md"),
        metadata={
            "layout": "test",
            "title": "Test Page",
            "show_header": True,
            "show_footer": False
        },
        content=content
    )
    
    result = render_content(item)
    # Header should be shown because show_header=True
    assert "<h1 id=\"site-header\">Site Header</h1>" in result
    # Nav should be shown because it has content
    assert "<a href=\"#\">Home</a>" in result
    # Content should always be shown
    assert "<h1 id=\"main-content\">Main Content</h1>" in result
    # Footer should be hidden because show_footer=False
    assert "© 2024 Test Site" not in result

def test_content_with_raw_blocks():
    """Test content rendering with raw blocks."""
    content = """
<main_content>
<script>
console.log("Hello");
</script>

<pre>
def hello():
    print("Hello")
</pre>

<fasthtml>
show(Div("Hello World"))
</fasthtml>
</main_content>
"""
    item = ContentItem(
        source_path=Path("test.md"),
        metadata={
            "layout": "test",
            "title": "Test Page"
        },
        content=content
    )
    
    result = render_content(item)
    assert 'console.log("Hello");' in result
    assert 'def hello():' in result
    assert 'print("Hello")' in result
    assert 'Hello World' in result

def test_content_with_nested_blocks():
    """Test content rendering with nested blocks."""
    content = """
<main_content>
<outer>
<inner>
# Inner Heading
Some **bold** text.
</inner>
</outer>
</main_content>
"""
    item = ContentItem(
        source_path=Path("test.md"),
        metadata={
            "layout": "test",
            "title": "Test Page"
        },
        content=content
    )
    
    result = render_content(item)
    assert 'data-slot="outer"' in result
    assert "<h1 id=\"inner-heading\">Inner Heading</h1>" in result
    assert "<strong>bold</strong>" in result

def test_content_with_attributes():
    """Test content rendering with HTML attributes."""
    content = """
<main_content>
<custom-block class="test" data-id="123">
# Heading
Content with **bold** text.
</custom-block>
</main_content>
"""
    item = ContentItem(
        source_path=Path("test.md"),
        metadata={
            "layout": "test",
            "title": "Test Page"
        },
        content=content
    )
    
    result = render_content(item)
    assert 'class="test"' in result
    assert 'data-id="123"' in result
    assert "<h1 id=\"heading\">Heading</h1>" in result
    assert "<strong>bold</strong>" in result

def test_content_with_void_elements():
    """Test content rendering with void elements."""
    content = """
<main_content>
<img src="test.jpg" alt="Test" />
<hr />
</main_content>
"""
    item = ContentItem(
        source_path=Path("test.md"),
        metadata={
            "layout": "test",
            "title": "Test Page"
        },
        content=content
    )
    
    result = render_content(item)
    assert 'src="test.jpg"' in result
    assert '<hr>' in result or '<hr />' in result

def test_content_with_pyxie_urls():
    """Test content rendering with pyxie: URLs."""
    content = """
<main_content>
![Test](pyxie:nature/800/600)
![Another](test.jpg)
</main_content>
"""
    item = ContentItem(
        source_path=Path("test.md"),
        metadata={
            "layout": "test",
            "title": "Test Page"
        },
        content=content
    )
    
    result = render_content(item)
    assert 'src="https://picsum.photos/seed/nature/800/600"' in result
    assert 'src="test.jpg"' in result

def test_debug_rendered_fragment():
    """Debug test to verify the content of rendered_fragment before slot processing."""
    # Create a test content item with known content
    content = """
# Welcome
<page_header>Site Header</page_header>
<main_content>Main Content</main_content>
<page_footer>Site Footer</page_footer>
"""
    item = ContentItem(
        content=content,
        metadata={},
        source_path="test.md"
    )
    
    # Create a simple test layout
    layout_html = """
    <div>
        <div data-slot="page_header"></div>
        <div data-slot="main_content"></div>
        <div data-slot="page_footer"></div>
    </div>
    """
    
    # Get the rendered fragment directly from render_content
    from src.pyxie.renderer import render_content
    from src.pyxie.slots import extract_slots
    from src.pyxie.layouts import LayoutResult
    
    # Mock the layout handler to return our test layout
    from unittest.mock import patch
    with patch('src.pyxie.renderer.handle_cache_and_layout') as mock_layout:
        mock_layout.return_value = LayoutResult(html=layout_html)
        
        # Render the content
        rendered_html = render_content(item)
        
        # Extract slots to see what we got
        main_content, slots = extract_slots(rendered_html)
        
        # Print debug information
        print("\n=== Debug Output ===")
        print("\nRendered HTML:")
        print(rendered_html)
        print("\nMain Content:")
        print(main_content)
        print("\nSlots:")
        for slot_name, slot_content in slots.items():
            print(f"\nSlot '{slot_name}':")
            print(slot_content)
        
        # Basic assertions to verify structure
        # The h1 should NOT be in the rendered HTML since it's not in a slot
        assert "<h1 id=\"welcome\">Welcome</h1>" not in rendered_html, "Heading found in rendered HTML but should not be since it's not in a slot"
        assert "<p>Site Header</p>" in rendered_html, "Header not found in rendered HTML"
        assert "<p>Main Content</p>" in rendered_html, "Main content not found in rendered HTML"
        assert "<p>Site Footer</p>" in rendered_html, "Footer not found in rendered HTML"

def test_slot_extraction():
    """Test slot extraction from rendered content."""
    rendered_html = """
    <div data-slot="page_header">Header Content</div>
    <div data-slot="page_nav">Nav Content</div>
    <div>Main Content</div>
    <div data-slot="page_footer">Footer Content</div>
    """
    main_content, slots = extract_slots(rendered_html) 