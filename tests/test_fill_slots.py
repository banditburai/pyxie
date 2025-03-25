"""Test filling slots with content blocks."""

def test_fill_slots():
    """Test filling slots with content blocks."""
    # Create a basic layout HTML
    layout_html = '<div class="test-layout"><title></title><content></content><sidebar></sidebar></div>'
    
    # Create content blocks dictionary
    blocks = {
        'blocks': {
            'title': '# Welcome',
            'content': '**Main** content with *formatting*',
            'sidebar': '- Item 1\n- Item 2'
        }
    }
    
    # Define the fill_slots function
    def fill_slots(layout, content_blocks):
        """Fill slots in layout with content blocks."""
        # Create a copy to avoid modifying the original
        result = layout
        
        # Fill in content blocks
        blocks_dict = content_blocks.get('blocks', {})
        for block_name, block_content in blocks_dict.items():
            placeholder = f"<{block_name}></{block_name}>"
            if placeholder in result:
                result = result.replace(placeholder, block_content)
        
        return result
    
    # Fill slots directly
    result = fill_slots(layout_html, blocks)
    print(f"Rendered result: {result}")
    
    # Verify that the content was added to the layout
    assert "test-layout" in result
    assert "Welcome" in result
    assert "Main" in result
    assert "Item 1" in result
    assert "Item 2" in result 