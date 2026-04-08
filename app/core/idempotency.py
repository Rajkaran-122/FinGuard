"""
Idempotency Management
======================
Provides in-memory short-circuiting plus persisted storage to avoid duplicate
processing of write operations. Fingerprints include method, path, body hash,
and user context to prevent cross-user replay.

All operations are async to be compatible with the ASGI stack.
"""

from typing import Any, Callable, Awaitable, Dict
import json
from hashlib import sha256
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.repositories import idempotency_repository
from app.core.config import settings
from app.core.logging import logger
from app.services.cache_service import cache_service


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
    """Coordinates persisted + in-memory idempotency handling (fully async)."""

    def __init__(self, ttl_seconds: int = settings.IDEMPOTENCY_TTL_SECONDS):
        self.ttl_seconds = ttl_seconds
        self.cache = cache_service

    async def process(
        self,
        db: AsyncSession,
        key: str,
        fingerprint: str,
        user_id: str,
        compute_response: Callable[[], Awaitable[Any]],
    ) -> Any:
        """
        Main gate (async):
        1. In-memory lookup (fast path) + fingerprint validation
        2. Persisted lookup (survives restarts)
        3. Insert pending lock to prevent race conditions
        4. Compute + persist + cache
        """
        cache_key = f"idem_{key}"
        cached_data = await self.cache.get(cache_key)
        if cached_data:
            if cached_data.get("fingerprint") != fingerprint:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "message": "Idempotency-Key already used for a different request payload",
                        "code": "VALIDATION_FAILED",
                    },
                )
            return cached_data.get("response")

        existing = await idempotency_repository.get_key(db, key)
        if existing:
            if existing.request_fingerprint != fingerprint or existing.user_id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "message": "Idempotency-Key already used for a different request payload",
                        "code": "VALIDATION_FAILED",
                    },
                )
            if existing.status == "pending":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "message": "Request is already being processed",
                        "code": "CONCURRENT_REQUEST",
                    },
                )
            return existing.response_body

        # Attempt to acquire lock by inserting a 'pending' record
        try:
            await idempotency_repository.create_lock(
                db=db,
                key=key,
                fingerprint=fingerprint,
                user_id=user_id,
                ttl_seconds=self.ttl_seconds,
            )
        except IntegrityError:
            # Another request (or this one) already started or finished.
            # Re-fetch to see if we should replay or conflict.
            await db.rollback()
            existing = await idempotency_repository.get_key(db, key)
            if existing:
                if existing.request_fingerprint != fingerprint or existing.user_id != user_id:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail={
                            "message": "Idempotency-Key already used for a different request payload",
                            "code": "VALIDATION_FAILED",
                        },
                    )
                if existing.status == "pending":
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail={
                            "message": "Request is already being processed",
                            "code": "CONCURRENT_REQUEST",
                        },
                    )
                return existing.response_body
            
            # If we gets here, it means we couldn't find it even after IntegrityError, 
            # which might happen if the other request failed and cleaned up.
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "Request is already being processed",
                    "code": "CONCURRENT_REQUEST",
                },
            )
        except Exception as e:
            await db.rollback()
            logger.error(f"idempotency: lock_acquisition_failed error={str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal error processing idempotency"
            )

        try:
            response = await compute_response()
            await idempotency_repository.save_key(
                db=db,
                key=key,
                fingerprint=fingerprint,
                user_id=user_id,
                response_body=response,
                ttl_seconds=self.ttl_seconds,
                status="completed",
            )
            await self.cache.set(
                cache_key,
                {"fingerprint": fingerprint, "response": response},
                ttl=self.ttl_seconds,
            )
            return response
        except Exception:
            # If computation fails, release the idempotency lock so they can retry
            await idempotency_repository.delete_key(db, key)
            raise

    async def cleanup_expired(self, db: AsyncSession, limit: int = 100):
        """Prune expired persisted idempotency rows."""
        await idempotency_repository.cleanup_expired(db, limit=limit)


# Global singleton used across routers/services
idempotency_manager = IdempotencyManager()
