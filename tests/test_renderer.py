def test_image_placeholder_rendering():
    """Test rendering of placeholder images in markdown."""
    from pyxie.renderer import render_markdown
    
    # Test basic pyxie syntax
    markdown1 = '![Mountain view](pyxie:mountain)'
    html1 = render_markdown(markdown1)
    assert 'https://picsum.photos/seed/mountain/800/600' in html1
    assert 'alt="Mountain view"' in html1
    
    # Test with custom dimensions
    markdown2 = '![Team photo](pyxie:team/1200/800)'
    html2 = render_markdown(markdown2)
    assert 'https://picsum.photos/seed/team/1200/800' in html2
    assert 'alt="Team photo"' in html2
    
    # Test simple placeholder syntax
    markdown3 = '![Forest path](placeholder)'
    html3 = render_markdown(markdown3)
    assert 'https://picsum.photos/seed/forest-path/800/600' in html3
    assert 'alt="Forest path"' in html3
    
    # Test that regular images are unchanged
    markdown4 = '![Real image](/images/photo.jpg)'
    html4 = render_markdown(markdown4)
    assert '/images/photo.jpg' in html4
    assert 'alt="Real image"' in html4

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
    assert '<h1>Testing Image Placeholders</h1>' in html
    assert '<img src="https://picsum.photos/seed/mountain/800/600" alt="Mountain view"' in html
    assert '<img src="https://picsum.photos/seed/lake/1200/500" alt="Lake view"' in html
    assert '<img src="https://picsum.photos/seed/forest-path/800/600" alt="Forest path"' in html 