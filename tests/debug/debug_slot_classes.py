"""Debug script for testing how slot classes are handled."""
from pyxie.layouts import layout, get_layout
from fastcore.xml import Html, Head, Body, Title, Div, H1, to_xml
from pyxie.slots import process_slots_and_visibility

def debug_slot_classes():
    """Test different ways of handling slot classes."""
    print("\n=== Testing Slot Classes ===\n")
    
    # Create a simple layout with classed slots
    layout_html = Html(
        Body(
            Div(
                # Test different ways of specifying slots with classes
                Div(None, data_slot="slot1", cls="prose"),
                Div(None, data_slot="slot2", class_="mt-8"),
                Div(None, data_slot="slot3", cls="prose dark:prose-invert max-w-none"),
                cls="container"
            )
        )
    )
    layout_str = to_xml(layout_html)
    print(f"Original layout:\n{layout_str}\n")

    # Test 1: Plain string content
    print("\nTest 1: Plain string content")
    slots1 = {
        "slot1": "This is plain text content",
        "slot2": "More plain text",
        "slot3": "Even more plain text"
    }
    result1 = process_slots_and_visibility(layout_str, slots1)
    print(f"Result with plain text:\n{result1.element}\n")
    print(f"Classes preserved? slot1='prose': {'prose' in result1.element}")
    print(f"Classes preserved? slot2='mt-8': {'mt-8' in result1.element}")
    print(f"Classes preserved? slot3='prose dark:prose-invert max-w-none': {'prose dark:prose-invert max-w-none' in result1.element}")

    # Test 2: HTML string content
    print("\nTest 2: HTML string content")
    slots2 = {
        "slot1": "<p>This is HTML content</p>",
        "slot2": "<div>More HTML content</div>",
        "slot3": "<span>Even more HTML content</span>"
    }
    result2 = process_slots_and_visibility(layout_str, slots2)
    print(f"Result with HTML strings:\n{result2.element}\n")
    print(f"Classes preserved? slot1='prose': {'prose' in result2.element}")
    print(f"Classes preserved? slot2='mt-8': {'mt-8' in result2.element}")
    print(f"Classes preserved? slot3='prose dark:prose-invert max-w-none': {'prose dark:prose-invert max-w-none' in result2.element}")

    # Test 3: List of strings
    print("\nTest 3: List of strings")
    slots3 = {
        "slot1": ["This is content in a list"],
        "slot2": ["More content in a list"],
        "slot3": ["Even more content in a list"]
    }
    result3 = process_slots_and_visibility(layout_str, slots3)
    print(f"Result with string lists:\n{result3.element}\n")
    print(f"Classes preserved? slot1='prose': {'prose' in result3.element}")
    print(f"Classes preserved? slot2='mt-8': {'mt-8' in result3.element}")
    print(f"Classes preserved? slot3='prose dark:prose-invert max-w-none': {'prose dark:prose-invert max-w-none' in result3.element}")

    # Test 4: Pre-wrapped HTML with classes
    print("\nTest 4: Pre-wrapped HTML with classes")
    slots4 = {
        "slot1": [f'<div class="prose">Pre-wrapped content</div>'],
        "slot2": [f'<div class="mt-8">More pre-wrapped content</div>'],
        "slot3": [f'<div class="prose dark:prose-invert max-w-none">Even more pre-wrapped content</div>']
    }
    result4 = process_slots_and_visibility(layout_str, slots4)
    print(f"Result with pre-wrapped HTML:\n{result4.element}\n")
    print(f"Classes preserved? slot1='prose': {'prose' in result4.element}")
    print(f"Classes preserved? slot2='mt-8': {'mt-8' in result4.element}")
    print(f"Classes preserved? slot3='prose dark:prose-invert max-w-none': {'prose dark:prose-invert max-w-none' in result4.element}")

if __name__ == "__main__":
    debug_slot_classes() 