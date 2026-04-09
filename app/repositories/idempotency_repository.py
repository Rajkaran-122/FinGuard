"""
Idempotency Repository
======================
Async DB access helpers for persisted idempotency keys.
Compatible with the async SQLAlchemy session used throughout the app.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional, Any, List
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
    
    now = datetime.now(timezone.utc)
    if record and record.ttl_expires_at:
        # Standardize awareness for SQLite compatibility
        expires_at = record.ttl_expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
            
        if expires_at < now:
            await db.delete(record)
            await db.commit()
            return None
        
    # Standardize response_body as a dict if it was stored as a JSON string (SQLite)
    if record and isinstance(record.response_body, str):
        try:
            record.response_body = json.loads(record.response_body)
        except (json.JSONDecodeError, TypeError):
            pass
            
    return record


async def save_key(
    db: AsyncSession,
    key: str,
    fingerprint: str,
    user_id: str,
    response_body: Any,
    ttl_seconds: int,
    status: str = "completed"
) -> IdempotencyKey:
    """UPSERT: Persist response for future re-play."""
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
    
    # For SQLite compatibility, ensure response_body is a JSON string
    stored_body = json.dumps(response_body) if isinstance(response_body, (dict, list)) else response_body

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


async def create_lock(
    db: AsyncSession,
    key: str,
    fingerprint: str,
    user_id: str,
    ttl_seconds: int,
) -> IdempotencyKey:
    """
    Atomic lock acquisition: direct INSERT.
    Fails with IntegrityError if key already exists.
    """
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
    record = IdempotencyKey(
        key=key,
        request_fingerprint=fingerprint,
        user_id=user_id,
        response_body=json.dumps({}),
        status="pending",
        ttl_expires_at=expires_at,
    )
    db.add(record)
    await db.commit()
    return record


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
