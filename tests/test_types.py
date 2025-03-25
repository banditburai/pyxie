def test_image_property(tmp_path):
    """Test the image property with different scenarios."""
    from pyxie.types import ContentItem, ContentBlock
    
    # Create a dummy source path 
    source_path = tmp_path / "test.md"
    
    # Test with direct image URL
    item1 = ContentItem(
        source_path=source_path,
        metadata={"image": "https://example.com/image.jpg", "title": "Test 1"},
        blocks={"content": [ContentBlock(
            tag_name="markdown",
            content="Test content",
            attrs_str="",
            content_type="markdown"
        )]}
    )
    assert item1.image == "https://example.com/image.jpg"
    
    # Test with image template using index
    item2 = ContentItem(
        source_path=source_path,
        metadata={
            "image_template": "https://example.com/img/{index}.jpg",
            "title": "Test 2",
            "index": 42
        },
        blocks={"content": [ContentBlock(
            tag_name="markdown",
            content="Test content",
            attrs_str="",
            content_type="markdown"
        )]}
    )
    assert item2.image == "https://example.com/img/42.jpg"
    
    # Test with image template using slug
    item3 = ContentItem(
        source_path=tmp_path / "test3.md",
        metadata={
            "image_template": "https://example.com/img/{slug}.jpg",
            "title": "Test 3"
        },
        blocks={"content": [ContentBlock(
            tag_name="markdown",
            content="Test content",
            attrs_str="",
            content_type="markdown"
        )]}
    )
    assert item3.image == "https://example.com/img/test3.jpg"
    
    # Test with custom dimensions
    item4 = ContentItem(
        source_path=source_path,
        metadata={
            "image_template": "https://example.com/img/{width}x{height}/{seed}.jpg",
            "image_width": 1024,
            "image_height": 768,
            "image_seed": "custom-seed",
            "title": "Test 4"
        },
        blocks={"content": [ContentBlock(
            tag_name="markdown",
            content="Test content",
            attrs_str="",
            content_type="markdown"
        )]}
    )
    assert item4.image == "https://example.com/img/1024x768/custom-seed.jpg"
    
    # Test fallback to default placeholder
    item5 = ContentItem(
        source_path=tmp_path / "test5.md",
        metadata={"title": "Test 5"},
        blocks={"content": [ContentBlock(
            tag_name="markdown",
            content="Test content",
            attrs_str="",
            content_type="markdown"
        )]}
    )
    assert "picsum.photos/seed/test5/" in item5.image
    
    # Test fallback when template formatting fails
    item6 = ContentItem(
        source_path=tmp_path / "test6.md",
        metadata={
            "image_template": "https://example.com/{nonexistent}/img.jpg",
            "title": "Test 6"
        },
        blocks={"content": [ContentBlock(
            tag_name="markdown",
            content="Test content",
            attrs_str="",
            content_type="markdown"
        )]}
    )
    assert "picsum.photos/seed/test6/" in item6.image

def test_slug_property(tmp_path):
    """Test the slug property with different scenarios."""
    from pyxie.types import ContentItem, ContentBlock
    
    # Test slug from source path
    item1 = ContentItem(
        source_path=tmp_path / "test-page.md",
        metadata={},
        blocks={}
    )
    assert item1.slug == "test-page"
    
    # Test explicit slug in metadata
    item2 = ContentItem(
        source_path=tmp_path / "test.md",
        metadata={"slug": "custom-slug"},
        blocks={}
    )
    assert item2.slug == "custom-slug"

def test_content_property(tmp_path):
    """Test the content property with different scenarios."""
    from pyxie.types import ContentItem, ContentBlock
    
    # Test with single content block
    item1 = ContentItem(
        source_path=tmp_path / "test.md",
        metadata={},
        blocks={"content": [ContentBlock(
            tag_name="markdown",
            content="Test content",
            attrs_str="",
            content_type="markdown"
        )]}
    )
    assert item1.content == "Test content"
    
    # Test with multiple content blocks (should return first)
    item2 = ContentItem(
        source_path=tmp_path / "test.md",
        metadata={},
        blocks={"content": [
            ContentBlock(
                tag_name="markdown",
                content="First content",
                attrs_str="",
                content_type="markdown"
            ),
            ContentBlock(
                tag_name="markdown",
                content="Second content",
                attrs_str="",
                content_type="markdown"
            )
        ]}
    )
    assert item2.content == "First content"
    
    # Test with no content blocks
    item3 = ContentItem(
        source_path=tmp_path / "test.md",
        metadata={},
        blocks={}
    )
    assert item3.content == ""

def test_title_property(tmp_path):
    """Test the title property with different scenarios."""
    from pyxie.types import ContentItem, ContentBlock
    
    # Test explicit title
    item1 = ContentItem(
        source_path=tmp_path / "test.md",
        metadata={"title": "Custom Title"},
        blocks={}
    )
    assert item1.title == "Custom Title"
    
    # Test title generated from slug
    item2 = ContentItem(
        source_path=tmp_path / "test-page.md",
        metadata={},
        blocks={}
    )
    assert item2.title == "Test Page"

def test_tags_property(tmp_path):
    """Test the tags property with different scenarios."""
    from pyxie.types import ContentItem, ContentBlock
    
    # Test with string tags
    item1 = ContentItem(
        source_path=tmp_path / "test.md",
        metadata={"tags": ["python", "testing"]},
        blocks={}
    )
    assert item1.tags == ["python", "testing"]
    
    # Test with no tags
    item2 = ContentItem(
        source_path=tmp_path / "test.md",
        metadata={},
        blocks={}
    )
    assert item2.tags == []
    
    # Test with mixed case tags (should be normalized)
    item3 = ContentItem(
        source_path=tmp_path / "test.md",
        metadata={"tags": ["Python", "TESTING", "web-dev"]},
        blocks={}
    )
    assert item3.tags == ["python", "testing", "web-dev"]

def test_serialization(tmp_path):
    """Test serialization and deserialization of ContentItem."""
    from pyxie.types import ContentItem, ContentBlock
    from datetime import datetime
    
    # Create a test item with various properties
    item = ContentItem(
        source_path=tmp_path / "test.md",
        metadata={
            "title": "Test Page",
            "tags": ["python", "testing"],
            "index": 42
        },
        blocks={
            "content": [ContentBlock(
                tag_name="markdown",
                content="Test content",
                attrs_str="",
                content_type="markdown"
            )],
            "scripts": [ContentBlock(
                tag_name="script",
                content="console.log('test')",
                attrs_str="",
                content_type="javascript"
            )]
        }
    )
    
    # Convert to dict
    data = item.to_dict()
    
    # Verify dict contains expected keys
    assert "slug" in data
    assert "content" in data
    assert "source_path" in data
    assert "metadata" in data
    assert "blocks" in data
    
    # Create new item from dict
    new_item = ContentItem.from_dict(data)
    
    # Verify properties match
    assert new_item.slug == item.slug
    assert new_item.title == item.title
    assert new_item.content == item.content
    assert new_item.tags == item.tags
    assert str(new_item.source_path) == str(item.source_path)
    assert len(new_item.blocks) == len(item.blocks)
    assert len(new_item.blocks["content"]) == len(item.blocks["content"])
    assert len(new_item.blocks["scripts"]) == len(item.blocks["scripts"])

def test_metadata_access(tmp_path):
    """Test accessing metadata through attributes."""
    from pyxie.types import ContentItem
    
    # Test accessing metadata through attributes
    item = ContentItem(
        source_path=tmp_path / "test.md",
        metadata={
            "title": "Test Page",
            "custom_field": "custom value",
            "nested": {"key": "value"}
        },
        blocks={}
    )
    
    # Test direct metadata access
    assert item.title == "Test Page"
    assert item.custom_field == "custom value"
    assert item.nested == {"key": "value"}
    
    # Test accessing non-existent metadata
    assert getattr(item, "nonexistent", None) is None

def test_status_property(tmp_path):
    """Test the status property."""
    from pyxie.types import ContentItem
    
    # Test with status set
    item1 = ContentItem(
        source_path=tmp_path / "test.md",
        metadata={"status": "draft"},
        blocks={}
    )
    assert item1.status == "draft"
    
    # Test without status
    item2 = ContentItem(
        source_path=tmp_path / "test.md",
        metadata={},
        blocks={}
    )
    assert item2.status is None

def test_collection_property(tmp_path):
    """Test the collection property."""
    from pyxie.types import ContentItem
    
    # Test with collection set
    item1 = ContentItem(
        source_path=tmp_path / "test.md",
        metadata={},
        blocks={},
        collection="blog"
    )
    assert item1.collection == "blog"
    
    # Test without collection
    item2 = ContentItem(
        source_path=tmp_path / "test.md",
        metadata={},
        blocks={}
    )
    assert item2.collection is None 