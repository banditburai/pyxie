import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.responses import Response

from pyxie import Pyxie
from pyxie.types import ContentItem
from pyxie.parser import NestedContentToken


@pytest.fixture
def test_md_file():
    """Create a temporary markdown file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as temp:
        temp.write(b"# Test Content\n\nThis is test markdown content.")
        temp_path = Path(temp.name)
    
    yield temp_path
    
    # Clean up
    os.unlink(temp_path)


@pytest.fixture
def pyxie_instance(test_md_file):
    """Create a Pyxie instance with mocked get_item method."""
    instance = Pyxie(content_dir=".")
    
    # Create a mock item that will be returned by get_item
    mock_item = ContentItem(
        source_path=test_md_file,
        metadata={
            "title": "Test Post",
            "tags": ["test"],
            "date": "2025-03-14"
        },
        content="# Test Content\n\nThis is test markdown content."
    )
    
    # Create a mock for the get_item method
    def mock_get_item(slug, **kwargs):
        if slug == "test-post":
            return mock_item, None
        elif slug == "no-source":
            no_source_item = ContentItem(
                source_path=None,
                metadata={"title": "No Source"},
                content="No source content"
            )
            return no_source_item, None
        else:
            return None, ("Post Not Found", f"Sorry, we couldn't find a post matching '{slug}'")
    
    # Replace the get_item method with our mock
    instance.get_item = mock_get_item
    
    return instance


def test_get_raw_content(pyxie_instance, test_md_file):
    """Test retrieving raw markdown content."""
    # Get content for existing item
    content = pyxie_instance.get_raw_content("test-post")
    assert content == "# Test Content\n\nThis is test markdown content."
    
    # Test with non-existent slug
    assert pyxie_instance.get_raw_content("non-existent") is None
    
    # Test with item that has no source path
    assert pyxie_instance.get_raw_content("no-source") is None
    
    # Test with file read error
    with patch.object(Path, 'read_text', side_effect=Exception("File read error")):
        assert pyxie_instance.get_raw_content("test-post") is None


@pytest.mark.asyncio
async def test_serve_md_middleware(pyxie_instance, test_md_file):
    """Test the markdown serving middleware."""
    middleware = pyxie_instance.serve_md()
    middleware_class = middleware.cls
    
    # Create middleware instance
    app = AsyncMock()
    middleware_instance = middleware_class(app)
    
    # Mock the read_text method to return our content
    with patch.object(Path, 'read_text', return_value="# Test Content\n\nThis is test markdown content."):
        # Test request for .md file
        md_request = MagicMock()
        md_request.url.path = "/blog/test-post.md"
        
        response = await middleware_instance.dispatch(md_request, AsyncMock())
        assert isinstance(response, Response)
        assert response.media_type == "text/markdown"
        assert response.body == b"# Test Content\n\nThis is test markdown content."
        
        # Test request for non-existent md file
        md_request.url.path = "/blog/non-existent.md"
        call_next = AsyncMock()
        await middleware_instance.dispatch(md_request, call_next)
        call_next.assert_called_once()
        
        # Test regular HTML request (non-md extension)
        html_request = MagicMock()
        html_request.url.path = "/blog/test-post"
        call_next = AsyncMock()
        await middleware_instance.dispatch(html_request, call_next)
        call_next.assert_called_once()


@pytest.mark.asyncio
async def test_serve_md_middleware_with_url_fragments(pyxie_instance, test_md_file):
    """Test the markdown serving middleware with URL fragments and query parameters."""
    middleware = pyxie_instance.serve_md()
    middleware_class = middleware.cls
    
    # Create middleware instance
    app = AsyncMock()
    middleware_instance = middleware_class(app)
    
    # Mock the read_text method to return our content
    with patch.object(Path, 'read_text', return_value="# Test Content\n\nThis is test markdown content."):
        # Test with anchor fragment
        anchor_request = MagicMock()
        anchor_request.url.path = "/blog/test-post.md"
        anchor_request.url.fragment = "heading-1"  # URL might be /blog/test-post.md#heading-1
        
        response = await middleware_instance.dispatch(anchor_request, AsyncMock())
        assert isinstance(response, Response)
        assert response.media_type == "text/markdown"
        assert response.body == b"# Test Content\n\nThis is test markdown content."
        
        # Test with query parameters
        query_request = MagicMock()
        query_request.url.path = "/blog/test-post.md"
        query_request.url.query = "version=1&highlight=true"  # URL might be /blog/test-post.md?version=1&highlight=true
        
        response = await middleware_instance.dispatch(query_request, AsyncMock())
        assert isinstance(response, Response)
        assert response.media_type == "text/markdown"
        assert response.body == b"# Test Content\n\nThis is test markdown content."
        
        # Handle edge case: unusual characters in slug path that would be affected by os.path.basename
        unusual_request = MagicMock()
        unusual_request.url.path = "/blog/test-post-with-unusual-chars.md"
        
        # Here we patch get_raw_content directly to return content for our specific test case
        with patch.object(pyxie_instance, 'get_raw_content', return_value="Special content"):
            response = await middleware_instance.dispatch(unusual_request, AsyncMock())
            assert isinstance(response, Response)
            assert response.media_type == "text/markdown"
            assert response.body == b"Special content"


@pytest.mark.asyncio
async def test_serve_md_middleware_with_complex_urls(pyxie_instance):
    """Test the markdown serving middleware with complex URLs that combine path, anchors and query params."""
    middleware = pyxie_instance.serve_md()
    middleware_class = middleware.cls
    
    app = AsyncMock()
    middleware_instance = middleware_class(app)
    
    # Set up a mock for get_raw_content to track what slug is being requested
    with patch.object(pyxie_instance, 'get_raw_content') as mock_get_content:
        mock_get_content.return_value = "# Content for test"
        
        # Test case: URL with both query params and anchors in actual URL
        # This simulates when a user clicks on a .md link while they're on a page with an anchor
        complex_request = MagicMock()
        complex_request.url.path = "/blog/test-post.md"
        complex_request.url.query = "version=2"
        complex_request.url.fragment = "section-2"
        
        await middleware_instance.dispatch(complex_request, AsyncMock())
        
        # Verify the slug extraction was correct (should just be "test-post")
        mock_get_content.assert_called_with("test-post")
        
        # Complex case: nested paths with unusual URL encoding
        encoded_request = MagicMock()
        encoded_request.url.path = "/blog/category/test-post%20with%20spaces.md"
        
        await middleware_instance.dispatch(encoded_request, AsyncMock())
        
        # The slug should be just "test-post with spaces" after URL decoding
        # and Path.basename handling
        assert mock_get_content.call_args[0][0] in ("test-post with spaces", "test-post%20with%20spaces") 