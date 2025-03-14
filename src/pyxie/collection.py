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

"""Handle collections of content files."""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any, Iterator

from .types import ContentItem, PathLike
from .utilities import log, load_content_file
from .errors import CollectionError

logger = logging.getLogger(__name__)

@dataclass
class Collection:
    """A collection of content files.
    
    Attributes:
        name: Collection name
        path: Path to content files
        default_layout: Default layout for items in this collection
        default_metadata: Default metadata for items in this collection
        _items: Internal storage for content items
    """
    name: str
    path: PathLike
    default_layout: str = "default"
    default_metadata: Dict[str, Any] = field(default_factory=dict)
    _items: Dict[str, ContentItem] = field(default_factory=dict, init=False)
    
    def __post_init__(self) -> None:
        """Convert path to Path object after initialization."""
        self.path = Path(self.path)
        
    def __iter__(self) -> Iterator[ContentItem]:
        """Iterate over all items in collection."""
        return iter(self._items.values())
        
    def __len__(self) -> int:
        """Get number of items in collection."""
        return len(self._items)
        
    def __contains__(self, slug: str) -> bool:
        """Check if collection contains an item."""
        return slug in self._items
    
    def load(self) -> None:
        """Load content files from disk."""
        try:
            # Create directory if it doesn't exist
            self.path.mkdir(parents=True, exist_ok=True)
            
            # Load all markdown files
            for file in self.path.glob("*.md"):
                try:
                    self._load_file(file)
                except Exception as e:
                    log(logger, "Collection", "error", "load", f"Failed to load {file}: {e}")
                    continue
            
            log(logger, "Collection", "info", "load", f"Loaded {len(self)} items from collection '{self.name}'")
            
        except Exception as e:
            raise CollectionError(f"Failed to load collection '{self.name}': {e}") from e
    
    def _load_file(self, file: Path) -> None:
        """Load a single content file.
        
        Args:
            file: Path to markdown file
        """
        # Add default_layout to default_metadata if not already present
        metadata = self.default_metadata.copy()
        if "layout" not in metadata:
            metadata["layout"] = self.default_layout
            
        item = load_content_file(file, metadata, logger)
        if item:
            self._items[item.slug] = item
    
    def get_item(self, slug: str) -> Optional[ContentItem]:
        """Get an item by slug."""
        return self._items.get(slug)
    
    def get_items(
        self,
        *,
        limit: Optional[int] = None,
        order_by: Optional[str] = None,
        **filters: Any
    ) -> List[ContentItem]:
        """Get items with optional filtering and sorting.
        
        Args:
            limit: Maximum number of items to return
            order_by: Metadata field to sort by (prefix with - for reverse)
            **filters: Metadata fields to filter by
            
        Returns:
            List of matching items
        """
        # Filter items
        items = [
            item for item in self
            if all(item.metadata.get(k) == v for k, v in filters.items())
        ]
        
        # Sort items
        if order_by:
            reverse = order_by.startswith("-")
            field = order_by[1:] if reverse else order_by
            items.sort(
                key=lambda x: x.metadata.get(field, ""),
                reverse=reverse
            )
        
        # Apply limit
        return items[:limit] if limit is not None else items 