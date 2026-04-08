"""
Idempotency Repository
======================
Async DB access helpers for persisted idempotency keys.
Compatible with the async SQLAlchemy session used throughout the app.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional
import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.models.idempotency import IdempotencyKey


async def get_key(db: AsyncSession, key: str) -> Optional[IdempotencyKey]:
    """Fetch idempotency record, pruning expired entries in-line."""
    result = await db.execute(
        select(IdempotencyKey).where(IdempotencyKey.key == key)
    )
    record = result.scalar_one_or_none()
    if not record:
        return None

    expires_at = record.ttl_expires_at
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        await db.delete(record)
        await db.commit()
        return None

    if isinstance(record.response_body, str):
        try:
            record.response_body = json.loads(record.response_body)
        except Exception:
            pass
    return record


async def save_key(
    db: AsyncSession,
    key: str,
    fingerprint: str,
    user_id: str,
    response_body: dict,
    ttl_seconds: int,
    status: str = "completed",
) -> IdempotencyKey:
    """Persist idempotent response for future replays (upsert via merge)."""
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)

    # Always JSON-encode for consistent storage across SQLite (tests) and PostgreSQL.
    stored_body = json.dumps(response_body, default=str)

    record = IdempotencyKey(
        key=key,
        request_fingerprint=fingerprint,
        user_id=user_id,
        response_body=stored_body,
        status=status,
        ttl_expires_at=expires_at,
    )
    merged = await db.merge(record)
    await db.commit()
    return merged


async def delete_key(db: AsyncSession, key: str) -> None:
    """Remove an idempotency key (used when computation fails so caller can retry)."""
    await db.execute(delete(IdempotencyKey).where(IdempotencyKey.key == key))
    await db.commit()


async def cleanup_expired(db: AsyncSession, limit: int = 100) -> None:
    """Best-effort cleanup to avoid table bloat."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(IdempotencyKey)
        .where(IdempotencyKey.ttl_expires_at < now)
        .limit(limit)
    )
    expired = result.scalars().all()
    for row in expired:
        await db.delete(row)
    if expired:
        await db.commit()
