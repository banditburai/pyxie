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

from .constants import DEFAULT_METADATA

logger = logging.getLogger(__name__)

@dataclass
class ContentItem:
    """A content item with metadata and content."""
    source_path: Path
    metadata: Dict[str, Any]
    content: str
    collection: Optional[str] = None
    
    # Protected property names that shouldn't be overwritten by metadata
    PROTECTED_PROPERTIES = {
        'source_path', 'metadata', 'content', 'collection',
        'slug', 'status', 'title', 'tags', 'image',
        'html', 'render'
    }
    
    @property
    def slug(self) -> str:
        """Get the slug from metadata or source path."""
        return self.metadata.get("slug", self.source_path.stem)

    def __post_init__(self):
        """Initialize metadata."""
        if not self.metadata:
            self.metadata = {}
            
        # Set title from slug if not present
        if "title" not in self.metadata and self.slug:
            self.metadata["title"] = self.slug.replace("-", " ").title()
            
        # Add metadata keys as attributes for easy access
        for key, value in self.metadata.items():
            if key not in self.PROTECTED_PROPERTIES:
                setattr(self, key, value)
            
    @property
    def status(self) -> Optional[str]:
        """Get content status."""
        return self.metadata.get("status")
    
    @property
    def title(self) -> str:
        """Get item title."""
        return self.metadata["title"]
    
    @property
    def tags(self) -> List[str]:
        """Get normalized list of tags."""
        from .utilities import normalize_tags
        raw_tags = self.metadata.get("tags", [])
        return normalize_tags(raw_tags)
    
    @property
    def image(self) -> Optional[str]:
        """Get image URL, using template if available."""
        from .utilities import log
        
        if image := self.metadata.get("image"):
            return image                    
        if template := self.metadata.get("image_template"):
            try:
                format_params = {"index": self.metadata.get("index"), "slug": self.slug}
                format_params.update({
                    key: self.metadata[f"image_{key}"]
                    for key in ["width", "height", "seed", "size", "color", "format"]
                    if f"image_{key}" in self.metadata
                })
                
                if 'seed' not in format_params and '{seed}' in template:
                    format_params['seed'] = self.slug.replace("-", "")
                
                return template.format(**format_params)
            except (KeyError, ValueError) as e:
                log(logger, "Types", "warning", "image", f"Failed to format template: {e}")
                
        return DEFAULT_METADATA["image_template"].format(
            seed=self.slug,
            width=DEFAULT_METADATA["image_width"],
            height=DEFAULT_METADATA["image_height"]
        ) if self.slug else None
    
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
    """Result of rendering a block."""
    content: str = ""
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        """Check if render was successful."""
        return self.error is None

class Metadata(TypedDict, total=False):
    """Common metadata fields."""
    title: str
    layout: str
    date: str
    tags: List[str]
    author: str
    description: str

@dataclass
class ContentBlock:
    """A content block in a markdown document."""
    tag_name: str
    content: str
    attrs_str: str
    marker: Optional[str] = None
    params: Dict[str, Any] = None    

    def __post_init__(self):
        """Initialize default values."""
        if self.params is None:
            self.params = {}
