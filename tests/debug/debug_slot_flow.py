"""Debug script to trace slot processing flow."""

import os
import sys
import logging
from typing import Dict, List, Any
from lxml import html
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.pyxie.slots import (
    process_layout,
    extract_slots,
    fill_slots,
    process_conditionals,
    SLOT_ATTR,
    CONDITION_ATTR
)

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def debug_slot_flow():
    """Debug the slot processing flow with a simple test case."""
    # Test layout with multiple slots
    layout = """
    <div class="container">
        <div data-slot="page_header">
            <h1>Default Header</h1>
        </div>
        <div data-slot="main_content" class="prose">
            <p>Default content</p>
        </div>
        <div data-slot="page_footer">
            <p>Default footer</p>
        </div>
    </div>
    """
    
    # Test rendered HTML with slot content
    rendered_html = """
    <div data-slot="page_header">
        <h1>Custom Header</h1>
    </div>
    <div data-slot="main_content" class="prose">
        <div class="custom-content">
            <h2>Section 1</h2>
            <p>This is custom content</p>
        </div>
    </div>
    <div data-slot="page_footer">
        <p>Custom footer</p>
    </div>
    """
    
    print("\n=== Input Data ===")
    print("Layout:")
    print(layout)
    print("\nRendered HTML:")
    print(rendered_html)
    
    # Debug extract_slots
    print("\n=== extract_slots ===")
    main_content, slots = extract_slots(rendered_html)
    print("Main content:")
    print(main_content)
    print("\nExtracted slots:")
    for name, content in slots.items():
        print(f"\n{name}:")
        print(f"  {content}")
    
    # Debug process_layout
    print("\n=== process_layout ===")
    result = process_layout(layout, rendered_html, {})
    print("Final result:")
    print(result)
    
    # Debug conditional visibility
    print("\n=== Conditional Visibility ===")
    layout_with_conditions = """
    <div class="container">
        <div data-slot="page_header" data-pyxie-show="page_header">
            <h1>Default Header</h1>
        </div>
        <div data-slot="main_content" class="prose">
            <p>Default content</p>
        </div>
        <div data-slot="page_footer" data-pyxie-show="page_footer">
            <p>Default footer</p>
        </div>
    </div>
    """
    
    test_cases = [
        # Both slots filled
        """
        <div data-slot="page_header">
            <h1>Custom Header</h1>
        </div>
        <div data-slot="page_footer">
            <p>Custom footer</p>
        </div>
        """,
        # Only header slot filled
        """
        <div data-slot="page_header">
            <h1>Custom Header</h1>
        </div>
        """,
        # Only footer slot filled
        """
        <div data-slot="page_footer">
            <p>Custom footer</p>
        </div>
        """,
        # No slots filled
        ""
    ]
    
    print("\nTesting conditional visibility:")
    for rendered_content in test_cases:
        print(f"\nRendered content:")
        print(rendered_content)
        result = process_layout(layout_with_conditions, rendered_content, {})
        print("Result:")
        print(result)

if __name__ == "__main__":
    debug_slot_flow() 