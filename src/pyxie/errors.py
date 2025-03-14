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