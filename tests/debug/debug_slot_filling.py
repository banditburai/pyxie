"""Debug script for testing slot filling in isolation."""

from pyxie.slots import fill_slots
from fastcore.xml import Div, H1, P, FT

def debug_slot_filling():
    """Debug slot filling functionality."""
    print("\n=== Testing Slot Filling ===\n")
    
    # Test 1: Simple slot filling
    print("Test 1: Simple slot filling")
    layout1 = Div(
        H1(None, data_slot="title"),
        P(None, data_slot="content")
    )
    
    slots1 = {
        "title": "Welcome",
        "content": "This is the content"
    }
    
    print("\nLayout:")
    print(layout1)
    print("\nSlots:")
    print(slots1)
    print("\nOutput:")
    result = fill_slots(layout1, slots1)
    print(result.element)
    
    # Test 2: HTML content in slots
    print("\nTest 2: HTML content in slots")
    layout2 = Div(
        Div(None, data_slot="header", cls="header"),
        Div(None, data_slot="content", cls="content")
    )
    
    slots2 = {
        "header": "<h1>Welcome</h1><p>Subtitle</p>",
        "content": """
        <h2>Section 1</h2>
        <p>Content here</p>
        <ul>
            <li>Item 1</li>
            <li>Item 2</li>
        </ul>
        """
    }
    
    print("\nLayout:")
    print(layout2)
    print("\nSlots:")
    print(slots2)
    print("\nOutput:")
    result = fill_slots(layout2, slots2)
    print(result.element)
    
    # Test 3: Nested slots
    print("\nTest 3: Nested slots")
    layout3 = Div(
        Div(
            H1(None, data_slot="title"),
            P(None, data_slot="subtitle"),
            cls="header"
        ),
        Div(
            Div(None, data_slot="content", cls="content"),
            Div(None, data_slot="sidebar", cls="sidebar"),
            cls="main"
        )
    )
    
    slots3 = {
        "title": "Welcome",
        "subtitle": "Subtitle here",
        "content": "<p>Main content</p>",
        "sidebar": "<ul><li>Sidebar item</li></ul>"
    }
    
    print("\nLayout:")
    print(layout3)
    print("\nSlots:")
    print(slots3)
    print("\nOutput:")
    result = fill_slots(layout3, slots3)
    print(result.element)

if __name__ == "__main__":
    debug_slot_filling() 