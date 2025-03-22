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
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from functools import lru_cache, wraps

from fastcore.xml import to_xml
import fasthtml.common as ft_common

from .errors import (
    FastHTMLConversionError, FastHTMLError, FastHTMLExecutionError,
    FastHTMLImportError, FastHTMLRenderError, Result, format_error_html
)
from .utilities import extract_content, log, safe_import

logger = logging.getLogger(__name__)

# Core constants and patterns
FASTHTML_BLOCK_NAMES = ('py', 'python', 'fasthtml')
FASTHTML_TAG_PATTERN = re.compile(r'<(py|python|fasthtml)([^>]*)>(.*?)</\1>', re.DOTALL)
FASTHTML_ATTR_PATTERN = re.compile(r'(\w+)=(["\'])(.*?)\2', re.DOTALL)
IMPORT_PATTERN = re.compile(r'^(?:from\s+([^\s]+)\s+import|import\s+([^#\n]+))', re.MULTILINE)
SCRIPT_TAG_PATTERN = re.compile(r'(<script[^>]*>)(.*?)(</script>)', re.DOTALL)

# New constant for the execution marker
EXECUTABLE_MARKER = "__EXECUTABLE_FASTHTML__"

@dataclass
class FastHTMLTagMatch:
    """Parsed FastHTML tag."""
    tag_name: str
    attributes: Dict[str, str]
    content: str
    full_match: str
    description: Optional[str] = None

# ---- Error Handling Decorators ----

def catch_errors(error_context="general"):
    """Decorator to catch and format errors in FastHTML processing."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_message = f"{e.__class__.__name__}: {e}"
                log(logger, "FastHTML", "error", error_context, error_message)
                
                # Create an appropriate FastHTMLError
                error = e if isinstance(e, FastHTMLError) else map_exception_to_fasthtml_error(e, error_context)
                return Result.failure(error)
        return wrapper
    return decorator

def map_exception_to_fasthtml_error(exception: Exception, context: str) -> FastHTMLError:
    """Map a Python exception to a specific FastHTML error type."""
    error_message = f"{exception.__class__.__name__}: {exception}"
    
    if context == "execute":
        if isinstance(exception, SyntaxError):
            return FastHTMLExecutionError(f"Syntax error: {exception}")
        return FastHTMLExecutionError(error_message)
    elif context == "render":
        return FastHTMLRenderError(error_message)
    elif context == "import":
        return FastHTMLImportError(error_message)
    elif context == "conversion":
        return FastHTMLConversionError(error_message)
    else:
        return FastHTMLError(error_message)

# ---- Content Detection ----

def is_fasthtml_content(content: str) -> bool:
    """Check if content contains FastHTML tags."""
    return bool(content and isinstance(content, str) and FASTHTML_TAG_PATTERN.search(content.strip()))

def is_direct_html_content(content: str) -> bool:
    """Check if content appears to be direct HTML."""
    return (content and isinstance(content, str) and 
            content.strip().startswith('<') and 
            content.strip().endswith('>') and 
            not content.strip().startswith('<%'))

def is_single_complete_tag(content: str) -> bool:
    """Check if content is a single complete FastHTML tag."""
    return (content and isinstance(content, str) and 
            content.strip().startswith('<') and 
            bool(FASTHTML_TAG_PATTERN.match(content.strip())))

def is_executable_fasthtml(content: str) -> bool:
    """Check if content has been marked as executable by the parser."""
    return content and isinstance(content, str) and content.startswith(EXECUTABLE_MARKER)

def extract_executable_content(content: str) -> str:
    """Extract the executable content from marked content."""
    if is_executable_fasthtml(content):
        return content[len(EXECUTABLE_MARKER):]
    return content

# ---- Tag Parsing ----

def parse_attributes(attributes_str: str) -> Dict[str, str]:
    """Parse HTML-like attributes into a dictionary."""
    if not attributes_str:
        return {}
    
    return {name: value for name, _, value in FASTHTML_ATTR_PATTERN.finditer(attributes_str)}

def parse_fasthtml_tags(content: str, first_only=False) -> List[FastHTMLTagMatch]:
    """
    Parse FastHTML tags from content.
    Returns a list of FastHTMLTagMatch objects or an empty list if none found.
    If first_only is True, returns only the first match.
    """
    if not content:
        return []
    
    if first_only:
        match = FASTHTML_TAG_PATTERN.search(content)
        if not match:
            return []
            
        tag = FastHTMLTagMatch(
            tag_name=match.group(1),
            full_match=match.group(0),
            attributes=parse_attributes(match.group(2)),
            content=extract_content(match.group(3)),
            description=None
        )
        
        if 'description' in tag.attributes:
            tag.description = tag.attributes['description']
            
        return [tag]
    
    # Find all tags
    return [
        FastHTMLTagMatch(
            tag_name=match.group(1),
            full_match=match.group(0),
            attributes=parse_attributes(match.group(2)),
            content=extract_content(match.group(3)),
            description=parse_attributes(match.group(2)).get('description')
        )
        for match in FASTHTML_TAG_PATTERN.finditer(content)
    ]

# ---- JavaScript Conversion ----

@catch_errors("conversion")
def py_to_js(obj, indent=0, indent_str="  "):
    """Convert Python objects to JavaScript code."""
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

def js_function(func_str):
    """Create JavaScript function strings."""
    return f"__FUNCTION__{func_str}"

# ---- Code Execution ----

@lru_cache(maxsize=1)
@catch_errors("setup")
def create_base_namespace() -> dict:
    """Create the base namespace with common functions and modules."""
    # Helper functions for namespace
    def show_function(obj):
        return obj
        
    def convert_function(obj):
        return obj
        
    namespace = {
        name: getattr(ft_common, name) 
        for name in dir(ft_common) if not name.startswith('_')
    }
    
    namespace.update({
        'show': show_function,
        'js_function': js_function,
        'NotStr': ft_common.NotStr,
        'convert': convert_function,
        '__builtins__': globals()['__builtins__'],
        '__name__': '__main__'
    })
    
    return namespace

@catch_errors("setup")
def create_namespace(context_path=None) -> dict:
    """Create a namespace for FastHTML execution."""
    return create_base_namespace().copy()

@catch_errors("import")
def process_imports(code: str, namespace: dict, context_path=None) -> Result[None]:
    """Process import statements in code."""
    for match in IMPORT_PATTERN.finditer(code):
        # Handle both "from X import Y" and "import X, Y, Z" patterns
        if module_name := match.group(1):  # from X import Y
            safe_import(module_name.strip(), namespace, context_path, logger)
        elif modules := match.group(2):    # import X, Y, Z
            # Import each module in the comma-separated list, ignoring comments
            [safe_import(clean_module, namespace, context_path, logger) 
             for module in modules.split(',')
             if (clean_module := module.split('#')[0].strip())]
    
    return Result.success(None)

@catch_errors("execute")
def execute_fasthtml_code(code: str, context_path: Optional[str] = None) -> Result[List[Any]]:
    """Execute FastHTML code and return captured results or error."""
    namespace = create_namespace(context_path)
    namespace["__results"] = []
    
    # Set up result capture
    def show_with_capture(obj):
        result = original_show(obj)
        namespace["__results"].append(result)
        return result
        
    original_show = namespace["show"]
    namespace["show"] = show_with_capture
    
    # Check syntax first - will raise SyntaxError if invalid
    compile(code, '<string>', 'exec')
    
    # Process imports and execute code
    imports_result = process_imports(code, namespace, context_path)
    if not imports_result.is_success:
        return imports_result
    
    # Execute the code and capture results
    exec(code, namespace)
    
    # Return captured results
    results = namespace.get("__results", [])
    if not results:
        log(logger, "FastHTML", "info", "execute", 
            "No results captured. Use show() to display components.")
    return Result.success(results)

# ---- Rendering ----

@catch_errors("render")
def render_components(results: List[Any], description: Optional[str] = None) -> str:
    """Render FastHTML components to XML."""
    if not results:
        return ""
    
    # Start with description comment if provided
    xml_parts = [f"<!-- {description} -->"] if description else []
    
    # Add rendered components
    xml_parts.extend(
        component.__pyxie_render__() if hasattr(component, "__pyxie_render__") else to_xml(component)
        for component in results
    )
    
    return "\n".join(xml_parts)

@catch_errors("render")
def protect_script_tags(xml_content: str) -> str:
    """Protect script tag content from HTML processing."""
    if not xml_content or "<script" not in xml_content:
        return xml_content
    
    def process_script(match):
        opening_tag, content, closing_tag = match.groups()
        
        # Unescape HTML entities in script content - using a simpler approach
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

def escape_fasthtml_content(content: str) -> str:
    """Escape FastHTML tags in content to prevent execution."""
    return content.replace('<', '&lt;') if content else content

# ---- Core Processing Functions ----

@catch_errors("process")
def process_tag(tag_match: FastHTMLTagMatch, context_path: Optional[str] = None) -> Result[str]:
    """Process a single FastHTML tag match."""
    # If it's direct HTML, return it as-is
    if is_direct_html_content(tag_match.content):
        return Result.success(tag_match.content)
    
    # Get content and check if it's executable
    content = tag_match.content
    
    # Only extract and execute if it has the executable marker
    if is_executable_fasthtml(content):
        # Extract the executable content without the marker
        content = extract_executable_content(content)
        tag_match.content = content
        log(logger, "FastHTML", "info", "process", "Executing FastHTML tag")
        
        # Execute the code and chain operations: execute -> render -> protect script tags
        return (execute_fasthtml_code(content, context_path)
                .map(lambda components: render_components(components, tag_match.description))
                .map(protect_script_tags))
    
    # For non-executable content, just return it as-is
    # This should generally not happen with our new flow
    log(logger, "FastHTML", "warning", "process", "Non-executable FastHTML tag received in process_tag")
    return Result.success(content)

@catch_errors("process")
def execute_raw_code_block(content: str, context_path: Optional[str] = None) -> Result[str]:
    """Execute raw FastHTML code and return rendered HTML."""
    return (execute_fasthtml_code(content, context_path)
            .map(render_components)
            .map(protect_script_tags))

@catch_errors("process")
def process_multiple_fasthtml_tags(
    content: str, 
    context_path: Optional[str] = None,    
) -> Result[str]:
    """
    Process all FastHTML tags embedded in content.
    Finds and replaces all FastHTML tags in the content with their rendered output.
    """
    # Check for empty content
    if not content:
        return Result.success("")
    
    # Process each matching tag
    def replace_tag(match):
        tags = parse_fasthtml_tags(match.group(0), first_only=True)
        if not tags:
            return match.group(0)
        
        # Process the tag and handle the result
        result = process_tag(tags[0], context_path)
        return result.content if result.is_success else format_error_html(result.error)
    
    # Process all FastHTML tags
    try:
        processed = FASTHTML_TAG_PATTERN.sub(replace_tag, content)
        return Result.success(processed)
    except Exception as e:
        error = map_exception_to_fasthtml_error(e, "processing")
        log(logger, "FastHTML", "error", "process", str(error))
        return Result.error(error)

@catch_errors("process")
def process_single_fasthtml_block(content: str, context_path: Optional[str] = None) -> Result[str]:
    """Process a single FastHTML block or raw code."""
    if not content:
        return Result.success("")
    
    # Check for executable marker first - this takes priority
    if is_executable_fasthtml(content):
        log(logger, "FastHTML", "info", "process", "Executing marked FastHTML code")
        # Extract the content without the marker
        extracted_content = extract_executable_content(content)
        
        # Try to find and extract FastHTML tags first
        extracted_tags = parse_fasthtml_tags(extracted_content, first_only=True)
        
        if extracted_tags:
            # Found valid tags - execute the inner content
            inner_content = extracted_tags[0].content
            log(logger, "FastHTML", "debug", "process", f"Executing inner content of FastHTML tag: {inner_content[:100]}...")
            return execute_raw_code_block(inner_content, context_path)
        
        # No tags found or invalid tags - look for show() function as direct code
        if "show(" in extracted_content:
            log(logger, "FastHTML", "info", "process", "No valid FastHTML tags found, executing as direct code")
            # Filter out any HTML-like lines that might cause syntax errors
            code_lines = [line for line in extracted_content.splitlines() 
                        if not (line.strip().startswith("<") and ">" in line)]
            code_to_execute = "\n".join(code_lines)
            return execute_raw_code_block(code_to_execute, context_path)
            
        # Last resort - try to execute the whole content
        log(logger, "FastHTML", "warning", "process", "Attempting to execute entire content block")
        return execute_raw_code_block(extracted_content, context_path)
    
    # For non-executable content, just return it as-is
    log(logger, "FastHTML", "warning", "process", "Non-executable FastHTML content received")
    return Result.success(content)

@catch_errors("render")
def render_fasthtml(
    content: str, 
    context_path: Optional[str] = None, 
    return_errors: bool = False
) -> Union[str, Tuple[str, List[str]]]:
    """Main entry point for rendering FastHTML content."""
    # Quick check for empty content
    if not content:
        return ("", []) if return_errors else ""
    
    # Check if this is executable FastHTML content
    if is_executable_fasthtml(content):
        # Process content with process_single_fasthtml_block which handles the executable marker
        result = process_single_fasthtml_block(content, context_path)
        # Return appropriate format based on return_errors flag
        return (
            (result.content, []) if result.is_success else ("", [str(result.error)])
        ) if return_errors else (
            result.content if result.is_success else format_error_html(result.error)
        )
    
    # Not FastHTML content or not marked for execution, return as is
    if not is_fasthtml_content(content):
        return (content, []) if return_errors else content
        
    # Process regular FastHTML content (non-executable)
    log(logger, "FastHTML", "warning", "render", "Non-executable FastHTML content received in render_fasthtml")
    result = process_multiple_fasthtml_tags(content, context_path)
    
    # Return appropriate format based on return_errors flag
    return (
        (result.content, []) if result.is_success else ("", [str(result.error)])
    ) if return_errors else (
        result.content if result.is_success else format_error_html(result.error)
    )
