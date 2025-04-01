"""Debug script for slot content handling scenarios."""

from lxml import html
from pyxie.slots import process_layout, SLOT_ATTR, extract_slots

def debug_slot_content():
    """Debug slot content handling behavior."""
    # Test case 1: Slot not provided in rendered HTML
    print("\n=== Test Case 1: Slot Not Provided ===")
    layout = """
    <div class="container">
        <h1 data-slot="page_title" class="title">Default Title</h1>
        <section data-slot="main_content" class="content">Default Content</section>
        <article data-slot="side_content" class="example"></article>
    </div>
    """
    rendered = ""  # No slots provided
    
    print("\nLayout:")
    print(layout)
    print("\nRendered:")
    print(rendered)
    
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
    
    # Test case 2: Empty slot in rendered HTML
    print("\n=== Test Case 2: Empty Slot Provided ===")
    rendered = """
    <h1 data-slot="page_title"></h1>
    <section data-slot="main_content"></section>
    """
    
    print("\nLayout:")
    print(layout)
    print("\nRendered:")
    print(rendered)
    
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
    
    # Test case 3: Slot with content in rendered HTML
    print("\n=== Test Case 3: Slot With Content ===")
    rendered = """
    <h1 data-slot="page_title">New Title</h1>
    <section data-slot="main_content">New Content</section>
    """
    
    print("\nLayout:")
    print(layout)
    print("\nRendered:")
    print(rendered)
    
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
    debug_slot_content() 