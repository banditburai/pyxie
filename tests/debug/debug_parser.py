"""Debug script for understanding FastHTML parsing flow."""

import logging
import sys
from pathlib import Path

# Add src directory to Python path
src_dir = Path(__file__).parent.parent / "src"
sys.path.append(str(src_dir))

from mistletoe import Document
from mistletoe.block_token import add_token
from mistletoe.html_renderer import HTMLRenderer
from pyxie.parser import FastHTMLToken
from pyxie.fasthtml import render_fasthtml

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class DebugRenderer(HTMLRenderer):
    """Debug renderer for testing FastHTML blocks."""
    
    def __init__(self):
        # Register FastHTML token before calling super().__init__()
        add_token(FastHTMLToken)
        super().__init__()
        self.render_map['FastHTMLToken'] = self.render_fast_html_token
    
    def render_fast_html_token(self, token):
        """Render a FastHTML token."""
        logger.debug(f"Rendering FastHTML token: {token.content[:100]}...")
        try:
            result = render_fasthtml(token.content)
            if result.error:
                logger.error(f"Error rendering FastHTML: {result.error}")
                return f"<ft>{token.content}</ft>"
            return result.content
        except Exception as e:
            logger.error(f"Error rendering FastHTML token: {e}")
            return f"<ft>{token.content}</ft>"

def test_direct_render():
    """Test direct rendering without mistletoe."""
    content = """
def MyComponent(text):
    return Div(text, cls="custom")

show(MyComponent("Hello from function"))
"""
    print("\nDirect render test:")
    print("Input:", content)
    result = render_fasthtml(content)
    print("\nOutput:", result.content)

def test_mistletoe_parse():
    """Test mistletoe parsing of FastHTML blocks."""
    content = """
<ft>
def MyComponent(text):
    return Div(text, cls="custom")

show(MyComponent("Hello from function"))
</ft>
"""
    print("\nMistletoe parse test:")
    print("Input:", content)
    
    # Register FastHTML token
    add_token(FastHTMLToken)
    
    # Parse with mistletoe
    doc = Document(content)
    
    # Print token information
    print("\nToken info:")
    for token in doc.children:
        print(f"Token type: {type(token).__name__}")
        print(f"Token content: {token.content}")
        print(f"Token children: {token.children}")
        print("---")

def test_renderer():
    """Test rendering FastHTML blocks with mistletoe."""
    content = """
<ft>
def MyComponent(text):
    return Div(text, cls="custom")

show(MyComponent("Hello from function"))
</ft>
"""
    print("\nRenderer test:")
    print("Input:", content)
    
    # Parse and render with mistletoe
    doc = Document(content)
    renderer = DebugRenderer()
    result = renderer.render(doc)
    print("\nOutput:", result)

if __name__ == "__main__":
    test_direct_render()
    test_mistletoe_parse()
    test_renderer() 