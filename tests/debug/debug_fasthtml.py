"""Debug script for exploring FastHTML code execution and error handling."""

import logging
from pathlib import Path
from pyxie.fasthtml import render_fasthtml, FastHTMLExecutor
from pyxie.types import ContentItem
from pyxie.renderer import render_content
from pyxie.layouts import layout, registry
from pyxie.parser import FastHTMLToken

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Set up test layout
@layout("default")
def default_layout(content: str = "") -> str:
    """Default layout that just renders the content directly."""
    return content

def debug_code_execution(code: str, context_path: Path = None):
    """Debug the execution of FastHTML code."""
    print("\n=== Debugging Code Execution ===")
    print("Input code:")
    print(code)
    print("\nTrying to execute with FastHTMLExecutor:")
    try:
        with FastHTMLExecutor(context_path) as executor:
            results = executor.execute(code)
            print("\nExecution successful!")
            print("Results:", results)
    except Exception as e:
        print("\nExecution failed!")
        print("Error:", str(e))
        print("Error type:", type(e).__name__)

def debug_render_fasthtml(content: str, context_path: Path = None):
    """Debug the render_fasthtml function."""
    print("\n=== Debugging render_fasthtml ===")
    print("Input content:")
    print(content)
    print("\nTrying to render:")
    result = render_fasthtml(content, context_path)
    print("\nResult:")
    print("Success:", result.success)
    print("Content:", result.content)
    print("Error:", result.error)

def debug_content_rendering(content: str):
    """Debug the full content rendering process."""
    print("\n=== Debugging Content Rendering ===")
    print("Input content:")
    print(content)
    print("\nCreating ContentItem:")
    item = ContentItem(
        source_path=Path("test.md"),
        metadata={"layout": "default"},
        content=content
    )
    print("\nTrying to render content:")
    try:
        html = render_content(item)
        print("\nRendering successful!")
        print("Output HTML:")
        print(html)
    except Exception as e:
        print("\nRendering failed!")
        print("Error:", str(e))
        print("Error type:", type(e).__name__)

def debug_token_parsing(content: str):
    """Debug how FastHTML tokens are parsed."""
    print("\n=== Debugging Token Parsing ===")
    print("Input content:")
    print(content)
    print("\nCreating FastHTMLToken:")
    # Remove empty lines at the start and end
    lines = [line for line in content.split('\n') if line.strip()]
    if not lines:
        print("No non-empty lines found")
        return
    token = FastHTMLToken(lines)
    print("\nToken details:")
    print("Content:", token.content)
    print("Attributes:", token.attrs)

def main():
    """Run all debug tests."""
    # Test 1: Basic FastHTML code
    print("\n=== Test 1: Basic FastHTML Code ===")
    code = """
def test_function():
    return "Hello World"
show(test_function())
"""
    debug_code_execution(code)
    debug_render_fasthtml(code)
    
    # Test 2: Syntax error
    print("\n=== Test 2: Syntax Error ===")
    code = """
def broken_function():
return "This will never execute"
"""
    debug_code_execution(code)
    debug_render_fasthtml(code)
    
    # Test 3: Runtime error
    print("\n=== Test 3: Runtime Error ===")
    code = """
def div_by_zero():
    x = 1/0
    return x
show(div_by_zero())
"""
    debug_code_execution(code)
    debug_render_fasthtml(code)
    
    # Test 4: Component rendering
    print("\n=== Test 4: Component Rendering ===")
    content = """
<ft>
def TestComponent():
    return Div(
        H1("Test Title"),
        P("Test content"),
        cls="test-component"
    )
show(TestComponent())
</ft>
"""
    debug_token_parsing(content)
    debug_content_rendering(content)
    
    # Test 5: Mixed content
    print("\n=== Test 5: Mixed Content ===")
    content = """
<ft>
show(Div("FastHTML content"))
</ft>

<script>
console.log("Script content");
</script>

Regular markdown content.

<ft>
show(Div("More FastHTML content"))
</ft>
"""
    debug_content_rendering(content)

if __name__ == "__main__":
    main() 