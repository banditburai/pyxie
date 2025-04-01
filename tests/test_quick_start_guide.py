"""Tests for the quick start guide content."""

import pytest
import logging
from pathlib import Path
from mistletoe import Document
from mistletoe.block_token import Heading, Paragraph, List, HtmlBlock
from pyxie.renderer import PyxieRenderer
from pyxie.parser import RawBlockToken, NestedContentToken, parse_frontmatter
from pyxie.types import ContentItem
from pyxie.renderer import render_content
from pyxie.layouts import layout
from fasthtml.common import *

logger = logging.getLogger(__name__)

# Test content with various sections
QUICK_START_CONTENT = """---
title: "Quick Start Guide: Build Your First Pyxie Site"
date: 2024-03-20
layout: basic
author: Pyxie Team
---

<featured_image>
![Pyxie Logo](logo.png)
</featured_image>

<toc>
## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Project Setup](#project-setup)
4. [Creating Content](#creating-content)
5. [Next Steps](#next-steps)
</toc>

<content>
# Prerequisites

Before you begin, make sure you have:
- Python 3.8 or higher installed
- A text editor or IDE
- Basic understanding of Markdown

# Installation

Install Pyxie using pip:

```bash
pip install pyxie
```

# Project Setup

Create a new project directory and initialize it:

```bash
mkdir my-pyxie-site
cd my-pyxie-site
pyxie init
```

This will create the basic project structure:

```
my-pyxie-site/
├── content/
│   └── index.md
├── layouts/
│   └── basic.py
├── static/
│   └── css/
└── pyxie.yaml
```

# Creating Content

Create your first content file:

```markdown
---
title: My First Page
layout: basic
---

<content>
# Welcome to My Site

This is my first page using Pyxie!
</content>
```

## Using FastHTML

You can also use FastHTML for dynamic content:

<ft>
def Greeting(name="World"):
    return Div(
        H1(f"Hello, {name}!"),
        P("Welcome to my site.")
    )

show(Greeting())
</ft>

## Adding Scripts

You can include custom scripts:

<script>
console.log("Hello from Pyxie!");
</script>

# Next Steps

1. Customize your layouts
2. Add more content
3. Deploy your site
</content>

<conclusion>
## Need Help?

Check out our [documentation](https://pyxie.dev/docs) or join our [community](https://pyxie.dev/community).
</conclusion>
"""

@layout("basic")
def basic_layout(title: str = "") -> FT:
    """Basic layout for testing."""
    return Div(
        H1(title),
        Div(None, data_slot="featured_image"),
        Div(None, data_slot="toc"),
        Div(None, data_slot="content"),
        Div(None, data_slot="conclusion")
    )

def test_quick_start_guide_parsing():
    """Test parsing of the quick start guide content."""
    # Parse the content
    metadata, content = parse_frontmatter(QUICK_START_CONTENT)
    
    # Create content item with the new structure
    content_item = ContentItem(
        source_path=None,
        metadata=metadata,
        content=content
    )
    
    # Verify the content structure
    assert content_item.metadata["title"] == "Quick Start Guide: Build Your First Pyxie Site"
    assert str(content_item.metadata["date"]) == "2024-03-20"
    assert content_item.metadata["layout"] == "basic"
    assert content_item.metadata["author"] == "Pyxie Team"
    
    # Verify content sections
    assert "<featured_image>" in content_item.content
    assert "<toc>" in content_item.content
    assert "<content>" in content_item.content
    assert "<conclusion>" in content_item.content
    
    # Verify specific content sections
    assert "![Pyxie Logo](logo.png)" in content_item.content
    assert "## Table of Contents" in content_item.content
    assert "# Prerequisites" in content_item.content
    assert "# Next Steps" in content_item.content
    assert "## Need Help?" in content_item.content

def test_quick_start_guide_rendering():
    """Test rendering of the quick start guide content."""
    # Parse the content
    metadata, content = parse_frontmatter(QUICK_START_CONTENT)
    
    # Create content item
    content_item = ContentItem(
        source_path=None,
        metadata=metadata,
        content=content
    )
    
    # Render the content
    rendered = render_content(content_item)
    
    # Verify the rendered content
    assert "Quick Start Guide: Build Your First Pyxie Site" in rendered
    assert "Pyxie Logo" in rendered
    assert "Table of Contents" in rendered
    assert "Prerequisites" in rendered
    assert "Installation" in rendered
    assert "Project Setup" in rendered
    assert "Creating Content" in rendered
    assert "Next Steps" in rendered
    assert "Need Help?" in rendered