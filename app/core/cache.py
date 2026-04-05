"""
Abstracted Cache Service Component 
==================================
Implements a fast LRU/TTL Memory wrapper simulating Redis deployments.
"""
from typing import Any, Dict, Optional
import time
import threading

class CacheManager:
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
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
            self._cache[key] = {
                "value": value,
                "expires_at": time.time() + ttl
            }

    def invalidate_prefix(self, prefix: str):
        """Mass evict keys matching a functional prefix when raw tables mutate."""
        with self._lock:
            keys_to_delete = [k for k in self._cache.keys() if k.startswith(prefix)]
            for k in keys_to_delete:
                del self._cache[k]

    def snapshot_metrics(self) -> Dict[str, int]:
        with self._lock:
            return {"hits": self.hits, "misses": self.misses, "size": len(self._cache)}

# Global cache bus
cache_service = CacheManager()
