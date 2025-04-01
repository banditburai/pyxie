#!/usr/bin/env python3
"""
Debug script to test self-closing tag handling.
"""

import logging
from pathlib import Path
from mistletoe import Document
from mistletoe import block_tokenizer
from mistletoe import block_token

from pyxie.parser import RawBlockToken, NestedContentToken
from pyxie.renderer import PyxieRenderer

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def debug_self_closing_tags():
    """Test various self-closing tag scenarios."""
    
    # Test cases with different self-closing tag scenarios
    test_cases = [
        # Basic self-closing tags
        """<br/>
<img src="test.jpg"/>
<input type="text"/>""",
        
        # Void elements without explicit self-closing
        """<br>
<img src="test.jpg">
<input type="text">""",
        
        # Mixed content with self-closing tags
        """<div>
<p>Some text</p>
<br/>
<img src="test.jpg"/>
<p>More text</p>
</div>""",
        
        # Nested self-closing tags
        """<div>
<p>Text with <br/> line break</p>
<p>Text with <img src="test.jpg"/> image</p>
</div>""",
        
        # Self-closing tags with attributes
        """<img src="test.jpg" alt="Test" width="100" height="100"/>
<input type="text" name="username" required/>
<br class="clear"/>"""
    ]
    
    # Add our custom tokens to Mistletoe's token types
    token_types = block_token._token_types + [RawBlockToken, NestedContentToken]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n=== Test Case {i} ===")
        print("Input markdown:")
        print(test_case)
        
        # Parse the document
        doc = Document(test_case)
        block_token._token_types = token_types  # Set token types globally
        
        print("\nParsed document structure:")
        for i, child in enumerate(doc.children):
            print(f"Child {i}: {child}")
            if hasattr(child, 'children'):
                for j, grandchild in enumerate(child.children):
                    print(f"  Grandchild {j}: {grandchild}")
        
        # Render with our custom renderer
        renderer = PyxieRenderer()
        rendered = renderer.render(doc)
        
        print("\nRendered HTML:")
        print(rendered)
        print("\nRendered HTML (repr):")
        print(repr(rendered))

if __name__ == "__main__":
    debug_self_closing_tags() 