"""Integration tests for Pyxie."""

import pytest
import logging
from pathlib import Path
from mistletoe import Document
from mistletoe.block_token import Heading, Paragraph, List, HtmlBlock
from fastcore.xml import FT, Div, H1, P, Span, Button, Time, Article, Img, Br, Hr, Input, to_xml

from pyxie.renderer import PyxieRenderer
from pyxie.parser import RawBlockToken, NestedContentToken, parse_frontmatter
from pyxie import Pyxie
from pyxie.errors import PyxieError
from pyxie.utilities import normalize_tags
from pyxie.layouts import layout, registry
from pyxie.types import ContentItem
from pyxie.renderer import render_content

logger = logging.getLogger(__name__)

# Helper functions
def create_test_file(content: str, path: Path) -> None:
    """Create a test file with the given content."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)

def create_test_post(dir_path: Path, filename: str, content: str) -> Path:
    """Create a test post file with the given content."""
    file_path = dir_path / f"{filename}.md"
    file_path.write_text(content)
    return file_path

def create_layout() -> FT:
    """Create a test layout with various slots."""
    return Div(
        H1(None, data_slot="title", cls="title"),
        Div(
            P(None, data_slot="excerpt", cls="excerpt"),
            Div(None, data_slot="content", cls="content"),
            Div(None, data_slot="example", cls="example bg-gray-100 p-4 rounded"),
            cls="body"
        ),
        cls="container"
    )

# Test fixtures
@pytest.fixture(autouse=True)
def setup_test_layout():
    """Set up test layout for all tests."""
    # Clear any existing layouts
    registry._layouts.clear()
    
    @layout("default")
    def default_layout(content: str = "") -> FT:
        """Default layout that just renders the content directly."""
        return Div(data_slot="main_content")
        
    @layout("page")
    def page_layout(content: str = "") -> FT:
        """Page layout with header and footer."""
        return Div(
            Div("Header", cls="header"),
            Div(data_slot="main_content", cls="content"),
            Div("Footer", cls="footer")
        )
        
    @layout("test")
    def test_layout(content: str = "") -> FT:
        """Test layout with content and sidebar."""
        return Div(
            Div(data_slot="main_content", cls="content"),
            Div(data_slot="page_sidebar", cls="sidebar")
        )
        
    @layout("blog")
    def blog_layout(content: str = "", title: str = "", date: str = None, author: str = None) -> FT:
        """Blog post layout."""
        return Article(
            H1(title, cls="title"),
            Time(date) if date else None,
            P(f"By {author}") if author else None,
            Div(data_slot="main_content", cls="content"),
            cls="blog-post"
        )
        
    @layout("custom")
    def custom_layout(title: str = "Custom Title", metadata=None) -> FT:
        """Custom layout for testing."""
        metadata = metadata or {}
        return Div(
            H1(metadata.get("title", title), cls="title"),
            Div(data_slot="page_header", cls="header"),
            Div(data_slot="page_toc", cls="toc"),
            Div(data_slot="main_content", cls="content"),
            Div(data_slot="page_sidebar", cls="sidebar"),
            cls="custom-layout"
        )
    
    @layout("post")
    def post_layout(title, date=None, author=None, metadata=None):
        metadata = metadata or {}
        return Article(
            H1(title, cls="post-title"),
            Time(date, cls="post-date") if date else None,
            P(f"By {author}", cls="post-author") if author else None,
            Div(None, data_slot="main_content", cls="post-content")
        )

    @layout("page")
    def page_layout(title, metadata=None):
        metadata = metadata or {}
        return Article(
            H1(title, cls="page-title"),
            Div(None, data_slot="main_content", cls="page-content")
        )
    
    # Verify layouts are registered
    assert "default" in registry
    assert "page" in registry
    assert "test" in registry
    assert "blog" in registry
    assert "custom" in registry

@pytest.fixture
def test_dir(tmp_path):
    """Create a temporary test directory."""
    return tmp_path

@pytest.fixture
def test_post(test_dir):
    """Create a test post file."""
    post = test_dir / "test_post.md"
    post.write_text("""
# Test Post

This is a test post with multiple content blocks.

<main_content>
**Main** content with *formatting*
</main_content>

<page_sidebar>
- Item 1
- Item 2
</page_sidebar>
""")
    return post

@pytest.fixture
def minimal_post(test_dir):
    """Create a minimal test post."""
    post = test_dir / "minimal.md"
    post.write_text("""<main_content>
# Minimal Post

Just some content.
</main_content>""")
    return post

@pytest.fixture
def pyxie_instance(test_dir):
    """Create a Pyxie instance for testing."""
    instance = Pyxie(content_dir=test_dir)
    
    # Register test layout
    @layout("test")
    def test_layout() -> FT:
        return Div(
            Div(data_slot="main_content", cls="content"),
            Div(data_slot="page_sidebar", cls="sidebar")
        )
    
    # Add collection
    instance.add_collection("content", test_dir)
    
    return instance

@pytest.fixture
def blog_post(test_dir):
    """Create a test blog post file."""
    post = test_dir / "blog_post.md"
    post.write_text("""---
layout: blog
title: My First Blog Post
date: 2024-04-01
author: Test Author
---

<main_content>
This is my first blog post. Welcome to my blog!

## Section 1

Some content here.

## Section 2

More content here.
</main_content>""")
    return post

@pytest.fixture
def self_closing_tags_post(test_dir):
    """Create a test post with self-closing tags."""
    post = test_dir / "self_closing_tags.md"
    post.write_text("""<main_content>
<img src="test.jpg" alt="Test Image"/>
<br/>
<hr/>
<input type="text" value="test"/>
</main_content>""")
    return post

# Integration tests
def test_full_rendering_pipeline(test_post):
    """Test the full rendering pipeline with a complex post."""
    # Parse the content
    content = test_post.read_text()
    metadata, _ = parse_frontmatter(content)
    
    # Create content item
    item = ContentItem(
        source_path=test_post,
        metadata={"layout": "test"},
        content=content
    )
    
    # Render content
    html = render_content(item)
    
    # Verify content
    assert "Main" in html
    assert "formatting" in html
    assert "Item 1" in html
    assert "Item 2" in html
    assert 'class="content"' in html
    assert 'class="sidebar"' in html

def test_minimal_post_rendering(minimal_post):
    """Test rendering of a minimal post."""
    # Parse the content
    content = minimal_post.read_text()
    metadata, _ = parse_frontmatter(content)
    
    # Create content item
    item = ContentItem(
        source_path=minimal_post,
        metadata={"layout": "default"},
        content=content
    )
    
    # Render content
    html = render_content(item)
    
    # Verify content
    assert '<h1 id="minimal-post">Minimal Post</h1>' in html
    assert "Just some content" in html

def test_blog_post_rendering(blog_post):
    """Test rendering a blog post with metadata."""
    # Parse the content
    content = blog_post.read_text()
    metadata, _ = parse_frontmatter(content)
    
    # Create content item
    item = ContentItem(
        source_path=blog_post,
        metadata=metadata,  # Use the parsed metadata
        content=content
    )
    
    # Render content
    html = render_content(item)
    
    # Verify content
    assert "My First Blog Post" in html
    assert "Test Author" in html
    assert "2024-04-01" in html
    assert '<h2 id="section-1">Section 1</h2>' in html

def test_self_closing_tags(self_closing_tags_post):
    """Test handling of self-closing tags."""
    # Parse the content
    content = self_closing_tags_post.read_text()
    metadata, _ = parse_frontmatter(content)

    # Create content item
    item = ContentItem(
        source_path=self_closing_tags_post,
        metadata={"layout": "default"},
        content=content
    )

    # Render content
    html = render_content(item)

    # Verify content - note that self-closing tags are rendered as HTML
    assert 'src="test.jpg"' in html
    assert 'alt="Test Image"' in html
    assert '<img' in html
    assert '<br' in html
    assert '<hr' in html
    assert '<input' in html
    assert 'type="text"' in html
    assert 'value="test"' in html

def test_custom_content_blocks():
    """Test handling of custom XML-like content blocks."""
    content = """---
title: Test Document
layout: custom
---

<page_header>
# Welcome to my site
</page_header>

<page_toc>
- Introduction
- Features
- Conclusion
</page_toc>

<main_content>
This is the main content.
</main_content>

<page_sidebar>
- Recent posts
- Categories
</page_sidebar>
"""
    # Parse the content
    metadata, content = parse_frontmatter(content)
    
    # Create content item
    item = ContentItem(
        source_path=Path("test.md"),
        metadata=metadata,
        content=content
    )
    
    # Render content
    html = render_content(item)
    
    # Verify content blocks are rendered correctly
    assert '<h1 id="welcome-to-my-site">Welcome to my site</h1>' in html

def test_custom_layout(test_dir):
    """Test using a custom layout for rendering."""
    # Create a test post with custom layout
    post = test_dir / "custom_layout_post.md"
    post.write_text("""---
title: Custom Layout Test
layout: custom
---

<main_content>
# Content
</main_content>
""")
    
    # Parse the content
    content = post.read_text()
    metadata, _ = parse_frontmatter(content)
    
    # Create content item
    item = ContentItem(
        source_path=post,
        metadata=metadata,  # Use the parsed metadata
        content=content
    )
    
    # Render content
    html = render_content(item)
    
    # Verify content
    assert "Custom Layout Test" in html  # Title comes from metadata
    assert '<h1 id="content">Content</h1>' in html

def test_full_pipeline_with_frontmatter():
    """Test the full pipeline with frontmatter and various content types."""
    content = """---
title: Test Document
author: Test Author
date: 2024-01-01
layout: test
---

<main_content>
# Introduction

This is a test document with various content types.

<ft>
show(Div("Hello from FastHTML"))
</ft>

<script>
console.log("Hello from script");
</script>

<custom-block>
This is a content block
</custom-block>
</main_content>
"""
    # Parse the content
    metadata, _ = parse_frontmatter(content)
    
    # Create content item
    item = ContentItem(
        source_path=Path("test.md"),
        metadata=metadata,
        content=content
    )
    
    # Render content
    html = render_content(item)
    
    # Verify content
    assert '<h1 id="introduction">Introduction</h1>' in html
    assert "Hello from FastHTML" in html
    assert "This is a content block" in html
    assert 'class="content"' in html  # Verify layout class

def test_full_pipeline_with_fasthtml_and_layout():
    """Test the full pipeline with FastHTML and layout."""
    content = """---
title: Test Document
layout: custom
---

<main_content>
<ft>
show(Div("Hello from FastHTML"))
</ft>
</main_content>
"""
    # Parse the content
    metadata, _ = parse_frontmatter(content)
    
    # Create content item
    item = ContentItem(
        source_path=Path("test.md"),
        metadata=metadata,
        content=content
    )
    
    # Render content
    html = render_content(item)
    
    # Verify content
    assert "Test Document" in html
    assert "Hello from FastHTML" in html
    assert 'class="title"' in html
    assert 'class="content"' in html  # Verify layout class

def test_blog_site_creation_workflow(tmp_path):
    """Test the complete workflow of creating a blog site."""
    test_dir = tmp_path / "blog"
    test_dir.mkdir()
    
    # Create content directory
    content_dir = test_dir / "content"
    content_dir.mkdir()
    
    # Create a test post
    post = content_dir / "first-post.md"
    post.write_text("""---
title: My First Post
date: 2024-01-01
---
This is my first post.
""")
    
    # Initialize Pyxie
    instance = Pyxie(content_dir=test_dir)
    assert "content" in instance.collections
    collection = instance._collections["content"]
    assert collection.path == test_dir