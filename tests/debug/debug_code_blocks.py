"""Debug script to examine code block token content."""

import logging
from pathlib import Path
import sys
import html
import re

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mistletoe import Document
from mistletoe.block_token import CodeFence, _token_types, HtmlBlock
from src.pyxie.renderer import PyxieRenderer
from pyxie.types import ContentItem
from pyxie.parser import NestedContentToken, RawBlockToken

def setup_tokens():
    """Set up custom tokens for parsing."""
    # Save original tokens
    original_tokens = list(_token_types)
    
    # Clear existing tokens
    _token_types.clear()
    
    # Add our custom tokens first (highest priority)
    _token_types.extend([RawBlockToken, NestedContentToken])
    
    # Add back original tokens except HtmlBlock
    for token in original_tokens:
        if token != HtmlBlock and token not in [RawBlockToken, NestedContentToken]:
            _token_types.append(token)
            
    return original_tokens

def restore_tokens(original_tokens):
    """Restore original token types."""
    _token_types.clear()
    _token_types.extend(original_tokens)

def debug_token_structure(token, depth=0, prefix=""):
    """Recursively debug token structure with detailed content analysis."""
    indent = "  " * depth
    print(f"{indent}{prefix}Token: {token.__class__.__name__}")
    
    # Print token attributes
    if hasattr(token, 'tag_name'):
        print(f"{indent}  Tag: {token.tag_name}")
    if hasattr(token, 'attrs'):
        print(f"{indent}  Attrs: {token.attrs}")
    
    # Special handling for CodeFence
    if isinstance(token, CodeFence):
        print(f"{indent}  Language: {token.language}")
        print(f"{indent}  Content (raw):")
        print(f"{indent}    {repr(token.content)}")
        print(f"{indent}  Content (lines):")
        for line in token.content.splitlines():
            print(f"{indent}    {repr(line)}")
    
    # Print raw content if available
    if hasattr(token, 'content') and not isinstance(token, CodeFence):
        print(f"{indent}  Content: {repr(token.content)}")
    
    # Recursively process children
    if hasattr(token, 'children') and token.children is not None:
        for i, child in enumerate(token.children):
            if child is not None:  # Skip None children
                debug_token_structure(child, depth + 1, f"Child {i}: ")

def debug_render_content(markdown_content: str) -> None:
    """Debug the rendering of markdown content."""
    print("\n=== Input Markdown ===\n")
    print(markdown_content)
    
    print("\n=== Parsing with Document ===\n")
    original_tokens = setup_tokens()
    doc = Document(markdown_content)
    
    print("Document structure:")
    debug_token_structure(doc)
    
    print("\n=== Rendering with PyxieRenderer ===\n")
    with PyxieRenderer() as renderer:
        rendered = renderer.render(doc)
        print("Rendered HTML:")
        print("---")
        print(rendered)
        print("---")
        print("\nRendered HTML (repr):")
        print(repr(rendered))
    
    restore_tokens(original_tokens)

if __name__ == "__main__":
    test_content = """<content>
## Project Setup

Create a new directory for your site and set up a basic structure:

```
my-site/
├── posts/          # Your markdown content
├── layouts/        # Your layout files
├── static/
│   └── css/       # Your CSS files
└── main.py        # App initialization
```

Create your app initialization file (`main.py`):

```python
from fasthtml.common import *
from pyxie import Pyxie

# Initialize Pyxie with content and layout directories
pyxie = Pyxie(
    "posts",                # Where to find your markdown content
    live=True              # Enable live reloading for development
)

# Create FastHTML app with Pyxie middleware
app, rt = fast_app(
    htmlkw=dict(lang="en"),
    middleware=(pyxie.serve_md(),)  # Serve markdown versions at {slug}.md
)
```

The `serve_md()` middleware automatically makes your original markdown content available at a `.md` endpoint. For example:
</content>"""

    debug_render_content(test_content) 