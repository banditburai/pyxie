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
from typing import Any, Callable, Dict, Optional, Protocol, TypeVar, cast
from dataclasses import dataclass, field
from functools import wraps

from fastcore.xml import FT, to_xml
from .utilities import log

logger = logging.getLogger(__name__)

class LayoutFunction(Protocol):
    """Protocol defining a layout function signature."""
    def __call__(self, *args: Any, **kwargs: Any) -> FT: ...

@dataclass(frozen=True)
class Layout:
    """Immutable layout registration."""
    name: str
    func: LayoutFunction
    
    def create(self, *args: Any, **kwargs: Any) -> str:
        """Create a layout instance.
        
        Args:
            *args: Positional arguments for the layout
            **kwargs: Keyword arguments for the layout
            
        Returns:
            The layout's HTML string
            
        Raises:
            TypeError: If the layout returns a non-FastHTML value
        """
        try:
            # Extract slots if provided
            slots = kwargs.pop("slots", None)
            
            # Call the layout function
            result = self.func(*args, **kwargs)
            
            # Handle different return types
            if isinstance(result, tuple) and all(isinstance(item, FT) for item in result):                
                # Just convert to XML directly
                layout_xml = to_xml(result)
            elif isinstance(result, (FT, str)):
                # Handle regular FT objects or strings
                layout_xml = to_xml(result)
            else:
                raise TypeError(
                    f"Layout '{self.name}' must return a FastHTML component "
                    f"or HTML string, got {type(result)}"
                )
                
            # Apply slots if provided
            if slots:
                from pyxie.slots import fill_slots
                # Convert slot values to lists as required by fill_slots
                slot_blocks = {name: [value] if not isinstance(value, list) else value 
                              for name, value in slots.items()}
                result = fill_slots(layout_xml, slot_blocks)
                return result.element
                
            return layout_xml
        except Exception as e:
            log(logger, "Layouts", "error", "create", f"Error creating layout '{self.name}': {e}")
            raise

@dataclass
class LayoutRegistry:
    """Registry of available layouts."""
    _layouts: Dict[str, Layout] = field(default_factory=dict)
    
    def register(self, name: str, func: LayoutFunction) -> None:
        """Register a layout function.
        
        Args:
            name: Name to register layout under
            func: Layout function to register
        """
        if name in self._layouts:
            log(logger, "Layouts", "warning", "register", f"Overwriting existing layout '{name}'")
        self._layouts[name] = Layout(name=name, func=func)
        log(logger, "Layouts", "debug", "register", f"Registered layout '{name}'")
    
    def get(self, name: str) -> Optional[Layout]:
        """Get a layout by name.
        
        Args:
            name: Name of layout to get
            
        Returns:
            Layout if found, None otherwise
        """
        if name not in self._layouts:
            log(logger, "Layouts", "warning", "get", f"Layout '{name}' not found")
            return None
        return self._layouts[name]
    
    def create(self, name: str, *args: Any, **kwargs: Any) -> Optional[str]:
        """Create a layout instance by name.
        
        Args:
            name: Name of the layout to create
            *args: Positional arguments for the layout
            **kwargs: Keyword arguments for the layout
            
        Returns:
            The layout's HTML string or None if layout not found
        """
        if layout := self.get(name):
            return layout.create(*args, **kwargs)
        return None
    
    def __contains__(self, name: str) -> bool:
        """Check if a layout exists."""
        return name in self._layouts

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