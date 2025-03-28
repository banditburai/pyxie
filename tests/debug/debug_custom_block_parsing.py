"""Debug script for testing custom block parsing in isolation."""

from pyxie.parser import FastHTMLToken, ScriptToken, NestedContentToken, custom_tokenize_block
from mistletoe import Document
from mistletoe.block_token import add_token

def debug_custom_block_parsing():
    """Debug custom block parsing."""
    print("\n=== Testing Custom Block Parsing ===\n")
    
    # Register tokens
    add_token(FastHTMLToken)
    add_token(ScriptToken)
    add_token(NestedContentToken)
    
    # Test 1: Simple custom block
    print("Test 1: Simple custom block")
    content1 = """<custom-content>
# Header
**Bold** and *italic*
</custom-content>"""
    
    print("\nInput:")
    print(content1)
    print("\nParsed tokens:")
    doc = Document('')
    doc.children = list(custom_tokenize_block(content1, [FastHTMLToken, ScriptToken, NestedContentToken]))
    for child in doc.children:
        print(f"\nToken type: {type(child).__name__}")
        print(f"Tag name: {getattr(child, 'tag_name', 'N/A')}")
        print(f"Attributes: {getattr(child, 'attrs', {})}")
        print(f"Content: {getattr(child, 'content', 'N/A')}")
        print(f"Children: {getattr(child, 'children', [])}")
    
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
    print("\nParsed tokens:")
    doc = Document('')
    doc.children = list(custom_tokenize_block(content2, [FastHTMLToken, ScriptToken, NestedContentToken]))
    for child in doc.children:
        print(f"\nToken type: {type(child).__name__}")
        print(f"Tag name: {getattr(child, 'tag_name', 'N/A')}")
        print(f"Attributes: {getattr(child, 'attrs', {})}")
        print(f"Content: {getattr(child, 'content', 'N/A')}")
        print(f"Children: {getattr(child, 'children', [])}")
    
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
    print("\nParsed tokens:")
    doc = Document('')
    doc.children = list(custom_tokenize_block(content3, [FastHTMLToken, ScriptToken, NestedContentToken]))
    for child in doc.children:
        print(f"\nToken type: {type(child).__name__}")
        print(f"Tag name: {getattr(child, 'tag_name', 'N/A')}")
        print(f"Attributes: {getattr(child, 'attrs', {})}")
        print(f"Content: {getattr(child, 'content', 'N/A')}")
        print(f"Children: {getattr(child, 'children', [])}")

if __name__ == "__main__":
    debug_custom_block_parsing() 