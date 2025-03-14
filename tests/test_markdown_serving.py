import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.requests import Request
from starlette.responses import Response

from pyxie import Pyxie
from pyxie.types import ContentItem


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
        slug="test-post",
        content="# Test Content\n\nThis is test markdown content.",
        source_path=test_md_file,
        metadata={
            "title": "Test Post",
            "tags": ["test"],
            "date": "2025-03-14"
        }
    )
    
    # Create a mock for the get_item method
    def mock_get_item(slug, **kwargs):
        if slug == "test-post":
            return mock_item, None
        elif slug == "no-source":
            no_source_item = ContentItem(
                slug="no-source",
                content="No source content",
                source_path=None,
                metadata={"title": "No Source"}
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