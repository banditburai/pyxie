"""Shared test fixtures for Pyxie tests."""

import pytest
from pathlib import Path
from typing import Dict
from pyxie.pyxie import Pyxie

@pytest.fixture
def test_paths(tmp_path: Path) -> Dict[str, Path]:
    """Create test directory structure.
    
    Returns:
        Dict with paths for:
        - layouts: Directory for layout files
        - content: Directory for content files
        - cache: Directory for cache files
    """
    return {
        'layouts': tmp_path / "layouts",
        'content': tmp_path / "content",
        'cache': tmp_path / "cache"
    }

@pytest.fixture
def pyxie(test_paths: Dict[str, Path]) -> Pyxie:
    """Create a Pyxie instance with test paths.
    
    Creates necessary directories and returns a configured Pyxie instance.
    """
    for path in test_paths.values():
        path.mkdir(exist_ok=True)
    
    return Pyxie(
        content_dir=test_paths['content'],
        cache_dir=test_paths['cache']
    ) 