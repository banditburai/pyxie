---
title: "Welcome to Pyxie"
date: 2024-03-19
author: "Pyxie Team"
category: "Getting Started"
summary: "Get started with Pyxie - a modern Python FastHTML site generator"
reading_time: "3 min read"
---

<featured_image>
![Pyxie Process](/content/images/pyxie_process.svg)
</featured_image>

<toc>
- [Quick Start](#quick-start)
- [Basic Features](#basic-features)
- [How It Works](#how-it-works)
</toc>

<content>
# Welcome to Pyxie

Pyxie is a modern Python static site generator that combines the simplicity of markdown with the power of FastHTML. Let's explore some basic features!

## Quick Start

Pyxie makes it easy to create beautiful websites. Here's what you need to know:

1. Write content in markdown
2. Use FastHTML for dynamic components
3. Incorporate html and tailwind classes to fully customize your layouts

## Basic Features

### Markdown Support

You can write content using standard markdown syntax:

- **Bold** and *italic* text
- Lists and sublists
- [Links](https://example.com)
- Code blocks

### FastHTML Integration

Pyxie allows you to use FastHTML blocks directly in your markdown. Here's a simple example:

<fasthtml>
def iconify(icon, cls=None, **kwargs):
    return ft_hx('iconify-icon', icon=icon, cls=cls, **kwargs)

def Counter(initial: int = 0):
    """A counter component with increment/decrement buttons and interactivity."""
    return Div(
        Button(
            iconify(icon="lucide:minus", cls="w-4 h-4"),
            cls="px-2 py-1 bg-red-100 dark:bg-red-900 text-red-600 dark:text-red-300 rounded-l-lg",
            onclick="this.nextElementSibling.textContent = parseInt(this.nextElementSibling.textContent) - 1"
        ),
        Div(
            str(initial),
            cls="px-4 py-1 bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 font-mono"
        ),
        Button(
            iconify(icon="lucide:plus", cls="w-4 h-4"),
            cls="px-2 py-1 bg-green-100 dark:bg-green-900 text-green-600 dark:text-green-300 rounded-r-lg",
            onclick="this.previousElementSibling.textContent = parseInt(this.previousElementSibling.textContent) + 1"
        ),
        cls="inline-flex items-center"
    ) 

# Use show() to render the counter component
show(Counter(5))
</fasthtml>

## How It Works

Pyxie transforms your markdown content into beautiful web pages through a simple yet powerful process:

![Pyxie Content](/content/images/pyxie_content.svg)

1. **Content Files**: Your markdown files with YAML frontmatter and XML elements
2. **Parser**: Processes your content into structured data
3. **Cache**: Stores processed content for better performance
4. **Renderer**: Transforms the structured data into HTML
5. **Output**: The final HTML pages ready to be served

</content>

<conclusion>
Pyxie makes it easy to create beautiful, content-focused websites. Start with simple markdown files and let Pyxie handle the rest. Ready to dive deeper? Explore our [Markdown Features](/posts/markdown-features) guide or learn about [styling](/posts/styling-guide).
</conclusion>

<share>
<div class="flex gap-3">
  <a href="https://twitter.com/share?text=Welcome to Pyxie&url=https://example.com/post/welcome" target="_blank" class="btn btn-sm btn-outline">
    <iconify-icon icon="fa:twitter" class="mr-2"></iconify-icon> Share on Twitter
  </a>
  <a href="https://www.facebook.com/sharer/sharer.php?u=https://example.com/post/welcome" target="_blank" class="btn btn-sm btn-outline">
    <iconify-icon icon="fa:facebook" class="mr-2"></iconify-icon> Share on Facebook
  </a>
</div>
</share> 