# ============================================================================
#  Minimal Blog Template - Built with Pyxie, FastHTML, and DaisyUI
# ============================================================================
from datetime import datetime
from pathlib import Path
from fasthtml.common import *
from pyxie import Pyxie, layout
from collections import Counter
from typing import Any, List, Optional, Dict, Tuple, Union

BASE_DIR = Path(__file__).parent
CONTENT_DIR = BASE_DIR / "content"
POSTS_DIR = CONTENT_DIR / "posts"
CACHE_DIR = BASE_DIR / ".cache"

DEFAULT_POST_METADATA = {
    "title": "Untitled Post",
    "date": datetime.now().strftime("%Y-%m-%d"),
    "author": "Anonymous",
    "category": "Uncategorized",
    "summary": "",
    "status": "published",
    "layout": "default"
}
SORT_OPTIONS = {
    "newest": ["-date", "title"],  # Newest first, then by title
    "oldest": ["date", "title"],   # Oldest first, then by title
    "alpha": ["title", "date"],    # Alphabetical by title, then by date
}
DEFAULT_SORT = "newest"
POSTS_PER_PAGE = 20

# Initialize the app
styles = Link(rel="stylesheet", href="/static/css/output.css", type="text/css")
iconify_script = Script(src="https://cdn.jsdelivr.net/npm/iconify-icon@2.0.0/dist/iconify-icon.min.js")

pyxie = Pyxie(
    POSTS_DIR,
    # cache_dir=CACHE_DIR,  # Comment out to disable caching
    default_metadata=DEFAULT_POST_METADATA,    
    # layout_paths=[BASE_DIR / "layouts"] # pass in a directory of layouts to use, 
)                                         # it will auto discover them from layouts/templates/or static

app, rt = fast_app(
    pico=False, surreal=False, live=False,
    hdrs=(styles, iconify_script),
    htmlkw=dict(lang="en", dir="ltr", data_theme="dark"),
    bodykw=dict(cls="min-h-screen bg-base-100"),
    middleware=(pyxie.serve_md(),) # middleware to serve markdown files for each post at the {slug path}.md
)

app.title = "Minimal Blog"

# Helper Functions
def format_date(date):
    return date.strftime('%B %d, %Y') if hasattr(date, 'strftime') else str(date)

def create_category_url(category):
    return f"/category/{category.lower().replace(' ', '-')}"

def handle_error(title, message):
    return app_layout(
        Div(
            H1(title, cls="text-3xl font-bold mb-4"),
            P(message, cls="mb-4"),
            A("← Back to Home", href="/", cls="text-primary hover:underline"),
            cls="max-w-3xl mx-auto"
        ),
        title=title
    )

# Data Access
def get_sorted_posts(category=None, page=1, sort=DEFAULT_SORT):
    order_by = SORT_OPTIONS.get(sort, SORT_OPTIONS[DEFAULT_SORT])
    return pyxie.get_items(
        status="published", category=category,
        order_by=order_by, page=page, per_page=POSTS_PER_PAGE
    )

def get_categories_with_counts():
    all_posts = pyxie.get_items(status="published", per_page=100).items
    categories = [post.category for post in all_posts if hasattr(post, 'category')]
    return dict(Counter(categories))

def get_recent_posts(count=5):
    return pyxie.get_items(
        status="published", order_by=["-date", "title"], per_page=count
    ).items

# UI Components
def iconify(icon, cls=None, **kwargs):
    return ft_hx('iconify-icon', icon=icon, cls=cls, **kwargs)

def theme_toggle():
    toggle_script = Script("""
    document.addEventListener('DOMContentLoaded', function() {
        const toggle = document.getElementById('theme-toggle');
        const html = document.documentElement;
        const defaultTheme = "dark", altTheme = "light";
        const savedTheme = localStorage.getItem('theme');
        const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        const initialTheme = savedTheme || (systemDark ? defaultTheme : altTheme);                
        html.setAttribute('data-theme', initialTheme);
        toggle.checked = initialTheme === defaultTheme;        
        toggle.addEventListener('change', function() {
            const newTheme = this.checked ? defaultTheme : altTheme;
            html.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
        });
    });
    """)
    
    return Div(
        Label(
            Input(type="checkbox", value="dark", cls="theme-controller", id="theme-toggle", checked=True),
            iconify(icon="material-symbols:wb-sunny-rounded", cls="swap-on text-2xl"),
            iconify(icon="material-symbols:dark-mode-rounded", cls="swap-off text-2xl"),
            cls="swap swap-rotate hover:text-primary text-base-content"
        ),
        toggle_script,
        cls="flex items-center"
    )

def github_link():
    return A(
        iconify(icon="fa:github", cls="text-2xl"),
        href="https://github.com/banditburai/pyxie", 
        target="_blank", rel="noopener noreferrer",
        cls="flex items-center justify-center text-base-content hover:text-primary transition-colors"
    )

def create_sidebar_section(title, items, cls="mb-8"):
    return Div(
        H2(title, cls="text-xl font-bold mb-2"),
        Ul(*[Li(A(text, href=url, cls="hover:underline")) for text, url in items], cls="space-y-2"),
        cls=cls
    )

def meta_section(date, author, cls="mb-4"):
    return Div(
        Span(format_date(date), cls="text-base-content/70"),
        Span(" • ", cls="text-base-content/50"),
        Span(author, cls="text-base-content/70"),
        cls=cls
    )

def pagination(page_info, base_path, sort):
    if not hasattr(page_info, 'total_pages') or page_info.total_pages <= 1:
        return Div()
    
    return Div(
        Div(
            A("← Previous", 
              href=f"{base_path}?page={page_info.previous_page}&sort={sort}",
              aria_label="Go to previous page",
              cls="btn btn-outline") if page_info.has_previous else Span(),
              
            A("Next →", 
              href=f"{base_path}?page={page_info.next_page}&sort={sort}",
              aria_label="Go to next page",
              cls="btn btn-outline") if page_info.has_next else Span(),
              
            cls="flex justify-center gap-6"
        ),
        cls="mt-12"
    )

def featured_image(src, alt, cls="aspect-[2/1] overflow-hidden mb-6 rounded-lg"):
    return Div(
        Img(src=src, alt=alt, loading="lazy", cls="w-full h-full object-cover"),
        cls=cls
    )

# Layout Functions
def site_header(include_toggle=True):
    site_title = H1("Minimal Blog", cls="text-4xl md:text-5xl font-bold")
    site_desc = P(
        "A minimal blog template built with FastHTML, DaisyUI, and Pyxie", 
        cls="text-lg opacity-80 mt-2 hidden md:block"
    )
    
    toggle_btn = None
    if include_toggle:
        toggle_btn = Label(
            iconify(icon="fa:bars", cls="text-2xl"),
            fr="sidebar-drawer", aria_label="open sidebar",
            cls="btn btn-square btn-ghost flex items-center justify-center cursor-pointer lg:hidden"
        )
    
    return Header(
        Div(            
            Div(A(site_title, href="/", cls="flex items-center gap-2"), site_desc, cls="flex-1 py-4"),
            Div(toggle_btn, cls="flex items-center") if toggle_btn else None,
            cls="w-full flex items-center justify-between"
        ),
        cls="w-full bg-base-200 border-b border-base-300 py-6 px-6 md:px-8",
        id="site-header"
    )

def sidebar_content(categories, posts):
    cat_links = [(f"{c} ({count})", create_category_url(c)) for c, count in categories]
    post_links = [(p.title, f"/post/{p.slug}") for p in posts]
    
    return Div(
        # Controls section
        Div(
            Div(Span("", cls="flex-1"), github_link(), theme_toggle(), cls="flex items-center justify-end w-full gap-4"),
            cls="pb-4 mb-24"
        ),
        
        # About section
        Div(
            H2("About", cls="text-xl font-bold mb-2"),
            P("A minimal blog template built with FastHTML, DaisyUI, and Pyxie for markdown parsing.", cls="mb-2"),
            P("Customize this section to introduce yourself or your blog.", cls="text-base-content/70"),
            cls="mb-8 pt-8"
        ),
                
        create_sidebar_section("Categories", cat_links),
        create_sidebar_section("Recent Posts", post_links),
        cls="p-4 lg:p-6"
    )

def app_layout(content, title="Minimal Blog"):
    app.title = title
    cat_list = sorted([(c, n) for c, n in get_categories_with_counts().items()], key=lambda x: x[0])
    posts = get_recent_posts(5)
    
    return Div(
        Input(id="sidebar-drawer", type="checkbox", cls="drawer-toggle"),
        
        # Main content area
        Div(
            site_header(include_toggle=True),
            Main(Div(content, cls="flex-1 p-4 lg:p-8 bg-base-100"), cls="flex flex-col bg-base-100"),
            cls="drawer-content flex flex-col"
        ),
        
        # Sidebar
        Div(
            Label(fr="sidebar-drawer", aria_label="close sidebar", cls="drawer-overlay"),
            Div(sidebar_content(cat_list, posts), cls="w-80 min-h-full bg-base-200 text-base-content"),
            cls="drawer-side"
        ),
        
        cls="drawer drawer-end lg:drawer-open min-h-screen bg-base-100"
    )

def post_preview(post, featured=False):
    # Card properties
    title_id = f"post-title-{post.slug}"
    date_str = format_date(post.date)
    post_url = f"/post/{post.slug}"
    cat_url = create_category_url(post.category)
    card_cls = "group border-2 border-transparent hover:border-base-300 hover:bg-base-300/10 transition-all duration-300 hover:scale-[0.99] post-card relative"
    
    # Create image
    duration = 500 if featured else 300
    img = Img(
        src=post.image, alt=f"Featured image for {post.title}", loading="lazy",
        cls=f"w-full h-full object-cover transition-transform duration-{duration} group-hover:scale-105"
    )
    
    img_container_cls = "aspect-[16/9] overflow-hidden mb-5 mt-3 rounded-xl shadow-sm" if featured else \
                        "w-full sm:w-44 lg:w-56 sm:h-44 aspect-video sm:aspect-auto overflow-hidden rounded-xl shadow-sm flex-shrink-0"
    
    # Create meta info
    meta_div = Div(
        Span(date_str, cls="text-sm text-base-content/60"),
        Span(" · ", cls="text-base-content/40 mx-2"),
        Span(f"By {post.author}", cls="text-sm text-base-content/60"),
        cls="mb-3" if featured else "mb-2"
    )
    
    # Create invisble link for entire card
    card_link = A(
        Span("Read full article", cls="sr-only"),
        href=post_url, aria_labelledby=title_id, cls="absolute inset-0 z-1"
    )
    
    # Create category link
    cat_link = A(
        post.category, href=cat_url,
        cls="text-xs tracking-wider uppercase text-primary font-medium hover:underline category-link"
    )

    if featured:
        # Featured post with large image
        card = Div(
            card_link, cat_link,
            Div(img, cls=img_container_cls),
            H2(post.title, cls="text-2xl font-bold mb-3 group-hover:text-primary transition-colors", id=title_id),
            meta_div,
            P(post.summary, cls="text-base-content/80 mb-5"),
            cls=f"{card_cls} p-5"
        )
        return Div(card, cls="mb-6 w-full")
    else:
        # Regular post
        content = Div(
            cat_link,
            H2(post.title, cls="text-xl font-bold mt-1 mb-2 group-hover:text-primary transition-colors", id=title_id),
            meta_div,
            P(post.summary, cls="text-base-content/80 line-clamp-2"),
            cls="flex-1 mt-3 sm:mt-0 sm:pl-5"
        )
        
        return Div(
            Div(
                card_link,
                Div(Div(img, cls=img_container_cls), content, cls="flex flex-col sm:flex-row gap-3 sm:gap-5 items-start"),
                cls=f"{card_cls} p-4"
            ),
            cls="mb-3"
        )

def post_list(posts, featured_first=True):
    if not posts:
        return Div()
    
    if featured_first and posts:
        return Div(
            post_preview(posts[0], featured=True),
            *[post_preview(p) for p in posts[1:]], 
            cls="space-y-3"
        )
    
    return Div(*[post_preview(p) for p in posts], cls="space-y-3")

@layout("default")
def blog_post_layout(metadata):
    """Default blog post layout for markdown content."""    
    # Create conditional elements with inline conditionals
    header_alert = Div(
        Div(
            Div(
                iconify("fa:info-circle", cls="flex-shrink-0 mr-2"),
                Span("This is the first post in our blog series. Stay tuned for more!"),
                cls="flex items-center"
            ),
            cls="alert alert-info shadow-lg"
        ),
        cls="mb-6"
    ) if metadata.get('is_first_post') else None
    
    reading_time_elem = Span(f" • {metadata.get('reading_time')}", cls="text-base-content/70") if metadata.get('reading_time') else None
    
    return Div(
        # Header with title and metadata
        Div(
            Div(
                A(metadata.get('category', 'Uncategorized'), 
                  href=create_category_url(metadata.get('category', 'Uncategorized')),
                  cls="text-xs tracking-wider uppercase text-primary font-medium hover:underline"),
                cls="mb-3"
            ),
            H1(metadata.get('title', 'Untitled Post'), cls="text-3xl md:text-4xl font-bold mb-4 leading-tight"),
            Div(meta_section(metadata.get('date', 'Unknown date'), metadata.get('author', 'Anonymous'), cls="inline"), 
                reading_time_elem, cls="mb-4"),
            header_alert,
            cls="mb-8"
        ),
        
        # Table of contents for longer posts
        Div(
            H2("Table of Contents", cls="text-xl font-bold mb-4"),
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
            H3("Conclusion", cls="text-xl font-semibold mb-4"),
            Div(None, data_slot="conclusion", cls="text-base-content/90 [&_a]:text-accent [&_a]:underline [&_a]:decoration-accent/30 hover:[&_a]:text-accent-focus"),
            cls="mt-10 p-6 bg-base-200 dark:bg-base-300/10 rounded-lg border border-base-300 shadow-inner",
            data_pyxie_show="conclusion"
        ),
               
        # Share section
        Div(None, data_slot="share", cls="mt-8 flex items-center justify-start"),
        
        cls="blog-post max-w-3xl mx-auto px-4 py-8 leading-relaxed"
    )

def blog_post_page(post, title=None):
    """Simple wrapper that applies the page shell while preserving post content structure."""            
    content = post.render()  # render is equivalent to NotStr(post.html)  
    return app_layout(content, title=title or post.title)

def article_page(page=1, sort=DEFAULT_SORT, category=None):
    result = get_sorted_posts(category=category, page=page, sort=sort)
    page_title = f"Category: {category}" if category else "Latest Posts"
    base_path = create_category_url(category) if category else "/"
    
    # Show empty state if no posts found
    if not result.items:
        return app_layout(
            Div(
                H1(page_title, cls="text-3xl font-bold mb-4 pt-8"),
                P("No posts found in this category.", cls="mb-4"),
                A("← Back to Home", href="/", cls="text-primary hover:underline"),
                cls="max-w-4xl mx-auto"
            ), 
            title=page_title
        )
    
    return app_layout(
        Div(
            H1(page_title, cls="text-3xl font-bold mb-12 pt-8"),
            post_list(result.items, featured_first=True),
            pagination(result.pagination, base_path, sort),
            cls="max-w-4xl mx-auto"
        ),
        title=page_title
    )

# Routes
@rt("/")
def home(page: int = 1, sort: str = DEFAULT_SORT):
    return article_page(page=page, sort=sort)

@rt("/post/{slug}")
def get_post(slug: str):
    post, error = pyxie.get_item(slug, status="published")
    return handle_error(error[0], error[1]) if error else blog_post_page(post)

@rt("/category/{category}")
def category_page(category: str, page: int = 1, sort: str = DEFAULT_SORT):  
    return article_page(page=page, sort=sort, category=category.replace('-', ' ').title())

if __name__ == "__main__":      
    serve(reload=False, port=5002)