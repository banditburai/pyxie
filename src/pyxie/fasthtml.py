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

import logging, re
from typing import Optional, Any, List, Dict
from pathlib import Path
from textwrap import dedent
from fastcore.xml import FT
import fasthtml.common as ft_common
from .utilities import safe_import
from .types import RenderResult
from .errors import log
from .parser import VOID_ELEMENTS

logger = logging.getLogger(__name__)
IMPORT_PATTERN = re.compile(r'^(?:from\s+([^\s]+)\s+import|import\s+([^#\n]+))', re.MULTILINE)

def py_to_js(obj, indent=0, indent_str="  "):
    try:
        current_indent, next_indent = indent_str * indent, indent_str * (indent + 1)
        match obj:
            case None: return "null"
            case bool(): return str(obj).lower()
            case int() | float(): return str(obj)
            case str() if obj.startswith("__FUNCTION__"):
                return obj[12:] if obj[12:].startswith("function") else f"function(index) {{ return {obj[12:]}; }}"
            case str():
                escaped = obj.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
                return f'"{escaped}"'
            case dict():
                if not obj: return "{}"
                pairs = [f"{next_indent}{py_to_js(k)}: {py_to_js(v, indent + 1)}" for k, v in obj.items()]
                return "{\n" + ",\n".join(pairs) + f"\n{current_indent}}}"
            case list():
                if not obj: return "[]"
                items = [f"{next_indent}{py_to_js(item, indent + 1)}" for item in obj]
                return "[\n" + ",\n".join(items) + f"\n{current_indent}]"
            case _ if callable(obj):
                func_name = getattr(obj, '__name__', '<lambda>')
                return f"function {func_name if func_name != '<lambda>' else ''}(index) {{ return index * 100; }}"
            case _: return str(obj)
    except Exception as e:
        log(logger, "FastHTML", "error", "conversion", f"{e}")
        return str(obj)

def js_function(func_str): return f"__FUNCTION__{func_str}"

class PyxieXML:
    def __init__(self, tag_name, *args, **kwargs):
        self.tag = tag_name
        self.content = args[0] if args else ""
        self.children = args[1:] if len(args) > 1 else []
        self.attrs = {k if k != 'cls' else 'class': v for k, v in kwargs.items()}
    
    def __str__(self):
        attrs = [f'{k}="{v}"' if v is not True else k for k, v in self.attrs.items() if v is not False]
        attr_str = ' ' + ' '.join(attrs) if attrs else ''
        
        if self.tag.lower() == 'script':
            return f'<script{attr_str}>{self.content}</script>'
                
        if self.tag.lower() in VOID_ELEMENTS:
            return f'<{self.tag}{attr_str}>'
        
        content = [str(self.content)] if self.content else []
        content.extend(str(child) for child in self.children)
        return f'<{self.tag}{attr_str}>{" ".join(content)}</{self.tag}>'

def create_namespace(context_path: Optional[Path] = None) -> Dict[str, Any]:
    """Create a namespace for FastHTML execution."""
    namespace = {name: getattr(ft_common, name) for name in dir(ft_common) if not name.startswith('_')}
    def show(*args):
        if '__results__' not in namespace: namespace['__results__'] = []
        namespace['__results__'].extend(args)
    namespace.update({
        'show': show,
        'PyxieXML': PyxieXML,
        'FT': FT,
        '__builtins__': __builtins__,
        '__name__': '__main__'
    })
    return namespace

def process_imports(code: str, namespace: dict, context_path=None) -> None:
    for match in IMPORT_PATTERN.finditer(code):
        if module := match.group(1) or match.group(2):
            for name in module.split(','):
                if clean_name := name.split('#')[0].strip():
                    safe_import(clean_name, namespace, context_path, logger)

class FastHTMLExecutor:
    def __init__(self, context_path: Optional[Path] = None):
        self.context_path = context_path
        self.namespace = None
    
    def __enter__(self):
        self.namespace = create_namespace(self.context_path)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.namespace = None
    
    def execute(self, code: str) -> List[Any]:
        if self.namespace is None:
            self.namespace = create_namespace(self.context_path)
        try:
            process_imports(code, self.namespace, self.context_path)
            self.namespace['__results__'] = []
            self.namespace['__builtins__'] = globals()['__builtins__']
            exec(code, self.namespace)
            return self.namespace.get('__results__', [])
        except Exception as e:
            log(logger, "FastHTML", "error", "execute", f"Error executing FastHTML code: {str(e)}")
            raise

class FastHTMLRenderer:
    @classmethod
    def to_xml(cls, results: List[Any]) -> str:
        return "\n".join(cls._render_component(r) for r in results).rstrip() if results else ""
    
    @classmethod
    def _render_component(cls, component: Any) -> str:
        if component is None: return ''
        if isinstance(component, (str, int, float, bool)): return str(component)
        if isinstance(component, (list, tuple)): return ' '.join(cls._render_component(c) for c in component)
        if not isinstance(component, FT): return str(component)
        
        tag = component.__class__.__name__.lower()
        attrs, content = {}, []
        
        for key, value in vars(component).items():
            if key == 'children':
                content.extend(value if isinstance(value, (list, tuple)) else [value])
            elif key == 'attrs' and value is not None:
                attrs.update({k: v for k, v in value.items() if v is not None})
            elif not key.startswith('_'):
                if key == 'tag': tag = value
                elif key not in ('listeners_', 'void_'): attrs[key] = value
        
        attr_list = [f'{k}="{v}"' if v is not True else k for k, v in attrs.items() if v is not False and v is not None and not k.startswith('_')]
        attr_str = ' ' + ' '.join(attr_list) if attr_list else ''
        
        if tag.lower() == 'script':
            script_content = [str(c) if isinstance(c, str) else cls._render_component(c) for c in content]
            return f'<script{attr_str}>\n{" ".join(script_content)}\n</script>'
                
        if tag.lower() in VOID_ELEMENTS:
            return f'<{tag}{attr_str}/>'
        
        rendered_content = ' '.join(cls._render_component(c) for c in content)
        return f'<{tag}{attr_str}>{rendered_content}</{tag}>'

def execute_fasthtml(content: str, context_path: Optional[Path] = None) -> RenderResult:
    """Execute FastHTML code and return the rendered result.
    
    Args:
        content: The FastHTML code to execute
        context_path: Optional path for resolving imports        
    Returns:
        RenderResult containing the rendered HTML or any error
    """
    if not content: return RenderResult()
    try:
        content = dedent(content.strip())
        with FastHTMLExecutor(context_path) as executor:
            try:
                results = executor.execute(content)
                return RenderResult(content=FastHTMLRenderer.to_xml(results))
            except Exception as e:
                return RenderResult(error=str(e))
    except Exception as e:
        return RenderResult(error=str(e))