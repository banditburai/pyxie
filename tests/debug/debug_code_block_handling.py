"""Debug script to understand how code blocks are handled."""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from mistletoe import Document
from mistletoe.block_token import add_token, CodeFence
from pyxie.parser import FastHTMLToken, ScriptToken, NestedContentToken, custom_tokenize_block
from pyxie.renderer import NestedRenderer

def debug_code_block_handling():
    """Debug how code blocks are handled in the rendering process."""
    print("\n=== Testing Code Block Handling ===\n")
    
    # Register tokens
    add_token(FastHTMLToken)
    add_token(ScriptToken)
    add_token(NestedContentToken)
    
    # Test case from test_mixed_content_handling
    content = """
# Mixed Content Example

Here's a regular paragraph.

And here's an example of FastHTML code in a code block:

```python
# Example FastHTML code
<fasthtml>
def ExampleComponent():
    return Div(
        H2("This should not be executed"),
        P("This is just an example")
    )

show(ExampleComponent())
</fasthtml>
```
"""
    
    print("Test Case: Mixed Content with Code Block")
    print("\nInput content:")
    print(content)
    
    # Step 1: Tokenization
    print("\nStep 1: Tokenization")
    doc = Document('')
    doc.children = list(custom_tokenize_block(content, [FastHTMLToken, ScriptToken, NestedContentToken]))
    
    print("\nDocument children:")
    for i, child in enumerate(doc.children):
        print(f"\nChild {i}:")
        print(f"Type: {type(child).__name__}")
        if isinstance(child, CodeFence):
            print(f"Language: {child.language}")
            print(f"Content: {child.content}")
            # Print the raw content to see how it's being processed
            print("Raw content:")
            print(child.content)
        else:
            print(f"Content: {getattr(child, 'content', 'N/A')}")
            if hasattr(child, 'children'):
                print("Children:")
                for j, grandchild in enumerate(child.children):
                    print(f"  Grandchild {j}:")
                    print(f"  Type: {type(grandchild).__name__}")
                    print(f"  Content: {getattr(grandchild, 'content', 'N/A')}")
    
    # Step 2: Rendering
    print("\nStep 2: Rendering")
    renderer = NestedRenderer()
    result = renderer.render(doc)
    
    print("\nRendered output:")
    print(result)
    
    # Step 3: Analysis
    print("\nStep 3: Analysis")
    print("\nExpected behavior:")
    print("1. Code block should be rendered as literal text")
    print("2. FastHTML content should be escaped")
    print("3. No FastHTML execution should occur")
    
    print("\nActual behavior:")
    print("1. Code block present:", '<pre><code class="language-python">' in result)
    print("2. FastHTML content escaped:", "&lt;fasthtml&gt;" in result)
    print("3. FastHTML executed:", '<h2>This should not be executed</h2>' in result)
    
    # Test case from test_documentation_with_imports
    content2 = """
## Component Usage

```markdown
<fasthtml>
# Import components from your app
from components import Button
from datetime import datetime

def Greeting():
    return Div(
        H1("Hello, World!", cls="text-3xl font-bold"),
        P(f"The time is: {datetime.now().strftime('%H:%M')}"),
        Button(text="Click me!", onclick="alert('Hello!')")
    )

show(Greeting())
</fasthtml>
```
"""
    
    print("\nTest Case: Documentation with Imports")
    print("\nInput content:")
    print(content2)
    
    # Step 1: Tokenization
    print("\nStep 1: Tokenization")
    doc = Document('')
    doc.children = list(custom_tokenize_block(content2, [FastHTMLToken, ScriptToken, NestedContentToken]))
    
    print("\nDocument children:")
    for i, child in enumerate(doc.children):
        print(f"\nChild {i}:")
        print(f"Type: {type(child).__name__}")
        print(f"Content: {getattr(child, 'content', 'N/A')}")
        if hasattr(child, 'children'):
            print("Children:")
            for j, grandchild in enumerate(child.children):
                print(f"  Grandchild {j}:")
                print(f"  Type: {type(grandchild).__name__}")
                print(f"  Content: {getattr(grandchild, 'content', 'N/A')}")
    
    # Step 2: Rendering
    print("\nStep 2: Rendering")
    result = renderer.render(doc)
    
    print("\nRendered output:")
    print(result)
    
    # Step 3: Analysis
    print("\nStep 3: Analysis")
    print("\nExpected behavior:")
    print("1. Code block should be rendered as literal text")
    print("2. FastHTML content should be escaped")
    print("3. No FastHTML execution should occur")
    
    print("\nActual behavior:")
    print("1. Code block present:", '<pre><code class="language-markdown">' in result)
    print("2. FastHTML content escaped:", "&lt;fasthtml&gt;" in result)
    print("3. FastHTML executed:", '<h1 class="text-3xl font-bold">' in result)

if __name__ == "__main__":
    debug_code_block_handling() 