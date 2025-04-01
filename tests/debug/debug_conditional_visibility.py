"""Debug script for conditional visibility issues."""

from lxml import html
from pyxie.slots import process_layout, CONDITION_ATTR, SLOT_ATTR, extract_slots, _check_visibility_condition

def debug_conditional_visibility():
    """Debug conditional visibility behavior."""
    # Test case 1: Only title present
    print("\n=== Test Case 1: Only Title Present ===")
    layout = """
    <div class="container">
        <div data-slot="page_title" data-pyxie-show="page_title">Title Section</div>
        <div data-slot="main_content">Main Content</div>
        <div data-slot="side_content" data-pyxie-show="!main_content">Side Content</div>
        <div data-slot="optional_content" data-pyxie-show="main_content">Optional Content</div>
    </div>
    """
    rendered = '<div data-slot="page_title">Test Title</div>'
    
    # Debug slot extraction
    main_content, slots = extract_slots(rendered)
    print("\nExtracted slots:")
    print(f"Main content: {main_content}")
    print(f"Slots: {slots}")
    
    # Debug condition evaluation
    print("\nCondition evaluation:")
    print(f"page_title: {_check_visibility_condition('page_title', slots)}")
    print(f"!main_content: {_check_visibility_condition('!main_content', slots)}")
    print(f"main_content: {_check_visibility_condition('main_content', slots)}")
    
    result = process_layout(layout, rendered, {})
    print("\nResult:")
    print(result)
    
    # Parse result to check structure
    dom = html.fromstring(result)
    print("\nElements in result:")
    for element in dom.xpath('//*'):
        print(f"- {element.tag}: {element.text}")
        if element.attrib:
            print(f"  Attributes: {element.attrib}")
    
    # Test case 2: Main content present
    print("\n=== Test Case 2: Main Content Present ===")
    rendered = '<div data-slot="main_content">Main Content</div>'
    
    # Debug slot extraction
    main_content, slots = extract_slots(rendered)
    print("\nExtracted slots:")
    print(f"Main content: {main_content}")
    print(f"Slots: {slots}")
    
    # Debug condition evaluation
    print("\nCondition evaluation:")
    print(f"page_title: {_check_visibility_condition('page_title', slots)}")
    print(f"!main_content: {_check_visibility_condition('!main_content', slots)}")
    print(f"main_content: {_check_visibility_condition('main_content', slots)}")
    
    result = process_layout(layout, rendered, {})
    print("\nResult:")
    print(result)
    
    # Parse result to check structure
    dom = html.fromstring(result)
    print("\nElements in result:")
    for element in dom.xpath('//*'):
        print(f"- {element.tag}: {element.text}")
        if element.attrib:
            print(f"  Attributes: {element.attrib}")

    # Test case 3: Test original content preservation
    print("\n=== Test Case 3: Original Content Preservation ===")
    layout = """
    <div class="container">
        <div data-pyxie-show="page_title">
            <h1>Original Title</h1>
            <div data-slot="page_title"></div>
        </div>
        <div data-pyxie-show="!main_content">
            <h2>Original Side Content</h2>
            <div data-slot="side_content"></div>
        </div>
    </div>
    """
    rendered = '<div data-slot="page_title">Test Title</div>'
    
    # Debug slot extraction
    main_content, slots = extract_slots(rendered)
    print("\nExtracted slots:")
    print(f"Main content: {main_content}")
    print(f"Slots: {slots}")
    
    # Debug condition evaluation
    print("\nCondition evaluation:")
    print(f"page_title: {_check_visibility_condition('page_title', slots)}")
    print(f"!main_content: {_check_visibility_condition('!main_content', slots)}")
    
    result = process_layout(layout, rendered, {})
    print("\nResult:")
    print(result)
    
    # Parse result to check structure
    dom = html.fromstring(result)
    print("\nElements in result:")
    for element in dom.xpath('//*'):
        print(f"- {element.tag}: {element.text}")
        if element.attrib:
            print(f"  Attributes: {element.attrib}")

    # Test case 4: Test conditional visibility with nested slots
    print("\n=== Test Case 4: Conditional Visibility with Nested Slots ===")
    layout = """
    <div class="container">
        <div data-pyxie-show="page_title">
            <h1>Original Title</h1>
            <div data-slot="page_title"></div>
        </div>
        <div data-pyxie-show="!main_content">
            <h2>Original Side Content</h2>
            <div data-slot="side_content">Default Side Content</div>
        </div>
        <div data-pyxie-show="main_content">
            <h2>Main Section</h2>
            <div data-slot="main_content">Default Main Content</div>
            <div data-slot="optional_content">Default Optional Content</div>
        </div>
    </div>
    """
    rendered = """
    <div data-slot="page_title">Test Title</div>
    <div data-slot="main_content">Test Main Content</div>
    """
    
    # Debug slot extraction
    main_content, slots = extract_slots(rendered)
    print("\nExtracted slots:")
    print(f"Main content: {main_content}")
    print(f"Slots: {slots}")
    
    # Debug condition evaluation
    print("\nCondition evaluation:")
    print(f"page_title: {_check_visibility_condition('page_title', slots)}")
    print(f"!main_content: {_check_visibility_condition('!main_content', slots)}")
    print(f"main_content: {_check_visibility_condition('main_content', slots)}")
    
    result = process_layout(layout, rendered, {})
    print("\nResult:")
    print(result)
    
    # Parse result to check structure
    dom = html.fromstring(result)
    print("\nElements in result:")
    for element in dom.xpath('//*'):
        print(f"- {element.tag}: {element.text}")
        if element.attrib:
            print(f"  Attributes: {element.attrib}")

if __name__ == "__main__":
    debug_conditional_visibility() 