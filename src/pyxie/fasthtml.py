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
import traceback
import re
from typing import Optional, Any, List, Tuple, Set, Union, Dict
from dataclasses import dataclass
from fastcore.xml import to_xml
import fasthtml.common as ft_common
from .errors import (
    FastHTMLError, FastHTMLImportError, FastHTMLExecutionError,
    FastHTMLRenderError, FastHTMLConversionError
)
from .utilities import log, extract_content, safe_import

logger = logging.getLogger(__name__)

FASTHTML_BLOCK_NAMES = {'ft', 'fasthtml'}
FASTHTML_TAG = 'fasthtml'
FASTHTML_TAG_PATTERN = re.compile(f'<{FASTHTML_TAG}([^>]*)>(.*?)</{FASTHTML_TAG}>', re.DOTALL)
FASTHTML_ATTR_PATTERN = re.compile(r'(\w+)=(["\'])(.*?)\2', re.DOTALL)

@dataclass
class FastHTMLTagMatch:
    """Parsed FastHTML tag."""
    full_match: str
    attributes: Dict[str, str]
    content: str
    description: Optional[str] = None

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
            case str() as s if s.startswith("__FUNCTION__"):
                func_content = s[12:]  # Remove prefix
                return func_content if func_content.startswith("function") else f"function(index) {{ return {func_content}; }}"
            case str():
                # Escape special characters
                escaped = obj.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
                return f'"{escaped}"'
            case dict() if not obj:
                return "{}"
            case dict():
                pairs = [f"{next_indent}{py_to_js(k)}: {py_to_js(v, indent + 1, indent_str)}" for k, v in obj.items()]
                return "{\n" + ",\n".join(pairs) + f"\n{current_indent}}}"
            case list() if not obj:
                return "[]"
            case list():
                items = [f"{next_indent}{py_to_js(item, indent + 1, indent_str)}" for item in obj]
                return "[\n" + ",\n".join(items) + f"\n{current_indent}]"
            case _ if callable(obj):
                func_name = getattr(obj, '__name__', '<lambda>')
                return f"function {func_name if func_name != '<lambda>' else ''}(index) {{ return index * 100; }}"
            case _:
                return str(obj)
            
    except Exception as e:
        log(logger, "FastHTML", "error", "conversion", f"Failed to convert {type(obj).__name__} to JavaScript: {str(e)}")
        raise FastHTMLConversionError(f"Failed to convert {type(obj).__name__} to JavaScript: {str(e)}") from e

def js_function(func_str):
    """Create JavaScript function strings."""
    return f"__FUNCTION__{func_str}"

def parse_fasthtml_tag(content: str) -> Optional[FastHTMLTagMatch]:
    """Extract and parse a FastHTML tag from content."""
    if not content or f'<{FASTHTML_TAG}' not in content:
        return None
        
    match = FASTHTML_TAG_PATTERN.search(content)
    if not match:
        return None
    
    attributes_str, inner_content = match.groups()
    attributes = {}
    
    if attributes_str:
        for attr_match in FASTHTML_ATTR_PATTERN.finditer(attributes_str):
            name, _, value = attr_match.groups()
            attributes[name] = value
    
    inner_content = extract_content(inner_content)
    
    return FastHTMLTagMatch(
        full_match=match.group(0),
        attributes=attributes,
        content=inner_content,
        description=attributes.get('description')
    )

def is_content_type(content: str, check_type: str = "fasthtml") -> bool:
    """Check if content matches specified type (fasthtml, fasthtml_block, or direct_html)"""
    if check_type == "fasthtml_block" and isinstance(content, str):
        return content.lower() in FASTHTML_BLOCK_NAMES
        
    if not content or not isinstance(content, str): 
        return False
        
    content = content.strip()
    
    if check_type == "fasthtml":
        return bool(FASTHTML_TAG_PATTERN.search(content))
    elif check_type == "direct_html":
        return (content.startswith('<') and 
                content.endswith('>') and 
                not content.startswith('<%'))
    
    return False

is_fasthtml_content = lambda content: is_content_type(content, "fasthtml")
is_fasthtml_block = lambda name: is_content_type(name, "fasthtml_block")
is_direct_html_content = lambda content: is_content_type(content, "direct_html")

def create_namespace(context_path=None) -> dict:
    """Create namespace with FastHTML components."""
    namespace = {name: getattr(ft_common, name) 
                for name in dir(ft_common) if not name.startswith('_')}
    
    namespace.update({
        'show': lambda obj: obj,
        'NotStr': ft_common.NotStr,
        'convert': lambda obj: obj,
        '__builtins__': globals()['__builtins__'],
        '__name__': '__main__'
    })
    
    return namespace

def process_imports(code: str, namespace: dict, context_path=None) -> None:
    """Process import statements in code."""
    import_pattern = re.compile(r'^(?:from\s+([^\s]+)\s+import|import\s+([^#\n]+))', re.MULTILINE)
    
    for match in import_pattern.finditer(code):
        if match.group(1):  # from X import Y
            safe_import(match.group(1).strip(), namespace, context_path, logger)
        else:  # import X, Y, Z
            for module in match.group(2).split(','):
                clean_module = module.split('#')[0].strip()
                if clean_module:
                    safe_import(clean_module, namespace, context_path, logger)

class FastHTMLExecutor:
    """Executes FastHTML code blocks and returns results."""
    
    def __init__(self, context_path=None):
        self.context_path = context_path
        self.namespace = None
        
    def __enter__(self):
        self.namespace = self.create_namespace()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        return False
        
    def create_namespace(self) -> dict:
        namespace = create_namespace(self.context_path)
        namespace["__results"] = []
        
        original_show = namespace["show"]
        def show_with_capture(obj):
            result = original_show(obj)
            namespace["__results"].append(result)
            return result
        namespace["show"] = show_with_capture
        
        return namespace
    
    def execute(self, code: str) -> List[Any]:
        """Execute FastHTML code and return results."""
        if self.namespace is None:
            self.namespace = self.create_namespace()
            
        try:
            process_imports(code, self.namespace, self.context_path)
            exec(code, self.namespace)
            
            results = self.namespace.get("__results", [])
            if not results:
                log(logger, "FastHTML", "info", "execute", "No results captured. Use show() to display components.")
            return results
            
        except SyntaxError as e:
            return self._handle_execution_error("Syntax error", e, f"Syntax error in FastHTML code: {str(e)}")
        except NameError as e:
            return self._handle_execution_error("Name error", e, f"Name error in FastHTML code: {str(e)}")
        except Exception as e:
            return self._handle_execution_error("Execution error", e, f"Error executing FastHTML code: {str(e)}")
    
    def _handle_execution_error(self, error_type: str, exception: Exception, error_message: str) -> None:
        """Handle execution errors with consistent logging and re-raising."""
        log(logger, "FastHTML", "error", "execute", f"{error_type}: {str(exception)}")
        raise FastHTMLExecutionError(error_message) from exception

class FastHTMLRenderer:
    """Renders FastHTML components to XML."""
    
    @classmethod
    def to_xml(cls, results: List[Any]) -> str:
        """Convert FastHTML results to XML."""
        if not results: return ""
        return "\n".join(cls._render_component(r) for r in results)
    
    @classmethod
    def _render_component(cls, component: Any) -> str:
        """Render a single component to XML."""
        if hasattr(component, "__pyxie_render__"):
            return component.__pyxie_render__()
        return to_xml(component)
    
    @staticmethod
    def handle_error(error: Exception) -> str:
        """Format error message."""
        return (f"SyntaxError: {error} at line {error.lineno}, offset {error.offset}" 
                if isinstance(error, SyntaxError) else 
                f"{error.__class__.__name__}: {error}\n{traceback.format_exc()}")

def protect_script_tags(xml_content: str) -> str:
    """Protect script tag content from HTML processing."""
    if not xml_content or "<script" not in xml_content:
        return xml_content
    
    script_pattern = re.compile(r'(<script[^>]*>)(.*?)(</script>)', re.DOTALL)
    
    def process_script(match):
        opening_tag, content, closing_tag = match.groups()
        
        for entity, char in [('&lt;', '<'), ('&gt;', '>'), ('&amp;', '&'), 
                            ('&quot;', '"'), ('&#x27;', "'"), ('&#39;', "'")]:
            content = content.replace(entity, char)
        
        content = re.sub(r'<pre><code[^>]*>(.*?)</code></pre>', r'\1', content, flags=re.DOTALL)
        
        if "data-raw" not in opening_tag:
            opening_tag = opening_tag.replace("<script", "<script data-raw=\"true\"", 1)
            
        return f"{opening_tag}{content}{closing_tag}"
    
    return script_pattern.sub(process_script, xml_content)

def execute_and_render(
    content: str,
    description: Optional[str] = None,
    context_path: Optional[str] = None,
    return_errors: bool = False,
    add_script_dependencies: bool = True,
    ) -> Union[str, Tuple[str, List[str]]]:
    """Execute FastHTML code and render results."""
    if not content:
        log(logger, "FastHTML", "warning", "render", "Empty content")
        return "" if not return_errors else ("", [])
    
    try:
        results = [content] if is_direct_html_content(content) else \
                 FastHTMLExecutor(context_path).execute(content)
        
        xml = FastHTMLRenderer.to_xml(results)
        if description:
            xml = f"<!-- {description} -->\n{xml}"
        if add_script_dependencies:
            xml = protect_script_tags(xml)
            
        return xml if not return_errors else (xml, [])
    except (FastHTMLError, Exception) as e:
        is_fasthtml_error = isinstance(e, FastHTMLError)
        error_message = f"{e.__class__.__name__}: {e}" if is_fasthtml_error else FastHTMLRenderer.handle_error(e)
        log(logger, "FastHTML", "error", "render", error_message)
        
        if return_errors:
            return "", [error_message]
        return f'<div class="fasthtml-error">{error_message}</div>'

def render_fasthtml_block(content: str, **kwargs) -> Union[str, Tuple[str, List[str]]]:
    """Render a FastHTML block or raw content."""
    tag_match = parse_fasthtml_tag(content)
    
    return execute_and_render(
        tag_match.content if tag_match else content,
        description=tag_match.description if tag_match else None,
        **kwargs
    )

def process_fasthtml_in_content(
    content: str,
    context_path: Optional[str] = None,
    ) -> str:
    """Process all FastHTML blocks in content."""
    if not content or f'<{FASTHTML_TAG}' not in content:
        return content
    
    return FASTHTML_TAG_PATTERN.sub(
        lambda match: _replace_fasthtml_match(match, context_path), 
        content
    )

def _check_syntax(code: str) -> Optional[str]:
    """Check code syntax and return error message if invalid, None if valid."""
    try:
        compile(code, '<string>', 'exec')
        return None
    except SyntaxError as e:
        msg = f"Syntax error in code: {str(e)}"
        log(logger, "FastHTML", "error", "execute", msg)
        return f'<div class="fasthtml-error">FastHTMLExecutionError: Syntax error in FastHTML code: {str(e)}</div>'

def _replace_fasthtml_match(match, context_path: Optional[str] = None) -> str:
    """Replace FastHTML tag with rendered content."""
    try:
        full_match = match.group(0)
                
        if not (tag_match := parse_fasthtml_tag(full_match)):
            return full_match
                    
        if is_direct_html_content(tag_match.content):
            return tag_match.content
        
        if error_msg := _check_syntax(tag_match.content):
            return error_msg
        
        if isinstance(result := render_fasthtml_block(full_match, context_path=context_path), tuple):
            return result[0] or '<div class="fasthtml-error">FastHTMLExecutionError: Failed to render FastHTML</div>'
        
        return result
    except Exception as e:
        error_message = f"FastHTMLExecutionError: Error in FastHTML execution: {e}"
        log(logger, "FastHTML", "error", "process", error_message)
        return f'<div class="fasthtml-error">{error_message}</div>'

def render_fasthtml(content: str, context_path: Optional[str] = None, return_errors: bool = False) -> Union[str, Tuple[str, List[str]]]:
    """Render any content that may contain FastHTML."""
    try:
        if is_fasthtml_content(content):
            return render_fasthtml_block(content, context_path=context_path, return_errors=return_errors)
        
        result = process_fasthtml_in_content(content, context_path)
        return result if not return_errors else (result, [])
    except Exception as e:
        error_message = f"{e.__class__.__name__}: {e}"
        log(logger, "FastHTML", "error", "render", error_message)
        return ("", [error_message]) if return_errors else f'<div class="fasthtml-error">{error_message}</div>'
