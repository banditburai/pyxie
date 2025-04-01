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
from typing import Optional, TypeVar, Union

T = TypeVar('T')

def log(logger_instance: logging.Logger, module: str, level: str, operation: str, message: str, file_path: Optional[Path] = None) -> None:
    """Log message with standardized format."""
    if file_path:
        file_info = f" in file {file_path}"
    else:
        file_info = ""
    getattr(logger_instance, level)(f"[{module}] {operation}: {message}{file_info}")

def format_error_html(error: Union[Exception, str], context: Optional[str] = None) -> str:
    """Format an error message as HTML for display.
    
    Args:
        error: Either an Exception object or an error message string
        context: Optional context for the error (e.g., 'parsing', 'rendering')
    """
    # Format the error message based on type
    if isinstance(error, Exception):
        error_message = f"{error.__class__.__name__}: {error}"
        if isinstance(error, SyntaxError):
            error_message = f"Syntax error: {error}"
    else:
        error_message = str(error)
    
    # Add context if provided
    if context:
        error_message = f"{context.upper()}: {error_message}"
    
    # Use a format that test assertions can detect even after HTML escaping
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
    """Error in layout operations."""

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