"""Test the renderer module."""

import re
import pytest
from unittest.mock import patch
from mistletoe import Document
from pyxie.renderer import PyxieHTMLRenderer, render_markdown, process_conditional_visibility
from pyxie.types import ContentBlock

@pytest.fixture
def renderer():
    """Create a fresh renderer instance for each test."""
    return PyxieHTMLRenderer()

def test_header_id_generation():
    """Test that headers get unique IDs."""
    markdown = "# Header 1\n\n## Header 2\n\n# Header 1\n\n### Header with ! Special @ Characters"
    html = render_markdown(markdown)
    
    assert '<h1 id="header-1">' in html
    assert '<h2 id="header-2">' in html
    assert '<h1 id="header-1-1">' in html  # Second instance gets -1 suffix
    assert '<h3 id="header-with-special-characters">' in html

def test_empty_header_handling():
    """Test handling of empty headers."""
    markdown = "#\n\n##\n\n#"
    html = render_markdown(markdown)
    
    assert '<h1 id="section">' in html
    assert '<h2 id="section-1">' in html
    assert '<h1 id="section-2">' in html

def test_html_in_header():
    """Test that HTML in headers is handled correctly."""
    markdown = "# Header with <em>emphasis</em>\n\n## Header with <strong>bold</strong>"
    html = render_markdown(markdown)
    
    assert '<h1 id="header-with-emphasis">' in html
    assert '<h2 id="header-with-bold">' in html

def test_unicode_headers():
    """Test handling of Unicode characters in headers."""
    markdown = "# Header with émojis 🎉\n\n## Another ünicode header ß"
    html = render_markdown(markdown)
    
    # The renderer preserves unicode characters in IDs
    assert '<h1 id="header-with-émojis-">' in html
    assert '<h2 id="another-ünicode-header-ß">' in html

def test_complex_document():
    """Test a more complex document structure."""
    markdown = "# Main Header\n\nSome content\n\n## Sub Header 1\n\nMore content\n\n## Sub Header 2\n\n### Deep Header\n\n## Sub Header 1\n\nDuplicate header"
    html = render_markdown(markdown)
    
    assert '<h1 id="main-header">' in html
    assert '<h2 id="sub-header-1">' in html
    assert '<h2 id="sub-header-2">' in html
    assert '<h3 id="deep-header">' in html
    assert '<h2 id="sub-header-1-1">' in html  # Second instance gets -1 suffix

def test_image_rendering():
    """Test image rendering with various configurations."""
    markdown = "![Alt Text](pyxie:test/800/600)\n\n![Placeholder](placeholder)\n\n![With Title](https://example.com/image.jpg \"Image Title\")"
    html = render_markdown(markdown)
    
    assert 'src="https://picsum.photos/seed/test/800/600"' in html
    assert 'src="https://picsum.photos/seed/placeholder/800/600"' in html
    assert 'src="https://example.com/image.jpg"' in html
    assert 'title="Image Title"' in html

def test_image_placeholder_rendering():
    """Test image placeholder rendering."""
    from pyxie.renderer import render_markdown
    
    # Test basic placeholder
    markdown = "![Test](pyxie:test)"
    html = render_markdown(markdown)
    assert 'src="https://picsum.photos/seed/test/800/600"' in html
    
    # Test custom dimensions
    markdown = "![Test](pyxie:test/400/300)"
    html = render_markdown(markdown)
    assert 'src="https://picsum.photos/seed/test/400/300"' in html
    
    # Test alt text as seed
    markdown = "![Mountain View](placeholder)"
    html = render_markdown(markdown)
    assert 'src="https://picsum.photos/seed/mountain-view/800/600"' in html

def test_markdown_rendering_with_placeholders():
    """Test complete markdown rendering with image placeholders."""
    from pyxie.renderer import render_markdown
    
    # Test markdown with a placeholder image
    markdown = """
# Testing Image Placeholders

Here's a placeholder image:

![Mountain view](pyxie:mountain)

And one with custom dimensions:

![Lake view](pyxie:lake/1200/500)

And one with the simple syntax:

![Forest path](placeholder)
    """
    
    # Render the markdown to HTML
    html = render_markdown(markdown)
    
    # Check that the placeholders were processed correctly
    assert 'https://picsum.photos/seed/mountain/800/600' in html
    assert 'https://picsum.photos/seed/lake/1200/500' in html
    assert 'https://picsum.photos/seed/forest-path/800/600' in html
    
    # Check that the HTML structure is correct
    assert '<h1 id="testing-image-placeholders">Testing Image Placeholders</h1>' in html
    assert '<p>Here\'s a placeholder image:</p>' in html

def test_self_closing_tags_rendering():
    """Test that self-closing tags like <br>, <img>, etc. are rendered correctly."""
    # Test markdown with self-closing tags
    markdown = "Line one<br>Line two\n\n<img src='test.jpg'>\n\n<hr>\n\n<input type='text'>"
    html = render_markdown(markdown)
    
    # Check that the self-closing tags are present in the rendered HTML
    assert "<br>" in html
    assert "<img" in html
    assert "<hr>" in html
    assert "<input" in html
    
    # Test in a layout with conditional visibility
    html_with_tags = """
    <div data-pyxie-show="content">
        <p>Line one<br>Line two</p>
        <img src='test.jpg'>
        <hr>
        <input type='text'>
    </div>
    """
    
    result = process_conditional_visibility(html_with_tags, {"content"})
    
    # Check that all self-closing tags are preserved after processing
    assert "<br>" in result
    assert "<img" in result
    assert "<hr>" in result
    assert "<input" in result 