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

"""Pyxie - A simple static site generator with component-based layouts."""

from .pyxie import Pyxie
from .layouts import layout
from .types import (
    ContentBlock,
    ContentItem,
    ContentProvider,
    Metadata,
    PathLike,
)
from .errors import (
    PyxieError,
    LayoutError,
    ContentError,
    RenderError,
)
from .renderer import render_content, render_markdown, render_block, render_blocks
from .collection import Collection

__version__ = "0.1.2"

# Add html property directly to ContentItem
# This avoids circular imports while keeping the API clean
ContentItem.html = property(lambda self: render_content(self, self._cache))

def _render_for_fasthtml(self):
    from fasthtml.common import NotStr
    if hasattr(self, 'html'):
        return NotStr(self.html)
    return None

ContentItem.render = _render_for_fasthtml

__all__ = [
    # Main class
    "Pyxie",
    
    # Decorators
    "layout",
    
    # Types
    "ContentBlock",
    "ContentItem",
    "ContentProvider",
    "Metadata",
    "PathLike",
    
    # Errors
    "PyxieError",
    "LayoutError",
    "ContentError",
    "RenderError",
    
    # Rendering functions
    "render_content",
    "render_markdown",
    "render_block",
    "render_blocks",
    
    # Collection
    "Collection",
] 