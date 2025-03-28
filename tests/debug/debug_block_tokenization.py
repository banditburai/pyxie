"""Debug script for testing block vs inline tokenization."""

from mistletoe import Document
from mistletoe.span_token import tokenize_inner

def debug_tokenization():
    """Debug different tokenization methods."""
    print("\n=== Testing Tokenization Methods ===\n")
    
    # Test content
    content = """# Header

This is a paragraph with **bold** and *italic*.

- List item 1
- List item 2

> Blockquote"""
    
    # Test 1: Block tokenization
    print("Test 1: Block tokenization")
    print("\nInput:")
    print(content)
    print("\nTokenized blocks:")
    doc = Document(content)
    for block in doc.children:
        print(f"\nToken type: {type(block).__name__}")
        print(f"Content: {getattr(block, 'content', 'N/A')}")
        print(f"Children: {getattr(block, 'children', [])}")
    
    # Test 2: Inline tokenization
    print("\nTest 2: Inline tokenization")
    print("\nInput:")
    print(content)
    print("\nTokenized inline:")
    inlines = list(tokenize_inner(content))
    for inline in inlines:
        print(f"\nToken type: {type(inline).__name__}")
        print(f"Content: {getattr(inline, 'content', 'N/A')}")
        print(f"Children: {getattr(inline, 'children', [])}")

if __name__ == "__main__":
    debug_tokenization() 