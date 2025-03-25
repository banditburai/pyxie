"""Debug script to test token handling in a single document."""

import logging
from mistletoe import Document
from mistletoe.html_renderer import HTMLRenderer
from mistletoe.block_token import add_token as add_block_token
from mistletoe.span_token import add_token as add_span_token

from pyxie.parser import FastHTMLToken
from pyxie.fasthtml import render_fasthtml
from pyxie.errors import format_error_html

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class DebugRenderer(HTMLRenderer):
    """Debug renderer that logs token handling."""
    
    def __init__(self):
        # Register FastHTML token
        add_block_token(FastHTMLToken)
        add_span_token(FastHTMLToken)
        super().__init__()
        
        # Add FastHTML token renderer
        self.render_map[FastHTMLToken.__name__] = self.render_fast_html_token
    
    def render_fast_html_token(self, token):
        """Render a FastHTML token."""
        logger.debug(f"Rendering FastHTML token: {token.content[:100]}...")
        result = render_fasthtml(token.content)
        if result.success:
            return result.content
        return format_error_html("rendering", result.error)

def print_token_info(token, indent=""):
    """Print information about a token and its children."""
    token_type = type(token).__name__
    print(f"\n{indent}Token Type: {token_type}")
    
    # Print content if available
    if hasattr(token, 'content'):
        content = token.content[:100] + "..." if len(token.content) > 100 else token.content
        print(f"{indent}Content: {content}")
    elif hasattr(token, 'children') and len(token.children) == 1:
        child = token.children[0]
        if hasattr(child, 'content'):
            content = child.content[:100] + "..." if len(child.content) > 100 else child.content
            print(f"{indent}Content (from child): {content}")
    
    # Print children if available
    if hasattr(token, 'children') and token.children:
        print(f"{indent}Children:")
        for child in token.children:
            print_token_info(child, indent + "  ")

def test_fasthtml_cases():
    """Test various FastHTML rendering cases."""
    content = """
# FastHTML Test Cases

1. Simple component:
<ft>
show(Div("Hello World", cls="test-class"))
</ft>

2. Multiple components in a single block:
<ft>
show(Div([
    H1("Title"),
    P("Content")
], cls="container"))
</ft>

3. Inline FastHTML: This is a paragraph with <ft>show(Strong("emphasized"))</ft> text.

4. Multiple components:
<ft>
show([
    H2("First"),
    P("Paragraph 1"),
    H2("Second"),
    P("Paragraph 2")
])
</ft>

5. Regular markdown mixed with FastHTML:
- List item 1
- List item with <ft>show(Em("emphasis"))</ft>
- List item 3
"""
    
    # Create document and render
    doc = Document(content)
    renderer = DebugRenderer()
    result = renderer.render(doc)
    
    print("\nRendered HTML:")
    print(result)
    
    print("\nToken Information:")
    for token in doc.children:
        print_token_info(token)

if __name__ == "__main__":
    test_fasthtml_cases() 