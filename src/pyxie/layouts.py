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

"""Layout registration and management for Pyxie.

Layouts are functions that return HTML elements with data-slot attributes.
They are registered using the @layout decorator and can be referenced
by name in content frontmatter.

Example:
    ```python
    @layout("blog")
    def blog_layout() -> FT:
        return Div(
            Header(
                Div(data_slot="header"),
                Nav(data_slot="nav", cls="main-nav")
            ),
            Main(
                Article(data_slot="main"),
                Aside(data_slot="sidebar"),
                cls="content-wrapper"
            )
        )
    ```
"""

import logging
from typing import Any, Callable, Dict, Optional, Protocol, List, Set, Tuple
from os import PathLike
from dataclasses import dataclass, field
from pathlib import Path
import importlib
import inspect
from lxml import html
from fastcore.xml import FT, to_xml
from .errors import log
from .types import ContentItem
from .cache import CacheProtocol

logger = logging.getLogger(__name__)

@dataclass
class LayoutResult:
    """Result of layout resolution."""
    html: str
    error: Optional[str] = None

def handle_cache_and_layout(item: ContentItem, cache: Optional[CacheProtocol] = None) -> LayoutResult:
    """Handle caching and layout resolution in one step."""
    collection = item.collection or "content"
    layout_name = item.metadata.get("layout")  # Don't use default layout
    
    if cache and (cached := cache.get(collection, item.source_path, layout_name or "default")):
        return LayoutResult(html=cached)
    
    if layout_name and (layout := get_layout(layout_name)):
        sig = inspect.signature(layout.func)
        params = list(sig.parameters.values())
        
        # If the layout function expects a single 'metadata' parameter, pass the entire metadata dict
        if len(params) == 1 and params[0].name == 'metadata':
            return LayoutResult(html=layout.create(metadata=item.metadata))
            
        # Otherwise, filter metadata to match the function's parameters
        metadata = {k: v for k, v in item.metadata.items() if k != "layout" and k in sig.parameters}
        return LayoutResult(html=layout.create(**metadata))
    
    if layout_name:
        error_msg = f"Layout '{layout_name}' not found"
        log(logger, "Renderer", "warning", "layout", error_msg)
        return LayoutResult(html="", error=error_msg)
    
    # If no layout is specified, use the default layout
    if default_layout := get_layout("default"):
        return LayoutResult(html=default_layout.create())
    
    # If no default layout exists, return empty string
    return LayoutResult(html="")

class LayoutError(Exception):
    """Base class for layout-related errors."""

class LayoutNotFoundError(LayoutError):
    """Raised when a layout is not found."""

class LayoutValidationError(LayoutError):
    """Raised when a layout is invalid."""

def log_errors(logger: logging.Logger, component: str, action: str) -> Callable:
    """Decorator to log errors and re-raise."""
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                log(logger, component, "error", action, str(e))
                raise
        return wrapper
    return decorator

class LayoutFunction(Protocol):
    """Protocol defining a layout function signature."""
    def __call__(self, *args: Any, **kwargs: Any) -> FT: ...

@dataclass(frozen=True)
class Layout:
    """Immutable layout registration."""
    name: str
    func: LayoutFunction
    
    @log_errors(logger, "Layouts", "create")
    def create(self, *args: Any, **kwargs: Any) -> str:
        """Create a layout instance.
        
        Args:
            *args: Positional arguments for the layout
            **kwargs: Keyword arguments for the layout
            
        Returns:
            The layout's HTML string
            
        Raises:
            LayoutValidationError: If the layout returns a non-FastHTML value
        """
        try:                        
            # Call the layout function
            result = self.func(*args, **kwargs)
            
            # Convert result to XML string
            if isinstance(result, FT):
                return to_xml(result)
            elif isinstance(result, str):
                return result
            else:
                raise LayoutValidationError(
                    f"Layout '{self.name}' must return a FastHTML component "
                    f"or HTML string, got {type(result)}"
                )
                
        except Exception as e:
            log(logger, "Layouts", "error", "create", f"Error creating layout '{self.name}': {e}")
            raise

@dataclass
class LayoutRegistry:
    """Registry of available layouts."""
    _layouts: Dict[str, Layout] = field(default_factory=dict)
    
    def register(self, name: str, func: LayoutFunction) -> None:
        """Register a layout function."""
        if name in self._layouts:
            log(logger, "Layouts", "warning", "register", f"Overwriting existing layout '{name}'")
        self._layouts[name] = Layout(name=name, func=func)
        log(logger, "Layouts", "debug", "register", f"Registered layout '{name}'")
    
    def get(self, name: str) -> Layout:
        """Get a layout by name or raise LayoutNotFoundError."""
        if name not in self._layouts:
            raise LayoutNotFoundError(f"Layout '{name}' not found")
        return self._layouts[name]
    
    def create(self, name: str, *args: Any, **kwargs: Any) -> Optional[str]:
        """Create a layout instance by name."""
        try:
            return self.get(name).create(*args, **kwargs)
        except LayoutNotFoundError:
            return None
    
    def __contains__(self, name: str) -> bool:
        """Check if a layout exists."""
        return name in self._layouts

    def resolve_layout_paths(self, content_dir: Optional[Path], layout_paths: Optional[List[PathLike]]) -> List[Path]:
        """Resolve layout search paths."""
        paths = []
        
        # Add custom paths if provided
        if layout_paths:
            paths.extend(Path(p) for p in layout_paths)
            
        # If no custom paths exist, or if they don't exist, fall back to default paths
        if not paths or not any(p.exists() and p.is_dir() for p in paths):
            if content_dir and content_dir.parent:
                app_dir = content_dir.parent
                paths.append(app_dir)
                
                for dirname in ["layouts", "templates", "static"]:
                    path = app_dir / dirname
                    if path.exists() and path.is_dir():
                        paths.append(path)
                
        return paths

    def _is_valid_python_file(self, path: Path) -> bool:
        """Check if a Python file should be processed for layouts."""
        return (path.suffix == '.py' and 
                '__pycache__' not in path.parts and
                not any(part.startswith('.') for part in path.parts))

    @log_errors(logger, "Layouts", "discover")
    def _process_layout_files(self, python_files: List[Path]) -> None:
        """Process Python files to find and register layouts."""
        for file in python_files:
            if not (spec := importlib.util.spec_from_file_location(file.stem, file)):
                continue
                
            try:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                for _, obj in inspect.getmembers(
                    module, 
                    lambda o: inspect.isfunction(o) and hasattr(o, '_layout_name')
                ):
                    log(logger, "Layouts", "debug", "discover", 
                        f"Found layout: {obj._layout_name} in {file.name}")
            except Exception as e:
                log(logger, "Layouts", "error", "discover", 
                    f"Error loading layout file {file}: {e}")

    def discover_layouts(self, content_dir: Optional[Path] = None, layout_paths: Optional[List[PathLike]] = None) -> None:
        """Discover and register layouts from Python modules."""
        paths = self.resolve_layout_paths(content_dir, layout_paths)
        
        for path in paths:
            if not path.exists() or not path.is_dir():
                log(logger, "Layouts", "warning", "discover", f"Layout directory not found: {path}")
                continue
                
            python_files = [f for f in path.glob("**/*.py") if self._is_valid_python_file(f)]
            self._process_layout_files(python_files)

# Global registry instance
registry = LayoutRegistry()

def layout(name: str) -> Callable[[LayoutFunction], LayoutFunction]:
    """Register a layout function.
    
    Args:
        name: Name to register layout under
        
    Returns:
        Decorator function that preserves the original function's type hints
        
    Example:
        ```python
        @layout("blog")
        def blog_layout(title: str) -> FT:
            return Div(H1(title))
        ```
    """
    def decorator(func: LayoutFunction) -> LayoutFunction:
        registry.register(name, func)
        # Store layout name on function for discovery
        func._layout_name = name
        return func
    return decorator

# Convenience functions that delegate to registry
def get_layout(name: str) -> Optional[Layout]:
    """Get a registered layout by name."""
    return registry.get(name)

def create_layout(name: str, *args: Any, **kwargs: Any) -> Optional[str]:
    """Create a layout instance by name."""
    return registry.create(name, *args, **kwargs) 