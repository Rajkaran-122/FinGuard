"""
Cache Service
=============
Handles Redis-based caching with JSON serialization.
Provides a foundation for high-performance dashboard analytics.
"""

import json
from typing import Any, Optional
import redis.asyncio as redis

from app.core.config import settings
from app.core.logging import logger


class CacheService:
    """
    Wraps Redis operations with standardized naming and serialization.
    """

    def __init__(self):
        self._redis: Optional[redis.Redis] = None

    async def connect(self):
        """Establish connection to the Redis server. Re-initializes if loop changed."""
        try:
            # Check if existing client is healthy and using the current loop
            if self._redis:
                try:
                    await self._redis.ping()
                    return
                except (RuntimeError, Exception):
                    # If ping fails, the loop might be closed or connection dead
                    self._redis = None

            self._redis = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                encoding="utf-8"
            )
            await self._redis.ping()
            logger.info("cache: connected_to_redis")
        except Exception as e:
            # If the loop is closed or connection fails, reset client
            err_msg = str(e).lower()
            if "event loop is closed" in err_msg or "runtimeerror" in err_msg:
                self._redis = None
            logger.error(f"cache: connection_failed error={str(e)}")
            self._redis = None

    async def get(self, key: str) -> Optional[Any]:
        """Fetch and deserialize a value from cache."""
        try:
            if not self._redis:
                await self.connect()
            
            if not self._redis:
                return None

            data = await self._redis.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            err_msg = str(e).lower()
            if "event loop is closed" in err_msg:
                self._redis = None
            logger.error(f"cache: get_failed key={key} error={str(e)}")
            return None

    async def set(self, key: str, value: Any, ttl: int = settings.CACHE_DEFAULT_TTL):
        """Serialize and store a value in cache with expiry."""
        try:
            if not self._redis:
                await self.connect()

            if not self._redis:
                return

            await self._redis.set(
                key,
                json.dumps(value),
                ex=ttl
            )
        except Exception as e:
            err_msg = str(e).lower()
            if "event loop is closed" in err_msg:
                self._redis = None
            logger.error(f"cache: set_failed key={key} error={str(e)}")

    async def delete(self, key: str):
        """Remove a key from cache. Fails silently if Redis is unavailable."""
        try:
            if not self._redis:
                await self.connect()

            if not self._redis:
                return

            await self._redis.delete(key)
        except Exception as e:
            err_msg = str(e).lower()
            if "event loop is closed" in err_msg:
                self._redis = None
            logger.error(f"cache: delete_failed key={key} error={str(e)}")

    async def clear_prefix(self, prefix: str):
        """Flush all keys matching a specific prefix."""
        try:
            if not self._redis:
                await self.connect()
            
            if not self._redis:
                return

            keys = await self._redis.keys(f"{prefix}*")
            if keys:
                await self._redis.delete(*keys)
        except Exception as e:
            err_msg = str(e).lower()
            if "event loop is closed" in err_msg:
                self._redis = None
            logger.error(f"cache: clear_prefix_failed prefix={prefix} error={str(e)}")


cache_service = CacheService()
