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

"""Main Pyxie class for content management and rendering."""

import logging
from pathlib import Path
from typing import Dict, Optional, Any, Tuple, List, Union

from .constants import DEFAULT_METADATA
from .types import ContentItem, PathLike
from .query import Query, QueryResult
from .cache import Cache
from .utilities import log, load_content_file, normalize_tags
from .collection import Collection

logger = logging.getLogger(__name__)

def apply_pagination(query: Query, page: Optional[int], per_page: Optional[int], 
                   offset: Optional[int], limit: Optional[int]) -> Query:
    """Apply pagination parameters to a query."""
    # Page-based pagination takes precedence
    if page is not None and per_page is not None:
        return query.page(page, per_page)
    
    # Apply offset and limit using function composition
    return (query.offset(offset) if offset else query).limit(limit) if limit else query

class Pyxie:
    """Main class for content management and rendering."""
    
    def __init__(
        self,
        content_dir: Optional[PathLike] = None,
        *,
        default_metadata: Optional[Dict[str, Any]] = None,
        cache_dir: Optional[PathLike] = None,
        default_layout: str = "default"
    ):
        """Initialize Pyxie content manager."""
        self.content_dir = Path(content_dir) if content_dir else None
        self.default_metadata = {
            **DEFAULT_METADATA,
            "layout": default_layout,
            **(default_metadata or {})
        }
        self.cache = Cache(cache_dir) if cache_dir else None
        
        # Collections
        self._collections: Dict[str, Collection] = {}
        self._items: Dict[str, ContentItem] = {}
        
        # Initialize if content directory provided
        if self.content_dir:
            self.add_collection("content", self.content_dir)
    
    @property
    def collections(self) -> List[str]:
        """Get list of collection names."""
        return list(self._collections.keys())
    
    @property
    def item_count(self) -> int:
        """Get total number of items."""
        return len(self._items)
    
    @property
    def collection_stats(self) -> Dict[str, int]:
        """Get item count per collection."""
        return {name: len(collection._items) for name, collection in self._collections.items()}
    
    def add_collection(
        self,
        name: str,
        path: PathLike,
        *,
        default_layout: str = "default",
        default_metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add a content collection."""
        path = Path(path)
        if not path.exists():
            path.mkdir(parents=True)
            
        collection = Collection(
            name=name,
            path=path,
            default_layout=default_layout,
            default_metadata={
                **self.default_metadata,
                **(default_metadata or {}),
                "collection": name
            }
        )
        
        self._collections[name] = collection
        self._load_collection(collection)
    
    def _process_content_item(self, item: ContentItem, index: int, collection: 'Collection') -> None:
        """Process and store a content item."""
        if not item:
            return
            
        # Set cache if available
        if self.cache:
            item._cache = self.cache
            
        # Set index
        item.index = index
        
        # Store in collection
        collection._items[item.slug] = item
        self._items[item.slug] = item
    
    def _load_collection(self, collection: Collection) -> None:
        """Load content items from collection."""
        next_index = len(self._items)
        
        for path in collection.path.glob("**/*.md"):
            item = load_content_file(path, collection.default_metadata, logger)
            if item:
                self._process_content_item(item, next_index, collection)
                next_index += 1
    
    def _get_collection_items(self, collection: Optional[str]) -> List[ContentItem]:
        """Get items from a specific collection or all items."""
        if collection:
            if collection not in self._collections:
                return []
            return list(self._collections[collection]._items.values())
        return list(self._items.values())
    
    def _apply_filters(self, query: Query, filters: Dict[str, Any]) -> Query:
        """Apply filters to a query."""
        return query.filter(**filters) if filters else query
    
    def _apply_sorting(self, query: Query, order: Any) -> Query:
        """Apply sorting to a query."""
        if not order:
            return query
        order_fields = [order] if isinstance(order, str) else order
        return query.order_by(*order_fields)
    
    def get_items(
        self,
        collection: Optional[str] = None,
        **filters: Any
    ) -> QueryResult[ContentItem]:
        """Get filtered content items."""
        # Get items from collection or all items
        items = self._get_collection_items(collection)
        if not items:
            return QueryResult(items=[], total=0)
            
        # Extract special parameters
        order = filters.pop("order_by", None)
        limit = filters.pop("limit", None)
        offset = filters.pop("offset", None)
        page = filters.pop("page", None)
        per_page = filters.pop("per_page", None)
        
        # Build query
        query = Query(items)
        query = self._apply_filters(query, filters)
        query = self._apply_sorting(query, order)
        query = apply_pagination(query, page, per_page, offset, limit)
                
        return query.execute()
    
    def get_item(
        self,
        slug: str,
        collection: Optional[str] = None,
        *,
        status: Optional[str] = "published"
    ) -> Tuple[Optional[ContentItem], Optional[Tuple[str, str]]]:
        """Get single content item by slug."""
        # Find item
        if collection:
            if collection not in self._collections:
                return None, ("Collection Not Found", f"Collection '{collection}' does not exist")
            
            item = self._collections[collection]._items.get(slug)
        else:
            item = self._items.get(slug)
            
        # Check if found
        if not item:
            return None, ("Post Not Found", f"Sorry, we couldn't find a post matching '{slug}'")
            
        # Check status if specified
        if status and item.metadata.get("status") != status:
            return None, ("Post Not Available", f"This post does not have status '{status}'")
                
        return item, None
    
    def get_tags(self, collection: Optional[str] = None) -> Dict[str, int]:
        """Get tag usage counts."""
        items = self._get_collection_items(collection)
        
        # Count tags using Counter
        from collections import Counter
        tag_counter = Counter()
        for item in items:
            tag_counter.update(item.tags)
                
        # Sort by count (desc) then name (asc)
        return {tag: count for tag, count in sorted(
            tag_counter.items(), key=lambda x: (-x[1], x[0])
        )}
    
    def get_all_tags(self, collection: Optional[str] = None) -> List[str]:
        """Get a simple list of all unique tags."""       
        return list(self.get_tags(collection).keys())
    
    def invalidate_cache(
        self,
        collection: Optional[str] = None,
        slug: Optional[str] = None
    ) -> None:
        """Invalidate cache for specific items or collections."""
        if not self.cache:
            return
            
        try:
            if collection and slug:
                # Invalidate specific item
                item = self._items.get(slug)
                if item and item.source_path:
                    self.cache.invalidate(collection, item.source_path)
            elif collection:
                # Invalidate entire collection
                self.cache.invalidate(collection)
            else:
                # Invalidate everything
                self.cache.invalidate()
        except Exception as e:
            log(logger, "Pyxie", "error", "cache", f"Failed to invalidate cache: {e}")
    
    def get_raw_content(self, slug: str, **kwargs) -> Optional[str]:
        """Get raw markdown content for a post by slug."""
        if not (item := self.get_item(slug, **kwargs)[0]) or not item.source_path:
            return None
            
        try:
            return item.source_path.read_text()
        except Exception:
            return None
    
    def serve_md(self):
        """Returns middleware for serving raw markdown files at the same routes with .md extension."""
        from starlette.middleware.base import BaseHTTPMiddleware
        from starlette.middleware import Middleware
        from starlette.responses import Response
        
        pyxie_instance = self
        
        class MarkdownMiddleware(BaseHTTPMiddleware):
            def __init__(self, app):
                super().__init__(app)
                self.pyxie = pyxie_instance
                
            async def dispatch(self, request, call_next):
                if not request.url.path.endswith('.md'):
                    return await call_next(request)
                    
                path_parts = request.url.path[:-3].split('/')
                if not path_parts:
                    return await call_next(request)
                
                slug = path_parts[-1]
                if raw_content := self.pyxie.get_raw_content(slug):
                    return Response(content=raw_content, media_type="text/markdown")
                
                return await call_next(request)
        
        return Middleware(MarkdownMiddleware)        