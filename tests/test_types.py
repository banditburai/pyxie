def test_image_property(tmp_path):
    """Test the image property with different scenarios."""
    from pyxie.types import ContentItem
    from pathlib import Path
    
    # Create a dummy source path 
    source_path = tmp_path / "test.md"
    
    # Test with direct image URL
    item1 = ContentItem(
        slug="test1",
        content="Test content",
        metadata={"image": "https://example.com/image.jpg"},
        source_path=source_path
    )
    assert item1.image == "https://example.com/image.jpg"
    
    # Test with image template using index
    item2 = ContentItem(
        slug="test2",
        content="Test content",
        metadata={"image_template": "https://example.com/img/{index}.jpg"},
        index=42,
        source_path=source_path
    )
    assert item2.image == "https://example.com/img/42.jpg"
    
    # Test with image template using slug
    item3 = ContentItem(
        slug="test3",
        content="Test content",
        metadata={"image_template": "https://example.com/img/{slug}.jpg"},
        source_path=source_path
    )
    assert item3.image == "https://example.com/img/test3.jpg"
    
    # Test with custom dimensions
    item4 = ContentItem(
        slug="test4",
        content="Test content",
        metadata={
            "image_template": "https://example.com/img/{width}x{height}/{seed}.jpg",
            "image_width": 1024,
            "image_height": 768,
            "image_seed": "custom-seed"
        },
        source_path=source_path
    )
    assert item4.image == "https://example.com/img/1024x768/custom-seed.jpg"
    
    # Test fallback to default placeholder
    item5 = ContentItem(
        slug="test5",
        content="Test content",
        metadata={},
        source_path=source_path
    )
    assert "picsum.photos/seed/test5/" in item5.image
    
    # Test fallback when template formatting fails
    item6 = ContentItem(
        slug="test6",
        content="Test content",
        metadata={"image_template": "https://example.com/{nonexistent}/img.jpg"},
        source_path=source_path
    )
    assert "picsum.photos/seed/test6/" in item6.image 