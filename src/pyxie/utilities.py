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

"""Utility functions and shared helpers for the Pyxie package.

This module contains general-purpose utilities used across the package.
"""

import logging
from typing import Dict, Optional, Any, List, Union, Callable, Tuple, Iterator
from html import escape
from pathlib import Path
import hashlib
import importlib.util
import os
import re
from dataclasses import dataclass
from .types import ContentItem, RenderResult

from .constants import DEFAULT_METADATA
from .errors import log

logger = logging.getLogger(__name__)

def format_error_html(error_type: str, message: str) -> str:
    """Format an error message as HTML."""
    return f'<div class="fasthtml-error">ERROR: {error_type.upper()}: {message}</div>'

def safe_html_escape(text: Optional[str], quote: bool = True) -> str:
    """Escape HTML text, handling None values."""
    return escape(text, quote=quote) if text else ""

def merge_html_classes(*classes: Optional[str]) -> str:
    """Combine multiple HTML class strings into space-separated unique classes."""
    all_classes = set()
    for cls in classes:
        if cls:
            all_classes.update(c.strip() for c in cls.split())
    return " ".join(sorted(all_classes))

def set_html_attributes(
    element: Any, 
    attributes: Dict[str, str], 
    logger_instance: Optional[logging.Logger] = None
) -> None:
    """Set HTML attributes on an element, handling different element types."""
    try:
        # Handle class/cls attributes consistently
        if 'cls' in attributes and 'class' not in attributes:
            attributes['class'] = attributes.pop('cls')
            
        for key, value in attributes.items():
            if hasattr(element, "set"):
                element.set(key, value)
            elif hasattr(element, "__setitem__"):
                element[key] = value
            elif hasattr(element, key):
                setattr(element, key, value)
            else:
                method = getattr(logger_instance, "warning") if logger_instance else print
                method(f"Could not set attribute {key} on element {element}")
    except Exception as e:
        method = getattr(logger_instance, "error") if logger_instance else print
        method(f"Error setting attributes: {e}")

def _split_html_at_scripts(content: str) -> Iterator[Tuple[str, bool, int, int]]:
    """Split HTML at script tag boundaries, yielding (content, is_script, start, end) tuples."""
    script_pattern = re.compile(r'(<script[^>]*>)(.*?)(</script>)', re.DOTALL)
    last_end = 0
    
    for match in script_pattern.finditer(content):
        start, end = match.start(), match.end()
        
        # Yield HTML before this script (if any)
        if start > last_end:
            yield (content[last_end:start], False, last_end, start)
        
        # Yield the script tag
        script_tag = match.group(0)
        yield (script_tag, True, start, end)
        
        last_end = end
    
    # Yield remaining content after last script
    if last_end < len(content):
        yield (content[last_end:], False, last_end, len(content))

def _process_script_tag(script_tag: str) -> str:
    """Ensure script tag has data-raw attribute and clean content of HTML escapes."""
    script_pattern = re.compile(r'(<script[^>]*>)(.*?)(</script>)', re.DOTALL)
    match = script_pattern.match(script_tag)
    
    if not match:
        return script_tag
        
    script_opening = match.group(1)
    script_content = match.group(2)
    script_closing = match.group(3)
    
    # Ensure data-raw attribute is present
    if "data-raw" not in script_opening:
        script_opening = script_opening.replace("<script", "<script data-raw=\"true\"", 1)
    
    # Clean script content of HTML escape sequences
    script_content = script_content.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
    
    return f"{script_opening}{script_content}{script_closing}"

def extract_scripts(content: str) -> List[Tuple[str, bool]]:
    """Extract script tags and HTML content, returning pairs of (content_fragment, is_script)."""
    parts = []
    
    for part, is_script, _, _ in _split_html_at_scripts(content):
        if is_script:
            parts.append((_process_script_tag(part), True))
        else:
            parts.append((part, False))
    
    return parts

def apply_html_attributes(
    html_str: str, 
    attributes: Dict[str, str], 
    logger_instance: Optional[logging.Logger] = None
) -> str:
    """Apply attributes to the first element in an HTML string."""
    try:
        from lxml import html
        temp_div = html.fragment_fromstring(f"<div>{html_str}</div>")
        
        children = temp_div.getchildren()
        first_element = children[0] if children else temp_div
        
        set_html_attributes(first_element, attributes, logger_instance)
        
        if children:
            return ''.join(
                html.tostring(child, encoding='unicode', method='html')
                for child in children
            )
        return html_str
    except Exception as e:
        method = getattr(logger_instance, "warning") if logger_instance else print
        method(f"Failed to add attributes to HTML: {e}")
        return html_str

def normalize_path(path: Union[str, Path]) -> str:
    """Convert a path to its resolved string representation."""
    if isinstance(path, Path):
        return str(path.resolve())
    return str(Path(path).resolve())

def hash_file(path: Union[str, Path], use_mtime: bool = True) -> Optional[str]:
    """Get a hash or modification timestamp of a file."""
    try:
        file_path = Path(path)
        if not file_path.exists():
            return None
            
        if use_mtime:
            # Use mtime for efficient change detection
            return str(file_path.stat().st_mtime)
        else:
            # Use content hash for more accurate change detection
            hash_obj = hashlib.md5()
            with open(file_path, 'rb') as f:
                # Read in chunks to handle large files
                for chunk in iter(lambda: f.read(4096), b''):
                    hash_obj.update(chunk)
            return hash_obj.hexdigest()
    except Exception as e:
        log(logger, "Utilities", "warning", "hash_file", f"Failed to hash file {path}: {e}")
        return None

def load_content_file(
    file_path: Path, 
    default_metadata: Optional[Dict[str, Any]] = None,
    logger_instance: Optional[logging.Logger] = None
) -> Optional["ContentItem"]:
    """Load a content file and create a ContentItem.
    
    Args:
        file_path: Path to the content file
        default_metadata: Optional metadata to merge with file metadata
        logger_instance: Optional logger for debugging
        
    Returns:
        ContentItem if successful, None if loading fails
    """
    try:
        from .parser import parse_frontmatter
        from .types import ContentItem
        from .constants import DEFAULT_METADATA
        
        # Load and parse content
        content = file_path.read_text()
        metadata, content = parse_frontmatter(content)
                
        merged_metadata = DEFAULT_METADATA | (default_metadata or {}) | metadata
        
        return ContentItem(
            source_path=file_path,
            metadata=merged_metadata,
            content=content
        )
    except Exception as e:
        if logger_instance:
            log(logger_instance, "ContentLoader", "error", "load", f"Failed to load {file_path}: {e}")
        return None

def merge_metadata(*metadata_dicts: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge multiple metadata dictionaries, non-None values taking precedence."""
    result: Dict[str, Any] = {}
    for meta in metadata_dicts:
        if meta:
            result.update({k: v for k, v in meta.items() if v is not None})
    return result

def resolve_default_layout(
    default_layout: str,
    metadata: Dict[str, Any],
    component_name: str,
    logger: Optional[logging.Logger] = None
) -> str:
    """Resolve default layout from parameters and metadata."""    
    metadata_layout = metadata.get("layout")
    resolved_layout = metadata_layout if default_layout == "default" and metadata_layout else default_layout
    
    # Only warn if both explicit layout and different metadata layout exist
    if default_layout != "default" and metadata_layout and metadata_layout != default_layout and logger:
        log(logger, "Config", "warning", "init", 
            f"Both default_layout and default_metadata['layout'] specified{' in ' + component_name if component_name else ''}. "
            f"Using default_layout='{default_layout}'.")
            
    return resolved_layout

def normalize_tags(tags: Any) -> List[str]:
    """Convert tags to a sorted list of unique, lowercase strings."""
    if not tags:
        return []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",")]
    return sorted(set(str(t).strip().lower() for t in tags if t))

def get_line_number(text: str, position: int) -> int:
    """Get 1-indexed line number for a character position in text."""
    if position <= 0:
        return 1
    return text[:position].count('\n') + 1

def convert_value(value: str) -> Any:
    """Convert string to appropriate Python type (bool, int, float, list, etc)."""
    value = value.strip()
    
    # Handle quoted values
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    
    # Handle lists
    if value.startswith('[') and value.endswith(']'):
        return [v.strip(' "\'') for v in value[1:-1].split(',') if v.strip()]
        
    # Handle other types
    match value.lower():
        case 'true' | 'yes':
            return True
        case 'false' | 'no':
            return False
        case 'null' | '~' | '':
            return None
        case s if s.isdigit():
            return int(s)
        case s if is_float(s):
            try:
                return float(s)
            except ValueError:
                pass
    
    return value

def is_float(value: str) -> bool:
    """Check if string can be converted to a float."""
    try:
        float(value)
        return True
    except ValueError:
        return False

def _find_module_in_context(
    module_name: str, 
    context_path: Path, 
    logger_instance: Optional[logging.Logger] = None
) -> Optional[Any]:
    """Find and load a module from a specific context path."""
    module_path = module_name.replace('.', os.path.sep)
    potential_paths = [
        context_path / f"{module_path}.py",
        context_path / module_path / "__init__.py"
    ]
    
    for path in potential_paths:
        if path.exists():
            if logger_instance:
                log(logger_instance, "Utilities", "debug", "import", f"Found module at '{path}'")
            spec = importlib.util.spec_from_file_location(module_name, path)
            if spec:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                return module
                
    return None

def _update_namespace_from_module(module: Any, module_name: str, namespace: Dict[str, Any]) -> None:
    """Add module and its attributes to the namespace dictionary."""
    module_short_name = module_name.split('.')[-1]
    namespace[module_short_name] = module
    
    for name in dir(module):
        if not name.startswith('_'):
            namespace[name] = getattr(module, name)

def safe_import(
    module_name: str, 
    namespace: Optional[Dict[str, Any]] = None, 
    context_path: Optional[Union[str, Path]] = None,
    logger_instance: Optional[logging.Logger] = None
) -> Optional[Any]:
    """Import a module with fallbacks to custom paths."""
    if logger_instance:
        log(logger_instance, "Utilities", "debug", "import", f"Attempting to import '{module_name}'")
    
    module = None
    
    # Try standard Python import
    try:
        module = importlib.import_module(module_name)
    except ImportError:
        # Fall back to context-relative import
        if context_path:
            try:
                if isinstance(context_path, str):
                    context_path = Path(context_path)
                
                module = _find_module_in_context(module_name, context_path, logger_instance)
            except Exception as e:
                if logger_instance:
                    log(logger_instance, "Utilities", "error", "import", f"Error importing from context path: {str(e)}")
                return None
        elif logger_instance:
            log(logger_instance, "Utilities", "warning", "import", 
                f"Module '{module_name}' not found in standard paths and no context path provided")
    
    # Update namespace if provided and module was found
    if module and namespace is not None:
        _update_namespace_from_module(module, module_name, namespace)
    
    # Log warning if module wasn't found
    if not module and logger_instance:
        log(logger_instance, "Utilities", "warning", "import", f"Could not import module '{module_name}'")
        
    return module 

def parse_html_fragment(content_html: str) -> Any:
    """Parse HTML fragment, wrapping in div if needed."""
    from lxml import html, etree
    
    # Create a custom parser that preserves custom tags
    parser = etree.HTMLParser(recover=True)
    etree.set_default_parser(parser)
    
    try:
        # First try to parse as-is
        fragment = html.fragment_fromstring(content_html, parser=parser)
        
        # If we got a div and it's not what we wanted, extract its children
        if fragment.tag == 'div' and not content_html.strip().startswith('<div'):
            children = list(fragment)
            if len(children) == 1:
                return children[0]
            return fragment
            
        return fragment
    except Exception:
        # If that fails, try wrapping in a div
        fragment = html.fragment_fromstring(f"<div>{content_html}</div>", parser=parser)
        
        # If we only have one child and it's not a div, return it
        children = list(fragment)
        if len(children) == 1 and not content_html.strip().startswith('<div'):
            return children[0]
            
        return fragment

def build_pagination_urls(
    base_url: str,
    pagination: Any,
    tag: Optional[str] = None,
    params: Optional[Dict[str, str]] = None
) -> Dict[str, str]:
    """Generate pagination URLs based on pagination info."""
    if pagination.total_pages <= 1:
        return {"current": base_url}
    
    def build_url(page: Optional[int]) -> str:
        if page is None or page < 1 or page > pagination.total_pages:
            return base_url
            
        url_params = {**(params or {})}
        if page > 1:
            url_params['page'] = str(page)
        if tag:
            url_params['tag'] = tag
            
        if not url_params:
            return base_url
            
        return f"{base_url}?{'&'.join(f'{k}={v}' for k, v in url_params.items())}"
    
    return {
        "current": build_url(pagination.current_page),
        "next": build_url(pagination.next_page),
        "prev": build_url(pagination.previous_page),
        "first": build_url(1),
        "last": build_url(pagination.total_pages),
        "pages": {p: build_url(p) for p in pagination.page_range()}
    } 

