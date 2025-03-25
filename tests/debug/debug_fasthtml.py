"""Debug script to test FastHTML execution and rendering."""

import logging
from pyxie.fasthtml import render_fasthtml
from pyxie.renderer import PyxieHTMLRenderer
from mistletoe import Document

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_fasthtml_execution():
    """Test FastHTML execution directly vs through renderer."""
    content = """
show(Div("Test content", cls="test"))
"""
    logger.info("Testing FastHTML execution with content:\n%s", content)
    
    # Test direct execution
    logger.info("Testing direct execution:")
    result = render_fasthtml(content)
    logger.info("Direct execution result:\n%s", result)
    
    # Test through renderer
    logger.info("Testing through renderer:")
    ft_content = f"<ft>\n{content}\n</ft>"
    doc = Document(ft_content)
    renderer = PyxieHTMLRenderer()
    result = renderer.render(doc)
    logger.info("Renderer result:\n%s", result)

if __name__ == "__main__":
    test_fasthtml_execution() 