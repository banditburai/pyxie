"""Test utilities for Pyxie tests."""

from typing import Optional, Any, List, TypeVar, Protocol
from dataclasses import dataclass
from bs4 import BeautifulSoup
from fastcore.xml import FT

T = TypeVar('T', bound=FT)

class TreePredicate(Protocol):
    """Protocol for tree predicates."""
    def __call__(self, node: Any) -> bool: ...

@dataclass
class ComponentFinder:
    """Helper for finding components in FastHTML trees."""
    
    @staticmethod
    def find_first(root: FT, predicate: TreePredicate) -> Optional[FT]:
        """Find first component matching predicate in tree."""
        if predicate(root):
            return root
        
        if hasattr(root, 'children'):
            for child in root.children:
                if isinstance(child, FT):
                    if result := ComponentFinder.find_first(child, predicate):
                        return result
        return None
    
    @staticmethod
    def find_all(root: FT, predicate: TreePredicate) -> List[FT]:
        """Find all components matching predicate in tree."""
        results: List[FT] = []
        
        if predicate(root):
            results.append(root)
        
        if hasattr(root, 'children'):
            for child in root.children:
                if isinstance(child, FT):
                    results.extend(ComponentFinder.find_all(child, predicate))
        return results
    
    @staticmethod
    def is_type(obj: Any, type_name: str) -> bool:
        """Check if object is of a given type by name."""
        return obj.__class__.__name__ == type_name

    @staticmethod
    def find_element(html: str, selector: str) -> Optional[BeautifulSoup]:
        """Find an element in HTML using a CSS selector."""
        soup = BeautifulSoup(html, 'html.parser')
        return soup.select_one(selector) 