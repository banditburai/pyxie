"""Debug script for testing layout inheritance and slot filling."""
from pyxie.layouts import layout, get_layout
from fastcore.xml import Html, Head, Body, Title, Div, H1, to_xml
from pyxie.slots import process_slots_and_visibility
from pyxie.types import ContentItem

def debug_slot_filling():
    """Test different ways of filling slots to understand what works."""
    print("\n=== Testing Slot Filling ===\n")
    
    # 1. Test direct XML content
    print("1. Testing with direct XML content:")
    content = Div(H1("Test"), Div("By Author", cls="author"), cls="article-content")
    content_xml = to_xml(content)
    print(f"Original content XML:\n{content_xml}\n")
    
    # Create a simple container with a slot
    container = Html(
        Body(
            Div(None, data_slot="content", cls="container")
        )
    )
    container_xml = to_xml(container)
    print(f"Container XML:\n{container_xml}\n")
    
    # Try different ways of passing content
    methods = {
        "Direct string": content_xml,
        "List with string": [content_xml],
        "Direct XML": content,
        "List with XML": [content],
    }
    
    for method_name, content_value in methods.items():
        print(f"\nTrying {method_name}:")
        print(f"Content type: {type(content_value)}")
        print(f"Content value: {content_value}")
        try:
            result = process_slots_and_visibility(
                container_xml,
                {"content": content_value}
            )
            print(f"Result:\n{result.element if result.was_filled else 'Failed'}\n")
            print(f"Was filled: {result.was_filled}")
            if not result.was_filled:
                print(f"Error: {result.error}")
        except Exception as e:
            print(f"Error: {e}")
    
    print("\n=== Testing with Layouts ===\n")
    
    # Test base layout independently
    print("Testing base layout:")
    @layout("debug_base")
    def debug_base_layout():
        return Html(
            Body(
                Div(None, data_slot="content", cls="base-container")
            )
        )
    
    base = get_layout("debug_base")
    print(f"Base layout retrieved: {base is not None}")
    
    # Test direct content in base layout
    print("\nTesting direct content in base layout:")
    base_result = base.create(slots={"content": content_xml})
    print(f"Base layout result:\n{base_result}\n")
    
    # Test article layout
    print("Testing article layout:")
    @layout("debug_article")
    def debug_article_layout():
        base = get_layout("debug_base")
        content = Div(
            H1("Article Title"),
            Div("By Debug Author", cls="author"),
            cls="article-content"
        )
        content_xml = to_xml(content)
        print(f"Article content XML:\n{content_xml}\n")
        
        result = base.create(slots={"content": content_xml})
        print(f"Article layout result:\n{result}\n")
        return result
    
    article = get_layout("debug_article")
    print(f"Article layout retrieved: {article is not None}")
    
    # Test article layout creation
    print("\nTesting article layout creation:")
    article_result = article.create()
    print(f"Final article result:\n{article_result}\n")

if __name__ == "__main__":
    debug_slot_filling() 