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

"""Shared type definitions for Pyxie."""

import logging
from typing import Dict, Any, TypedDict, Union, Optional, List
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime

from .constants import DEFAULT_METADATA
from .errors import log

logger = logging.getLogger(__name__)

@dataclass
class ContentItem:
    """A content item with flexible metadata and content handling.
    
    All frontmatter key-value pairs are stored in metadata and accessible
    as attributes. For example, if frontmatter has {"author": "John"},
    you can access it as:
        item.metadata["author"] or item.author
    """
    source_path: Path
    metadata: Dict[str, Any] = field(default_factory=dict)
    content: str = ""  # Raw content string
    
    collection: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    index: int = field(default=0)  # New field for unique indexing
            
    _cache: Any = field(default=None, repr=False)    
    _pyxie: Any = field(default=None, repr=False)
    
    # Optional fields that can be derived
    _slug: Optional[str] = field(default=None, repr=False)

    def __post_init__(self):
        """Add metadata keys as attributes for easy access."""
        # Ensure source_path is a Path object
        if not isinstance(self.source_path, Path):
            self.source_path = Path(str(self.source_path))
            
        if "title" not in self.metadata and "slug" not in self.metadata:
            # Get the stem from source_path (now guaranteed to be a Path)
            title = self.source_path.stem
            # Replace both hyphens and underscores with spaces
            title = title.replace("-", " ").replace("_", " ")
            self.metadata["title"] = title.title()
    
    def __getattr__(self, name: str) -> Any:
        """Allow accessing metadata as attributes."""
        if name in self.metadata:
            return self.metadata[name]
        raise AttributeError(f"'ContentItem' has no attribute '{name}'")
    
    @property
    def slug(self) -> str:
        """Get the slug from metadata, explicit value, or source path."""
        if self._slug is not None:
            return self._slug
        return self.metadata.get("slug", self.source_path.stem)
    
    @slug.setter
    def slug(self, value: str) -> None:
        """Set the slug value."""
        self._slug = value
    
    @property
    def title(self) -> str:
        """Get item title from metadata or fall back to slug."""
        if "title" in self.metadata:
            return self.metadata["title"]
        return self.slug.replace("-", " ").title()
    
    @property
    def status(self) -> Optional[str]:
        """Get content status."""
        return self.metadata.get("status")
    
    @property
    def tags(self) -> List[str]:
        """Get normalized list of tags."""
        raw_tags = self.metadata.get("tags", [])
        from .utilities import normalize_tags
        return normalize_tags(raw_tags)
    
    def _generate_image_seed(self) -> str:
        """Generate a unique seed for image generation.
        
        Combines the content index and slug to ensure uniqueness across posts.
        The index ensures uniqueness even if slugs are similar, while the slug
        ensures consistent image generation for the same post.
        """
        # Remove special characters from slug to make it more URL-friendly
        clean_slug = self.slug.replace("-", "").replace("_", "")        
        return f"{self.index:04d}-{clean_slug}"
    
    @property
    def image(self) -> Optional[str]:
        """Get image URL, using template if available."""        
        if image := self.metadata.get("image"):
            return image
        if featured_image := self.metadata.get("featured_image"):
            return featured_image
        # Fall back to template if available
        if template := self.metadata.get("image_template"):
            try:
                format_params = {
                    "index": self.index,
                    "slug": self.slug,
                    "seed": self._generate_image_seed()
                }
                format_params.update({
                    key: self.metadata[f"image_{key}"]
                    for key in ["width", "height", "size", "color", "format"]
                    if f"image_{key}" in self.metadata
                })
                return template.format(**format_params)
            except Exception as e:
                log(logger, "ContentItem", "error", "image", f"Failed to format image URL: {e}")
                return None
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "slug": self.slug,
            "content": self.content,
            "source_path": str(self.source_path),
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContentItem":
        """Create from dictionary."""
        return cls(
            source_path=Path(data["source_path"]),
            metadata=data["metadata"],
            content=data["content"]
        )

PathLike = Union[str, Path]

@dataclass
class RenderResult:
    """Result of rendering content."""
    content: str = ""
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        """Return True if there is no error."""
        return self.error is None and not 'class="error"' in self.content

class Metadata(TypedDict, total=False):
    """Common metadata fields."""
    title: str
    layout: str
    date: str
    tags: List[str]
    author: str
    description: str