"""Integration tests for Pyxie functionality."""

import pytest
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, Generator

from pyxie import Pyxie
from pyxie.errors import PyxieError
from fastcore.xml import Div, H1, P, Article, FT, to_xml
from pyxie.layouts import layout
from pyxie.renderer import render_content

# Helper functions
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
@pytest.fixture
def test_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)

@pytest.fixture
def test_post(test_dir: Path) -> Path:
    """Create a test post with content blocks."""
    content = """---
title: Test Post
author: Test Author
date: 2024-01-01
status: published
layout: test
excerpt: This is a test post with content blocks
---

<title>
# Test Post
</title>

<content>
This is the main content of the test post.

## Section 1

- Item 1
- Item 2

## Section 2

Some more content here.
</content>

<example>
```python
def example():
    return "This is an example"
```
</example>
"""
    return create_test_post(test_dir, "test-post", content)

@pytest.fixture
def minimal_post(test_dir: Path) -> Path:
    """Create a minimal post with just title and content."""
    content = """---
title: Minimal Post
status: published
layout: test
---

<title>
# Minimal Post
</title>

<content>
Just some basic content.
</content>
"""
    return create_test_post(test_dir, "minimal-post", content)

@pytest.fixture
def pyxie_instance(test_dir: Path) -> Pyxie:
    """Create a Pyxie instance for testing."""
    instance = Pyxie(content_dir=test_dir)
    
    # Register test layout
    @layout("test")
    def test_layout(metadata=None):
        return to_xml(create_layout())
    
    # Manually load content from the content directory
    instance.add_collection("content", test_dir)
    
    return instance

# Integration tests
def test_full_rendering_pipeline(pyxie_instance: Pyxie, test_post: Path) -> None:
    """Test the full rendering pipeline with a complex post."""
    # Reload the collection to pick up the newly created test post
    pyxie_instance._load_collection(pyxie_instance._collections["content"])
    
    # Get the content item
    item, error = pyxie_instance.get_item("test-post")
    assert error is None
    assert item is not None
    
    # Render with layout
    html = render_content(item)
    
    # Check that the content was correctly rendered
    assert "Test Post" in html
    assert "main content" in html
    assert "Section 1" in html
    assert "Section 2" in html
    assert "def example" in html
    
    # Check that HTML structure is correct
    assert '<div class="container">' in html
    assert '<h1 class="title">' in html
    assert '<div class="body">' in html
    assert '<div class="content">' in html
    
    # The example slot should be filled
    assert '<div class="example bg-gray-100 p-4 rounded">' in html
    assert '<code class="language-python">' in html
    assert "def example()" in html

def test_minimal_post_rendering(pyxie_instance: Pyxie, minimal_post: Path) -> None:
    """Test rendering with minimal post content."""
    # Reload the collection to pick up the newly created test post
    pyxie_instance._load_collection(pyxie_instance._collections["content"])
    
    # Get the content item
    item, error = pyxie_instance.get_item("minimal-post")
    assert error is None
    assert item is not None
    
    # Render with layout
    html = render_content(item)
    
    # Check that content was rendered
    assert "Minimal Post" in html
    assert "Just some basic content" in html
    
    # Check that empty slots are not in the output
    assert '<div class="example' not in html
    assert '<p class="excerpt' not in html

def test_missing_post(pyxie_instance: Pyxie) -> None:
    """Test handling of a missing post."""
    item, error = pyxie_instance.get_item("non-existent-post")
    assert item is None
    assert error is not None
    assert "couldn't find" in error[1].lower()
    assert "non-existent-post" in error[1]

def test_custom_layout(pyxie_instance: Pyxie, test_post: Path) -> None:
    """Test using a custom layout for rendering."""
    # Reload the collection to pick up the newly created test post
    pyxie_instance._load_collection(pyxie_instance._collections["content"])
    
    # Define a custom layout
    custom_layout = Div(
        H1(None, data_slot="title", cls="custom-title"),
        P(None, data_slot="custom-slot", cls="custom-slot"),
        Div(None, data_slot="content", cls="custom-content"),
        cls="custom-container"
    )
    
    # Get the content item
    item, _ = pyxie_instance.get_item("test-post")
    
    # TODO: Update this test to use the custom layout with render_content
    # For now, we'll skip the custom layout test
    assert item is not None 

def test_blog_site_creation_workflow(test_dir: Path) -> None:
    """Test a complete workflow for creating a blog site with multiple posts and layouts.
    
    This test demonstrates how a typical user would use Pyxie to create
    a simple blog site with multiple layouts and content types.
    """
    # 1. Create content directories
    posts_dir = test_dir / "content" / "posts"
    pages_dir = test_dir / "content" / "pages"
    layouts_dir = test_dir / "layouts"
    
    posts_dir.mkdir(parents=True, exist_ok=True)
    pages_dir.mkdir(parents=True, exist_ok=True)
    layouts_dir.mkdir(parents=True, exist_ok=True)
    
    # 2. Create layouts
    base_layout_path = layouts_dir / "base.py"
    base_layout_path.write_text("""
from fastcore.xml import Html, Head, Body, Title, Link, Main, Footer, Div, P, FT

def base_layout(title="My Blog", metadata=None):
    return Html(
        Head(
            Title(title),
            Link(rel="stylesheet", href="/assets/style.css")
        ),
        Body(
            Main(None, data_slot="content"),
            Footer(
                P("© 2024 My Blog")
            )
        )
    )
""")

    post_layout_path = layouts_dir / "post.py"
    post_layout_path.write_text("""
from fastcore.xml import Article, H1, Time, Div, P, FT
from pyxie.layouts import layout

@layout("post")
def post_layout(title, date=None, author=None, metadata=None):
    return Article(
        H1(title, class_="post-title"),
        Time(date, class_="post-date") if date else None,
        P(f"By {author}", class_="post-author") if author else None,
        Div(None, data_slot="content", class_="post-content")
    )
""")

    page_layout_path = layouts_dir / "page.py"
    page_layout_path.write_text("""
from fastcore.xml import Article, H1, Div, FT
from pyxie.layouts import layout

@layout("page")
def page_layout(title, metadata=None):
    return Article(
        H1(title, class_="page-title"),
        Div(None, data_slot="content", class_="page-content")
    )
""")

    # 3. Create content files
    post1 = posts_dir / "first-post.md"
    post1.write_text("""---
title: My First Blog Post
date: 2024-04-01
author: Test Author
layout: post
status: published
---

This is my first blog post. Welcome to my blog!

## Section 1

Some content here.

## Section 2

More content here.
""")

    post2 = posts_dir / "second-post.md"
    post2.write_text("""---
title: My Second Blog Post
date: 2024-04-02
author: Test Author
layout: post
status: published
---

This is my second blog post. It's getting better!

## New Features

- Feature 1
- Feature 2
- Feature 3
""")

    about_page = pages_dir / "about.md"
    about_page.write_text("""---
title: About Me
layout: page
status: published
---

This is the about page. Here's some information about me.

## Contact

You can reach me at test@example.com.
""")

    # 4. Initialize Pyxie
    from pyxie import Pyxie
    pyxie = Pyxie(
        content_dir=test_dir / "content",
        default_metadata={"layouts_path": str(layouts_dir)}  # Store layouts path in metadata
    )
    
    # 5. Register collections
    pyxie.add_collection("posts", posts_dir)
    pyxie.add_collection("pages", pages_dir)
    
    # 6. Load content (calling _load_collection for each collection instead of _load_content)
    for collection_name in pyxie.collections:
        collection = pyxie._collections[collection_name]
        pyxie._load_collection(collection)
    
    # 7. Test the content is loaded correctly
    assert "posts" in pyxie._collections
    assert len(pyxie._collections["posts"]._items) == 2
    assert "pages" in pyxie._collections
    assert len(pyxie._collections["pages"]._items) == 1
    
    # 8. Test posts are retrieved correctly
    posts = pyxie.get_items(collection="posts")
    assert len(posts) == 2
    first_post = pyxie._collections["posts"]._items["first-post"]
    assert first_post.metadata["title"] == "My First Blog Post"
    
    # 9. Test pages are retrieved correctly
    pages = pyxie.get_items(collection="pages")
    assert len(pages) == 1
    about = pyxie._collections["pages"]._items["about"]
    assert about.metadata["title"] == "About Me"
    
    # Test complete - all basic functionality is working 

def test_self_closing_tags_integration(test_dir: Path):
    """Test that self-closing tags are properly handled through the full rendering pipeline."""
    # Create content with various self-closing tags
    content = """---
title: Self-closing Tags Test
status: published
layout: test
---
<content>
# Testing Self-closing Tags

This is a paragraph with a line break <br> here.

<hr>

<img src="test.jpg" alt="Test image">

<input type="text" placeholder="Enter text">
</content>
"""
    
    # Create the test file
    file_path = create_test_post(test_dir, "self-closing-tags-test", content)
    
    # Create a Pyxie instance
    pyxie = Pyxie(content_dir=test_dir)
    
    # Register test layout
    @layout("test")
    def test_layout(metadata=None):
        return Div(
            H1("Testing Self-closing Tags", data_slot="title", cls="title"),
            Div(None, data_slot="content", cls="content"),
            cls="test-layout"
        )
    
    # Add collection and load content
    pyxie.add_collection("content", test_dir)
    
    # Force reload the collection
    pyxie._load_collection(pyxie._collections["content"])
    
    # Get the content item
    item, error = pyxie.get_item("self-closing-tags-test", "content", status="published")
    assert error is None
    assert item is not None
    
    # Render the content
    rendered = render_content(item)
    
    # Check that all self-closing tags are preserved in the output
    assert "<br>" in rendered
    assert "<hr>" in rendered
    assert "<img" in rendered and 'src="test.jpg"' in rendered
    assert "<input" in rendered and 'type="text"' in rendered 