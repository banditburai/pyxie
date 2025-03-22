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

from dataclasses import dataclass
from typing import Any, Generic, Optional, TypeVar

T = TypeVar('T')

@dataclass
class Result(Generic[T]):
    """Generic result of an operation which may succeed or fail."""
    is_success: bool
    content: T = None
    error: Optional[Exception] = None
    
    @classmethod
    def success(cls, content: T) -> "Result[T]":
        """Create a successful result with content."""
        # If content is already a Result, don't wrap it again
        if isinstance(content, Result):
            return content
        return cls(is_success=True, content=content)
        
    @classmethod
    def failure(cls, error: Exception) -> "Result[T]":
        """Create a failure result with error."""
        # If error is already a Result in failed state, don't wrap it again
        if isinstance(error, Result) and not error.is_success:
            return error
        return cls(is_success=False, error=error)
    
    def __str__(self) -> str:
        """String representation of the result."""
        if self.is_success:
            return f"Success: {self.content}"
        return f"Error: {self.error}"
    
    def map(self, fn):
        """Transform the value if successful, preserving the error otherwise.
        
        If the function returns a Result, it will be flattened to avoid nested Results.
        """
        if not self.is_success:
            return self
            
        try:
            result = fn(self.content)
            # If fn returns a Result, flatten it instead of wrapping
            if isinstance(result, Result):
                return result
            return Result.success(result)
        except Exception as e:
            # Capture any exceptions from the mapping function
            return Result.failure(e)
    
    def and_then(self, fn):
        """Chain operations that might fail, passing the value to the next function.
        
        The function `fn` must return a Result object.
        """
        if not self.is_success:
            return self
            
        try:
            # fn must return a Result
            return fn(self.content)
        except Exception as e:
            # Capture any exceptions from the chaining function
            return Result.failure(e)
    
    def map_error(self, fn):
        """Transform the error if failed, preserving the success otherwise.
        
        If the function returns a Result, it will be flattened.
        """
        if self.is_success:
            return self
            
        try:
            result = fn(self.error)
            # If fn returns a Result, use it directly
            if isinstance(result, Result):
                return result
            return Result.failure(result)
        except Exception as e:
            # Capture any exceptions from the error mapping function
            return Result.failure(e)

def format_error_html(error: Exception) -> str:
    """Format an error message as HTML for display."""
    error_message = f"{error.__class__.__name__}: {error}"
    if isinstance(error, SyntaxError):
        error_message = f"Syntax error: {error}"
    
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