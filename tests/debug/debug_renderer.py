"""Debug script for testing PyxieHTMLRenderer's handling of FastHTML tokens."""

import logging
from mistletoe import Document
from pyxie.parser import FastHTMLToken
from pyxie.renderer import PyxieHTMLRenderer
from pyxie.types import ContentBlock

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_direct_token_rendering():
    """Test rendering a FastHTML token directly."""
    content = "<ft>show(Div('Test', cls='test-class'))</ft>"
    match = FastHTMLToken.pattern.match(content)
    if not match:
        logger.error("Failed to match FastHTML pattern")
        return
        
    token = FastHTMLToken(match)
    renderer = PyxieHTMLRenderer()
    result = renderer.render_fast_html_token(token)
    logger.info(f"Direct token rendering result:\n{result}")

def test_document_rendering():
    """Test rendering a document containing FastHTML tokens."""
    content = """
<ft>
def MyComponent(text):
    return Div(text, cls="custom")

show(MyComponent("Test"))
</ft>

Some markdown text in between.

<ft>show(Div("Another test"))</ft>
"""
    doc = Document(content)
    renderer = PyxieHTMLRenderer()
    result = renderer.render(doc)
    logger.info(f"Document rendering result:\n{result}")

def test_paragraph_handling():
    """Test how paragraphs containing FastHTML tokens are rendered."""
    content = """
This is a paragraph with FastHTML:
<ft>show(Div("Inside paragraph"))</ft>
And some more text.

<ft>show(Div("Outside paragraph"))</ft>
"""
    doc = Document(content)
    renderer = PyxieHTMLRenderer()
    result = renderer.render(doc)
    logger.info(f"Paragraph handling result:\n{result}")

def test_nested_content():
    """Test rendering nested FastHTML content."""
    content = """
<ft>
component = Div(
    Div("Inner content", cls="inner"),
    cls="outer"
)
show(component)
</ft>
"""
    doc = Document(content)
    renderer = PyxieHTMLRenderer()
    result = renderer.render(doc)
    logger.info(f"Nested content rendering result:\n{result}")

if __name__ == "__main__":
    logger.info("Testing direct token rendering...")
    test_direct_token_rendering()
    
    logger.info("\nTesting document rendering...")
    test_document_rendering()
    
    logger.info("\nTesting paragraph handling...")
    test_paragraph_handling()
    
    logger.info("\nTesting nested content rendering...")
    test_nested_content() 