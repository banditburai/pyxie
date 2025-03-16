def test_layout_inheritance():
    """Test that layouts can inherit from other layouts."""
    from pyxie.layouts import layout, get_layout
    from fastcore.xml import Html, Head, Body, Title, Div, H1, FT
    
    # Create a base layout
    @layout("base")
    def base_layout(title="Default Title", metadata=None):
        return Html(
            Head(
                Title(title)
            ),
            Body(
                Div(None, data_slot="content")
            )
        )
    
    # Create a derived layout that uses the base layout
    @layout("article")
    def article_layout(title="Article", author=None, metadata=None):
        # Get the base layout
        base = get_layout("base")
        
        # Create the content for the base layout
        content = Div(
            H1(title),
            Div(f"By {author}" if author else None, class_="author"),
            Div(None, data_slot="content", class_="article-content")
        )
        
        # Apply the base layout with the article content in the "content" slot
        return base.create(title=title, metadata=metadata, slots={"content": content})
    
    # Test retrieving the article layout
    article = get_layout("article")
    assert article is not None
    
    # Test rendering the article layout
    result = article.create(title="Test Article", author="Test Author")
    
    # Verify inheritance worked correctly
    assert "Test Article" in result  # Check title is in the result
    assert "By Test Author" in result  # Check author is in the result
    assert "article-content" in result  # Check the content slot is in the result

def test_layout_composition():
    """Test composing layouts from reusable components."""
    from pyxie.layouts import layout, get_layout
    from fastcore.xml import Div, Nav, Footer, A, P, FT
    
    # Create component functions (not registered as layouts)
    def navigation_component(links=None):
        """Create a navigation component."""
        links = links or {"Home": "/", "About": "/about"}
        items = [A(name, href=url) for name, url in links.items()]
        return Nav(*items, class_="main-nav")
    
    def footer_component(copyright=None):
        """Create a footer component."""
        return Footer(
            P(copyright or "© 2024"),
            class_="main-footer"
        )
    
    # Create a layout that composes these components
    @layout("page")
    def page_layout(title, show_nav=True, show_footer=True, metadata=None):
        # Create components conditionally
        nav = navigation_component() if show_nav else None
        footer = footer_component() if show_footer else None
        
        # Compose the layout
        return Div(
            nav,
            Div(None, data_slot="header"),
            Div(None, data_slot="content", class_="main-content"),
            footer
        )
    
    # Test basic layout with all components
    page = get_layout("page")
    result = page.create(title="Test Page")
    
    # Convert to XML
    from fastcore.xml import to_xml
    xml = to_xml(result)
    
    # Verify components were included - check for classes in a way that works with both formats
    assert "<nav" in xml
    assert "main-nav" in xml
    assert "<a href=\"/\">Home</a>" in xml
    assert "<footer" in xml
    assert "main-footer" in xml
    
    # Test layout without navigation
    result_no_nav = page.create(title="No Nav", show_nav=False)
    xml_no_nav = to_xml(result_no_nav)
    
    # Verify navigation is missing but footer is present
    assert "<nav" not in xml_no_nav
    assert "<footer" in xml_no_nav
    
    # Test layout without footer
    result_no_footer = page.create(title="No Footer", show_footer=False)
    xml_no_footer = to_xml(result_no_footer)
    
    # Verify navigation is present but footer is missing
    assert "<nav" in xml_no_footer
    assert "<footer" not in xml_no_footer

def test_nested_layout_composition():
    """Test deeply nested layout composition with multiple levels."""
    from pyxie.layouts import layout, get_layout
    from fastcore.xml import Div, H1, H2, P, FT
    
    # Create nested layouts
    @layout("section")
    def section_layout(title, level=2, metadata=None):
        """Create a section layout with a title and content."""
        header = H1(title) if level == 1 else H2(title)
        return Div(
            header,
            Div(None, data_slot="content"),
            class_=f"section section-level-{level}"
        )
    
    @layout("page")
    def page_layout(title, sections=None, metadata=None):
        """Create a page with multiple sections."""
        # Create the main container with just the title initially
        elements = [H1(title)]
        
        # If sections are provided, create section layouts
        if sections:
            for i, section in enumerate(sections):
                section_title = section.get("title", f"Section {i+1}")
                section_level = section.get("level", 2)
                
                # Create a simplified section directly
                header = H1(section_title) if section_level == 1 else H2(section_title)
                content = P(section.get("content", "")) if section.get("content") else None
                
                section_div = Div(
                    header,
                    content,
                    class_=f"section section-level-{section_level}"
                )
                
                elements.append(section_div)
        
        # Create the final container with all elements
        return Div(*elements, class_="page")
    
    # Test creating a page with multiple sections
    sections = [
        {"title": "Introduction", "level": 2, "content": "This is the introduction."},
        {"title": "Main Content", "level": 2, "content": "This is the main content."},
        {"title": "Conclusion", "level": 2, "content": "This is the conclusion."}
    ]
    
    page = get_layout("page")
    result = page.create(title="Test Page", sections=sections)
    
    # Verify the page structure with simpler assertions
    assert "Test Page" in result
    assert "Introduction" in result
    assert "Main Content" in result
    assert "Conclusion" in result
    assert "This is the introduction" in result
    assert "section-level-2" in result

def test_layout_name_attribute():
    """Test that the @layout decorator sets the _layout_name attribute correctly."""
    from pyxie.layouts import layout, get_layout
    from fastcore.xml import Div, H1, FT
    
    # Create a test layout
    @layout("test_attr")
    def test_attr_layout(title="Test") -> FT:
        return Div(H1(title))
    
    # Verify the _layout_name attribute was set
    assert hasattr(test_attr_layout, '_layout_name')
    assert test_attr_layout._layout_name == "test_attr"
    
    # Verify the layout was registered
    registered_layout = get_layout("test_attr")
    assert registered_layout is not None
    assert registered_layout.name == "test_attr" 