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
from typing import Any, List, Optional, Sequence, TypeVar, Generic, Callable, Dict, Union, Tuple
from datetime import datetime
from operator import attrgetter
from dataclasses import dataclass

from .types import ContentItem
from .utilities import log

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=ContentItem)

# Type aliases for clarity
FilterFunc = Callable[[T], bool]
ValueFunc = Callable[[T], Any]
PredicateFunc = Callable[[Any, Any], bool]

# Constants
TAGS_FIELD = "tags"
DATE_FORMATS = ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S"]

# Supported comparison operators
COMPARISON_OPERATORS = {
    "gt": lambda a, b: a > b,
    "gte": lambda a, b: a >= b,
    "lt": lambda a, b: a < b,
    "lte": lambda a, b: a <= b,
    "eq": lambda a, b: a == b,
    "ne": lambda a, b: a != b,
}

# Special operators and their handlers
CONTAINS_OP = "contains"
IN_OP = "in"

@dataclass
class QueryResult(Generic[T]):
    """Result of a query operation."""
    items: List[T]
    total: int
    page: int = 1
    per_page: Optional[int] = None
    
    def __iter__(self):
        """Make QueryResult iterable over its items."""
        return iter(self.items)
        
    def __len__(self):
        """Return number of items in current page."""
        return len(self.items)
    
    @property
    def has_next(self) -> bool:
        """Whether there are more pages."""
        if not self.per_page:
            return False
        return self.total > self.page * self.per_page
    
    @property
    def has_prev(self) -> bool:
        """Whether there are previous pages."""
        return self.page > 1
    
    @property
    def pages(self) -> int:
        """Total number of pages."""
        if not self.per_page:
            return 1
        return (self.total + self.per_page - 1) // self.per_page

def get_item_value(item: ContentItem, field: str) -> Any:
    """Get value from item attribute or metadata."""
    if hasattr(item, field):
        return getattr(item, field)
    return item.metadata.get(field)

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
        self._order_by: List[ValueFunc] = []
        self._reverse = False
        self._offset = 0
        self._limit: Optional[int] = None
    
    def filter(self, **kwargs) -> "Query[T]":
        """Add filters to query."""
        for key, value in kwargs.items():
            if op_parts := key.split("__", 1) if "__" in key else None:
                field, op = op_parts
                self._add_operator_filter(field, op, value)
            else:
                self._add_exact_filter(key, value)
        return self
    
    def _create_filter(self, field: str, predicate: PredicateFunc, value: Any) -> FilterFunc:
        """Create a filter function with given field and predicate."""
        def filter_fn(item: T) -> bool:
            item_value = get_item_value(item, field)
            if item_value is None:
                return False
                
            try:
                return predicate(item_value, value)
            except (TypeError, ValueError):
                return False
                
        return filter_fn
    
    def _add_exact_filter(self, field: str, value: Any) -> None:
        """Add exact match filter."""
        if isinstance(value, (list, tuple, set)):
            # Value is a collection - check if item's value is in this collection
            predicate = lambda item_val, val: item_val in val
        else:
            # Simple equality check
            predicate = lambda item_val, val: item_val == val
            
        self._filters.append(self._create_filter(field, predicate, value))
    
    def _create_iterable_predicate(self, all_match: bool = False) -> PredicateFunc:
        """Create a predicate for working with iterables."""
        if all_match:
            return lambda item_val, val: all(v in item_val for v in val)
        return lambda item_val, val: val in item_val

    def _add_operator_filter(self, field: str, op: str, value: Any) -> None:
        """Add a filter with an operator (e.g., field__gte=value)."""
        if op == CONTAINS_OP:
            self._add_contains_filter(field, value)
        elif op == IN_OP:
            self._add_in_filter(field, value)
        elif op in COMPARISON_OPERATORS:
            self._add_comparison_filter(field, op, value)
        else:
            log(logger, "Query", "warning", "filter", f"Unknown operator: {op}")
        
    def _add_contains_filter(self, field: str, value: Any) -> None:
        """Add contains filter for collections."""
        # Special case for tags field
        if field == TAGS_FIELD:
            def filter_fn(item: T) -> bool:
                if isinstance(value, str):
                    return value in item.tags
                return all(tag in item.tags for tag in value)
            self._filters.append(filter_fn)
            return
        
        # For other fields, create a contains filter
        predicate = (
            self._create_iterable_predicate(all_match=True) 
            if isinstance(value, (list, tuple, set))
            else self._create_iterable_predicate()
        )
        self._filters.append(self._create_filter(field, predicate, value))
    
    def _add_in_filter(self, field: str, value: Any) -> None:
        """Add a filter for 'in' operation (field__in=[val1, val2])."""
        try:
            # Value must be iterable
            iter(value)
            self._filters.append(self._create_filter(field, lambda item_val, val: item_val in val, value))
        except (TypeError, ValueError):
            log(logger, "Query", "warning", "filter", 
                f"Value for 'in' operator must be iterable: {value}")
    
    def _add_comparison_filter(self, field: str, op: str, value: Any) -> None:
        """Add a comparison filter (lt, gt, etc.)."""
        try:
            # Try to normalize and compare with the base value
            norm_value = normalize_value(value)
            self._filters.append(self._create_filter(field, COMPARISON_OPERATORS[op], norm_value))
        except (TypeError, ValueError):
            log(logger, "Query", "warning", "filter", 
                f"Invalid comparison value for {field} {op} {value}")
    
    def order_by(self, *fields: str) -> "Query[T]":
        """Add sorting to query."""
        self._order_by = []
        last_reverse = False
        
        for field in fields:
            reverse = field.startswith("-")
            if reverse:
                field = field[1:]
                
            def get_value(item: T, f=field) -> Any:
                return get_item_value(item, f)
                
            self._order_by.append(get_value)
            last_reverse = reverse
            
        # Use the last field's direction as the overall direction
        self._reverse = last_reverse  
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
        self._offset = (page - 1) * per_page
        self._limit = per_page
        return self
    
    def _apply_filters(self, items: List[T]) -> List[T]:
        """Apply filters to items and return filtered items."""
        for filter_fn in self._filters:
            items = [item for item in items if filter_fn(item)]
        return items
        
    def _apply_sorting(self, items: List[T]) -> List[T]:
        """Apply sorting to items and return sorted items."""
        if not self._order_by:
            return items
            
        # Create a single key function for more efficient sorting
        key_fn = lambda item: tuple(fn(item) for fn in self._order_by)
        return sorted(items, key=key_fn, reverse=self._reverse)
    
    def _apply_pagination(self, items: List[T], total: int) -> Tuple[List[T], int, Optional[int]]:
        """Apply pagination and return (items, page, per_page)."""
        if self._offset or self._limit is not None:
            start = self._offset
            end = None if self._limit is None else start + self._limit
            items = items[start:end]
        
        # Calculate page info
        page = 1
        per_page = None
        if self._limit is not None and self._offset:
            per_page = self._limit
            page = (self._offset // per_page) + 1
            
        return items, page, per_page
    
    def execute(self) -> QueryResult[T]:
        """Execute query and return results."""
        # Process the items through the pipeline
        items = self._apply_filters(self._items)
        total = len(items)
        
        items = self._apply_sorting(items)
        items, page, per_page = self._apply_pagination(items, total)
            
        return QueryResult(
            items=items,
            total=total,
            page=page,
            per_page=per_page
        ) 