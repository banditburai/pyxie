"""Debug script to analyze block grouping with complex markdown content."""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, List, Any

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.pyxie.parser import FastHTMLToken, ScriptToken, NestedContentToken, custom_tokenize_block, parse_frontmatter
from mistletoe import Document

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def debug_block_grouping():
    """Debug block grouping with a complex markdown document."""
    # Test content with various block types
    content = """---
title: Styling Guide for Blog Posts
date: 2023-05-20
author: Design Team
category: Design
summary: How to style your blog posts to look great in the Minimal Blog template
reading_time: 3 min read
---

<featured_image>
![Blog post styling example](pyxie:style/1200/600)
</featured_image>

<toc>
- [Text Formatting](#text-formatting)
- [Lists](#lists)
- [Blockquotes](#blockquotes)
- [Links](#links)
- [Code Blocks](#code-blocks)
</toc>

<content>
# Styling Guide for Blog Posts

Learn how to make your blog posts look great with some simple styling tips.

## Text Formatting

**Bold text** is great for emphasis, while *italic text* can be used for less strong emphasis.

### Headings

Use headings to organize your content. Start with H1 for the title, and use H2, H3, etc. for sections and subsections.

## Lists

Unordered lists:

- Item 1
- Item 2
- Item 3

Ordered lists:

1. First item
2. Second item
3. Third item

## Blockquotes

> Blockquotes can be used to highlight important information or quotes from other sources.

## Links

[Links](https://example.com) are essential for referencing other resources.

## Code Blocks

Inline code like `var x = 10;` is useful for short snippets.

For longer code blocks, use triple backticks:

```css
.blog-post {
  max-width: 800px;
  margin: 0 auto;
  padding: 2rem;
}
```
</content>

<conclusion>
Following these styling guidelines will ensure your blog posts look consistent and professional. Remember that good styling enhances the reading experience and helps your readers focus on your content.

For more advanced styling options, check out our [design documentation](https://example.com/design-docs).
</conclusion>

<share>
<div class="flex gap-3">
  <a href="https://twitter.com/share?text=Styling Guide for Blog Posts&url=https://example.com/post/styling-guide" target="_blank" class="btn btn-sm btn-outline">
    <iconify-icon icon="fa:twitter" class="mr-2"></iconify-icon> Share on Twitter
  </a>
  <a href="https://www.facebook.com/sharer/sharer.php?u=https://example.com/post/styling-guide" target="_blank" class="btn btn-sm btn-outline">
    <iconify-icon icon="fa:facebook" class="mr-2"></iconify-icon> Share on Facebook
  </a>
</div>
</share>"""

    print("\n=== Input Content ===")
    print(content)
    
    # Parse frontmatter first
    print("\n=== Frontmatter Parsing ===")
    metadata, content = parse_frontmatter(content)
    print("Metadata:", metadata)
    print("\nContent after frontmatter parsing:")
    print(content)
    
    # Debug tokenization
    print("\n=== Tokenization ===")
    tokens = list(custom_tokenize_block(content, [FastHTMLToken, ScriptToken, NestedContentToken]))
    print("Tokens:")
    for token in tokens:
        print(f"\nType: {type(token).__name__}")
        if hasattr(token, 'tag_name'):
            print(f"Tag name: {token.tag_name}")
        if hasattr(token, 'content'):
            print(f"Content: {token.content[:100]}...")  # Truncate long content
        if hasattr(token, 'children') and token.children is not None:
            print(f"Number of children: {len(token.children)}")
            for child in token.children:
                print(f"  Child type: {type(child).__name__}")
                if hasattr(child, 'content'):
                    print(f"  Child content: {child.content[:50]}...")
    
    # Debug block grouping
    print("\n=== Block Grouping ===")
    blocks: Dict[str, List[Any]] = {}
    current_block = "_pyxie_default"
    
    for token in tokens:
        if isinstance(token, NestedContentToken):
            current_block = token.tag_name
            if current_block not in blocks:
                blocks[current_block] = []
            blocks[current_block].append(token)
        else:
            if current_block not in blocks:
                blocks[current_block] = []
            blocks[current_block].append(token)
    
    print("\nBlocks:")
    for name, block_tokens in blocks.items():
        print(f"\n{name}:")
        print(f"Number of tokens: {len(block_tokens)}")
        for token in block_tokens:
            print(f"  Type: {type(token).__name__}")
            if hasattr(token, 'content'):
                print(f"  Content: {token.content[:50]}...")
            if hasattr(token, 'children') and token.children is not None:
                print(f"  Number of children: {len(token.children)}")

if __name__ == "__main__":
    debug_block_grouping() 