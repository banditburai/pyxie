"""Debug script for testing mistletoe's custom rendering with FastHTML tokens."""

import logging
from mistletoe.html_renderer import HTMLRenderer
from mistletoe.block_token import add_token
from mistletoe import Document
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
    
    def render_html_block(self, token):
        """Override render_html_block to handle FastHTML blocks."""
        if isinstance(token, FastHTMLToken):
            return self.render_fast_html_token(token)
        return super().render_html_block(token)
    
    def render_paragraph(self, token):
        """Override render_paragraph to handle FastHTML blocks."""
        if any(isinstance(child, FastHTMLToken) for child in token.children):
            return '\n'.join(self.render(child) for child in token.children)
        return super().render_paragraph(token)
    
    def render_inner(self, token):
        """Override render_inner to handle FastHTML blocks."""
        if isinstance(token, FastHTMLToken):
            return self.render_fast_html_token(token)
        return super().render_inner(token)
    
    def render(self, token):
        """Override render to handle FastHTML blocks."""
        if isinstance(token, FastHTMLToken):
            return self.render_fast_html_token(token)
        return super().render(token)

def test_simple_fasthtml():
    """Test rendering a simple FastHTML block."""
    content = """
<ft>
show(Div("Hello World", cls="test-class"))
</ft>
"""
    print("\nSimple FastHTML test:")
    print("Input:", content)
    doc = Document(content)
    print("\nOutput:", DebugRenderer().render(doc))

def test_mixed_content():
    """Test rendering mixed Markdown and FastHTML content."""
    content = """
# Heading

<ft>
show(Div("FastHTML content", cls="ft-content"))
</ft>

Regular markdown paragraph.

<ft>
show(Div("More FastHTML", cls="ft-content"))
</ft>
"""
    print("\nMixed content test:")
    print("Input:", content)
    doc = Document(content)
    print("\nOutput:", DebugRenderer().render(doc))

def test_nested_fasthtml():
    """Test rendering nested FastHTML blocks."""
    content = """
<ft>
def MyComponent(text):
    return Div(text, cls="custom")

show(MyComponent("Hello from function"))
</ft>
"""
    print("\nNested FastHTML test:")
    print("Input:", content)
    doc = Document(content)
    print("\nOutput:", DebugRenderer().render(doc))

if __name__ == "__main__":
    test_simple_fasthtml()
    test_mixed_content()
    test_nested_fasthtml() 