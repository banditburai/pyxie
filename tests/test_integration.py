"""Integration tests for Pyxie functionality."""

import pytest
from pathlib import Path
from pyxie import Pyxie
from fastcore.xml import Div, H1, P, FT, to_xml, Time, Article, Img, Br, Hr, Input
from pyxie.layouts import layout, registry
from pyxie.renderer import render_content
from pyxie.parser import parse_frontmatter, FastHTMLToken, ScriptToken, NestedContentToken
from mistletoe.block_token import add_token
from fastcore.xml import FT, Div, H1, P, Span, Button
from pyxie.types import ContentItem
from pyxie.parser import FastHTMLToken, ScriptToken, NestedContentToken, parse_frontmatter
from pyxie.renderer import render_content
from pyxie.layouts import layout, registry
from pyxie.errors import PyxieError
from pyxie.utilities import normalize_tags

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
@pytest.fixture(autouse=True)
def setup_test_layout():
    """Set up test layout for all tests."""
    # Clear any existing layouts
    registry._layouts.clear()
    
    @layout("default")
    def default_layout(content: str = "") -> FT:
        """Default layout that just renders the content directly."""
        return Div(data_slot="content")
        
    @layout("page")
    def page_layout(content: str = "") -> FT:
        """Page layout with header and footer."""
        return Div(
            Div("Header", cls="header"),
            Div(data_slot="content", cls="content"),
            Div("Footer", cls="footer")
        )
        
    @layout("test")
    def test_layout(content: str = "") -> FT:
        """Test layout with content and sidebar."""
        return Div(
            Div(data_slot="content", cls="content"),
            Div(data_slot="sidebar", cls="sidebar")
        )
        
    @layout("blog")
    def blog_layout(content: str = "", title: str = "", date: str = None, author: str = None) -> FT:
        """Blog post layout."""
        return Article(
            H1(title, cls="title"),
            Time(date) if date else None,
            P(f"By {author}") if author else None,
            Div(content, data_slot="content"),
            cls="blog-post"
        )

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

<content>
**Main** content with *formatting*
</content>

<sidebar>
- Item 1
- Item 2
</sidebar>
""")
    return post

@pytest.fixture
def minimal_post(test_dir):
    """Create a minimal test post."""
    post = test_dir / "minimal.md"
    post.write_text("# Minimal Post\n\nJust some content.")
    return post

@pytest.fixture
def pyxie_instance(test_dir):
    """Create a Pyxie instance for testing."""
    instance = Pyxie(content_dir=test_dir)
    
    # Register test layout
    @layout("test")
    def test_layout() -> FT:
        return Div(
            Div(data_slot="content", cls="content"),
            Div(data_slot="sidebar", cls="sidebar")
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

This is my first blog post. Welcome to my blog!

## Section 1

Some content here.

## Section 2

More content here.
""")
    return post

@pytest.fixture
def self_closing_tags_post(test_dir):
    """Create a test post with self-closing tags."""
    post = test_dir / "self_closing_tags.md"
    post.write_text("""<content>
<img src="test.jpg" alt="Test Image"/>
<br/>
<hr/>
<input type="text" value="test"/>
</content>""")
    return post

# Integration tests
def test_full_rendering_pipeline(test_post):
    """Test the full rendering pipeline with a complex post."""
    # Register content block tokens
    add_token(FastHTMLToken)
    add_token(ScriptToken)
    add_token(NestedContentToken)
    
    # Parse the content
    content = test_post.read_text()
    metadata, _ = parse_frontmatter(content)
    
    # Create content item
    item = ContentItem(
        source_path=test_post,
        metadata={"layout": "test"},
        content="""# Test Post

<content>
**Main** content with *formatting*
</content>

<sidebar>
- Item 1
- Item 2
</sidebar>"""
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
    # Register content block tokens
    add_token(FastHTMLToken)
    add_token(ScriptToken)
    add_token(NestedContentToken)
    
    # Parse the content
    content = minimal_post.read_text()
    metadata, _ = parse_frontmatter(content)
    
    # Create content item
    item = ContentItem(
        source_path=minimal_post,
        metadata={"layout": "default"},
        content="# Minimal Post\n\nJust some content."
    )
    
    # Render content
    html = render_content(item)
    
    # Verify content
    assert '<h1 id="minimal-post">Minimal Post</h1>' in html
    assert "Just some content" in html

def test_blog_post_rendering(blog_post):
    """Test rendering a blog post with metadata."""
    # Register content block tokens
    add_token(FastHTMLToken)
    add_token(ScriptToken)
    add_token(NestedContentToken)

    # Parse the content
    content = blog_post.read_text()
    metadata, content = parse_frontmatter(content)

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
    assert '<h2 id="section-2">Section 2</h2>' in html
    assert "Some content here" in html
    assert "More content here" in html

def test_self_closing_tags(self_closing_tags_post):
    """Test handling of self-closing tags."""
    # Register content block tokens
    add_token(FastHTMLToken)
    add_token(ScriptToken)
    add_token(NestedContentToken)

    # Parse the content
    content = self_closing_tags_post.read_text()
    metadata, content = parse_frontmatter(content)

    # Create content item
    item = ContentItem(
        source_path=self_closing_tags_post,
        metadata={"layout": "default"},
        content=content.strip()
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

<header>
# Welcome to my site
</header>

<toc>
- Introduction
- Features
- Conclusion
</toc>

<content>
This is the main content.
</content>

<sidebar>
- Recent posts
- Categories
</sidebar>
"""
    # Register content block tokens
    add_token(FastHTMLToken)
    add_token(ScriptToken)
    add_token(NestedContentToken)

    # Register custom layout
    @layout("custom")
    def custom_layout(content: str = "") -> FT:
        return Div(
            Div(None, data_slot="header", cls="header"),
            Div(None, data_slot="toc", cls="toc"),
            Div(None, data_slot="content", cls="content"),
            Div(None, data_slot="sidebar", cls="sidebar"),
            cls="custom-layout"
        )

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

<content>
# Content
</content>
""")

    # Register custom layout
    @layout("custom")
    def custom_layout(content: str = "") -> FT:
        return Div(
            H1("Custom Title", cls="custom-title"),
            Div(content, data_slot="content", cls="custom-content"),
            cls="custom-layout"
        )

    # Parse the content
    content = post.read_text()
    metadata, content = parse_frontmatter(content)

    # Create content item
    item = ContentItem(
        source_path=post,
        metadata=metadata,  # Use the parsed metadata
        content=content
    )

    # Render content
    html = render_content(item)

    # Verify content
    assert "Custom Title" in html
    assert '<h1 id="content">Content</h1>' in html
    assert 'class="custom-title"' in html
    assert 'class="custom-content"' in html
    assert 'class="custom-layout"' in html

def test_full_pipeline_with_frontmatter():
    """Test the full pipeline with frontmatter and various content types."""
    content = """---
title: Test Document
author: Test Author
date: 2024-01-01
layout: test
---

<content>
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
</content>
"""
    # Register content block tokens
    add_token(FastHTMLToken)
    add_token(ScriptToken)
    add_token(NestedContentToken)

    # Register test layout
    @layout("test")
    def test_layout(content: str = "", title: str = "", author: str = "", date: str = "") -> FT:
        return Div(
            H1(title, cls="title"),
            P(f"By {author}") if author else None,
            Time(date) if date else None,
            Div(content, data_slot="content", cls="content")
        )

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

    # Verify content
    assert '<h1 id="introduction">Introduction</h1>' in html
    assert "Hello from FastHTML" in html
    assert "This is a content block" in html
    assert "Test Document" in html
    assert "Test Author" in html
    assert "2024-01-01" in html

def test_full_pipeline_with_layout():
    """Test the full pipeline with a custom layout."""
    content = """---
title: Test Document
layout: custom
---

<content>
# Content
</content>
"""
    # Register content block tokens
    add_token(FastHTMLToken)
    add_token(ScriptToken)
    add_token(NestedContentToken)

    # Parse the content
    metadata, content = parse_frontmatter(content)

    # Create content item
    item = ContentItem(
        source_path=Path("test.md"),
        metadata=metadata,
        content=content
    )

    # Register custom layout
    @layout("custom")
    def custom_layout(content: str = "", title: str = "") -> FT:
        return Div(
            H1(title, cls="title"),
            Div(content, data_slot="content", cls="content"),
            cls="custom-layout"
        )

    # Render content
    html = render_content(item)

    # Verify content
    assert "Test Document" in html
    assert '<h1 id="content">Content</h1>' in html
    assert 'class="title"' in html
    assert 'class="content"' in html
    assert 'class="custom-layout"' in html

def test_full_pipeline_with_fasthtml_and_layout():
    """Test the full pipeline with FastHTML and layout."""
    content = """---
title: Test Document
layout: custom
---

<content>
<ft>
show(Div("Hello from FastHTML"))
</ft>
</content>
"""
    # Register content block tokens
    add_token(FastHTMLToken)
    add_token(ScriptToken)
    add_token(NestedContentToken)

    # Parse the content
    metadata, content = parse_frontmatter(content)

    # Create content item
    item = ContentItem(
        source_path=Path("test.md"),
        metadata=metadata,
        content=content
    )

    # Register custom layout
    @layout("custom")
    def custom_layout(title: str = "") -> FT:
        return Div(
            H1(title, cls="title"),
            Div(None, data_slot="content", cls="content-special"),
            cls="custom-layout"
        )

    # Render content
    html = render_content(item)

    # Verify content
    assert "Test Document" in html
    assert "Hello from FastHTML" in html
    assert 'class="title"' in html
    assert 'class="content-special"' in html
    assert 'class="custom-layout"' in html

def test_blog_site_creation_workflow(test_dir):
    """Test a complete workflow for creating a blog site with multiple posts and layouts."""
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
    pyxie = Pyxie(
        content_dir=test_dir / "content",
        default_metadata={"layouts_path": str(layouts_dir)}
    )
    
    # 5. Register collections
    pyxie.add_collection("posts", posts_dir)
    pyxie.add_collection("pages", pages_dir)
    
    # 6. Load content
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
    
    # 10. Test rendering of posts
    rendered_post = render_content(first_post)
    assert '<h2 id="section-1">Section 1</h2>' in rendered_post
    assert '<h2 id="section-2">Section 2</h2>' in rendered_post
    assert "Some content here" in rendered_post
    assert "More content here" in rendered_post
    
    # 11. Test rendering of pages
    rendered_about = render_content(about)
    assert '<h2 id="contact">Contact</h2>' in rendered_about
    assert "test@example.com" in rendered_about