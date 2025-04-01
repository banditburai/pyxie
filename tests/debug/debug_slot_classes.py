"""Debug script for testing how slot classes are handled."""
import logging
from pyxie.layouts import layout, get_layout
from fastcore.xml import Html, Head, Body, Title, Div, H1, to_xml
from pyxie.slots import process_layout
from lxml import html

# Configure logging
logging.basicConfig(level=logging.DEBUG)

def debug_slot_classes():
    """Test different ways of handling slot classes."""
    print("\n=== Testing Slot Classes ===\n")
    
    # Create a simple layout with classed slots
    layout_html = """
    <div class="container">
        <div data-slot="slot1" class="prose"></div>
        <div data-slot="slot2" class="mt-8"></div>
        <div data-slot="slot3" class="prose dark:prose-invert max-w-none"></div>
    </div>
    """
    print(f"Original layout:\n{layout_html}\n")

    # Test 1: Plain string content
    print("\nTest 1: Plain string content")
    rendered_html1 = """
    <div data-slot="slot1" class="prose">
        This is plain text content
    </div>
    <div data-slot="slot2" class="mt-8">
        More plain text
    </div>
    <div data-slot="slot3" class="prose dark:prose-invert max-w-none">
        Even more plain text
    </div>
    """
    result1 = process_layout(layout_html, rendered_html1, {})
    print(f"Rendered HTML:\n{rendered_html1}\n")
    print(f"Result:\n{result1}\n")
    print(f"Classes preserved? slot1='prose': {'prose' in result1}")
    print(f"Classes preserved? slot2='mt-8': {'mt-8' in result1}")
    print(f"Classes preserved? slot3='prose dark:prose-invert max-w-none': {'prose dark:prose-invert max-w-none' in result1}")

    # Test 2: HTML string content
    print("\nTest 2: HTML string content")
    rendered_html2 = """
    <div data-slot="slot1" class="prose">
        <p>This is HTML content</p>
    </div>
    <div data-slot="slot2" class="mt-8">
        <div>More HTML content</div>
    </div>
    <div data-slot="slot3" class="prose dark:prose-invert max-w-none">
        <span>Even more HTML content</span>
    </div>
    """
    result2 = process_layout(layout_html, rendered_html2, {})
    print(f"Rendered HTML:\n{rendered_html2}\n")
    print(f"Result:\n{result2}\n")
    print(f"Classes preserved? slot1='prose': {'prose' in result2}")
    print(f"Classes preserved? slot2='mt-8': {'mt-8' in result2}")
    print(f"Classes preserved? slot3='prose dark:prose-invert max-w-none': {'prose dark:prose-invert max-w-none' in result2}")

    # Test 3: Pre-wrapped HTML with classes
    print("\nTest 3: Pre-wrapped HTML with classes")
    rendered_html3 = """
    <div data-slot="slot1" class="prose">
        <div class="prose">Pre-wrapped content</div>
    </div>
    <div data-slot="slot2" class="mt-8">
        <div class="mt-8">More pre-wrapped content</div>
    </div>
    <div data-slot="slot3" class="prose dark:prose-invert max-w-none">
        <div class="prose dark:prose-invert max-w-none">Even more pre-wrapped content</div>
    </div>
    """
    result3 = process_layout(layout_html, rendered_html3, {})
    print(f"Rendered HTML:\n{rendered_html3}\n")
    print(f"Result:\n{result3}\n")
    print(f"Classes preserved? slot1='prose': {'prose' in result3}")
    print(f"Classes preserved? slot2='mt-8': {'mt-8' in result3}")
    print(f"Classes preserved? slot3='prose dark:prose-invert max-w-none': {'prose dark:prose-invert max-w-none' in result3}")

if __name__ == "__main__":
    debug_slot_classes() 