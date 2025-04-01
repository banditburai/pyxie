import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from lxml import etree, html
from src.pyxie.slots import process_layout

def test_case_1():
    """Test case 1: Invalid layout with valid slot content"""
    layout = "not an element"
    slot_html = '<p data-slot="test_content">Test content</p>'
    
    print("\nTest Case 1: Invalid layout with valid slot content")
    print("Layout:", layout)
    print("Slot HTML:", slot_html)
    
    # Try parsing the slot content first
    try:
        slot_content = html.fromstring(slot_html)
        print("\nParsed slot content:", etree.tostring(slot_content, encoding='unicode', method='html'))
    except Exception as e:
        print("Failed to parse slot content:", e)
    
    # Try parsing the layout
    try:
        layout_element = html.fromstring(layout)
        print("\nParsed layout:", etree.tostring(layout_element, encoding='unicode', method='html'))
    except Exception as e:
        print("Failed to parse layout:", e)
    
    # Try the actual process_layout
    result = process_layout(layout, slot_html, {})
    print("\nprocess_layout result:", result)

def test_case_2():
    """Test case 2: Invalid layout with multiple slots"""
    layout = "not an element"
    slot_html = """
    <p data-slot="slot1">Content 1</p>
    <p data-slot="slot2">Content 2</p>
    """
    
    print("\nTest Case 2: Invalid layout with multiple slots")
    print("Layout:", layout)
    print("Slot HTML:", slot_html)
    
    # Try parsing the slot content first
    try:
        slot_content = html.fromstring(slot_html)
        print("\nParsed slot content:", etree.tostring(slot_content, encoding='unicode', method='html'))
    except Exception as e:
        print("Failed to parse slot content:", e)
    
    # Try the actual process_layout
    result = process_layout(layout, slot_html, {})
    print("\nprocess_layout result:", result)

def test_case_3():
    """Test case 3: Invalid layout with invalid slot content"""
    layout = "not an element"
    slot_html = "<p data-slot='test'>Unclosed paragraph<p>"
    
    print("\nTest Case 3: Invalid layout with invalid slot content")
    print("Layout:", layout)
    print("Slot HTML:", slot_html)
    
    # Try parsing the slot content first
    try:
        slot_content = html.fromstring(slot_html)
        print("\nParsed slot content:", etree.tostring(slot_content, encoding='unicode', method='html'))
    except Exception as e:
        print("Failed to parse slot content:", e)
    
    # Try the actual process_layout
    result = process_layout(layout, slot_html, {})
    print("\nprocess_layout result:", result)

if __name__ == "__main__":
    test_case_1()
    test_case_2()
    test_case_3() 