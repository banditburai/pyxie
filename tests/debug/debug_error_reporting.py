"""Debug script to test error reporting in the parser."""

from mistletoe import Document
from mistletoe.block_token import add_token
from pyxie.parser import FastHTMLToken, ScriptToken, NestedContentToken

def test_script_handling():
    """Test script tag handling."""
    print("\n=== Testing Script Tag Handling ===\n")
    
    # Register tokens
    add_token(FastHTMLToken)
    add_token(ScriptToken)
    add_token(NestedContentToken)
    
    # Test 1: Basic script tag
    print("Test 1: Basic script tag")
    try:
        content = """<script>
console.log("test");
</script>"""
        lines = iter(content.split('\n'))
        content_lines = ScriptToken.read(lines)
        token = ScriptToken(content_lines)
        print(f"Success! Token content: {token.content}")
    except ValueError as e:
        print(f"Unexpected error: {e}")
    
    # Test 2: Script tag with attributes
    print("\nTest 2: Script tag with attributes")
    try:
        content = """<script type="text/javascript">
console.log("test");
</script>"""
        lines = iter(content.split('\n'))
        content_lines = ScriptToken.read(lines)
        token = ScriptToken(content_lines)
        print(f"Success! Token content: {token.content}")
        print(f"Token attributes: {token.attrs}")
    except ValueError as e:
        print(f"Unexpected error: {e}")
    
    # Test 3: Script tag with line breaks
    print("\nTest 3: Script tag with line breaks")
    try:
        content = """<script>

console.log("test");

</script>"""
        lines = iter(content.split('\n'))
        content_lines = ScriptToken.read(lines)
        token = ScriptToken(content_lines)
        print(f"Success! Token content: {token.content}")
    except ValueError as e:
        print(f"Unexpected error: {e}")
    
    # Test 4: Script tag inside nested content
    print("\nTest 4: Script tag inside nested content")
    try:
        content = """<custom>
<script>
console.log("test");
</script>
</custom>"""
        lines = iter(content.split('\n'))
        content_lines = NestedContentToken.read(lines)
        token = NestedContentToken(content_lines)
        print(f"Success! Token children: {len(token.children)}")
        for child in token.children:
            print(f"Child type: {type(child).__name__}")
            if isinstance(child, ScriptToken):
                print(f"Script content: {child.content}")
    except ValueError as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    test_script_handling() 