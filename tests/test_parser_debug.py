"""Debug tests for the parser to understand how content is being processed."""

import pytest
from mistletoe import Document
from pyxie.parser import (
    NestedContentToken, FastHTMLToken, ScriptToken,
    custom_tokenize_block, parse_frontmatter
)

def test_nested_content_token_initialization():
    """Test how NestedContentToken initializes and processes content."""
    # Test case 1: Simple markdown content
    content = """<custom>
This is **bold** and *italic* content
</custom>"""
    lines = content.split('\n')
    token = NestedContentToken(lines)
    
    print("\nTest 1: Simple markdown content")
    print(f"Tag name: {token.tag_name}")
    print(f"Content: {token.content}")
    print(f"Number of children: {len(token.children)}")
    for i, child in enumerate(token.children):
        print(f"Child {i}: {type(child).__name__}")
        print(f"Child content: {child.content if hasattr(child, 'content') else 'No content'}")
        if hasattr(child, 'children'):
            print(f"Child's children: {len(child.children)}")
            for j, grandchild in enumerate(child.children):
                print(f"Grandchild {j}: {type(grandchild).__name__}")
                print(f"Grandchild content: {grandchild.content if hasattr(grandchild, 'content') else 'No content'}")
    
    # Test case 2: Nested content
    content = """<custom>
This is **bold** content
<nested>
- Item 1
- Item 2
</nested>
</custom>"""
    lines = content.split('\n')
    token = NestedContentToken(lines)
    
    print("\nTest 2: Nested content")
    print(f"Tag name: {token.tag_name}")
    print(f"Content: {token.content}")
    print(f"Number of children: {len(token.children)}")
    for i, child in enumerate(token.children):
        print(f"Child {i}: {type(child).__name__}")
        if isinstance(child, NestedContentToken):
            print(f"Child tag name: {child.tag_name}")
            print(f"Child content: {child.content}")
            print(f"Number of child's children: {len(child.children)}")
            for j, grandchild in enumerate(child.children):
                print(f"Grandchild {j}: {type(grandchild).__name__}")
                print(f"Grandchild content: {grandchild.content if hasattr(grandchild, 'content') else 'No content'}")

def test_block_splitting():
    """Test how content is split into blocks."""
    # Test case 1: Simple markdown content
    content = """<custom>
This is **bold** content
</custom>"""
    lines = content.split('\n')
    token = NestedContentToken(lines)
    
    print("\nTest 1: Block splitting - Simple content")
    print(f"Original content: {content}")
    print(f"Number of children: {len(token.children)}")
    for i, child in enumerate(token.children):
        print(f"Child {i}: {type(child).__name__}")
        print(f"Child content: {child.content if hasattr(child, 'content') else 'No content'}")
    
    # Test case 2: Mixed content
    content = """<custom>
This is **bold** content
<ft>
show(Div("Hello"))
</ft>
<nested>
- Item 1
- Item 2
</nested>
</custom>"""
    lines = content.split('\n')
    token = NestedContentToken(lines)
    
    print("\nTest 2: Block splitting - Mixed content")
    print(f"Original content: {content}")
    print(f"Number of children: {len(token.children)}")
    for i, child in enumerate(token.children):
        print(f"Child {i}: {type(child).__name__}")
        if isinstance(child, NestedContentToken):
            print(f"Child tag name: {child.tag_name}")
            print(f"Child content: {child.content}")
            print(f"Number of child's children: {len(child.children)}")
            for j, grandchild in enumerate(child.children):
                print(f"Grandchild {j}: {type(grandchild).__name__}")
                print(f"Grandchild content: {grandchild.content if hasattr(grandchild, 'content') else 'No content'}")
        else:
            print(f"Child content: {child.content if hasattr(child, 'content') else 'No content'}")

def test_custom_tokenize_block():
    """Test how custom_tokenize_block processes content."""
    # Test case 1: Simple markdown content
    content = """# Title
<custom>
This is **bold** content
</custom>"""
    tokens = list(custom_tokenize_block(content, [FastHTMLToken, ScriptToken, NestedContentToken]))
    
    print("\nTest 1: custom_tokenize_block - Simple content")
    print(f"Original content: {content}")
    print(f"Number of tokens: {len(tokens)}")
    for i, token in enumerate(tokens):
        print(f"Token {i}: {type(token).__name__}")
        if isinstance(token, NestedContentToken):
            print(f"Tag name: {token.tag_name}")
            print(f"Content: {token.content}")
            print(f"Number of children: {len(token.children)}")
            for j, child in enumerate(token.children):
                print(f"Child {j}: {type(child).__name__}")
                print(f"Child content: {child.content if hasattr(child, 'content') else 'No content'}")
                if hasattr(child, 'children'):
                    print(f"Child's children: {len(child.children)}")
                    for k, grandchild in enumerate(child.children):
                        print(f"Grandchild {k}: {type(grandchild).__name__}")
                        print(f"Grandchild content: {grandchild.content if hasattr(grandchild, 'content') else 'No content'}")
    
    # Test case 2: Complex nested content
    content = """# Title
<custom>
This is **bold** content
<nested>
- Item 1
- Item 2
</nested>
</custom>"""
    tokens = list(custom_tokenize_block(content, [FastHTMLToken, ScriptToken, NestedContentToken]))
    
    print("\nTest 2: custom_tokenize_block - Complex content")
    print(f"Original content: {content}")
    print(f"Number of tokens: {len(tokens)}")
    for i, token in enumerate(tokens):
        print(f"Token {i}: {type(token).__name__}")
        if isinstance(token, NestedContentToken):
            print(f"Tag name: {token.tag_name}")
            print(f"Content: {token.content}")
            print(f"Number of children: {len(token.children)}")
            for j, child in enumerate(token.children):
                print(f"Child {j}: {type(child).__name__}")
                if isinstance(child, NestedContentToken):
                    print(f"Child tag name: {child.tag_name}")
                    print(f"Child content: {child.content}")
                    print(f"Number of child's children: {len(child.children)}")
                    for k, grandchild in enumerate(child.children):
                        print(f"Grandchild {k}: {type(grandchild).__name__}")
                        print(f"Grandchild content: {grandchild.content if hasattr(grandchild, 'content') else 'No content'}")

def test_full_rendering_pipeline():
    """Test the full rendering pipeline with debug output."""
    content = """# Title
<custom>
This is **bold** content
<nested>
- Item 1
- Item 2
</nested>
</custom>"""
    
    print("\nFull rendering pipeline test")
    print(f"Original content: {content}")
    
    # Step 1: Tokenize blocks
    tokens = list(custom_tokenize_block(content, [FastHTMLToken, ScriptToken, NestedContentToken]))
    print("\nStep 1: Tokenized blocks")
    for i, token in enumerate(tokens):
        print(f"Token {i}: {type(token).__name__}")
        if isinstance(token, NestedContentToken):
            print(f"Tag name: {token.tag_name}")
            print(f"Content: {token.content}")
            print(f"Number of children: {len(token.children)}")
            for j, child in enumerate(token.children):
                print(f"Child {j}: {type(child).__name__}")
                if isinstance(child, NestedContentToken):
                    print(f"Child tag name: {child.tag_name}")
                    print(f"Child content: {child.content}")
                    print(f"Number of child's children: {len(child.children)}")
                    for k, grandchild in enumerate(child.children):
                        print(f"Grandchild {k}: {type(grandchild).__name__}")
                        print(f"Grandchild content: {grandchild.content if hasattr(grandchild, 'content') else 'No content'}")
    
    # Step 2: Create Document
    doc = Document('')
    doc.children = tokens
    
    # Step 3: Render with debug output
    from pyxie.renderer import NestedRenderer
    with NestedRenderer() as renderer:
        rendered = renderer.render(doc)
        print("\nStep 3: Rendered output")
        print(rendered) 