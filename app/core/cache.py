"""
Abstracted Cache Service Component 
==================================
Implements a bounded LRU/TTL Memory wrapper simulating Redis deployments.

DESIGN DECISION: maxsize prevents unbounded memory growth.
At 100k users with ~10 query param combinations each, the cache
would grow to ~1M entries without bounds. maxsize=10000 limits
memory to approximately 50MB (assuming ~5KB per cached value).

PRODUCTION UPGRADE PATH:
  Replace this class internals with redis-py. The .get/.set/.invalidate_prefix
  API contract remains identical — zero changes to service layers.
"""
from typing import Any, Dict, Optional
import time
import threading


class CacheManager:
    """Bounded TTL cache with LRU eviction and observability metrics."""

    def __init__(self, maxsize: int = 10_000):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._maxsize = maxsize
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            data = self._cache.get(key)
            if not data:
                self.misses += 1
                return None
            if time.time() > data["expires_at"]:
                del self._cache[key]
                self.misses += 1
                return None
            self.hits += 1
            return data["value"]

    def set(self, key: str, value: Any, ttl: int = 3600):
        with self._lock:
            # LRU eviction: if at capacity, remove oldest entries
            if len(self._cache) >= self._maxsize and key not in self._cache:
                self._evict_oldest(count=max(1, self._maxsize // 10))
            self._cache[key] = {
                "value": value,
                "expires_at": time.time() + ttl
            }

    def invalidate_prefix(self, prefix: str):
        """Mass evict keys matching a functional prefix when raw tables mutate."""
        with self._lock:
            keys_to_delete = [k for k in self._cache if k.startswith(prefix)]
            for k in keys_to_delete:
                del self._cache[k]

    def clear(self):
        """Flush entire cache (used in testing)."""
        with self._lock:
            self._cache.clear()
            self.hits = 0
            self.misses = 0

    def snapshot_metrics(self) -> Dict[str, int]:
        with self._lock:
            return {
                "hits": self.hits,
                "misses": self.misses,
                "size": len(self._cache),
                "maxsize": self._maxsize,
            }

    def _evict_oldest(self, count: int = 1):
        """Evict the oldest N entries by expiry time (approximates LRU)."""
        if not self._cache:
            return
        sorted_keys = sorted(
            self._cache.keys(),
            key=lambda k: self._cache[k]["expires_at"]
        )
        for key in sorted_keys[:count]:
            del self._cache[key]


# Global cache bus
cache_service = CacheManager()
