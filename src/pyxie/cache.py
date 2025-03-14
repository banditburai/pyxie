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

"""SQLite-based caching system for rendered HTML content."""

import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from contextlib import contextmanager

from .errors import PyxieError
from .utilities import log, normalize_path, hash_file

logger = logging.getLogger(__name__)

# SQL Queries
SCHEMA = """
CREATE TABLE IF NOT EXISTS cache (
    collection TEXT,
    file_path TEXT,
    html TEXT,
    source_hash TEXT,
    template_name TEXT,
    updated_at TEXT,
    PRIMARY KEY (collection, file_path)
);

CREATE INDEX IF NOT EXISTS idx_cache_path ON cache(file_path);
"""

class CacheError(PyxieError):
    """Base class for cache-related errors."""
    pass

class Cache:
    """SQLite-based cache for rendered HTML content."""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """Initialize cache.
        
        Args:
            cache_dir: Directory for cache database. Defaults to ~/.cache/pyxie
        """
        if cache_dir is None:
            cache_dir = Path.home() / ".cache" / "pyxie"
            
        cache_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = cache_dir / "cache.db"
        
        # Initialize database
        with self._connect() as conn:
            conn.executescript(SCHEMA)
    
    @contextmanager
    def _connect(self):
        """Create a database connection with proper configuration."""
        conn = sqlite3.connect(str(self.db_path), isolation_level="IMMEDIATE")
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise CacheError(f"Cache operation failed: {e}") from e
        finally:
            conn.close()
    
    def get(
        self,
        collection: str,
        file_path: Path,
        template_name: str
    ) -> Optional[str]:
        """Get cached HTML if valid.
        
        Args:
            collection: Collection name
            file_path: Path to source file
            template_name: Template name for invalidation
            
        Returns:
            Cached HTML if valid, None otherwise
        """
        try:
            # Get current source hash
            current_hash = hash_file(file_path)
            if not current_hash:
                return None
                
            # Check cache
            with self._connect() as conn:
                row = conn.execute("""
                    SELECT html, source_hash, template_name
                    FROM cache
                    WHERE collection = ? AND file_path = ?
                """, (collection, normalize_path(file_path))).fetchone()
                
                if not row:
                    return None
                    
                # Validate source hasn't changed
                if row["source_hash"] != current_hash:
                    return None
                    
                # Validate template hasn't changed
                if row["template_name"] != template_name:
                    return None
                    
                return row["html"]
                
        except Exception as e:
            log(logger, "Cache", "warning", "get", f"Failed to get cache entry: {e}")
            return None
    
    def store(
        self,
        collection: str,
        file_path: Path,
        html: str,
        template_name: str
    ) -> bool:
        """Store rendered HTML in cache.
        
        Args:
            collection: Collection name
            file_path: Path to source file
            html: Rendered HTML content
            template_name: Template name for invalidation
            
        Returns:
            True if stored successfully
        """
        try:
            # Get current source hash
            current_hash = hash_file(file_path)
            if not current_hash:
                return False
                
            # Store in cache
            with self._connect() as conn:
                conn.execute("""
                    INSERT INTO cache (
                        collection, file_path, html,
                        source_hash, template_name, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT (collection, file_path) DO UPDATE SET
                        html = excluded.html,
                        source_hash = excluded.source_hash,
                        template_name = excluded.template_name,
                        updated_at = excluded.updated_at
                """, (
                    collection,
                    normalize_path(file_path),
                    html,
                    current_hash,
                    template_name,
                    datetime.now().isoformat()
                ))
                return True
                
        except Exception as e:
            log(logger, "Cache", "warning", "store", f"Failed to store cache entry: {e}")
            return False
    
    def invalidate(
        self,
        collection: Optional[str] = None,
        file_path: Optional[Path] = None
    ) -> bool:
        """Invalidate cache entries.
        
        Args:
            collection: Optional collection to invalidate
            file_path: Optional file path to invalidate
            
        Returns:
            True if invalidation successful
        """
        try:
            with self._connect() as conn:
                if collection and file_path:
                    # Invalidate specific entry
                    conn.execute(
                        "DELETE FROM cache WHERE collection = ? AND file_path = ?",
                        (collection, normalize_path(file_path))
                    )
                elif collection:
                    # Invalidate collection
                    conn.execute(
                        "DELETE FROM cache WHERE collection = ?",
                        (collection,)
                    )
                else:
                    # Invalidate everything
                    conn.execute("DELETE FROM cache")
                return True
                
        except Exception as e:
            log(logger, "Cache", "warning", "invalidate", f"Failed to invalidate cache: {e}")
            return False 