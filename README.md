# Pyxie

Create flexible websites with markdown content and FastHTML layouts - no design constraints.

## Overview

Pyxie is a Python package that combines the simplicity of Markdown with the power of FastHTML to create modern, dynamic websites. Write your content in Markdown for maximum readability and maintainability, while leveraging component-based layouts for dynamic features. The result is content that's both beautiful to look at and semantically structured - making it ideal for both human readers and AI/LLM processing.

## Features

- **Markdown-First**: Write content in plain markdown with optional FastHTML components
- **Flexible Layouts**: Define custom layouts with slots for different content sections
- **Content Management**: Query and filter content using metadata
- **FastHTML Integration**: Create dynamic components with Python

## Quick Start

1. Install Pyxie:
```bash
pip install pyx2
```

2. Create a basic app (`main.py`):
```python
from pathlib import Path
from fasthtml.common import *
from datetime import datetime
from pyxie import Pyxie

# Setup paths
BASE_DIR = Path(__file__).parent
CONTENT_DIR = BASE_DIR / "content"
POSTS_DIR = CONTENT_DIR / "posts"

# Initialize Pyxie
pyxie = Pyxie(
    POSTS_DIR,                             # Content directory    
    cache_dir=BASE_DIR / ".cache",         # Enable caching for better performance
    default_layout="default",              # Layout to use if not specified in metadata
    layout_paths=[BASE_DIR / "layouts"],   # Where to look for layouts    
)

# Create FastHTML app with Pyxie middleware
app, rt = fast_app(
    htmlkw=dict(lang="en"),
    middleware=(pyxie.serve_md(),)  # Serve markdown files at their slug paths
)
```

Key configuration options:
- First argument is the content directory path
- `default_metadata`: Default values for new posts (optional)
- `cache_dir`: Enable caching for better performance (optional)
- `default_layout`: Layout to use if not specified in metadata (defaults to "default")
- `layout_paths`: Where to look for layouts (defaults to checking `layouts`, `templates`, `static`)
- `auto_discover_layouts`: Whether to automatically find layouts (defaults to True)

3. Create your content structure:
```
my-site/
├── content/
│   └── posts/          # Your markdown content
├── layouts/            # Your layout files
│   └── default.py      # Default layout
├── main.py            # App initialization
└── .cache/            # Generated cache files
```

## Writing Content

Create markdown files with frontmatter metadata:

```markdown
---
title: "My First Post"
date: 2024-03-19
layout: default
status: published
---

<featured_image>
![My Image](path/to/image.jpg)
</featured_image>

<content>
# Hello World

Regular markdown content here...

<fasthtml>
def Greeting():
    return H1("Welcome to my site!", cls="text-3xl font-bold")

show(Greeting())
</fasthtml>

More markdown content...
</content>
```

## Creating Layouts

Layouts define the structure of your pages and what content sections (slots) are available:

```python
@layout("default")  # Register as the "default" layout
def default_post_layout(metadata):
    """Basic blog post layout."""
    return Div(
        # Header with title
        H1(metadata.get('title', 'Untitled'), cls="text-3xl font-bold"),
        
        # Featured image slot - optional
        Div(None, data_slot="featured_image"),
        
        # Main content slot - required
        Div(None, data_slot="content", cls="prose"),
        
        # Optional conclusion slot
        Div(None, data_slot="conclusion"),
        
        cls="max-w-3xl mx-auto px-4 py-8"
    )
```

Key concepts:
- Use `@layout(name)` to register a layout
- `data_slot="name"` defines where content sections appear
- `data_pyxie_show="name"` shows that element only when the named slot is filled
- `data_pyxie_show="!name"` shows that element only when the named slot is empty
- Access metadata from the markdown frontmatter

## Querying Content

Pyxie provides a powerful API for querying content:

```python
# Get recent published posts
recent_posts = pyxie.get_items(
    status="published",      # Filter by metadata
    order_by=["-date"],     # Sort by date descending
    per_page=5              # Limit results
).items

# Get posts by category
tech_posts = pyxie.get_items(
    category="tech",
    status="published"
).items

# Complex queries
featured_posts = pyxie.get_items(
    status="published",
    is_featured=True,
    order_by=["-date", "title"]  # Sort by date then title
).items
```

Query features:
- Filter by any metadata field
- Sort by multiple fields (prefix with `-` for descending)
- Pagination support with `per_page` and `page`
- Returns an object with `items` and pagination info

## Learn More

- [Documentation](https://docs.pyxie.dev)
- [Minimal App Example](https://minimal.pyxie.dev)

## License

This project is licensed under the Apache License 2.0 - see the LICENSE file for details.

## Acknowledgements

This project is built on top of [FastHTML](https://github.com/answerDotAI/fasthtml/), a powerful web framework for creating HTML applications with python code. FastHTML provides the core functionality for handling layouts and components in Pyxie. We're grateful to the FastHTML team and community for creating such an excellent foundation to build upon.
