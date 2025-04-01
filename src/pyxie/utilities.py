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
from typing import Dict, Optional, Any, List, Union
from pathlib import Path
import hashlib
import importlib.util
import os
from .types import ContentItem

from .errors import log

logger = logging.getLogger(__name__)

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
        
        # Skip file if metadata parsing failed
        if metadata is None or content is None:
            if logger_instance:
                log(logger_instance, "ContentLoader", "warning", "load", f"Skipping {file_path} due to invalid frontmatter")
            return None
                
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

