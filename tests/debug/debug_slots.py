"""Debug script to trace through slot processing steps."""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any, List

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.pyxie.slots import process_slots_and_visibility, process_element
from src.pyxie.layouts import handle_cache_and_layout, registry, layout
from src.pyxie.types import ContentItem
from fastcore.xml import Div, H1, FT, Span, A
from lxml import html

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def debug_slot_processing():
    """Debug slot processing with detailed tracing."""
    
    # Define test metadata
    metadata = {
        "layout": "blog_post",
        "title": "Test Blog Post",
        "date": "2024-03-20",
        "author": "Test Author",
        "category": "Test Category",
        "reading_time": "5 min read",
        "is_first_post": True
    }
    
    # Create a test layout
    @layout("blog_post")
    def blog_post_layout(metadata):
        """Default blog post layout for markdown content."""    
        # Create conditional elements with inline conditionals
        header_alert = Div(
            Div(
                Div(
                    iconify("fa:info-circle", cls="flex-shrink-0 mr-2 text-info"),
                    Span("This is the first post in our blog series. Stay tuned for more!"),
                    cls="flex items-center"
                ),
                cls="flex items-center p-4 rounded-lg bg-info/10 border border-info/20 shadow-lg"
            ),
            cls="mb-6"
        ) if metadata.get('is_first_post') else None
        
        reading_time_elem = Span(f" • {metadata.get('reading_time')}", cls="text-base-content/70") if metadata.get('reading_time') else None       
        
        return Div(
            # Header with title and metadata
            Div(
                Div(
                    A(metadata.get('category', 'Uncategorized'), 
                      href=f"/category/{metadata.get('category', 'Uncategorized').lower().replace(' ', '-')}",
                      cls="text-xs tracking-wider uppercase text-primary font-medium hover:underline"),
                    cls="mb-3"
                ),
                H1(metadata.get('title', 'Untitled Post'), cls="text-3xl md:text-4xl font-bold mb-4 leading-tight"),
                Div(
                    Span(str(metadata.get('date', 'Unknown date')), cls="text-base-content/70"),
                    Span(" • ", cls="text-base-content/50"),
                    Span(metadata.get('author', 'Anonymous'), cls="text-base-content/70"),
                    reading_time_elem,
                    cls="mb-4"
                ),
                header_alert,
                cls="mb-8"
            ),
            
            # Table of contents for longer posts
            Div(
                H1("Table of Contents", cls="text-xl font-bold mb-4"),
                Div(
                    None, 
                    data_slot="toc",
                    cls="space-y-2 [&_ul]:mt-2 [&_ul]:ml-4 [&_li]:text-base-content/70 hover:[&_li]:text-base-content [&_a]:block [&_a]:py-1 [&_a]:transition-colors [&_a:hover]:text-primary"
                ),
                cls="mb-8 p-6 bg-base-200 rounded-lg shadow-inner",
                data_pyxie_show="toc"
            ),
            
            # Featured image slot
            Div(None, data_slot="featured_image", cls="mb-8 rounded-xl overflow-hidden shadow-md"),
            
            # Main content
            Div(None, data_slot="content", 
                cls="prose dark:prose-invert prose-headings:scroll-mt-24 prose-img:rounded-lg prose-img:shadow-md max-w-none prose-pre:bg-base-300 prose-code:text-primary prose-a:text-primary prose-a:underline prose-a:decoration-primary/30 hover:prose-a:text-primary-focus"),

            # Optional conclusion/summary uses data-pyxie-show to control visibility
            Div(
                H1("Conclusion", cls="text-xl font-semibold mb-4"),
                Div(None, data_slot="conclusion", cls="text-base-content/90 [&_a]:text-accent [&_a]:underline [&_a]:decoration-accent/30 hover:[&_a]:text-accent-focus"),
                cls="mt-10 p-6 bg-base-200 dark:bg-base-300/10 rounded-lg border border-base-300 shadow-inner",
                data_pyxie_show="conclusion"
            ),
                   
            # Share section
            Div(None, data_slot="share", cls="mt-8"),        
            cls="blog-post max-w-3xl mx-auto px-4 py-8 leading-relaxed"
        )

    def iconify(icon, cls=None, **kwargs):
        """Create an iconify icon element."""
        return Div(icon=icon, cls=cls, **kwargs)

    # Create a test content item
    content_item = ContentItem(
        source_path="test.md",
        content="Test content",
        metadata=metadata
    )
    
    # Get layout result
    print("\n=== Testing Layout Handling ===")
    print("Input metadata:", metadata)
    
    layout_result = handle_cache_and_layout(content_item)
    print("\nLayout Result:")
    print("Error:", layout_result.error)
    print("\nLayout HTML:")
    print(layout_result.html)
    
    # Create test blocks with different content types
    test_blocks = {
        "toc": [
            """
            <ul>
                <li><a href="#section1">Section 1</a></li>
                <li><a href="#section2">Section 2</a></li>
            </ul>
            """
        ],
        "featured_image": [
            """
            <img src="test.jpg" alt="Featured Image" class="w-full h-64 object-cover">
            """
        ],
        "content": [
            """
            <h2>Section 1</h2>
            <p>This is a test paragraph with <strong>bold</strong> and <em>italic</em> text.</p>
            <pre><code>print("Hello, World!")</code></pre>
            <h2>Section 2</h2>
            <p>Another paragraph with a <a href="https://example.com">link</a>.</p>
            """
        ],
        "conclusion": [
            """
            <p>This is the conclusion with a <a href="https://example.com">final link</a>.</p>
            """
        ],
        "share": [
            """
            <div class="flex gap-4">
                <button class="btn btn-primary">Share on Twitter</button>
                <button class="btn btn-secondary">Share on LinkedIn</button>
            </div>
            """
        ]
    }
    
    print("\n=== Testing Slot Processing ===")
    print("Test blocks:")
    for name, blocks in test_blocks.items():
        print(f"\n{name}:")
        print(blocks[0])
    
    # Parse layout HTML
    print("\n=== Parsing Layout HTML ===")
    try:
        root = html.fromstring(layout_result.html)
        print("Successfully parsed layout HTML")
    except Exception as e:
        print(f"Failed to parse layout HTML: {e}")
    
    # Get filled slot names
    filled_slots = {name for name in test_blocks.keys() if name != "_pyxie_default"}
    print("\nFilled slots:", filled_slots)
    
    # Process each element
    print("\n=== Processing Elements ===")
    try:
        success = process_element(root, test_blocks, filled_slots)
        print(f"Element processing {'succeeded' if success else 'failed'}")
        
        # Get final HTML
        final_html = html.tostring(root, encoding='unicode', method='html')
        print("\nFinal HTML:")
        print(final_html)
    except Exception as e:
        print(f"Error during element processing: {e}")
    
    # Test process_slots_and_visibility directly
    print("\n=== Testing process_slots_and_visibility ===")
    result = process_slots_and_visibility(layout_result.html, test_blocks)
    print("Result error:", result.error)
    print("\nResult HTML:")
    print(result.content)

if __name__ == "__main__":
    debug_slot_processing() 