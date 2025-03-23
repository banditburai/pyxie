# Copyright 2025 firefly
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License. 

"""FastHTML processing for Pyxie - execution of Python code and rendering of components."""

import logging
import re
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from functools import lru_cache

from fastcore.xml import to_xml
import fasthtml.common as ft_common

from .utilities import log, safe_import

logger = logging.getLogger(__name__)

FASTHTML_TAG_PATTERN = re.compile(r'<(fasthtml)([^>]*)>(.*?)</(?i:\1)>', re.DOTALL)
FASTHTML_ATTR_PATTERN = re.compile(r'(\w+)=(["\'])(.*?)\2', re.DOTALL)
IMPORT_PATTERN = re.compile(r'^(?:from\s+([^\s]+)\s+import|import\s+([^#\n]+))', re.MULTILINE)
SCRIPT_TAG_PATTERN = re.compile(r'(<script[^>]*>)(.*?)(</script>)', re.DOTALL)
EXECUTABLE_MARKER = "__EXECUTABLE_FASTHTML__"

@dataclass
class FastHTMLTagMatch:
    """Parsed FastHTML tag."""
    tag_name: str
    attributes: Dict[str, str]
    content: str
    full_match: str
    description: Optional[str] = None

@dataclass
class RenderResult:
    """Result of rendering a block."""
    content: str = ""
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        """Check if render was successful."""
        return self.error is None

def is_executable_fasthtml(content: str) -> bool:
    """Check if content has been marked as executable by the parser."""
    return content and isinstance(content, str) and content.startswith(EXECUTABLE_MARKER)

def extract_executable_content(content: str) -> str:
    """Extract the executable content from marked content."""
    if not is_executable_fasthtml(content):
        return content
    
    # Extract content without the marker
    extracted = content[len(EXECUTABLE_MARKER):]
    
    # Unescape any HTML entities that might have been added during parsing
    html_entities = {'&lt;': '<', '&gt;': '>', '&amp;': '&', '&quot;': '"', '&#x27;': "'", '&#39;': "'"}
    for entity, char in html_entities.items():
        extracted = extracted.replace(entity, char)
    
    return extracted

def parse_fasthtml_tags(content: str, first_only: bool = False) -> List[FastHTMLTagMatch]:
    """Parse FastHTML tags from content."""
    if not content:
        return []
    
    matches = []
    for match in FASTHTML_TAG_PATTERN.finditer(content):
        tag_name, attrs_str, tag_content = match.groups()
        
        # Parse attributes
        attributes = {}
        for attr_match in FASTHTML_ATTR_PATTERN.finditer(attrs_str or ""):
            name, _, value = attr_match.groups()
            attributes[name] = value
            
        # Create the match object
        matches.append(FastHTMLTagMatch(
            tag_name=tag_name,
            attributes=attributes,
            content=tag_content.strip(),
            full_match=match.group(0)
        ))
        
        if first_only:
            break
            
    return matches

def py_to_js(obj, indent=0, indent_str="  "):
    """Convert Python objects to JavaScript code."""
    try:
        current_indent = indent_str * indent
        next_indent = indent_str * (indent + 1)
        
        match obj:
            case None:
                return "null"
            case bool():
                return "true" if obj else "false"
            case int() | float():
                return str(obj)
            case str() if obj.startswith("__FUNCTION__"):
                func_content = obj[12:]  # Remove prefix
                return func_content if func_content.startswith("function") else f"function(index) {{ return {func_content}; }}"
            case str():
                # Escape special characters
                escaped = obj.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
                return f'"{escaped}"'
            case dict():
                if not obj:
                    return "{}"
                pairs = [f"{next_indent}{py_to_js(k)}: {py_to_js(v, indent + 1, indent_str)}" for k, v in obj.items()]
                return "{\n" + ",\n".join(pairs) + f"\n{current_indent}}}"
            case list():
                if not obj:
                    return "[]"
                items = [f"{next_indent}{py_to_js(item, indent + 1, indent_str)}" for item in obj]
                return "[\n" + ",\n".join(items) + f"\n{current_indent}]"
            case _ if callable(obj):
                func_name = getattr(obj, '__name__', '<lambda>')
                return f"function {func_name if func_name != '<lambda>' else ''}(index) {{ return index * 100; }}"
            case _:
                return str(obj)
    except Exception as e:
        log(logger, "FastHTML", "error", "conversion", f"{e}")
        return str(obj)

def js_function(func_str):
    """Create JavaScript function strings."""
    return f"__FUNCTION__{func_str}"

@lru_cache(maxsize=1)
def create_namespace(context_path=None) -> dict:
    """Create a namespace for FastHTML execution."""
    try:
        # Helper function for showing components
        def show_function(obj):
            """Show function renders components but returns the original object for chaining."""                
            return obj
            
        # Create base namespace with common utilities
        namespace = {
            name: getattr(ft_common, name) 
            for name in dir(ft_common) if not name.startswith('_')
        }
        
        namespace.update({
            'show': show_function,
            'js_function': js_function,
            'NotStr': ft_common.NotStr,
            'convert': lambda obj: obj,  # Simple pass-through
            '__builtins__': globals()['__builtins__'],
            '__name__': '__main__'
        })
        
        return namespace.copy()
    except Exception as e:
        log(logger, "FastHTML", "error", "setup", f"{e}")
        return {}

def process_imports(code: str, namespace: dict, context_path=None) -> RenderResult:
    """Process import statements in code."""
    try:
        for match in IMPORT_PATTERN.finditer(code):
            # Handle both "from X import Y" and "import X, Y, Z" patterns
            if module_name := match.group(1):  # from X import Y
                safe_import(module_name.strip(), namespace, context_path, logger)
            elif modules := match.group(2):    # import X, Y, Z
                for module in modules.split(','):
                    if clean_module := module.split('#')[0].strip():
                        safe_import(clean_module, namespace, context_path, logger)
        
        return RenderResult()
    except Exception as e:
        error_msg = f"Import error: {e.__class__.__name__}: {e}"
        log(logger, "FastHTML", "error", "import", f"{e}")
        return RenderResult(error=error_msg)

def execute_fasthtml_code(code: str, context_path: Optional[str] = None) -> RenderResult:
    """Execute FastHTML code and return captured results or error."""
    try:
        namespace = create_namespace(context_path)
        namespace["__results"] = []
        
        # Set up result capture
        original_show = namespace["show"]
        namespace["show"] = lambda obj: namespace["__results"].append(original_show(obj)) or obj
        
        # Check syntax first
        compile(code, '<string>', 'exec')
        
        # Process imports and execute code
        imports_result = process_imports(code, namespace, context_path)
        if imports_result.error:
            return imports_result
        
        # Execute the code and capture results
        exec(code, namespace)
        
        # Return captured results
        results = namespace.get("__results", [])
        if not results:
            log(logger, "FastHTML", "info", "execute", 
                "No results captured. Use show() to display components.")
        return RenderResult(content=results)
    except Exception as e:
        error_msg = f"{e.__class__.__name__}: {e}"
        if isinstance(e, SyntaxError):
            error_msg = f"Syntax error: {e}"
        log(logger, "FastHTML", "error", "execute", f"{e}")
        return RenderResult(error=error_msg)

def render_components(results: Union[List[Any], Any]) -> str:
    """Render FastHTML components to XML."""
    try:
        # Handle both lists and single components
        if not isinstance(results, list):
            results = [results]
        
        if not results:
            return ""
        
        xml_parts = []
        for component in results:
            if hasattr(component, "__pyxie_render__"):
                xml_parts.append(component.__pyxie_render__())
            elif type(component).__module__ == 'fastcore.xml':
                # It's a FastCore FT object - render to XML
                xml_parts.append(to_xml(component))
            elif isinstance(component, list) and len(component) == 3:
                # It's a compatible FT structure - render to XML
                xml_parts.append(to_xml(component))
            else:
                # For other types, convert to string
                xml_parts.append(str(component))
        
        return "\n".join(xml_parts)
    except Exception as e:
        log(logger, "FastHTML", "error", "render", f"{e}")
        raise

def protect_script_tags(xml_content: str) -> str:
    """Protect script tag content from HTML processing."""
    if not xml_content or "<script" not in xml_content:
        return xml_content
    
    try:
        def process_script(match):
            opening_tag, content, closing_tag = match.groups()
            
            # Unescape HTML entities in script content
            html_entities = {'&lt;': '<', '&gt;': '>', '&amp;': '&', '&quot;': '"', '&#x27;': "'", '&#39;': "'"}
            for entity, char in html_entities.items():
                content = content.replace(entity, char)
            
            # Remove pre/code wrappers
            content = re.sub(r'<pre><code[^>]*>(.*?)</code></pre>', r'\1', content, flags=re.DOTALL)
            
            # Add data-raw attribute if not present
            if "data-raw" not in opening_tag:
                opening_tag = opening_tag.replace("<script", "<script data-raw=\"true\"", 1)
                
            return f"{opening_tag}{content}{closing_tag}"
        
        return SCRIPT_TAG_PATTERN.sub(process_script, xml_content)
    except Exception as e:
        log(logger, "FastHTML", "error", "render", f"{e}")
        return xml_content

def render_fasthtml(content: str, context_path: Optional[str] = None) -> RenderResult:
    """Process a single FastHTML block or raw code."""
    if not content:
        return RenderResult(content="")
    
    try:
        # For non-executable content, just return it as-is
        if not is_executable_fasthtml(content):
            log(logger, "FastHTML", "warning", "process", "Non-executable FastHTML content received")
            return RenderResult(content=content)
            
        # Extract the content without the marker
        extracted_content = extract_executable_content(content)
        
        # Try to find and extract FastHTML tags
        inner_content = extracted_content
        extracted_tags = parse_fasthtml_tags(extracted_content, first_only=True)
        if extracted_tags:
            inner_content = extracted_tags[0].content
            
        # Execute the code
        exec_result = execute_fasthtml_code(inner_content, context_path)
        if not exec_result.success:
            return exec_result
            
        # Render the components to HTML
        rendered = render_components(exec_result.content)
        protected = protect_script_tags(rendered)
        return RenderResult(content=protected)
    except Exception as e:
        error_msg = f"{e.__class__.__name__}: {e}"
        log(logger, "FastHTML", "error", "process", f"Error processing block: {e}")
        return RenderResult(error=error_msg)
