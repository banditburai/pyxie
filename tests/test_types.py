import pytest
from pyxie.types import ContentItem, RenderResult
from pyxie.layouts import layout, registry
from pathlib import Path
from datetime import datetime

@pytest.fixture(autouse=True)
def setup_test_layout():
    """Set up test layout for all tests."""
    registry._layouts.clear()
    
    @layout("minimal")
    def minimal_layout(content: str = "") -> str:
        """Minimal layout that just renders the content directly."""
        if content is None:
            return '<div class="error">Error: Content is None</div>'
        return f'<div data-slot="main_content">{content}</div>'

@pytest.fixture
def create_test_item(tmp_path):
    def _create_test_item(content=None, metadata=None, index=0):
        content = content or "Test content"
        metadata = metadata or {}
        source_path = tmp_path / "test.md"
        source_path.write_text(content)
        return ContentItem(
            content=content,
            metadata=metadata,
            source_path=source_path,
            index=index
        )
    return _create_test_item

def test_image_property(tmp_path):
    """Test the image property with different scenarios."""
    # Test with direct image URL
    item1 = ContentItem(
        source_path=tmp_path / "test.md",
        metadata={"image": "https://example.com/image.jpg"},
        content="Test content"
    )
    assert item1.image == "https://example.com/image.jpg"
    
    # Test with featured image
    item2 = ContentItem(
        source_path=tmp_path / "test.md",
        metadata={"featured_image": "https://example.com/featured.jpg"},
        content="Test content"
    )
    assert item2.image == "https://example.com/featured.jpg"
    
    # Test with image template
    item3 = ContentItem(
        source_path=tmp_path / "test.md",
        metadata={
            "image_template": "https://example.com/{seed}.jpg",
            "image_width": "800",
            "image_height": "600"
        },
        content="Test content",
        index=42
    )
    assert item3.image.startswith("https://example.com/")
    assert item3.image.endswith(".jpg")
    assert "0042-test" in item3.image  # The seed should include the index and slug
    
    # Test with no image
    item4 = ContentItem(
        source_path=tmp_path / "test.md",
        metadata={},
        content="Test content"
    )
    assert item4.image is None
    
    # Test with invalid template (missing required format parameter)
    item5 = ContentItem(
        source_path=tmp_path / "test.md",
        metadata={
            "image_template": "https://example.com/{missing_param}.jpg"
        },
        content="Test content"
    )
    assert item5.image is None  # Should return None when template formatting fails

def test_slug_property(tmp_path):
    """Test the slug property with different scenarios."""
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
    
    # Test explicit slug setting
    item3 = ContentItem(
        source_path=tmp_path / "test.md",
        metadata={},
        content=""
    )
    item3.slug = "explicit-slug"
    assert item3.slug == "explicit-slug"

def test_title_property(tmp_path):
    """Test the title property with different scenarios."""
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
    # Create a test item with various properties
    item = ContentItem(
        source_path=tmp_path / "test.md",
        metadata={
            "title": "Test Page",
            "tags": ["python", "testing"],
            "index": 42
        },
        content="Test content",
        index=42
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
    with pytest.raises(AttributeError):
        _ = item.nonexistent

def test_status_property(tmp_path):
    """Test the status property."""
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
    # Test with collection set
    item1 = ContentItem(
        source_path=tmp_path / "test.md",
        metadata={},
        content="",
        collection="blog"
    )
    assert item1.collection == "blog"
    
    # Test with no collection
    item2 = ContentItem(
        source_path=tmp_path / "test.md",
        metadata={},
        content=""
    )
    assert item2.collection is None

def test_render_result():
    """Test the RenderResult class."""
    # Test successful result
    result1 = RenderResult(content="<div>Success</div>")
    assert result1.success is True
    assert result1.error is None
    
    # Test result with error class in content
    result2 = RenderResult(content='<div class="error">Error</div>')
    assert result2.success is False
    assert result2.error is None
    
    # Test result with error message
    result3 = RenderResult(content="<div>Content</div>", error="Test error")
    assert result3.success is False
    assert result3.error == "Test error"
    
    # Test result with both error class and error message
    result4 = RenderResult(content='<div class="error">Error</div>', error="Test error")
    assert result4.success is False
    assert result4.error == "Test error"

def test_post_init_behavior(tmp_path):
    """Test the post-initialization behavior of ContentItem."""
    # Test with Path object
    item1 = ContentItem(
        source_path=tmp_path / "test-page.md",
        metadata={},
        content=""
    )
    assert item1.title == "Test Page"
    
    # Test with string path
    item2 = ContentItem(
        source_path=str(tmp_path / "test-page.md"),
        metadata={},
        content=""
    )
    assert item2.title == "Test Page"
    
    # Test with multiple hyphens
    item3 = ContentItem(
        source_path=tmp_path / "my-test-page.md",
        metadata={},
        content=""
    )
    assert item3.title == "My Test Page"
    
    # Test with special characters
    item4 = ContentItem(
        source_path=tmp_path / "test_page@123.md",
        metadata={},
        content=""
    )
    assert item4.title == "Test Page@123"

def test_getattr_behavior(tmp_path):
    """Test the attribute access behavior of ContentItem."""
    # Test with nested metadata
    item1 = ContentItem(
        source_path=tmp_path / "test.md",
        metadata={
            "nested": {"key": "value"},
            "list": [1, 2, 3],
            "number": 42,
            "boolean": True
        },
        content=""
    )
    assert item1.nested == {"key": "value"}
    assert item1.list == [1, 2, 3]
    assert item1.number == 42
    assert item1.boolean is True
    
    # Test with non-string metadata keys
    item2 = ContentItem(
        source_path=tmp_path / "test.md",
        metadata={
            42: "number key",
            True: "boolean key",
            None: "none key"
        },
        content=""
    )
    assert item2.metadata[42] == "number key"
    assert item2.metadata[True] == "boolean key"
    assert item2.metadata[None] == "none key"
    
    # Test missing attribute
    with pytest.raises(AttributeError) as exc_info:
        _ = item2.nonexistent
    assert str(exc_info.value) == "'ContentItem' has no attribute 'nonexistent'"

def test_image_property_edge_cases(tmp_path):
    """Test edge cases for the image property."""
    # Test with malformed URL
    item1 = ContentItem(
        source_path=tmp_path / "test.md",
        metadata={"image": "not a valid url"},
        content=""
    )
    assert item1.image == "not a valid url"  # Should still return the value even if invalid
    
    # Test with complex template
    item2 = ContentItem(
        source_path=tmp_path / "test.md",
        metadata={
            "image_template": "https://example.com/{width}x{height}/{seed}.jpg",
            "image_width": "800",
            "image_height": "600"
        },
        content="",
        index=42
    )
    assert item2.image.startswith("https://example.com/800x600/")
    assert item2.image.endswith(".jpg")
    
    # Test with missing template parameters
    item3 = ContentItem(
        source_path=tmp_path / "test.md",
        metadata={
            "image_template": "https://example.com/{width}x{height}/{seed}.jpg",
            "image_width": "800"  # Missing height
        },
        content=""
    )
    assert item3.image is None  # Should return None when template formatting fails
    
    # Test with invalid template format
    item4 = ContentItem(
        source_path=tmp_path / "test.md",
        metadata={
            "image_template": "https://example.com/{invalid:format}.jpg"
        },
        content=""
    )
    assert item4.image is None  # Should return None for invalid format strings 