"""Test the complete rendering pipeline including layout handling and slot filling."""

import re
import yaml
from typing import Dict, List, Set, Tuple, Any
from mistletoe import Document, HtmlRenderer
from mistletoe.block_token import BlockToken, add_token
from mistletoe.span_token import tokenize_inner
from mistletoe.block_tokenizer import tokenize_block
from lxml import html
from pathlib import Path

# Import our actual implementations
from src.pyxie.fasthtml import execute_fasthtml
from src.pyxie.types import ContentItem
from src.pyxie.layouts import get_layout
from src.pyxie.slots import fill_slots
from src.pyxie.constants import PYXIE_SHOW_ATTR

PYXIE_SHOW_ATTR = 'data-pyxie-show'

# Reserved tag names that should not be treated as nested content
RESERVED_TAGS = {
    'script', 'fasthtml', 'ft', 'html', 'head', 'body', 'div', 'span', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'ul', 'ol', 'li', 'a', 'img', 'table', 'tr', 'td', 'th', 'thead', 'tbody', 'form', 'input', 'button',
    'select', 'option', 'textarea', 'label', 'meta', 'link', 'style', 'title', 'header', 'footer', 'nav',
    'main', 'article', 'section', 'aside', 'figure', 'figcaption', 'blockquote', 'pre', 'code', 'em', 'strong',
    'i', 'b', 'u', 'mark', 'small', 'sub', 'sup', 'del', 'ins', 'q', 'cite', 'abbr', 'address', 'time',
    'progress', 'meter', 'canvas', 'svg', 'video', 'audio', 'source', 'track', 'embed', 'object', 'param',
    'map', 'area', 'col', 'colgroup', 'caption', 'tfoot', 'fieldset', 'legend', 'datalist', 'optgroup',
    'keygen', 'output', 'details', 'summary', 'menuitem', 'menu', 'dialog', 'slot', 'template', 'portal'
}

# Frontmatter patterns
FRONTMATTER_PATTERN = re.compile(r'^\s*---\s*\n(?P<frontmatter>.*?)\n\s*---\s*\n(?P<content>.*)', re.DOTALL)
EMPTY_FRONTMATTER_PATTERN = re.compile(r'^\s*---\s*\n\s*---\s*\n(?P<content>.*)', re.DOTALL)

def parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    """Parse YAML frontmatter from content."""
    if not content.strip().startswith('---'):
        return {}, content
        
    if empty_match := EMPTY_FRONTMATTER_PATTERN.match(content):
        return {}, empty_match.group('content')
        
    if not (match := FRONTMATTER_PATTERN.match(content)):
        return {}, content
        
    frontmatter_text, remaining_content = match.group('frontmatter'), match.group('content')
    
    try:
        metadata = yaml.safe_load(frontmatter_text) or {}
        if not isinstance(metadata, dict):
            raise ValueError(f"Frontmatter must be a dictionary, got {type(metadata).__name__}")
        return metadata, remaining_content
    except Exception as e:
        print(f"Warning: Failed to parse frontmatter: {e}")
        return {}, remaining_content

# Reuse token classes from debug_block_tokenizer.py
class FastHTMLToken(BlockToken):
    """Token for FastHTML blocks."""
    pattern = re.compile(r'^<(?:ft|fasthtml)(?:\s+([^>]*))?>')
    closing_pattern = re.compile(r'^\s*</(?:ft|fasthtml)>\s*$')
    parse_inner = False
    priority = 100
    
    def __init__(self, lines):
        self.lines = lines
        self.content = '\n'.join(lines[1:-1])  # Skip opening/closing tags
        self.attrs = self._parse_attrs(lines[0])
        
    def _parse_attrs(self, opening_line):
        """Parse attributes from opening tag."""
        match = self.pattern.match(opening_line)
        if not match:
            return {}
            
        attrs = {}
        attrs_str = match.group(1) if match.group(1) else ''
        for attr in attrs_str.split():
            if '=' in attr:
                key, value = attr.split('=', 1)
                attrs[key.strip()] = value.strip('"\'')
            else:
                attrs[attr.strip()] = True
        return attrs

    @classmethod
    def start(cls, line):
        """Check if line starts a FastHTML block."""
        return bool(cls.pattern.match(line))
    
    @classmethod
    def read(cls, lines):
        """Read a FastHTML block."""
        # Store the opening line
        opening_line = next(lines)
        content_lines = [opening_line]
        
        # Read until we find the closing tag
        for line in lines:
            content_lines.append(line)
            if cls.closing_pattern.match(line):
                break
        
        return content_lines

class ScriptToken(BlockToken):
    """Token for script blocks."""
    pattern = re.compile(r'^<script(?:\s+([^>]*))?>')
    closing_pattern = re.compile(r'^\s*</script>\s*$')
    parse_inner = False
    priority = 100
    
    def __init__(self, lines):
        self.lines = lines
        self.content = '\n'.join(lines[1:-1])  # Skip opening/closing tags
        self.attrs = self._parse_attrs(lines[0])
        
    def _parse_attrs(self, opening_line):
        """Parse attributes from opening tag."""
        match = self.pattern.match(opening_line)
        if not match:
            return {}
            
        attrs = {}
        attrs_str = match.group(1) if match.group(1) else ''
        for attr in attrs_str.split():
            if '=' in attr:
                key, value = attr.split('=', 1)
                attrs[key.strip()] = value.strip('"\'')
            else:
                attrs[attr.strip()] = True
        return attrs

    @classmethod
    def start(cls, line):
        """Check if line starts a script block."""
        return bool(cls.pattern.match(line))
    
    @classmethod
    def read(cls, lines):
        """Read a script block."""
        # Store the opening line
        opening_line = next(lines)
        content_lines = [opening_line]
        
        # Read until we find the closing tag
        for line in lines:
            content_lines.append(line)
            if cls.closing_pattern.match(line):
                break
        
        return content_lines

class NestedContentToken(BlockToken):
    """A token that supports nested markdown content in any valid XML tag."""
    pattern = re.compile(r'^<([a-zA-Z][a-zA-Z0-9-]*)(?:\s+([^>]*))?>\s*$')
    closing_pattern = re.compile(r'^\s*</([a-zA-Z][a-zA-Z0-9-]*)>\s*$')
    parse_inner = True
    priority = 100
    
    def __init__(self, lines):
        self.lines = lines
        self.content = '\n'.join(lines[1:-1])  # Skip opening/closing tags
        self.attrs = self._parse_attrs(lines[0])
        self.tag_name = self._parse_tag_name(lines[0])
        
        # Split content into blocks
        self.blocks = self._split_blocks(self.content)
        
        # Create a Document for the inner content and get its children
        inner_doc = Document('\n'.join(block for block in self.blocks if not self._is_special_block(block)))
        self.children = inner_doc.children
    
    def _parse_tag_name(self, opening_line):
        """Parse the tag name from the opening line."""
        match = self.pattern.match(opening_line)
        if not match:
            return None
        return match.group(1)
    
    def _parse_attrs(self, opening_line):
        """Parse attributes from opening tag."""
        match = self.pattern.match(opening_line)
        if not match or not match.group(2):
            return {}
            
        attrs = {}
        attrs_str = match.group(2)
        for attr in attrs_str.split():
            if '=' in attr:
                key, value = attr.split('=', 1)
                attrs[key.strip()] = value.strip('"\'')
            else:
                attrs[attr.strip()] = True
        return attrs
    
    def _is_special_block(self, block):
        """Check if a block is a special block (FastHTML, Script, or custom tag)."""
        lines = block.strip().split('\n')
        if not lines:
            return False
        first_line = lines[0].strip()
        return (FastHTMLToken.start(first_line) or 
                ScriptToken.start(first_line) or 
                (NestedContentToken.start(first_line) and 
                 NestedContentToken.pattern.match(first_line).group(1).lower() not in RESERVED_TAGS))
    
    def _split_blocks(self, content):
        """Split content into blocks, preserving special blocks."""
        lines = content.split('\n')
        blocks = []
        current_block = []
        in_special_block = False
        special_tag = None
        
        for line in lines:
            # Check for special block start
            if not in_special_block:
                if FastHTMLToken.start(line):
                    if current_block:
                        blocks.append('\n'.join(current_block))
                        current_block = []
                    in_special_block = True
                    special_tag = 'fasthtml'
                    current_block.append(line)
                elif ScriptToken.start(line):
                    if current_block:
                        blocks.append('\n'.join(current_block))
                        current_block = []
                    in_special_block = True
                    special_tag = 'script'
                    current_block.append(line)
                elif NestedContentToken.start(line):
                    match = NestedContentToken.pattern.match(line)
                    if match and match.group(1).lower() not in RESERVED_TAGS:
                        if current_block:
                            blocks.append('\n'.join(current_block))
                            current_block = []
                        in_special_block = True
                        special_tag = match.group(1)
                        current_block.append(line)
                    else:
                        current_block.append(line)
                else:
                    current_block.append(line)
            else:
                current_block.append(line)
                # Check for special block end
                if special_tag == 'fasthtml' and FastHTMLToken.closing_pattern.match(line):
                    blocks.append('\n'.join(current_block))
                    current_block = []
                    in_special_block = False
                    special_tag = None
                elif special_tag == 'script' and ScriptToken.closing_pattern.match(line):
                    blocks.append('\n'.join(current_block))
                    current_block = []
                    in_special_block = False
                    special_tag = None
                elif special_tag and re.match(f'^\\s*</{special_tag}>\\s*$', line):
                    blocks.append('\n'.join(current_block))
                    current_block = []
                    in_special_block = False
                    special_tag = None
        
        if current_block:
            blocks.append('\n'.join(current_block))
        
        return blocks

    @classmethod
    def start(cls, line):
        """Check if line starts a valid nested content block."""
        match = cls.pattern.match(line)
        if not match:
            return False
            
        tag_name = match.group(1)
        return tag_name.lower() not in RESERVED_TAGS

    @classmethod
    def read(cls, lines):
        """Read a content block."""
        # Store the opening line
        opening_line = next(lines)
        content_lines = [opening_line]
        
        # Get the tag name for closing pattern
        tag_name = cls.pattern.match(opening_line).group(1)
        closing_pattern = re.compile(f'^\\s*</{tag_name}>\\s*$')
        
        # Read until we find the closing tag
        nested_level = 1
        
        for line in lines:
            content_lines.append(line)
            
            # Check for nested tags
            if cls.pattern.match(line) and cls.pattern.match(line).group(1) == tag_name:
                nested_level += 1
            elif closing_pattern.match(line):
                nested_level -= 1
                if nested_level == 0:
                    break
        
        return content_lines

class NestedRenderer(HtmlRenderer):
    """A renderer that handles nested markdown content."""
    
    def __init__(self):
        super().__init__()
        self.render_map['NestedContentToken'] = self.render_nested_content
        self.render_map['FastHTMLToken'] = self.render_fasthtml
        self.render_map['ScriptToken'] = self.render_script
    
    def render_nested_content(self, token):
        """Render a content block with nested markdown."""
        try:
            print(f"\nRendering nested content:")
            print(f"  Tag: {token.tag_name}")
            print(f"  Content:\n{token.content}")
            print(f"  Blocks: {len(token.blocks)}")
            
            # Render each block
            rendered_blocks = []
            for block in token.blocks:
                if token._is_special_block(block):
                    # Create appropriate token for special block
                    lines = block.strip().split('\n')
                    if FastHTMLToken.start(lines[0]):
                        rendered_blocks.append(self.render(FastHTMLToken(lines)))
                    elif ScriptToken.start(lines[0]):
                        rendered_blocks.append(self.render(ScriptToken(lines)))
                    else:
                        rendered_blocks.append(self.render(NestedContentToken(lines)))
                else:
                    # Create a Document for regular markdown content
                    doc = Document(block)
                    # Use render_inner to preserve HTML
                    rendered_blocks.append(self.render_inner(doc))
            
            # Build attributes string
            attrs_str = ' '.join(f'{k}="{v}"' for k, v in token.attrs.items())
            if attrs_str:
                attrs_str = ' ' + attrs_str
            
            # Join blocks with newlines
            inner = '\n'.join(rendered_blocks)
            return f'<{token.tag_name}{attrs_str}>\n{inner}\n</{token.tag_name}>'
        except Exception as e:
            print(f"Error rendering nested content: {e}")
            return f'<{token.tag_name} class="error">Error: {e}</{token.tag_name}>'
    
    def render_fasthtml(self, token):
        """Render a FastHTML block."""
        try:
            print(f"\nRendering FastHTML:")
            print(f"  Content:\n{token.content}")
            
            # Build attributes string
            attrs_str = ' '.join(f'{k}="{v}"' for k, v in token.attrs.items())
            if attrs_str:
                attrs_str = ' ' + attrs_str
            
            # Render FastHTML content
            result = execute_fasthtml(token.content)
            if result.error:
                return f'<div class="error">Error: {result.error}</div>'
            elif result.content:
                return f'<div{attrs_str}>\n{result.content}\n</div>'
            else:
                # Mock FastHTML rendering for testing
                return f'<div{attrs_str}>\n<p>FastHTML output: {token.content}</p>\n</div>'
        except Exception as e:
            print(f"Error rendering FastHTML: {e}")
            return f'<div class="error">Error: {e}</div>'
    
    def render_script(self, token):
        """Render a script block."""
        try:
            print(f"\nRendering script:")
            print(f"  Content:\n{token.content}")
            
            # Build attributes string
            attrs_str = ' '.join(f'{k}="{v}"' for k, v in token.attrs.items())
            if attrs_str:
                attrs_str = ' ' + attrs_str
            
            return f'<script{attrs_str}>\n{token.content}\n</script>'
        except Exception as e:
            print(f"Error rendering script: {e}")
            return f'<script class="error">Error: {e}</script>'

def extract_slots_with_content(rendered_blocks: Dict[str, List[str]]) -> Set[str]:
    """Extract slot names that have content."""
    return {name for name, blocks in rendered_blocks.items() if any(block.strip() for block in blocks)}

def check_visibility_condition(slot_names: List[str], filled_slots: Set[str]) -> bool:
    """Determine if an element should be visible based on slot conditions."""
    if not slot_names:
        return True
        
    has_positive = False
    for slot in (s.strip() for s in slot_names):
        if not slot:
            continue
        if slot.startswith('!'):
            if slot[1:].strip() in filled_slots:
                return False
        else:
            has_positive = True
            if slot in filled_slots:
                return True
    return not has_positive

def process_element(element: html.HtmlElement, parent: html.HtmlElement, filled_slots: Set[str]) -> None:
    """Process a single element for conditional visibility."""
    if PYXIE_SHOW_ATTR in element.attrib:
        slot_names = [name.strip() for name in element.attrib[PYXIE_SHOW_ATTR].split(',')]
        if not check_visibility_condition(slot_names, filled_slots):
            return
    
    # Create new element with same tag and attributes
    new_element = html.Element(element.tag)
    # Copy all attributes except data-pyxie-show
    for key, value in element.attrib.items():
        if key != PYXIE_SHOW_ATTR:
            new_element.set(key, value)
    new_element.text = element.text
    new_element.tail = element.tail
    parent.append(new_element)
    
    # Process children
    for child in element.getchildren():
        process_element(child, new_element, filled_slots)

def process_conditional_visibility(layout_html: str, filled_slots: Set[str]) -> str:
    """Process data-pyxie-show attributes in HTML."""
    try:
        # Parse HTML
        doc = html.fromstring(layout_html)
        
        # Create new root element with all attributes
        new_doc = html.Element(doc.tag)
        for key, value in doc.attrib.items():
            new_doc.set(key, value)
        new_doc.text = doc.text
        new_doc.tail = doc.tail
        
        # Process each child of the root
        for element in doc.getchildren():
            process_element(element, new_doc, filled_slots)
        
        # Convert back to string with proper indentation
        result = html.tostring(new_doc, encoding='unicode', pretty_print=True, method='html')
        # Fix indentation by removing extra spaces at the start of lines
        lines = result.split('\n')
        fixed_lines = []
        for line in lines:
            if line.strip():
                fixed_lines.append(line)
            else:
                fixed_lines.append('')
        return '\n'.join(fixed_lines)
        
    except Exception as e:
        print(f"Error processing conditional visibility: {e}")
        return layout_html

def fill_slots_in_element(element: html.HtmlElement, rendered_blocks: Dict[str, List[str]]) -> None:
    """Fill slots in an element and its children."""
    # Check if element's text contains a slot marker
    if element.text:
        for slot_name, blocks in rendered_blocks.items():
            marker = f"{{{{{slot_name}}}}}"
            if marker in element.text:
                # Parse the rendered content as HTML
                try:
                    content_doc = html.fromstring('\n'.join(blocks))
                    # Replace the marker with an empty string
                    element.text = element.text.replace(marker, '')
                    # Add the content elements as children
                    for content_element in content_doc.getchildren():
                        element.append(content_element)
                except Exception as e:
                    print(f"Error parsing rendered content: {e}")
                    element.text = element.text.replace(marker, '\n'.join(blocks))
    
    # Process children
    for child in element.getchildren():
        fill_slots_in_element(child, rendered_blocks)
        # Check child's tail text
        if child.tail:
            for slot_name, blocks in rendered_blocks.items():
                marker = f"{{{{{slot_name}}}}}"
                if marker in child.tail:
                    try:
                        content_doc = html.fromstring('\n'.join(blocks))
                        # Replace the marker with an empty string
                        child.tail = child.tail.replace(marker, '')
                        # Add the content elements as siblings after the current child
                        parent = child.getparent()
                        index = list(parent).index(child)
                        for i, content_element in enumerate(content_doc.getchildren(), 1):
                            parent.insert(index + i, content_element)
                    except Exception as e:
                        print(f"Error parsing rendered content: {e}")
                        child.tail = child.tail.replace(marker, '\n'.join(blocks))

def fill_slots(layout_html: str, rendered_blocks: Dict[str, List[str]]) -> ContentItem:
    """Fill slots in layout HTML with rendered content."""
    try:
        # Parse HTML
        doc = html.fromstring(layout_html)
        
        # Fill slots in the document
        fill_slots_in_element(doc, rendered_blocks)
        
        # Convert back to string with proper indentation
        result = html.tostring(doc, encoding='unicode', pretty_print=True, method='html')
        # Fix indentation by removing extra spaces at the start of lines
        lines = result.split('\n')
        fixed_lines = []
        for line in lines:
            if line.strip():
                fixed_lines.append(line)
            else:
                fixed_lines.append('')
        return ContentItem(
            source_path=Path("layout.html"),
            content='\n'.join(fixed_lines),
            metadata={}
        )
        
    except Exception as e:
        print(f"Error filling slots: {e}")
        return ContentItem(
            source_path=Path("error.html"),
            content=f"Error: {e}",
            metadata={"error": str(e)}
        )

def custom_tokenize_block(lines, token_types):
    """Custom block tokenizer that prioritizes our content blocks."""
    line_buffer = []
    line_iter = iter(lines)
    
    try:
        while True:
            line = next(line_iter)
            
            # Check for block starts in priority order
            if FastHTMLToken.start(line):
                # Yield any buffered lines
                if line_buffer:
                    for token in tokenize_block(line_buffer, token_types):
                        yield token
                    line_buffer = []
                
                # Read the FastHTML block
                content_lines = [line]  # Include opening line
                for next_line in line_iter:
                    content_lines.append(next_line)
                    if FastHTMLToken.closing_pattern.match(next_line):
                        break
                
                # Create and yield the FastHTML token
                yield FastHTMLToken(content_lines)
            elif ScriptToken.start(line):
                # Yield any buffered lines
                if line_buffer:
                    for token in tokenize_block(line_buffer, token_types):
                        yield token
                    line_buffer = []
                
                # Read the script block
                content_lines = [line]  # Include opening line
                for next_line in line_iter:
                    content_lines.append(next_line)
                    if ScriptToken.closing_pattern.match(next_line):
                        break
                
                # Create and yield the script token
                yield ScriptToken(content_lines)
            elif NestedContentToken.start(line):
                # Yield any buffered lines
                if line_buffer:
                    for token in tokenize_block(line_buffer, token_types):
                        yield token
                    line_buffer = []
                
                # Read the content block
                content_lines = [line]  # Include opening line
                tag_name = NestedContentToken.pattern.match(line).group(1)
                closing_pattern = re.compile(f'^\\s*</{tag_name}>\\s*$')
                
                # Read until we find the closing tag
                nested_content = []
                nested_level = 1
                
                for next_line in line_iter:
                    content_lines.append(next_line)
                    
                    # Check for nested tags
                    if NestedContentToken.start(next_line):
                        nested_level += 1
                    elif closing_pattern.match(next_line):
                        nested_level -= 1
                        if nested_level == 0:
                            break
                
                # Create and yield the content token
                yield NestedContentToken(content_lines)
            else:
                line_buffer.append(line)
    except StopIteration:
        pass
    
    # Yield any remaining buffered lines
    if line_buffer:
        for token in tokenize_block(line_buffer, token_types):
            yield token

def test_full_pipeline():
    """Test the complete rendering pipeline including layout handling and slot filling."""
    print("\n=== Testing Full Rendering Pipeline ===")
    
    # Register our custom tokens
    add_token(FastHTMLToken)
    add_token(ScriptToken)
    add_token(NestedContentToken)
    
    # Create renderer
    renderer = NestedRenderer()
    
    # Test cases with layouts and frontmatter
    test_cases = [
        # Simple layout with content and frontmatter
        {
            'content': '''---
title: Welcome
layout: simple
---

<content>
# Welcome
This is a simple test with **bold** and *italic*.
</content>''',
            'layout': '''<div class="container">
    <header data-pyxie-show="header">
        <h1>{{title}}</h1>
    </header>
    <main>
        <div data-pyxie-show="content">
            {{content}}
        </div>
    </main>
    <footer data-pyxie-show="footer">
        <p>Site Footer</p>
    </footer>
</div>'''
        },
        
        # Complex layout with multiple slots and frontmatter
        {
            'content': '''---
title: Complex Layout
layout: complex
tags: [test, example]
---

<content>
# Main Content
This is the main content with a <custom>nested tag</custom>.

<fasthtml>
def render():
    return "FastHTML Component"
</fasthtml>

<script>
console.log("Test script");
</script>
</content>''',
            'layout': '''<div class="complex-layout">
    <nav data-pyxie-show="nav">
        <ul>
            <li><a href="#">Home</a></li>
            <li><a href="#">About</a></li>
        </ul>
    </nav>
    
    <div class="content-wrapper">
        <aside data-pyxie-show="sidebar">
            <h2>Sidebar</h2>
            <p>Sidebar content</p>
        </aside>
        
        <main>
            <div data-pyxie-show="content">
                {{content}}
            </div>
        </main>
        
        <aside data-pyxie-show="!sidebar">
            <h2>Alternative Sidebar</h2>
            <p>Alternative content</p>
        </aside>
    </div>
    
    <footer data-pyxie-show="footer">
        <p>Footer content</p>
    </footer>
</div>'''
        },
        
        # Layout with conditional visibility and frontmatter
        {
            'content': '''---
title: Conditional Test
layout: conditional
show_header: true
---

<content>
# Conditional Test
This content should show different elements based on slots.

<custom>
This is a custom block
</custom>
</content>''',
            'layout': '''<div class="conditional-layout">
    <div data-pyxie-show="header,content">
        <h1>{{title}}</h1>
        {{content}}
    </div>
    
    <div data-pyxie-show="!header">
        <p>No header content</p>
    </div>
    
    <div data-pyxie-show="footer">
        <p>Footer content</p>
    </footer>
</div>'''
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\nTest Case {i}:")
        print("Content:", case['content'])
        print("\nLayout:", case['layout'])
        
        try:
            # Parse frontmatter and content
            metadata, content = parse_frontmatter(case['content'])
            print("\nMetadata:", metadata)
            
            # Create document with custom tokenizer for content
            content_doc = Document('')
            content_doc.children = list(custom_tokenize_block(content.split('\n'), [FastHTMLToken, ScriptToken, NestedContentToken]))
            
            # Render document
            rendered_html = renderer.render(content_doc)
            print("\nRendered HTML:", rendered_html)
            
            # Extract slots from the rendered HTML
            filled_slots = extract_slots_with_content({"content": [rendered_html]})
            print("\nFilled slots:", filled_slots)
            
            # Process conditional visibility
            layout_html = process_conditional_visibility(case['layout'], filled_slots)
            print("\nProcessed layout:", layout_html)
            
            # Fill slots
            result = fill_slots(layout_html, {"content": [rendered_html]})
            print("\nFinal result:", result.content)
            
            if "error" in result.metadata:
                print("Error:", result.metadata["error"])
            
        except Exception as e:
            print(f"Error processing test case: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    test_full_pipeline() 