"""
Unit Tests — Cache Module
===========================
Tests the CacheManager in isolation without database or FastAPI dependencies.
Validates TTL expiry, LRU eviction, prefix invalidation, and metric tracking.
"""

import time
from app.core.cache import CacheManager


class TestCacheManager:
    """Test suite for bounded TTL cache with LRU eviction."""

    def setup_method(self):
        self.cache = CacheManager(maxsize=5)

    def test_set_and_get(self):
        """Basic set/get round-trip."""
        self.cache.set("key1", {"data": 123}, ttl=60)
        assert self.cache.get("key1") == {"data": 123}

    def test_get_nonexistent_returns_none(self):
        """Missing key returns None and increments misses."""
        result = self.cache.get("nonexistent")
        assert result is None
        assert self.cache.misses == 1

    def test_ttl_expiry(self):
        """Expired entries are evicted on access."""
        self.cache.set("expiring", "value", ttl=0)
        time.sleep(0.01)
        assert self.cache.get("expiring") is None
        assert self.cache.misses == 1

    def test_hit_miss_tracking(self):
        """Verify hit/miss counters update correctly."""
        self.cache.set("hit_key", "value", ttl=60)
        self.cache.get("hit_key")  # hit
        self.cache.get("miss_key")  # miss
        metrics = self.cache.snapshot_metrics()
        assert metrics["hits"] == 1
        assert metrics["misses"] == 1

    def test_invalidate_prefix(self):
        """Prefix invalidation removes matching keys only."""
        self.cache.set("dashboard_summary_1", "a", ttl=60)
        self.cache.set("dashboard_summary_2", "b", ttl=60)
        self.cache.set("user_profile_1", "c", ttl=60)
        self.cache.invalidate_prefix("dashboard_summary_")
        assert self.cache.get("dashboard_summary_1") is None
        assert self.cache.get("dashboard_summary_2") is None
        assert self.cache.get("user_profile_1") == "c"

    def test_lru_eviction_at_maxsize(self):
        """When cache is full, oldest entries are evicted on next set."""
        for i in range(5):
            self.cache.set(f"key_{i}", f"val_{i}", ttl=60)

        assert self.cache.snapshot_metrics()["size"] == 5

        # This should trigger eviction
        self.cache.set("key_overflow", "new_value", ttl=60)
        # After eviction, size should not exceed maxsize
        assert self.cache.snapshot_metrics()["size"] <= 5

    def test_clear_resets_everything(self):
        """Clear flushes cache and resets metrics."""
        self.cache.set("a", 1, ttl=60)
        self.cache.get("a")
        self.cache.clear()
        metrics = self.cache.snapshot_metrics()
        assert metrics["size"] == 0
        assert metrics["hits"] == 0
        assert metrics["misses"] == 0

    def test_snapshot_includes_maxsize(self):
        """Metrics snapshot includes configured maxsize."""
        metrics = self.cache.snapshot_metrics()
        assert metrics["maxsize"] == 5

    def test_overwrite_existing_key_no_eviction(self):
        """Overwriting an existing key does not trigger eviction."""
        for i in range(5):
            self.cache.set(f"key_{i}", f"val_{i}", ttl=60)
        # Overwrite existing key — should not trigger eviction
        self.cache.set("key_0", "updated", ttl=60)
        assert self.cache.get("key_0") == "updated"
        assert self.cache.snapshot_metrics()["size"] == 5
