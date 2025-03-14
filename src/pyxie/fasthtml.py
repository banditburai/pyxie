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

"""FastHTML processing module for Pyxie.

Provides execution of Python code and rendering of FastHTML components.
Uses a show() function pattern similar to Jupyter notebooks.
"""

import logging
import os
import importlib.util
import traceback
import re
from typing import Optional, Any, List, Tuple, Set, Union
from fastcore.xml import to_xml
import fasthtml.common as ft_common
from .errors import (
    FastHTMLError, FastHTMLImportError, FastHTMLExecutionError,
    FastHTMLRenderError, FastHTMLConversionError
)
from .utilities import log, extract_content, safe_import

# Set up logging
logger = logging.getLogger(__name__)

# Constants
FASTHTML_BLOCK_NAMES = {'ft', 'fasthtml'}
FASTHTML_TAG = 'fasthtml'

def _dict_to_js(obj, indent=0, indent_str="  "):
    """Convert dictionary to JavaScript object."""
    if not obj:
        return "{}"
        
    current_indent = indent_str * indent
    next_indent = indent_str * (indent + 1)
    pairs = [f"{next_indent}\"{k}\": {py_to_js(v, indent + 1, indent_str)}" 
             if isinstance(k, str) else f"{next_indent}{k}: {py_to_js(v, indent + 1, indent_str)}"
             for k, v in obj.items()]
    
    return "{\n" + ",\n".join(pairs) + f"\n{current_indent}}}"

def _list_to_js(obj, indent=0, indent_str="  "):
    """Convert list to JavaScript array."""
    if not obj:
        return "[]"
        
    current_indent = indent_str * indent
    next_indent = indent_str * (indent + 1)
    items = [f"{next_indent}{py_to_js(item, indent + 1, indent_str)}" for item in obj]
    return "[\n" + ",\n".join(items) + f"\n{current_indent}]"

def _callable_to_js(obj):
    """Convert callable to JavaScript function."""
    if hasattr(obj, '__name__') and obj.__name__ != '<lambda>':
        return f"function {obj.__name__}(index) {{ return index * 100; }}"
    return "function(index) { return index * 100; }"

def _str_to_js(obj, *_):
    """Convert string to JavaScript string."""
    if obj.startswith("__FUNCTION__"):
        # Handle special function markers
        func_content = obj[12:]  # Remove the __FUNCTION__ prefix
        if func_content.startswith("function"):
            return func_content
        return f"function(index) {{ return {func_content}; }}"
    
    # Regular string - escape special characters
    escaped = obj.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
    return f'"{escaped}"'

def py_to_js(obj, indent=0, indent_str="  "):
    """Convert Python objects to JavaScript code representation."""
    try:
        converters = {
            dict: _dict_to_js,
            list: _list_to_js,
            str: _str_to_js,
            type(None): lambda *_: "null",
            bool: lambda x, *_: "true" if x else "false",
        }
        
        # Get the correct converter or use default
        for typ, converter in converters.items():
            if isinstance(obj, typ):
                return converter(obj, indent, indent_str)
                
        # Handle callables
        if callable(obj):
            return _callable_to_js(obj)
            
        # Default for numbers and other types
        return str(obj)
    except Exception as e:
        log(logger, "FastHTML", "error", "conversion", f"Failed to convert {type(obj).__name__} to JavaScript: {str(e)}")
        raise FastHTMLConversionError(f"Failed to convert {type(obj).__name__} to JavaScript: {str(e)}") from e

def js_function(func_str):
    """Helper to create JavaScript function strings for embedding in objects."""
    return f"__FUNCTION__{func_str}"

def extract_inner_content(content: str) -> str:
    """Extract content from within FastHTML tags and dedent it."""
    if not content:
        return ""
    
    # Handle tags with or without attributes
    pattern = re.compile(f'<{FASTHTML_TAG}(?:\\s+[^>]*)?>(.*?)</{FASTHTML_TAG}>', re.DOTALL)
    match = pattern.search(content)
    if match:
        return extract_content(match.group(1))
    
    return content

def is_fasthtml_content(content: str) -> bool:
    """Check if content is wrapped in FastHTML tags."""
    if not isinstance(content, str):
        return False
    content = content.strip()
    return (content.startswith(f'<{FASTHTML_TAG}>') and 
            content.endswith(f'</{FASTHTML_TAG}>'))

def is_fasthtml_block(name: str) -> bool:
    """Check if a block name indicates FastHTML content."""
    return name.lower() in FASTHTML_BLOCK_NAMES

def is_script_component(obj):
    """Check if an object is a Script component."""
    return hasattr(obj, '__class__') and getattr(obj, '__class__').__name__ == 'Script'

def extract_functions_from_script(script_content: str) -> Set[str]:
    """Extract function names defined in a script."""
    # Simple regex to find function declarations
    function_pattern = r'function\s+([a-zA-Z0-9_]+)\s*\('
    return set(re.findall(function_pattern, script_content))

def create_namespace(context_path=None) -> dict:
    """Create a namespace with FastHTML components and functions."""
    # Add non-private attributes from fasthtml.common
    namespace = {name: getattr(ft_common, name) 
                for name in dir(ft_common) if not name.startswith('_')}
    
    # Add necessary components
    namespace.update({
        'show': lambda obj: obj,
        'NotStr': ft_common.NotStr,
        'convert': lambda obj: obj,
        '__builtins__': globals()['__builtins__'],
        '__name__': '__main__'
    })
    
    return namespace

def process_imports(code: str, namespace: dict, context_path=None) -> None:
    """Process import statements in the code."""
    for line in code.splitlines():
        line = line.strip()
        if line.startswith('import '):
            # Handle: import module
            modules = line[7:].split(',')
            for module in modules:
                safe_import(module.strip(), namespace, context_path, logger)
        elif line.startswith('from '):
            # Handle: from module import x
            parts = line[5:].split(' import ')
            if len(parts) == 2:
                module_name = parts[0].strip()
                safe_import(module_name, namespace, context_path, logger)

def protect_script_tags(xml_content: str) -> str:
    """Protect script tag content from HTML/markdown processing."""
    if "<script" not in xml_content:
        return xml_content
    
    # Use regex to find script tags and their content
    script_pattern = re.compile(r'(<script[^>]*>)(.*?)(</script>)', re.DOTALL)
    
    def protect_script(match):
        opening_tag, content, closing_tag = match.groups()
        
        # Decode HTML entities
        content = content.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
        content = content.replace('&quot;', '"').replace('&#x27;', "'").replace('&#39;', "'")
        
        # Remove code blocks
        content = re.sub(r'<pre><code[^>]*>(.*?)</code></pre>', r'\1', content, flags=re.DOTALL)
        
        # Add data-raw attribute
        if "data-raw" not in opening_tag:
            opening_tag = opening_tag.replace("<script", "<script data-raw=\"true\"", 1)
            
        return f"{opening_tag}{content}{closing_tag}"
    
    return script_pattern.sub(protect_script, xml_content)

def render_to_xml(
    content: str,
    sanitize: bool = True,
    context_path: Optional[str] = None,
    return_errors: bool = False,
    add_script_dependencies: bool = True,
    ) -> Union[str, Tuple[str, List[str]]]:
    """
    Render FastHTML content to XML/HTML.

    Args:
        content: FastHTML content
        sanitize: Whether to sanitize the output
        context_path: Path for relative imports
        return_errors: If True, return (xml, errors) tuple
        add_script_dependencies: Add script tag dependencies

    Returns:
        XML string or (xml, errors) tuple if return_errors is True
    """
    try:
        # Extract tag attributes if present
        tag_pattern = re.compile(f'<{FASTHTML_TAG}([^>]*)>', re.DOTALL)
        tag_match = tag_pattern.search(content)
        
        # Get description attribute if present
        description = None
        if tag_match:
            attr_pattern = re.compile(r'(\w+)=(["\'])(.*?)\2', re.DOTALL)
            for attr_match in attr_pattern.finditer(tag_match.group(1)):
                if attr_match.group(1) == 'description':
                    description = attr_match.group(3)
                    break
        
        # Extract and validate code
        code = extract_inner_content(content)
        if not code:
            log(logger, "FastHTML", "warning", "render", "Empty content")
            return "" if not return_errors else ("", [])

        # Set up executor and execute code
        executor = FastHTMLExecutor(context_path)
        results = executor.execute(code)
        
        # Convert results to XML
        xml = FastHTMLRenderer.to_xml(results)
        
        # Add description as comment if present
        if description:
            xml = f"<!-- {description} -->\n{xml}"
        
        # Handle script tags - protect them from further processing
        if add_script_dependencies:
            xml = protect_script_tags(xml)
            
        return xml if not return_errors else (xml, [])
    except FastHTMLError as e:
        error_message = f"{e.__class__.__name__}: {e}"
        log(logger, "FastHTML", "error", "render", error_message)
        if return_errors:
            return "", [error_message]
        return f'<div class="fasthtml-error">{error_message}</div>'
    except Exception as e:
        error_message = FastHTMLRenderer.handle_error(e)
        log(logger, "FastHTML", "error", "render", error_message)
        if return_errors:
            return "", [error_message]
        return f'<div class="fasthtml-error">{error_message}</div>'

class FastHTMLExecutor:
    """Executes FastHTML code blocks and returns results."""
    
    def __init__(self, context_path: Optional[str] = None):
        """Initialize with optional context path for imports."""
        self.context_path = context_path
        
    def create_namespace(self) -> dict:
        """Create execution namespace with components and result capturing."""
        namespace = create_namespace(self.context_path)
        
        # Set up result capture
        namespace["__results"] = []
        
        # Override show function to capture results
        original_show = namespace["show"]
        def show_with_capture(obj):
            result = original_show(obj)
            namespace["__results"].append(result)
            return result
        namespace["show"] = show_with_capture
        
        return namespace
            
    def execute(self, code: str) -> List[Any]:
        """Execute FastHTML code and return results from show() calls.
        
        To render components, they must be explicitly passed to the show() function.
        For example: show(Div("Hello World"))
        """
        # Create namespace and process imports
        namespace = self.create_namespace()
        try:
            process_imports(code, namespace, self.context_path)
        except Exception as e:
            log(logger, "FastHTML", "error", "execute", f"Import failed: {str(e)}")
            raise FastHTMLImportError(f"Failed to import module: {str(e)}") from e

        # Execute the code
        try:
            exec(code, namespace)
        except SyntaxError as e:
            log(logger, "FastHTML", "error", "execute", f"Syntax error in code: {str(e)}")
            raise FastHTMLExecutionError(f"Syntax error in FastHTML code: {str(e)}") from e
        except NameError as e:
            log(logger, "FastHTML", "error", "execute", f"Name error: {str(e)}")
            raise FastHTMLExecutionError(f"Name error in FastHTML code: {str(e)}") from e
        except Exception as e:
            log(logger, "FastHTML", "error", "execute", f"Execution error: {str(e)}")
            raise FastHTMLExecutionError(f"Error executing FastHTML code: {str(e)}") from e
        
        # Return results captured via show()
        results = namespace.get("__results", [])
        if not results:
            log(logger, "FastHTML", "info", "execute", "No results captured. Use show() to display components.")
        
        return results

class FastHTMLRenderer:
    """Renders FastHTML components to XML."""
    
    @classmethod
    def to_xml(cls, results: List[Any]) -> str:
        """Convert FastHTML results to XML."""
        if not results:
            return ""
        
        try:
            # Handle single result
            if len(results) == 1:
                return cls._render_component(results[0])
            
            # Handle multiple results
            return "\n".join(cls._render_component(r) for r in results)
        except Exception as e:
            error_msg = cls.handle_error(e)
            log(logger, "FastHTML", "error", "render", f"Error converting to XML: {error_msg}")
            raise FastHTMLRenderError(f"Error converting to XML: {str(e)}") from e
    
    @classmethod
    def _render_component(cls, component: Any) -> str:
        """Render a single component to XML, handling exceptions."""
        try:
            if hasattr(component, "__pyxie_render__"):
                return component.__pyxie_render__()
            return to_xml(component)
        except Exception as e:
            error_msg = cls.handle_error(e)
            log(logger, "FastHTML", "error", "render", f"Error rendering component: {error_msg}")
            raise FastHTMLRenderError(f"Error rendering component: {str(e)}") from e
    
    @staticmethod
    def handle_error(error: Exception) -> str:
        """Format error message for FastHTML errors."""
        if isinstance(error, SyntaxError):
            return f"SyntaxError: {error} at line {error.lineno}, offset {error.offset}"
        return f"{error.__class__.__name__}: {error}\n{traceback.format_exc()}" 