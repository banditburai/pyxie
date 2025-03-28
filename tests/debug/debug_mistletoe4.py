from mistletoe import Document as BaseDocument
from mistletoe import HtmlRenderer
from mistletoe.block_token import BlockToken, tokenize
from mistletoe.span_token import tokenize_inner
import re
from io import StringIO

class ContentBlockToken(BlockToken):
    """Token for content blocks that may contain nested markdown and HTML."""
    
    pattern = re.compile(r'^\s*<(?!(?:ft|fasthtml|script)(?:\s|>))([a-zA-Z][\w-]*)(?:\s+([^>]*))?>\s*$')
    priority = 100  # Much higher priority than HTML blocks (10)
    
    def __init__(self, tag_name=None, attrs=None, children=None, line_number=1):
        self.tag_name = tag_name
        self.attrs = attrs or {}
        self.line_number = line_number
        # Store children before initializing base class
        self._children = children or []
        # Initialize base class with empty lines and a tokenize function that returns stored children
        super().__init__([], lambda x: self._children)
        # Set children after base class initialization
        BlockToken.children.__set__(self, self._children)
    
    @property
    def children(self):
        return self._children
    
    @children.setter
    def children(self, value):
        self._children = value
        # Call the base class's setter with the actual children
        BlockToken.children.__set__(self, value)
    
    def __repr__(self):
        return f'<{self.tag_name}>'
    
    @classmethod
    def start(cls, line):
        """Check if this line starts a content block."""
        match = cls.pattern.match(line)
        print(f"Checking if line starts content block: {line}")
        print(f"Match result: {match is not None}")
        return bool(match)
    
    @classmethod
    def read(cls, lines):
        """Read the content block and its nested content."""
        # Get the first line
        first_line = next(lines)
        print(f"Reading content block starting with: {first_line}")
        
        # Parse the opening tag
        match = cls.pattern.match(first_line)
        if not match:
            return None
        
        tag_name = match.group(1)
        attrs_str = match.group(2) or ''
        print(f"Found tag: {tag_name} with attrs: {attrs_str}")
        
        # Parse attributes
        attrs = {}
        for attr in attrs_str.split():
            if '=' in attr:
                key, value = attr.split('=', 1)
                value = value.strip('"\'')
                attrs[key] = value
            else:
                attrs[attr] = True
        
        # Collect content until we find the matching end tag
        content_lines = []
        nesting_level = 1
        end_tag = f'</{tag_name}>'
        
        while nesting_level > 0:
            try:
                line = next(lines)
                print(f"Processing line: {line}")
                if line.strip() == end_tag:
                    nesting_level -= 1
                    print(f"Found end tag, nesting level: {nesting_level}")
                    if nesting_level == 0:
                        break
                elif cls.pattern.match(line) and cls.pattern.match(line).group(1) == tag_name:
                    nesting_level += 1
                    print(f"Found nested tag, nesting level: {nesting_level}")
                content_lines.append(line)
            except StopIteration:
                break
        
        # First tokenize the block-level content
        children = tokenize(content_lines) if content_lines else []
        
        # Then process span tokens in the children recursively
        def process_spans(tokens):
            for t in tokens:
                if hasattr(t, 'children'):
                    if isinstance(t.children, (list, tuple)):
                        # Process block-level children recursively
                        process_spans(t.children)
                    else:
                        # Process span-level children
                        t.children = tokenize_inner(str(t.children))
        
        process_spans(children)
        print(f"Created children: {children}")
        
        # Create a token with the parsed data and children
        token = cls(tag_name=tag_name, attrs=attrs, line_number=1)
        token.children = children  # Set children after creation
        return token

class Document(BaseDocument):
    """Custom Document class that handles content blocks."""
    
    def __init__(self, lines):
        # Register our token type
        from mistletoe.block_token import _token_types, HTMLBlock
        if ContentBlockToken not in _token_types:
            # Remove HTMLBlock temporarily
            if HTMLBlock in _token_types:
                _token_types.remove(HTMLBlock)
            _token_types.insert(0, ContentBlockToken)
            print("Token types:", [t.__name__ for t in _token_types])
        super().__init__(lines)

class TestRenderer(HtmlRenderer):
    """Simple renderer to test nested content handling."""
    
    def __init__(self):
        super().__init__()
        from mistletoe.block_token import Heading, Paragraph
        self.Heading = Heading
        self.Paragraph = Paragraph
        self.render_map['ContentBlockToken'] = self.render_content_block_token
    
    def render_content_block_token(self, token):
        """Render content blocks with nested markdown and HTML."""
        print(f"Rendering content block token: {token.tag_name}")
        print(f"Children: {token._children}")  # Access _children directly
        
        # Use render_inner to handle nested content
        content = self.render_inner(token)
        
        # Build the HTML tag with attributes
        attrs_str = ' ' + ' '.join(f'{k}="{v}"' for k, v in token.attrs.items()) if token.attrs else ''
        return f'<{token.tag_name}{attrs_str}>\n{content}\n</{token.tag_name}>'
    
    def render(self, token):
        """Override render to handle content blocks at the document level."""
        print(f"Rendering token of type: {type(token)}")
        if isinstance(token, ContentBlockToken):
            return self.render_content_block_token(token)
        elif isinstance(token, Document):
            return self.render_inner(token)
        return super().render(token)

def test_nested_parsing():
    """Test how mistletoe handles nested content."""
    
    test_cases = [
        # Test case 1: Content block with nested markdown
        {
            'input': '<content-block class="test">\n# Inner heading\nSome **bold** text\n</content-block>',
            'desc': 'Content block with nested markdown'
        },
        
        # Test case 2: Complex nesting
        {
            'input': '<outer-block>\n# Heading\n<inner-block>Nested content</inner-block>\nMore text\n</outer-block>',
            'desc': 'Complex nested structure'
        },
        
        # Test case 3: Complex nesting with HTML and Markdown
        {
            'input': '''<div class="container">
# Main Heading
Some **bold** text
<div class="inner">
    <span style="color: red">Red text</span>
    *Italic text*
    <button>Click me</button>
</div>
## Subheading
More content with `code` and [links](http://example.com)
</div>''',
            'desc': 'Complex nesting with HTML and Markdown'
        }
    ]
    
    # Create a custom renderer instance
    renderer = TestRenderer()
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n=== Test Case {i}: {case['desc']} ===")
        print("Input:", case['input'])
        
        # Parse and render the document
        doc = Document(case['input'].split('\n'))
        print("Document children:", [type(child).__name__ for child in doc.children])
        result = renderer.render(doc)
        
        print("Result:", result)
        print("\nExpected behavior:")
        print("1. HTML tags should be preserved")
        print("2. Markdown should be rendered within HTML blocks")
        print("3. Nested structure should be maintained")
        print("4. Attributes should be preserved")
        print("5. Both block and inline markdown should work")

if __name__ == '__main__':
    test_nested_parsing() 