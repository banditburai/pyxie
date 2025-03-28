def test_image_property(tmp_path):
    """Test the image property with different scenarios."""
    from pyxie.types import ContentItem
    
    # Create a dummy source path
    source_path = tmp_path / "test.md"
    
    # Test with direct image URL
    item1 = ContentItem(
        source_path=source_path,
        metadata={"image": "https://example.com/image.jpg", "title": "Test 1"},
        content="Test content"
    )
    assert item1.image == "https://example.com/image.jpg"
    
    # Test with image template
    item2 = ContentItem(
        source_path=source_path,
        metadata={
            "image_template": "https://example.com/{seed}.jpg",
            "title": "Test 2",
            "index": 42
        },
        content="Test content"
    )
    assert item2.image.startswith("https://example.com/")
    assert item2.image.endswith(".jpg")
    assert "0042-test" in item2.image  # The seed should include the index and slug
    
    # Test with no image
    item3 = ContentItem(
        source_path=source_path,
        metadata={"title": "Test 3"},
        content="Test content"
    )
    assert item3.image is None

def test_slug_property(tmp_path):
    """Test the slug property with different scenarios."""
    from pyxie.types import ContentItem
    
    # Test slug from source path
    item1 = ContentItem(
        source_path=tmp_path / "test-page.md",
        metadata={},
        content=""
    )
    assert item1.slug == "test-page"
    
    # Test slug from metadata
    item2 = ContentItem(
        source_path=tmp_path / "test.md",
        metadata={"slug": "custom-slug"},
        content=""
    )
    assert item2.slug == "custom-slug"
    
    # Test explicit slug
    item3 = ContentItem(
        source_path=tmp_path / "test.md",
        metadata={},
        content=""
    )
    item3.slug = "explicit-slug"
    assert item3.slug == "explicit-slug"

def test_content_property(tmp_path):
    """Test the content property with different scenarios."""
    from pyxie.types import ContentItem
    
    # Test with content
    item1 = ContentItem(
        source_path=tmp_path / "test.md",
        metadata={},
        content="Test content"
    )
    assert item1.content == "Test content"
    
    # Test with empty content
    item2 = ContentItem(
        source_path=tmp_path / "test.md",
        metadata={},
        content=""
    )
    assert item2.content == ""

def test_title_property(tmp_path):
    """Test the title property with different scenarios."""
    from pyxie.types import ContentItem
    
    # Test explicit title
    item1 = ContentItem(
        source_path=tmp_path / "test.md",
        metadata={"title": "Custom Title"},
        content=""
    )
    assert item1.title == "Custom Title"
    
    # Test title from slug
    item2 = ContentItem(
        source_path=tmp_path / "test-page.md",
        metadata={},
        content=""
    )
    assert item2.title == "Test Page"
    
    # Test title from metadata slug
    item3 = ContentItem(
        source_path=tmp_path / "test.md",
        metadata={"slug": "custom-slug"},
        content=""
    )
    assert item3.title == "Custom Slug"

def test_tags_property(tmp_path):
    """Test the tags property with different scenarios."""
    from pyxie.types import ContentItem
    
    # Test with string tags
    item1 = ContentItem(
        source_path=tmp_path / "test.md",
        metadata={"tags": ["python", "testing"]},
        content=""
    )
    assert item1.tags == ["python", "testing"]
    
    # Test with no tags
    item2 = ContentItem(
        source_path=tmp_path / "test.md",
        metadata={},
        content=""
    )
    assert item2.tags == []
    
    # Test with mixed case tags
    item3 = ContentItem(
        source_path=tmp_path / "test.md",
        metadata={"tags": ["Python", "TESTING", "django"]},
        content=""
    )
    assert item3.tags == ["django", "python", "testing"]

def test_serialization(tmp_path):
    """Test serialization and deserialization of ContentItem."""
    from pyxie.types import ContentItem
    from datetime import datetime
    
    # Create a test item with various properties
    item = ContentItem(
        source_path=tmp_path / "test.md",
        metadata={
            "title": "Test Page",
            "tags": ["python", "testing"],
            "index": 42
        },
        content="Test content"
    )
    
    # Convert to dictionary
    data = item.to_dict()
    
    # Verify dictionary contents
    assert data["slug"] == "test"
    assert data["content"] == "Test content"
    assert data["metadata"]["title"] == "Test Page"
    assert data["metadata"]["tags"] == ["python", "testing"]
    assert data["metadata"]["index"] == 42
    
    # Create new item from dictionary
    new_item = ContentItem.from_dict(data)
    
    # Verify properties are preserved
    assert new_item.title == item.title
    assert new_item.tags == item.tags
    assert new_item.content == item.content
    assert new_item.metadata["index"] == item.metadata["index"]

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
        content=""
    )
    
    # Test direct metadata access
    assert item.title == "Test Page"
    assert item.custom_field == "custom value"
    assert item.nested == {"key": "value"}
    
    # Test missing attribute
    try:
        _ = item.nonexistent
        assert False, "Should raise AttributeError"
    except AttributeError:
        pass

def test_status_property(tmp_path):
    """Test the status property."""
    from pyxie.types import ContentItem
    
    # Test with status set
    item1 = ContentItem(
        source_path=tmp_path / "test.md",
        metadata={"status": "draft"},
        content=""
    )
    assert item1.status == "draft"
    
    # Test with no status
    item2 = ContentItem(
        source_path=tmp_path / "test.md",
        metadata={},
        content=""
    )
    assert item2.status is None

def test_collection_property(tmp_path):
    """Test the collection property."""
    from pyxie.types import ContentItem
    
    # Test with collection set
    item1 = ContentItem(
        source_path=tmp_path / "test.md",
        metadata={},
        content="",
        collection="blog"
    )
    assert item1.collection == "blog"
    
    # Test without collection
    item2 = ContentItem(
        source_path=tmp_path / "test.md",
        metadata={},
        content=""
    )
    assert item2.collection is None 