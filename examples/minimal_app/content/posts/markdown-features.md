---
title: "Pyxie Markdown Guide"
date: 2024-03-19
author: "Pyxie Team"
category: "Features"
summary: "Master Pyxie's markdown features and FastHTML integration"
reading_time: "5 min read"
---

<featured_image>
![Markdown Features](pyxie:features/1200/600)
</featured_image>

<toc>
- [Document Structure](#document-structure)
- [Markdown Syntax](#markdown-syntax)
- [FastHTML Basics](#fasthtml-basics)
</toc>

<content>
# Pyxie Markdown Guide

Learn how to create rich content using Pyxie's markdown features and FastHTML integration.

## Document Structure

Pyxie markdown files are flexible and can be adapted to your chosen layout. The only required part is the frontmatter metadata at the top and at least one xml section:

```markdown
---
title: "Your Title"
date: 2024-03-19  # ISO format date
author: "Author Name"
category: "Category"
summary: "Brief summary"
reading_time: "5 min read"  # Optional
tags: ["tag1", "tag2"]  # Optional
---
```

### XML Elements

Pyxie uses XML-style elements to structure content. The available sections depend on your chosen layout. Common sections include:

- `<featured_image>`: Hero image at the top
- `<toc>`: Table of contents (auto-generated from headings)
- `<content>`: Main content area
- `<conclusion>`: Summary or call-to-action
- `<share>`: Social sharing buttons

Some layouts may define additional sections like `<share>` for social sharing buttons. If you don't define a section that's available in your layout, that part of the page simply won't be rendered. This flexibility lets you create different types of content using the same layout.

## Markdown Syntax

### Text Formatting

- **Bold** with `**text**`
- *Italic* with `*text*`
- ~~Strikethrough~~ with `~~text~~`
- `Code` with \`text\`

### Lists

1. Ordered lists
2. Use numbers
   - Nested items
   - Work too

- Unordered lists
- Use dashes
  * Or asterisks
  * For nested items

### Code Blocks

```python
def hello_world():
    print("Hello from Pyxie!")
```

### Tables

| Feature | Description | Support |
|---------|-------------|---------|
| Markdown | Basic syntax | ✅ |
| FastHTML | Python components | ✅ |
| DaisyUI | UI components | ✅ |

## FastHTML Basics

FastHTML lets you create dynamic components right in your markdown. Here's a simple example:

<fasthtml>
import random
from datetime import datetime
from zoneinfo import ZoneInfo

def get_random_city_time():
    cities = [
        ("Durban", "Africa/Johannesburg"),
        ("Tokyo", "Asia/Tokyo"),
        ("New York", "America/New_York"),
        ("London", "Europe/London"),
        ("Sydney", "Australia/Sydney"),
        ("Dubai", "Asia/Dubai"),
        ("Singapore", "Asia/Singapore"),
        ("Paris", "Europe/Paris"),
        ("Mumbai", "Asia/Kolkata"),
        ("Rio de Janeiro", "America/Sao_Paulo")
    ]
    city, timezone = random.choice(cities)
    time = datetime.now(ZoneInfo(timezone))
    return city, time.strftime("%I:%M %p")

def Greeting():
    city, time = get_random_city_time()
    return Div(
        H2("Hello from FastHTML!", cls="text-2xl font-bold mb-4"),
        P("This component was created using Python code."),
        P(f"It's {time} in {city} right now!", cls="text-lg font-medium text-primary mt-2"),
        cls="p-6 bg-base-200 rounded-lg"
    )

show(Greeting())
</fasthtml>

### Basic FastHTML Elements

FastHTML provides XML element constructors that let you create HTML elements using Python:

```python
# Common elements - these are XML constructors that create HTML elements
Div("content", cls="my-class")  # Creates a <div> element
P("paragraph text")            # Creates a <p> element
H1("heading 1")                # Creates an <h1> element
H2("heading 2")                # Creates an <h2> element
Span("inline text")            # Creates a <span> element

# Interactive elements
Button("Click me", onclick="handleClick()")  # Creates a <button> element
Input(type="text", placeholder="Enter text")  # Creates an <input> element
```

### Adding Classes and Styles

Use the `cls` parameter to add CSS classes to any element:

```python
Div(
    "Content with styling",
    cls="p-4 bg-blue-100 rounded-lg shadow-md"
)
```

### Nesting Elements

FastHTML elements can be nested to create complex structures:

```python
Div(
    H2("Title", cls="text-2xl"),
    P("Description", cls="text-gray-600"),
    Button("Action", cls="btn btn-primary"),
    cls="card p-4"
)
```
</content>

<conclusion>
With Pyxie's markdown features and FastHTML integration, you can create rich content that goes far beyond traditional static markdown. Try combining these features to create engaging content!
</conclusion> 