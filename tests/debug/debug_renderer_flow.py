"""Debug script to trace the renderer's content processing flow."""

import os
import sys
import logging
from typing import Dict, List, Any
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.pyxie.renderer import render_content, NestedRenderer
from src.pyxie.types import ContentItem
from src.pyxie.parser import FastHTMLToken, ScriptToken, NestedContentToken, custom_tokenize_block
from src.pyxie.layouts import layout
from mistletoe import Document
from fastcore.xml import Div, H1, P

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def get_token_content(token):
    """Safely get token content."""
    if hasattr(token, 'content'):
        return token.content
    elif hasattr(token, 'children'):
        return ' '.join(str(child) for child in token.children)
    return str(token)

def debug_renderer_flow():
    """Debug the renderer's content processing flow."""
    # Register test layout
    @layout("test")
    def test_layout(title: str = "", content: str = "") -> str:
        return Div(
            H1(title, cls="title"),
            Div(None, data_slot="content", cls="content"),
            cls="test-layout"
        )
    
    # Test content with FastHTML inside nested content
    content = """
# Main Title

<content>
## Section 1
This is content in a content block.

<ft>
show(Div("Hello from FastHTML"))
</ft>

<script>
console.log("Hello from script");
</script>
</content>

<custom>
This is a custom block
</custom>
"""
    
    # Create content item
    item = ContentItem(
        source_path=Path("test.md"),
        metadata={"layout": "test", "title": "Test Page"},
        content=content
    )
    
    print("\n=== Input Content ===")
    print(content)
    
    # Debug tokenization
    print("\n=== Tokenization ===")
    tokens = list(custom_tokenize_block(content, [FastHTMLToken, ScriptToken, NestedContentToken]))
    print("Tokens:")
    for token in tokens:
        print(f"\nType: {type(token).__name__}")
        print(f"Content: {get_token_content(token)}")
        if hasattr(token, 'tag_name'):
            print(f"Tag name: {token.tag_name}")
        if hasattr(token, 'children'):
            print("Children:")
            for child in token.children:
                print(f"  Type: {type(child).__name__}")
                print(f"  Content: {get_token_content(child)}")
                if hasattr(child, 'tag_name'):
                    print(f"  Tag name: {child.tag_name}")
    
    # Debug block grouping
    print("\n=== Block Grouping ===")
    blocks: Dict[str, List[Any]] = {}
    current_block = "_pyxie_default"
    
    for token in tokens:
        if isinstance(token, NestedContentToken):
            current_block = token.tag_name
            if current_block not in blocks:
                blocks[current_block] = []
        else:
            if current_block not in blocks:
                blocks[current_block] = []
            blocks[current_block].append(token)
    
    print("Blocks:")
    for name, block_tokens in blocks.items():
        print(f"\n{name}:")
        for token in block_tokens:
            print(f"  Type: {type(token).__name__}")
            print(f"  Content: {get_token_content(token)}")
            if hasattr(token, 'children'):
                print("  Children:")
                for child in token.children:
                    print(f"    Type: {type(child).__name__}")
                    print(f"    Content: {get_token_content(child)}")
                    if hasattr(child, 'tag_name'):
                        print(f"    Tag name: {child.tag_name}")
    
    # Debug rendering
    print("\n=== Rendering ===")
    renderer = NestedRenderer()
    rendered_blocks: Dict[str, List[str]] = {}
    
    for block_name, block_tokens in blocks.items():
        print(f"\nRendering block: {block_name}")
        doc = Document('')
        doc.children = block_tokens
        with renderer:
            rendered = renderer.render(doc)
            rendered_blocks[block_name] = [rendered]
            print(f"Rendered content: {rendered}")
    
    # Debug final render
    print("\n=== Final Render ===")
    result = render_content(item)
    print(f"Final HTML: {result}")

if __name__ == "__main__":
    debug_renderer_flow() 