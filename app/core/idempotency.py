"""
Idempotency Management
======================
Provides in-memory short-circuiting plus persisted storage to avoid duplicate
processing of write operations. Fingerprints include method, path, body hash,
and user context to prevent cross-user replay.
"""

from typing import Any, Callable, Dict, Optional
import time
import threading
import json
from hashlib import sha256
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories import idempotency_repository
from app.core.config import settings


class IdempotencyEngine:
    """Simple in-memory TTL cache (Redis-drop-in interface)."""

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


def make_fingerprint(method: str, path: str, body: Dict[str, Any], user_id: str) -> str:
    """Canonical SHA256 fingerprint for idempotent writes."""
    payload = {
        "method": method.upper(),
        "path": path,
        "body": body,
        "user_id": user_id,
    }
    canonical = json.dumps(payload, sort_keys=True, default=str)
    return sha256(canonical.encode("utf-8")).hexdigest()


class IdempotencyManager:
    """Coordinates persisted + in-memory idempotency handling."""

    def __init__(self, ttl_seconds: int = settings.IDEMPOTENCY_TTL_SECONDS):
        self.ttl_seconds = ttl_seconds
        self.cache = IdempotencyEngine()

    def process(
        self,
        db: Session,
        key: str,
        fingerprint: str,
        user_id: str,
        compute_response: Callable[[], Any],
    ) -> Any:
        """
        Main gate:
        1. Persisted lookup (survives restarts)
        2. In-memory lookup (fast path)
        3. Compute + persist + cache
        """
        existing = idempotency_repository.get_key(db, key)
        if existing:
            if existing.request_fingerprint != fingerprint or existing.user_id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "message": "Idempotency-Key already used for a different request payload",
                        "code": "VALIDATION_FAILED",
                    },
                )
            return existing.response_body

        cached = self.cache.get_response(key)
        if cached:
            return cached

        response = compute_response()
        idempotency_repository.save_key(
            db=db,
            key=key,
            fingerprint=fingerprint,
            user_id=user_id,
            response_body=response,
            ttl_seconds=self.ttl_seconds,
            status="completed",
        )
        self.cache.save_response(key, response, ttl_seconds=self.ttl_seconds)
        return response

    def cleanup_expired(self, db: Session, limit: int = 100):
        """Prune expired persisted idempotency rows."""
        idempotency_repository.cleanup_expired(db, limit=limit)


# Global singleton used across routers/services
idempotency_manager = IdempotencyManager()
