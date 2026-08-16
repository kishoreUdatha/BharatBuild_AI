"""
LRU Cache and Memory Management Utilities

Provides bounded caches with TTL eviction to prevent memory leaks
in singleton agents.
"""

import asyncio
import time
from collections import OrderedDict
from typing import Dict, Any, Optional, TypeVar, Generic
from dataclasses import dataclass

from app.core.logging_config import logger


T = TypeVar('T')


@dataclass
class CacheEntry(Generic[T]):
    """Cache entry with TTL tracking."""
    value: T
    created_at: float
    last_accessed: float
    access_count: int = 0


class LRUCache(Generic[T]):
    """
    Thread-safe LRU cache with TTL eviction.

    Features:
    - Maximum size enforcement (evicts LRU on overflow)
    - TTL-based expiration
    - Access count tracking
    - Async-safe with asyncio.Lock

    Usage:
        cache = LRUCache(max_size=100, ttl_seconds=300)
        cache.set("key", value)
        result = cache.get("key")  # Returns None if expired/missing
    """

    def __init__(self, max_size: int = 100, ttl_seconds: float = 300.0, name: str = ""):
        self._store: OrderedDict[str, CacheEntry[T]] = OrderedDict()
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds
        self._lock = asyncio.Lock()
        self._name = name or f"LRUCache({max_size})"
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[T]:
        """
        Get value from cache. Returns None if missing or expired.
        Moves accessed item to end (most recently used).
        """
        entry = self._store.get(key)
        if entry is None:
            self._misses += 1
            return None

        # Check TTL
        now = time.time()
        if (now - entry.created_at) > self._ttl_seconds:
            # Expired
            del self._store[key]
            self._misses += 1
            return None

        # Move to end (most recently used)
        self._store.move_to_end(key)
        entry.last_accessed = now
        entry.access_count += 1
        self._hits += 1
        return entry.value

    def set(self, key: str, value: T) -> None:
        """
        Set value in cache. Evicts LRU if at capacity.
        """
        now = time.time()

        # If key exists, update it
        if key in self._store:
            self._store[key] = CacheEntry(
                value=value,
                created_at=now,
                last_accessed=now,
                access_count=self._store[key].access_count + 1,
            )
            self._store.move_to_end(key)
            return

        # Evict if at capacity
        while len(self._store) >= self._max_size:
            evicted_key, _ = self._store.popitem(last=False)
            logger.debug(f"[{self._name}] Evicted LRU entry: {evicted_key}")

        # Insert new entry
        self._store[key] = CacheEntry(
            value=value,
            created_at=now,
            last_accessed=now,
        )

    def remove(self, key: str) -> bool:
        """Remove a key from cache. Returns True if key existed."""
        if key in self._store:
            del self._store[key]
            return True
        return False

    def clear(self) -> None:
        """Clear all entries."""
        self._store.clear()

    def cleanup_expired(self) -> int:
        """Remove all expired entries. Returns count of removed entries."""
        now = time.time()
        expired_keys = [
            key for key, entry in self._store.items()
            if (now - entry.created_at) > self._ttl_seconds
        ]
        for key in expired_keys:
            del self._store[key]

        if expired_keys:
            logger.debug(f"[{self._name}] Cleaned up {len(expired_keys)} expired entries")
        return len(expired_keys)

    @property
    def size(self) -> int:
        """Current number of entries."""
        return len(self._store)

    @property
    def stats(self) -> Dict[str, Any]:
        """Cache statistics."""
        total = self._hits + self._misses
        return {
            "name": self._name,
            "size": len(self._store),
            "max_size": self._max_size,
            "ttl_seconds": self._ttl_seconds,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / total, 3) if total > 0 else 0,
        }

    def __contains__(self, key: str) -> bool:
        """Check if key exists and is not expired."""
        return self.get(key) is not None

    def __len__(self) -> int:
        return len(self._store)


class AsyncLRUCache(LRUCache[T]):
    """
    Async-safe LRU cache using asyncio.Lock.

    Use this when cache is accessed from async code with potential concurrent access.
    """

    async def async_get(self, key: str) -> Optional[T]:
        """Thread-safe async get."""
        async with self._lock:
            return self.get(key)

    async def async_set(self, key: str, value: T) -> None:
        """Thread-safe async set."""
        async with self._lock:
            self.set(key, value)

    async def async_remove(self, key: str) -> bool:
        """Thread-safe async remove."""
        async with self._lock:
            return self.remove(key)

    async def async_cleanup(self) -> int:
        """Thread-safe async cleanup of expired entries."""
        async with self._lock:
            return self.cleanup_expired()


class BoundedDict(Generic[T]):
    """
    A simple bounded dictionary that evicts oldest entries when full.
    Lighter weight than LRUCache for cases where TTL isn't needed.

    Usage:
        agents = BoundedDict(max_size=50, name="memory_agents")
        agents["project_123"] = MemoryAgent(...)
    """

    def __init__(self, max_size: int = 100, name: str = ""):
        self._store: OrderedDict[str, T] = OrderedDict()
        self._max_size = max_size
        self._name = name or f"BoundedDict({max_size})"

    def __getitem__(self, key: str) -> T:
        if key not in self._store:
            raise KeyError(key)
        self._store.move_to_end(key)
        return self._store[key]

    def __setitem__(self, key: str, value: T) -> None:
        if key in self._store:
            self._store.move_to_end(key)
            self._store[key] = value
            return

        while len(self._store) >= self._max_size:
            evicted_key, _ = self._store.popitem(last=False)
            logger.info(f"[{self._name}] Evicted oldest entry: {evicted_key}")

        self._store[key] = value

    def __delitem__(self, key: str) -> None:
        del self._store[key]

    def __contains__(self, key: str) -> bool:
        return key in self._store

    def __len__(self) -> int:
        return len(self._store)

    def get(self, key: str, default: Optional[T] = None) -> Optional[T]:
        try:
            return self[key]
        except KeyError:
            return default

    def keys(self):
        return self._store.keys()

    def values(self):
        return self._store.values()

    def items(self):
        return self._store.items()

    def clear(self) -> None:
        self._store.clear()
