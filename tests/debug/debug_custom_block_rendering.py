"""Debug script for testing custom block rendering in isolation."""

from pyxie.parser import FastHTMLToken, ScriptToken, NestedContentToken, custom_tokenize_block
from pyxie.renderer import NestedRenderer
from mistletoe import Document
from mistletoe.block_token import add_token

def debug_custom_block_rendering():
    """Debug custom block rendering."""
    print("\n=== Testing Custom Block Rendering ===\n")
    
    # Register tokens
    add_token(FastHTMLToken)
    add_token(ScriptToken)
    add_token(NestedContentToken)
    
    # Create renderer
    renderer = NestedRenderer()
    
    # Test 1: Simple custom block
    print("Test 1: Simple custom block")
    content1 = """<custom-content>
# Header
**Bold** and *italic*
</custom-content>"""
    
    print("\nInput:")
    print(content1)
    print("\nRendered output:")
    doc = Document('')
    doc.children = list(custom_tokenize_block(content1, [FastHTMLToken, ScriptToken, NestedContentToken]))
    print(renderer.render(doc))
    
    # Test 2: Multiple custom blocks
    print("\nTest 2: Multiple custom blocks")
    content2 = """<page-header>
# Welcome
</page-header>

<page-sidebar>
- Item 1
- Item 2
</page-sidebar>"""
    
    print("\nInput:")
    print(content2)
    print("\nRendered output:")
    doc = Document('')
    doc.children = list(custom_tokenize_block(content2, [FastHTMLToken, ScriptToken, NestedContentToken]))
    print(renderer.render(doc))
    
    # Test 3: Nested custom blocks
    print("\nTest 3: Nested custom blocks")
    content3 = """<custom-content>
<page-header>
# Welcome
</page-header>

<page-sidebar>
- Item 1
- Item 2
</page-sidebar>
</custom-content>"""
    
    print("\nInput:")
    print(content3)
    print("\nRendered output:")
    doc = Document('')
    doc.children = list(custom_tokenize_block(content3, [FastHTMLToken, ScriptToken, NestedContentToken]))
    print(renderer.render(doc))

if __name__ == "__main__":
    debug_custom_block_rendering() 