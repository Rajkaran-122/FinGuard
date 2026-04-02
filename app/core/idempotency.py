"""
Idempotency Cache Implementation
================================
Provides a fast key-value store to prevent duplicate processing of mutations.
In a production ecosystem, this directly maps to a Redis cluster.
"""

from typing import Any, Dict, Optional
import time
import threading

class IdempotencyEngine:
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def get_response(self, key: str) -> Optional[Any]:
        """Fetch previously computed response if active."""
        with self._lock:
            data = self._cache.get(key)
            if not data:
                return None
            
            # Evict if expired
            if time.time() > data["expires_at"]:
                del self._cache[key]
                return None
            
            return data["response"]

    def save_response(self, key: str, response: Any, ttl_seconds: int = 86400):
        """Save computed response for 24 hours."""
        with self._lock:
            self._cache[key] = {
                "response": response,
                "expires_at": time.time() + ttl_seconds
            }

    def clear(self):
        with self._lock:
            self._cache.clear()

# Global pseudo-Redis allocation
idempotency_cache = IdempotencyEngine()
