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
from .utilities import log, load_content_file, resolve_default_layout
from .errors import CollectionError

logger = logging.getLogger(__name__)

class Collection:
    """Content collection.
    
    A collection is a logical grouping of content items with common default settings.
    """
    
    def __init__(
        self, 
        name: str, 
        path: PathLike, 
        default_layout: str = "default", 
        default_metadata: Optional[Dict[str, Any]] = None
    ):
        """Initialize a collection.
        
        Args:
            name: Name of collection
            path: Path to content directory
            default_layout: Default layout to use for content items
            default_metadata: Default metadata values
        """
        self.name = name
        self.path = Path(path)
        self.default_metadata = default_metadata or {}
        
        # Resolve default layout using helper
        self.default_layout = resolve_default_layout(
            default_layout=default_layout,
            metadata=self.default_metadata,
            component_name=f"Collection '{name}'",
            logger=logger
        )
        
        self._items: Dict[str, ContentItem] = {}
        
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
            self.path.mkdir(parents=True, exist_ok=True)            
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
        metadata = {**self.default_metadata, "layout": self.default_layout}
        
        if item := load_content_file(file, metadata, logger):
            item.collection = self.name
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
        items = [
            item for item in self
            if all(item.metadata.get(k) == v for k, v in filters.items())
        ]
        
        if order_by:
            reverse = order_by.startswith("-")
            field = order_by[1:] if reverse else order_by
            items.sort(
                key=lambda x: x.metadata.get(field, ""),
                reverse=reverse
            )
        
        return items[:limit] if limit is not None else items 