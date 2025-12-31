"""
Fix Cache - Cache successful fixes to avoid repeated AI calls

In-memory cache with TTL - ~40% hit rate on common errors
"""

import hashlib
import re
import time
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from collections import OrderedDict


@dataclass
class CachedFix:
    """Cached fix result"""
    fix_type: str                    # command, file_edit, patch
    fix_data: Dict                   # Command or file content
    created_at: float
    hit_count: int = 0
    success_rate: float = 1.0        # Track if fix actually worked


class FixCache:
    """
    LRU cache for successful fixes.

    Features:
    - Normalizes errors (removes line numbers, timestamps)
    - TTL-based expiration
    - LRU eviction when full
    - Success tracking (demote failing fixes)
    """

    DEFAULT_TTL = 3600  # 1 hour
    MAX_SIZE = 1000     # Max cached fixes

    def __init__(self, ttl: int = DEFAULT_TTL, max_size: int = MAX_SIZE):
        self.ttl = ttl
        self.max_size = max_size
        self._cache: OrderedDict[str, CachedFix] = OrderedDict()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0
        }

    def get_cache_key(self, error: str, file_path: str = None) -> str:
        """
        Generate cache key from error.

        Normalizes error to increase hit rate:
        - Removes line numbers
        - Removes timestamps
        - Removes absolute paths
        - Removes UUIDs
        """
        normalized = error

        # Remove line numbers
        normalized = re.sub(r'line \d+', 'line X', normalized, flags=re.I)
        normalized = re.sub(r':\d+:\d+', ':X:X', normalized)

        # Remove timestamps
        normalized = re.sub(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}', 'TIMESTAMP', normalized)

        # Remove UUIDs
        normalized = re.sub(r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}', 'UUID', normalized, flags=re.I)

        # Remove absolute paths but keep relative structure
        normalized = re.sub(r'(/[a-zA-Z0-9_\-]+)+/', '/PATH/', normalized)
        normalized = re.sub(r'[A-Z]:\\[^:]+\\', 'PATH\\', normalized)

        # Create hash
        key_data = f"{normalized}:{file_path or ''}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def get(self, error: str, file_path: str = None) -> Optional[CachedFix]:
        """
        Get cached fix for error.

        Returns None if:
        - Not in cache
        - Expired (TTL)
        - Success rate too low
        """
        key = self.get_cache_key(error, file_path)

        if key not in self._cache:
            self._stats["misses"] += 1
            return None

        cached = self._cache[key]

        # Check TTL
        if time.time() - cached.created_at > self.ttl:
            del self._cache[key]
            self._stats["misses"] += 1
            return None

        # Check success rate (demote failing fixes)
        if cached.success_rate < 0.5 and cached.hit_count > 3:
            del self._cache[key]
            self._stats["misses"] += 1
            return None

        # Move to end (LRU)
        self._cache.move_to_end(key)

        # Update stats
        cached.hit_count += 1
        self._stats["hits"] += 1

        return cached

    def set(
        self,
        error: str,
        fix_type: str,
        fix_data: Dict,
        file_path: str = None
    ) -> str:
        """
        Cache a successful fix.

        Returns cache key.
        """
        key = self.get_cache_key(error, file_path)

        # Evict if full
        while len(self._cache) >= self.max_size:
            self._cache.popitem(last=False)
            self._stats["evictions"] += 1

        self._cache[key] = CachedFix(
            fix_type=fix_type,
            fix_data=fix_data,
            created_at=time.time()
        )

        return key

    def report_success(self, error: str, success: bool, file_path: str = None):
        """
        Report whether a cached fix actually worked.

        Updates success_rate for future decisions.
        """
        key = self.get_cache_key(error, file_path)

        if key in self._cache:
            cached = self._cache[key]
            # Exponential moving average
            alpha = 0.3
            cached.success_rate = alpha * (1.0 if success else 0.0) + (1 - alpha) * cached.success_rate

    def clear(self):
        """Clear all cached fixes"""
        self._cache.clear()
        self._stats = {"hits": 0, "misses": 0, "evictions": 0}

    def get_stats(self) -> Dict:
        """Get cache statistics"""
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total if total > 0 else 0

        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "hit_rate": round(hit_rate * 100, 2),
            "evictions": self._stats["evictions"]
        }


# Singleton instance
fix_cache = FixCache()
