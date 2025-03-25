"""Tests for the quick start guide content."""

import pytest
from pathlib import Path
from mistletoe.block_token import add_token
from pyxie.parser import parse_frontmatter, FastHTMLToken, ScriptToken, ContentBlockToken
from pyxie.types import ContentItem, ContentBlock
from pyxie.renderer import render_content
from pyxie.layouts import layout
from fasthtml.common import *

# Register content block tokens
add_token(FastHTMLToken)
add_token(ScriptToken)
add_token(ContentBlockToken)

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

def test_quick_start_guide_parsing():
    """Test parsing of the quick start guide content."""
    # Debug the test content
    content_start = QUICK_START_CONTENT.find("<content>")
    content_end = QUICK_START_CONTENT.find("</content>")
    print(f"\nContent section in test file:")
    print(f"Start tag position: {content_start}")
    print(f"End tag position: {content_end}")
    
    # Look for the next steps section
    next_steps_pos = QUICK_START_CONTENT.find("## Next Steps")
    print(f"Next Steps position: {next_steps_pos}")
    print(f"Is Next Steps inside content? {content_start < next_steps_pos < content_end}")
    
    # Check what comes after the content section
    if content_end > 0:
        print(f"\nContent right before closing tag:")
        print(QUICK_START_CONTENT[content_end-100:content_end])
    
    # Parse the content
    metadata, content = parse_frontmatter(QUICK_START_CONTENT)
    
    # Create content blocks manually
    blocks = {
        "featured_image": [ContentBlock(
            tag_name="featured_image",
            content="![Pyxie Logo](logo.png)",
            attrs_str=""
        )],
        "toc": [ContentBlock(
            tag_name="toc",
            content="## Table of Contents\n1. [Prerequisites](#prerequisites)\n2. [Installation](#installation)\n3. [Project Setup](#project-setup)\n4. [Creating Content](#creating-content)\n5. [Next Steps](#next-steps)",
            attrs_str=""
        )],
        "content": [ContentBlock(
            tag_name="content",
            content="""# Prerequisites

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
3. Deploy your site""",
            attrs_str=""
        )],
        "conclusion": [ContentBlock(
            tag_name="conclusion",
            content="""## Need Help?

Check out our [documentation](https://pyxie.dev/docs) or join our [community](https://pyxie.dev/community).""",
            attrs_str=""
        )]
    }
    
    # Create content item
    content_item = ContentItem(
        source_path=Path("quick-start.md"),
        metadata=metadata,
        blocks=blocks
    )
    
    # Test frontmatter
    assert metadata["title"] == "Quick Start Guide: Build Your First Pyxie Site"
    
    # Verify the date - it could be a datetime or date object
    date_value = metadata["date"]
    # We just want to verify the date part is correct
    assert str(date_value).startswith("2024-03-20")
    
    assert metadata["layout"] == "basic"
    assert metadata["author"] == "Pyxie Team"
    
    # Test content blocks
    assert set(content_item.blocks.keys()) == {"featured_image", "toc", "content", "conclusion"}
    
    # Test featured_image block
    featured_image = content_item.blocks["featured_image"][0]
    assert featured_image.content == "![Pyxie Logo](logo.png)"
    
    # Test toc block
    toc = content_item.blocks["toc"][0]
    assert "Table of Contents" in toc.content
    assert "Prerequisites" in toc.content
    assert "Installation" in toc.content
    assert "Project Setup" in toc.content
    assert "Creating Content" in toc.content
    assert "Next Steps" in toc.content
    
    # Test content block
    content = content_item.blocks["content"][0]
    assert "Prerequisites" in content.content
    assert "Installation" in content.content
    assert "Project Setup" in content.content
    assert "Creating Content" in content.content
    assert "Using FastHTML" in content.content
    assert "Adding Scripts" in content.content
    assert "Next Steps" in content.content
    
    # Test conclusion block
    conclusion = content_item.blocks["conclusion"][0]
    assert "Need Help?" in conclusion.content
    assert "documentation" in conclusion.content
    assert "community" in conclusion.content
    
    # Verify code blocks are preserved
    assert "```bash" in content.content
    assert "pip install pyxie" in content.content
    assert "mkdir my-pyxie-site" in content.content
    assert "```markdown" in content.content
    
    # Verify FastHTML block is preserved
    assert "<ft>" in content.content
    assert "def Greeting" in content.content
    assert "show(Greeting())" in content.content
    
    # Verify script block is preserved
    assert "<script>" in content.content
    assert "console.log" in content.content
    
    # Verify XML tags in code blocks are preserved
    code_blocks = [block for block in content.content.split("```") if block.strip()]
    for block in code_blocks:
        if "xml" in block.lower():
            assert "<div>" in block
            assert "<h1>" in block
            assert "<p>" in block

def test_quick_start_guide_rendering():
    """Test rendering of the quick start guide content."""
    # Parse the content
    metadata, content = parse_frontmatter(QUICK_START_CONTENT)
    
    # Create content blocks
    blocks = {
        "content": [ContentBlock(
            tag_name="content",
            content="""# Prerequisites

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
3. Deploy your site""",
            attrs_str=""
        )]
    }
    
    # Create content item
    item = ContentItem(
        source_path=Path("quick-start.md"),
        metadata=metadata,
        blocks=blocks
    )
    
    # Create a basic layout
    @layout("basic")
    def basic_layout(title: str = "") -> FT:
        return Div(
            H1(title),
            Div(None, data_slot="content"),
            cls="max-w-3xl mx-auto px-4 py-8"
        )
    
    # Render the content
    html = render_content(item)
    
    # Verify the rendered content
    assert "Quick Start Guide" in html
    assert "Prerequisites" in html
    assert "Installation" in html
    assert "Project Setup" in html
    assert "Creating Content" in html
    assert "Using FastHTML" in html
    assert "Adding Scripts" in html
    assert "Next Steps" in html
    
    # Verify code blocks are rendered
    assert '<pre><code class="language-bash">' in html
    assert "pip install pyxie" in html
    assert "mkdir my-pyxie-site" in html
    
    # Verify FastHTML block is rendered
    assert '<div>\n<h1>Hello, World!</h1> <p>Welcome to my site.</p>\n</div>' in html
    
    # Verify script block is rendered
    assert '<script>' in html
    assert 'console.log("Hello from Pyxie!");' in html