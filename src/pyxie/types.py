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

from .utilities import log
from .constants import DEFAULT_METADATA

logger = logging.getLogger(__name__)

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
    content_type: Optional[str] = None

    def __post_init__(self):
        """Initialize default values."""
        if self.params is None:
            self.params = {}

@dataclass
class MarkdownDocument:
    """Represents a parsed markdown document with its content blocks."""
    metadata: Dict[str, Any]
    raw_content: str
    html: Optional[str] = None
    
    # Content blocks organized by type
    fasthtml_blocks: List[ContentBlock] = field(default_factory=list)
    script_blocks: List[ContentBlock] = field(default_factory=list)
    content_blocks: Dict[str, List[ContentBlock]] = field(default_factory=dict)
    
    def get_block(self, block_type: str, index: Optional[int] = None) -> Optional[ContentBlock]:
        """Get a content block by type and optional index."""
        blocks = self.content_blocks.get(block_type, [])
        return blocks[index or 0] if blocks and (index is None or 0 <= index < len(blocks)) else None
    
    def get_blocks(self, block_type: str) -> List[ContentBlock]:
        """Get all blocks of a given type."""
        return self.content_blocks.get(block_type, [])

@dataclass
class ContentItem:
    """A content item with metadata and blocks."""
    source_path: Path
    metadata: Dict[str, Any]
    blocks: Dict[str, List[ContentBlock]]
    collection: Optional[str] = None
    
    @property
    def slug(self) -> str:
        """Get the slug from metadata or source path."""
        return self.metadata.get("slug", self.source_path.stem)

    @property
    def content(self) -> str:
        """Get the raw content from the first content block."""
        content_blocks = self.blocks.get("content", [])
        if not content_blocks:
            return ""
        return content_blocks[0].content

    def __post_init__(self):
        """Initialize metadata and content."""
        if not self.metadata:
            self.metadata = {}
            
        # Set title from slug if not present
        if "title" not in self.metadata and self.slug:
            self.metadata["title"] = self.slug.replace("-", " ").title()
            
        # Add metadata keys as attributes for easy access, skipping properties
        for key, value in self.metadata.items():
            if not hasattr(self.__class__, key) or not isinstance(getattr(self.__class__, key), property):
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
            "metadata": self.metadata,
            "blocks": {
                name: [block.__dict__ for block in blocks]
                for name, blocks in self.blocks.items()
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContentItem":
        """Create from dictionary."""
        item = cls(
            source_path=Path(data["source_path"]),
            metadata=data["metadata"],
            blocks={}
        )
        
        for name, block_list in data.get("blocks", {}).items():
            item.blocks[name] = [
                ContentBlock(**block_data)
                for block_data in block_list
            ]
        
        return item
