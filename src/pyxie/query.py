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

"""Query system for filtering and sorting content items.

This module provides a flexible query interface for content items, supporting:
1. Field-based filtering (status="published")
2. Operator-based filtering (date__gte="2024-01-01")
3. Complex queries (tags__contains=["python", "web"])
4. Sorting and pagination
"""

import logging
from typing import Any, List, Optional, Sequence, TypeVar, Generic, Callable, Dict, Union, Tuple, Protocol, Collection
from datetime import datetime
from dataclasses import dataclass
import math

from .types import ContentItem
from .utilities import log

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=ContentItem, covariant=True)

# Type aliases for clarity
FilterFunc = Callable[[T], bool]
ValueFunc = Callable[[T], Any]
SortKeyFunc = Callable[[T], Any]

# Constants
TAGS_FIELD = "tags"
DATE_FORMATS = ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S"]
DEFAULT_PER_PAGE = 20

# Supported comparison operators
COMPARISON_OPERATORS = {
    "gt": lambda a, b: a > b,
    "gte": lambda a, b: a >= b,
    "lt": lambda a, b: a < b,
    "lte": lambda a, b: a <= b,
    "eq": lambda a, b: a == b,
    "ne": lambda a, b: a != b,
}

# Special operators
CONTAINS_OP = "contains"
IN_OP = "in"

@dataclass
class PaginationInfo:
    """Detailed pagination information."""
    current_page: int
    total_pages: int
    total_items: int
    per_page: int
    has_next: bool
    has_previous: bool
    next_page: Optional[int]
    previous_page: Optional[int]
    
    def page_range(self, window: int = 5) -> Sequence[int]:
        """Return page numbers centered around current page."""
        if self.total_pages <= 1:
            return [1] if self.total_pages == 1 else []
            
        half = window // 2
        start = max(1, self.current_page - half)
        end = min(self.total_pages, start + window - 1)
        start = max(1, end - window + 1)  # Adjust start if near end
        return range(start, end + 1)

@dataclass
class QueryResult(Generic[T]):
    """Result of a query operation."""
    items: List[T]
    total: int
    page: int = 1
    per_page: Optional[int] = None
    
    def __iter__(self) -> Any:
        """Make QueryResult iterable over its items."""
        return iter(self.items)
        
    def __len__(self) -> int:
        """Return number of items in current page."""
        return len(self.items)
    
    @property
    def has_next(self) -> bool:
        """Whether there are more pages."""
        return self.per_page and self.per_page > 0 and self.page < self.pages
    
    @property
    def has_prev(self) -> bool:
        """Whether there are previous pages."""
        return self.page > 1
    
    @property
    def pages(self) -> int:
        """Total number of pages."""
        # Early return for invalid pagination parameters
        if not (self.per_page and self.per_page > 0 and self.total > 0):
            return 1
        return math.ceil(self.total / self.per_page)

    @property
    def pagination(self) -> PaginationInfo:
        """Get comprehensive pagination information."""        
        effective_per_page = max(1, self.per_page or len(self.items))
        
        return PaginationInfo(
            current_page=self.page,
            total_pages=self.pages,
            total_items=self.total,
            per_page=effective_per_page,
            has_next=self.has_next,
            has_previous=self.has_prev,
            next_page=self.page + 1 if self.has_next else None,
            previous_page=self.page - 1 if self.has_prev else None
        )

class Paginator:
    """Handles different pagination strategies."""
    
    @staticmethod
    def offset_pagination(items: List[T], offset: int, limit: Optional[int]) -> Tuple[List[T], int, Optional[int]]:
        """Apply offset-based pagination to items."""
        if not offset and limit is None:            
            return items, 1, len(items) if items else DEFAULT_PER_PAGE
            
        start = max(0, offset)
        end = None if limit is None else start + limit
        paginated_items = items[start:end]
        
        page = 1
        per_page = limit  # Use limit as per_page
        if limit is not None and offset:
            per_page = limit
            page = (offset // per_page) + 1
        elif limit is None and offset:            
            per_page = DEFAULT_PER_PAGE
            page = (offset // per_page) + 1
                    
        per_page = per_page if per_page is not None else DEFAULT_PER_PAGE
            
        return paginated_items, page, per_page
    
    @staticmethod
    def cursor_pagination(
        items: List[T], 
        field: str,
        cursor_value: Any = None,
        limit: int = 10,
        direction: str = "forward"
    ) -> List[T]:
        """Paginate items using cursor-based approach."""
        if not field or not items:
            return items[:limit] if limit else items
                
        if cursor_value is None:
            if direction == "backward":
                return items[-limit:] if limit < len(items) else items
            return items[:limit]
        
        get_value = lambda item: getattr(item, field, None) or item.metadata.get(field)
        is_forward = direction == "forward"
        
        if is_forward:
            matches = [item for item in items if 
                      (item_value := get_value(item)) is not None and
                      item_value > cursor_value]
            return matches[:limit]
        else:
            before_cursor = [item for item in items if 
                           (item_value := get_value(item)) is not None and
                           item_value < cursor_value]
            
            return before_cursor[-limit:] if len(before_cursor) > limit else before_cursor

class FilterFactory:
    """Factory for creating filter functions."""
    
    @staticmethod
    def create_filter(field: str, predicate: Callable[[Any, Any], bool], value: Any) -> FilterFunc:
        """Create a filter function with given field and predicate."""
        def filter_fn(item: ContentItem) -> bool:
            item_value = getattr(item, field, None) or item.metadata.get(field)
            if item_value is None:
                return False
                    
            try:
                return predicate(item_value, value)
            except (TypeError, ValueError):
                return False
                
        return filter_fn
    
    @staticmethod
    def create_exact_filter(field: str, value: Any) -> FilterFunc:
        """Create a filter for exact matching."""
        if isinstance(value, (list, tuple, set)):
            return FilterFactory.create_filter(field, lambda item_val, val: item_val in val, value)
        else:
            return FilterFactory.create_filter(field, lambda item_val, val: item_val == val, value)
    
    @staticmethod
    def create_tags_filter(value: Any) -> FilterFunc:
        """Create a specialized filter for tags."""
        def filter_fn(item: ContentItem) -> bool:
            tags = getattr(item, 'tags', None)
            if not tags:  # Handles None and empty sequences
                return False
                
            if isinstance(value, str):
                normalized_value = value.replace("-", " ").lower()
                return any(tag.lower() == normalized_value for tag in tags)
                
            elif isinstance(value, (list, tuple, set)):
                return all(tag in tags for tag in value)
                
            return False
        
        return filter_fn
    
    @staticmethod
    def create_contains_filter(field: str, value: Any) -> FilterFunc:
        """Create a filter for 'contains' operation."""
        if value is None:
            return lambda _: False
            
        if field == TAGS_FIELD:
            return FilterFactory.create_tags_filter(value)
        
        if isinstance(value, (list, tuple, set)):
            return FilterFactory.create_filter(
                field, lambda item_val, val: all(v in item_val for v in val), value
            )
        else:
            return FilterFactory.create_filter(
                field, lambda item_val, val: val in item_val, value
            )
    
    @staticmethod
    def create_in_filter(field: str, value: Any) -> FilterFunc:
        """Create a filter for 'in' operation."""
        try:
            iter(value)
            return FilterFactory.create_filter(field, lambda item_val, val: item_val in val, value)
        except (TypeError, ValueError):
            log(logger, "Query", "warning", "filter", 
                f"Value for 'in' operator must be iterable: {value}")
            return lambda _: False
    
    @staticmethod
    def create_comparison_filter(field: str, op: str, value: Any) -> FilterFunc:
        """Create a filter for comparison operations."""
        if op not in COMPARISON_OPERATORS:
            log(logger, "Query", "warning", "filter", f"Unknown operator: {op}")
            return lambda _: False
            
        try:
            norm_value = normalize_value(value)
            return FilterFactory.create_filter(field, COMPARISON_OPERATORS[op], norm_value)
        except (TypeError, ValueError):
            log(logger, "Query", "warning", "filter", 
                f"Invalid comparison value for {field} {op} {value}")
            return lambda _: False

def normalize_value(value: Any) -> Any:
    """Normalize value for comparison."""
    if isinstance(value, (int, float, datetime, bool)):
        return value
        
    if isinstance(value, str):
        # Try parsing as date
        for fmt in DATE_FORMATS:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        
        # Try parsing as number
        try:
            return float(value)
        except ValueError:
            pass
            
    return value

class Query(Generic[T]):
    """Query builder for content items."""
    
    def __init__(self, items: Sequence[T]):
        """Initialize query with sequence of items."""
        self._items = list(items)
        self._filters: List[FilterFunc] = []
        self._sort_keys: List[Tuple[SortKeyFunc, bool]] = []  # (key_func, reverse)
        self._offset = 0
        self._limit: Optional[int] = None
        # Cursor pagination fields
        self._use_cursor = False
        self._cursor_field: Optional[str] = None
        self._cursor_value: Any = None
        self._cursor_limit: Optional[int] = None
        self._cursor_direction: str = "forward"
    
    def filter(self, **kwargs) -> "Query[T]":
        """Add filters to query."""
        for key, value in kwargs.items():
            if value is None:
                continue
                
            if "__" in key:
                field, op = key.split("__", 1)
                self._add_operator_filter(field, op, value)
            else:
                self._filters.append(FilterFactory.create_exact_filter(key, value))
        return self

    def _add_operator_filter(self, field: str, op: str, value: Any) -> None:
        """Add a filter with an operator."""
        if op == CONTAINS_OP:
            self._filters.append(FilterFactory.create_contains_filter(field, value))
        elif op == IN_OP:
            self._filters.append(FilterFactory.create_in_filter(field, value))
        elif op in COMPARISON_OPERATORS:
            self._filters.append(FilterFactory.create_comparison_filter(field, op, value))
        else:
            log(logger, "Query", "warning", "filter", f"Unknown operator: {op}")
    
    def order_by(self, *fields: str) -> "Query[T]":
        """Add sorting to query."""
        self._sort_keys = []
        
        def make_key_func(field_name):
            return lambda item: getattr(item, field_name, None) or item.metadata.get(field_name)
        
        for field in fields:
            reverse = field.startswith("-")
            actual_field = field[1:] if reverse else field
            self._sort_keys.append((make_key_func(actual_field), reverse))
            
        return self
    
    def offset(self, n: int) -> "Query[T]":
        """Skip first n items."""
        self._offset = max(0, n)
        return self
    
    def limit(self, n: Optional[int]) -> "Query[T]":
        """Limit number of items returned."""
        self._limit = n
        return self
    
    def page(self, page: int, per_page: int) -> "Query[T]":
        """Get specific page of results."""
        page = max(1, page)
        per_page = max(1, per_page)
        self._offset = (page - 1) * per_page
        self._limit = per_page
        return self
    
    def cursor(self, field: str, value: Any = None, limit: int = 10, direction: str = "forward") -> "Query[T]":
        """Set up cursor-based pagination."""
        self._use_cursor = True
        self._cursor_field = field
        self._cursor_value = value
        self._cursor_limit = max(1, limit) if limit is not None else None
        self._cursor_direction = direction if direction in ("forward", "backward") else "forward"
        return self
    
    def _apply_filters(self, items: List[T]) -> List[T]:
        """Apply filters to items and return filtered items."""
        if not self._filters:
            return items
        return [item for item in items if all(f(item) for f in self._filters)]
        
    def _apply_sorting(self, items: List[T]) -> List[T]:
        """Apply sorting to items and return sorted items."""
        if not self._sort_keys:
            return items
                
        result = items.copy()    
        for key_func, reverse in reversed(self._sort_keys):
            result = sorted(result, key=key_func, reverse=reverse)
            
        return result
    
    def execute(self) -> QueryResult[T]:
        """Execute query and return results."""
        filtered_items = self._apply_filters(self._items)
        total = len(filtered_items)
        
        sorted_items = self._apply_sorting(filtered_items)
        
        if self._use_cursor:
            paginated_items = Paginator.cursor_pagination(
                sorted_items,
                self._cursor_field,
                self._cursor_value,
                self._cursor_limit,
                self._cursor_direction
            )
            page = 1
            per_page = self._cursor_limit
        else:
            paginated_items, page, per_page = Paginator.offset_pagination(
                sorted_items, 
                self._offset, 
                self._limit
            )            
        if per_page is None:
            if self._limit:
                per_page = self._limit
            elif len(paginated_items) > 0:
                per_page = len(paginated_items)
            else:
                per_page = DEFAULT_PER_PAGE
                
        return QueryResult(
            items=paginated_items,
            total=total,
            page=page,
            per_page=per_page
        ) 