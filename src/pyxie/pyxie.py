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
from typing import Dict, Optional, Any, Tuple, List, TypeVar, cast
from collections import Counter
import importlib.util
import inspect

from .constants import DEFAULT_METADATA
from .types import ContentItem, PathLike
from .query import Query, QueryResult
from .cache import Cache
from .utilities import log, load_content_file, resolve_default_layout
from .collection import Collection
from .layouts import registry

logger = logging.getLogger(__name__)

# Constants
DEFAULT_PER_PAGE = 20
DEFAULT_CURSOR_LIMIT = 10

Q = TypeVar('Q', bound=Query)

class Pyxie:
    """Main class for content management and rendering."""
    
    def __init__(
        self,
        content_dir: Optional[PathLike] = None,
        *,
        default_metadata: Optional[Dict[str, Any]] = None,
        cache_dir: Optional[PathLike] = None,
        default_layout: str = "default",
        auto_discover_layouts: bool = True,
        layout_paths: Optional[List[PathLike]] = None
    ):
        """Initialize Pyxie content manager."""
        self.content_dir = Path(content_dir) if content_dir else None
        self.default_metadata = {**DEFAULT_METADATA, **(default_metadata or {})}
        
        # Resolve default layout using helper
        self.default_layout = resolve_default_layout(
            default_layout=default_layout,
            metadata=self.default_metadata,
            component_name="Pyxie",
            logger=logger
        )
        
        self.cache = Cache(cache_dir) if cache_dir else None
        self._collections: Dict[str, Collection] = {}
        self._items: Dict[str, ContentItem] = {}
        self.watcher = None
        
        if self.content_dir:
            self.add_collection("content", self.content_dir)                    
        if auto_discover_layouts:
            registry.discover_layouts(self.content_dir, layout_paths)
    
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
        default_layout: Optional[str] = None,
        default_metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add a content collection."""
        path = Path(path)
        if not path.exists():
            path.mkdir(parents=True)
            
        collection = Collection(
            name=name,
            path=path,
            default_layout=default_layout or self.default_layout,
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
        if self.cache:
            item._cache = self.cache            
        item.index = index
        item._pyxie = self      
        collection._items[item.slug] = item
        self._items[item.slug] = item
    
    def _load_collection(self, collection: Collection) -> None:
        """Load content items from collection."""
        next_index = len(self._items)
        
        for path in collection.path.glob("**/*.md"):
            if item := load_content_file(path, collection.default_metadata, logger):
                self._process_content_item(item, next_index, collection)
                next_index += 1
    
    def _get_collection_items(self, collection: Optional[str]) -> List[ContentItem]:
        """Get items from a specific collection or all items."""
        if not collection:
            return list(self._items.values())
        collection_obj = self._collections.get(collection)
        if not collection_obj:
            return []
            
        return list(collection_obj._items.values())
    
    def _apply_filters(self, query: Q, filters: Dict[str, Any]) -> Q:
        """Apply filters to a query."""
        return query.filter(**filters) if filters else query
    
    def _apply_sorting(self, query: Q, order: Any) -> Q:
        """Apply sorting to a query."""
        if not order:
            return query
            
        order_fields = [order] if isinstance(order, str) else order
        return query.order_by(*order_fields)
    
    @staticmethod
    def _cursor_pagination(
        query: Q, 
        cursor_field: str, 
        cursor_value: Any, 
        limit: Optional[int], 
        direction: str = "forward"
    ) -> Q:
        """Apply cursor-based pagination."""
        return query.cursor(
            cursor_field,
            cursor_value,
            limit or DEFAULT_CURSOR_LIMIT,
            direction
        )
        
    @staticmethod
    def _offset_pagination(
        query: Q, 
        page: Optional[int], 
        per_page: Optional[int], 
        offset: Optional[int], 
        limit: Optional[int]
    ) -> Q:
        """Apply offset-based pagination."""
        if page is not None:
            return query.page(page, per_page or DEFAULT_PER_PAGE)
        return query.offset(offset or 0).limit(limit) if offset or limit else query
    
    def get_items(
        self,
        collection: Optional[str] = None,
        **filters: Any
    ) -> QueryResult[ContentItem]:
        """Get filtered content items."""
        items = self._get_collection_items(collection)
        if not items:
            return QueryResult(items=[], total=0)
            
        order = filters.pop("order_by", None)
        limit = filters.pop("limit", None)
        offset = filters.pop("offset", None)
        page = max(1, int(page)) if (page := filters.pop("page", None)) is not None else None
        per_page = max(1, int(per_page)) if (per_page := filters.pop("per_page", None)) is not None else None
        
        cursor_field = filters.pop("cursor_field", None)
        cursor_value = filters.pop("cursor_value", None)
        cursor_limit = filters.pop("cursor_limit", None) or limit
        cursor_direction = filters.pop("cursor_direction", "forward")
        
        query = cast(Query, self._apply_sorting(self._apply_filters(Query(items), filters), order))
        
        if cursor_field:
            query = self._cursor_pagination(query, cursor_field, cursor_value, cursor_limit, cursor_direction)
        else:
            query = self._offset_pagination(query, page, per_page, offset, limit)
                
        return query.execute()
    
    def get_item(
        self,
        slug: str,
        **kwargs
    ) -> Tuple[Optional[ContentItem], Optional[Tuple[str, str]]]:
        """Get a single content item by slug.
        
        Args:
            slug: The slug to get content for
            **kwargs: Additional arguments passed to get_items
            
        Returns:
            A tuple of (item, error) where error is None if successful
        """
        # Check if we have a watcher enabled
        if self.watcher:
            self.watcher.check()
            
        # Get all items matching the slug
        items = self.get_items(slug=slug, **kwargs).items
        if not items:
            return None, ("Post Not Found", f"No post found with slug '{slug}'")
            
        return items[0], None
    
    def get_tags(self, collection: Optional[str] = None) -> Dict[str, int]:
        """Get tag usage counts."""
        items = self._get_collection_items(collection)
        
        tag_counter = Counter()
        for item in items:
            tag_counter.update(item.tags)
                
        return {tag: count for tag, count in sorted(
            tag_counter.items(), key=lambda x: (-x[1], x[0])
        )}
    
    def get_all_tags(self, collection: Optional[str] = None) -> List[str]:
        """Get a simple list of all unique tags."""
        return list(self.get_tags(collection))
    
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
                if item := self._items.get(slug):
                    if item.source_path:
                        self.cache.invalidate(collection, item.source_path)
            elif collection:                
                self.cache.invalidate(collection)
            else:
                self.cache.invalidate()
        except (IOError, OSError) as e:
            log(logger, "Pyxie", "error", "cache", f"Failed to invalidate cache: {e}")
    
    def get_raw_content(self, slug: str, **kwargs) -> Optional[str]:
        """Get raw markdown content for a post by slug."""
        item_result = self.get_item(slug, **kwargs)
        if not (item := item_result[0]) or not item.source_path:
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

    def rebuild_content(self) -> None:
        """Rebuild all content collections."""
        # Clear existing items
        self._items.clear()
        
        # Reload all collections
        for collection in self._collections.values():
            self._load_collection(collection)
            
        # Invalidate cache if it exists
        if self.cache:
            self.cache.invalidate()        