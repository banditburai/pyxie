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
from enum import Enum, auto
from typing import Dict, Any, TypedDict, Protocol, Union, NotRequired, Optional, List, Literal
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime

from .utilities import log
from .constants import (
    ContentType, VALID_CONTENT_TYPES, RequiredMetadata,
    DEFAULT_METADATA, COMMON_DATE_FORMATS
)

logger = logging.getLogger(__name__)

PathLike = Union[str, Path]
MetadataDict = Dict[str, Any]

class LayoutProvider(Protocol):
    """Protocol for layout providers."""
    def get_layout(self, name: str) -> Any: ...
    def register_layout(self, name: str, layout: Any) -> None: ...

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
    """A block of content with specific type and parameters."""
    name: str
    content: str
    content_type: ContentType = "markdown"
    params: Dict[str, Any] = field(default_factory=dict)
    index: int = 0

    def __post_init__(self):
        """Validate and normalize content type."""
        if self.content_type not in VALID_CONTENT_TYPES:
            log(logger, "Types", "warning", "content_type", 
                f"Invalid content type '{self.content_type}', defaulting to 'markdown'")
            self.content_type = "markdown"

@dataclass
class ContentItem:
    """A content item with flexible metadata and content handling.
    
    All frontmatter key-value pairs are stored in metadata and accessible
    as attributes. For example, if frontmatter has {"author": "John"},
    you can access it as:
        item.metadata["author"] or item.author
    """
    slug: str
    content: str
    source_path: Path
    content_type: ContentType = "markdown"
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    collection: Optional[str] = None
    
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    index: int = field(default=0)  # New field for unique indexing
        
    blocks: Dict[str, List[ContentBlock]] = field(default_factory=dict)        
    _cache: Any = field(default=None, repr=False)    
    _pyxie: Any = field(default=None, repr=False)

    def __post_init__(self):
        """Add metadata keys as attributes for easy access."""
        if "title" not in self.metadata:
            self.metadata["title"] = self.slug.replace("-", " ").title()
            
        if "status" not in self.metadata:
            self.metadata["status"] = "draft"
    
    def __getattr__(self, name: str) -> Any:
        """Allow accessing metadata as attributes."""
        if name in self.metadata:
            return self.metadata[name]
        raise AttributeError(f"'ContentItem' has no attribute '{name}'")
    
    @property
    def title(self) -> str:
        """Get item title."""
        return self.metadata["title"]
    
    @property
    def status(self) -> str:
        """Get content status."""
        return self.metadata["status"]
    
    @property
    def tags(self) -> List[str]:
        """Get normalized list of tags."""
        raw_tags = self.metadata.get("tags", [])
        from .utilities import normalize_tags
        return normalize_tags(raw_tags)
    
    @property
    def image(self) -> Optional[str]:
        """Get image URL, using template if available."""        
        if image := self.metadata.get("image"):
            return image                    
        if template := self.metadata.get("image_template"):
            try:
                format_params = {"index": self.index, "slug": self.slug}
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
            "content_type": self.content_type,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "index": self.index,  # Include index in serialization
            "blocks": {
                name: [block.__dict__ for block in blocks]
                for name, blocks in self.blocks.items()
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContentItem":
        """Create from dictionary."""
        item = cls(
            metadata=data["metadata"],
            content=data["content"],
            slug=data["slug"],
            source_path=Path(data["source_path"]),
            content_type=data.get("content_type", "markdown"),
            collection=data.get("collection"),
            index=data.get("index", 0)
        )
        
        for name, block_list in data.get("blocks", {}).items():
            item.blocks[name] = [
                ContentBlock(**block_data)
                for block_data in block_list
            ]
        
        return item

class ContentProvider(Protocol):
    """Protocol for content providers."""
    def get_blocks(self, name: str) -> List[ContentBlock]: ...
    def get_block(self, name: str, index: int = 0) -> Optional[ContentBlock]: ...