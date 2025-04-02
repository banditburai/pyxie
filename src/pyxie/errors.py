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

"""Core exceptions for Pyxie."""

import logging
from pathlib import Path
from typing import Optional, TypeVar, Union, Callable, Any

T = TypeVar('T')

def log(logger_instance: logging.Logger, module: str, level: str, operation: str, message: str, file_path: Optional[Path] = None) -> None:
    """Log message with standardized format."""
    if file_path:
        file_info = f" in file {file_path}"
    else:
        file_info = ""
    getattr(logger_instance, level)(f"[{module}] {operation}: {message}{file_info}")

def log_errors(logger: logging.Logger, component: str, action: str) -> Callable:
    """Decorator to log errors and re-raise.
    
    This decorator wraps a function to catch any exceptions, log them using
    the standardized format, and then re-raise them to propagate up the call stack.
    
    Args:
        logger: Logger instance to use for logging
        component: Component name for log message
        action: Action being performed for log message
        
    Returns:
        Decorator function that preserves the original function's type hints
        
    Example:
        ```python
        @log_errors(logger, "Component", "action")
        def some_function():
            # Code that might raise an exception
            pass
        ```
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                log(logger, component, "error", action, str(e))
                raise
        return wrapper
    return decorator

def format_error_html(error: Union[Exception, str], context: Optional[str] = None) -> str:
    """Format an error message as HTML for display.
    
    Args:
        error: Either an Exception object or an error message string
        context: Optional context for the error (e.g., 'parsing', 'rendering')
    """
    if isinstance(error, Exception):
        error_message = f"{error.__class__.__name__}: {error}"
        if isinstance(error, SyntaxError):
            error_message = f"Syntax error: {error}"
    else:
        error_message = str(error)
    
    if context:
        error_message = f"{context.upper()}: {error_message}"
    
    return f'<div class="fasthtml-error">ERROR: {error_message}</div>'

class PyxieError(Exception):
    """Base exception for all Pyxie errors."""

class ParseError(PyxieError):
    """Base class for parsing-related errors."""

class FrontmatterError(ParseError):
    """Error parsing frontmatter."""
    
class BlockError(ParseError):
    """Error parsing content blocks."""

class ValidationError(PyxieError):
    """Error validating content or metadata."""

class RenderError(PyxieError):
    """Error rendering content to HTML."""

class CollectionError(PyxieError):
    """Error in collection operations."""

class LayoutError(PyxieError):
    """Base class for layout-related errors."""

class LayoutNotFoundError(LayoutError):
    """Raised when a layout is not found."""

class LayoutValidationError(LayoutError):
    """Raised when a layout is invalid."""

class SlotError(PyxieError):
    """Error in slot operations."""

class ContentError(PyxieError):
    """Error in content operations."""

class CacheError(PyxieError):
    """Error in cache operations."""

# FastHTML-specific exceptions
class FastHTMLError(PyxieError):
    """Base exception for FastHTML-related errors."""

class FastHTMLImportError(FastHTMLError):
    """Error importing modules in FastHTML code."""

class FastHTMLExecutionError(FastHTMLError):
    """Error executing FastHTML code."""

class FastHTMLRenderError(FastHTMLError):
    """Error rendering FastHTML components to XML."""

class FastHTMLConversionError(FastHTMLError):
    """Error converting Python objects to JavaScript.""" 