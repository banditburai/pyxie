"""Debug script for testing custom blocks and slot filling."""

from pyxie.parser import FastHTMLToken, ScriptToken, NestedContentToken
from pyxie.renderer import render_content
from pyxie.types import ContentItem
from pyxie.layouts import layout
from mistletoe.block_token import add_token
from fastcore.xml import Div, H1

def debug_custom_blocks():
    """Debug custom blocks rendering."""
    print("\n=== Testing Custom Blocks ===\n")
    
    # Register tokens
    add_token(FastHTMLToken)
    add_token(ScriptToken)
    add_token(NestedContentToken)
    
    # Test 1: Simple custom block
    print("Test 1: Simple custom block")
    content1 = """<content>
# Header
**Bold** and *italic*
</content>"""
    
    item1 = ContentItem(
        source_path="test.md",
        metadata={},
        content=content1
    )
    
    print("\nInput:")
    print(content1)
    print("\nOutput:")
    print(render_content(item1))
    
    # Test 2: Multiple custom blocks
    print("\nTest 2: Multiple custom blocks")
    content2 = """<header>
# Welcome
</header>

<sidebar>
- Item 1
- Item 2
</sidebar>"""
    
    item2 = ContentItem(
        source_path="test.md",
        metadata={},
        content=content2
    )
    
    print("\nInput:")
    print(content2)
    print("\nOutput:")
    print(render_content(item2))
    
    # Test 3: Custom blocks with layout
    print("\nTest 3: Custom blocks with layout")
    
    @layout("test")
    def test_layout():
        return Div(
            Div(None, data_slot="header", cls="header"),
            Div(None, data_slot="sidebar", cls="sidebar"),
            cls="layout"
        )
    
    content3 = """<header>
# Welcome
</header>

<sidebar>
- Item 1
- Item 2
</sidebar>"""
    
    item3 = ContentItem(
        source_path="test.md",
        metadata={"layout": "test"},
        content=content3
    )
    
    print("\nInput:")
    print(content3)
    print("\nOutput:")
    print(render_content(item3))

if __name__ == "__main__":
    debug_custom_blocks() 