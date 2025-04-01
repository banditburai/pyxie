"""Debug script for testing slot filling functionality."""
import logging
from pyxie.layouts import layout, get_layout
from fastcore.xml import Html, Head, Body, Title, Div, H1, to_xml
from pyxie.slots import process_layout
from lxml import html

# Configure logging
logging.basicConfig(level=logging.DEBUG)

def debug_slot_filling():
    """Test different slot filling scenarios."""
    print("\n=== Testing Slot Filling ===\n")
    
    # Test 1: Simple slot filling
    print("\nTest 1: Simple slot filling")
    layout_html = """
    <div class="container">
        <div data-slot="header">Default header</div>
        <div data-slot="content">Default content</div>
        <div data-slot="footer">Default footer</div>
    </div>
    """
    rendered_html = """
    <div data-slot="header">
        <h1>Custom Header</h1>
    </div>
    <div data-slot="content">
        <p>Custom content goes here</p>
    </div>
    <div data-slot="footer">
        <p>Custom footer text</p>
    </div>
    """
    result1 = process_layout(layout_html, rendered_html, {})
    print(f"Layout:\n{layout_html}\n")
    print(f"Rendered HTML:\n{rendered_html}\n")
    print(f"Result:\n{result1}\n")

    # Test 2: HTML content in slots
    print("\nTest 2: HTML content in slots")
    layout_html2 = """
    <div class="container">
        <div data-slot="main" class="prose">
            <p>Default main content</p>
        </div>
        <div data-slot="sidebar" class="bg-gray-100">
            <p>Default sidebar content</p>
        </div>
    </div>
    """
    rendered_html2 = """
    <div data-slot="main" class="prose">
        <h2>Main Content</h2>
        <p>This is the main content area with some HTML.</p>
        <ul>
            <li>Item 1</li>
            <li>Item 2</li>
        </ul>
    </div>
    <div data-slot="sidebar" class="bg-gray-100">
        <h3>Sidebar</h3>
        <p>This is the sidebar content with some HTML.</p>
        <div class="widget">
            <h4>Widget Title</h4>
            <p>Widget content</p>
        </div>
    </div>
    """
    result2 = process_layout(layout_html2, rendered_html2, {})
    print(f"Layout:\n{layout_html2}\n")
    print(f"Rendered HTML:\n{rendered_html2}\n")
    print(f"Result:\n{result2}\n")

    # Test 3: Default slot handling
    print("\nTest 3: Default slot handling")
    layout_html3 = """
    <div class="container">
        <div data-slot="main">
            <p>Default main content</p>
        </div>
    </div>
    """
    rendered_html3 = """
    <p>This is content without a slot.</p>
    <p>It should go into the default slot.</p>
    """
    result3 = process_layout(layout_html3, rendered_html3, {})
    print(f"Layout:\n{layout_html3}\n")
    print(f"Rendered HTML:\n{rendered_html3}\n")
    print(f"Result:\n{result3}\n")

if __name__ == "__main__":
    debug_slot_filling() 