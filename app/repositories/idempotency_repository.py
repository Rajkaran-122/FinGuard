"""
Idempotency Repository
======================
DB access helpers for persisted idempotency keys.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models.idempotency import IdempotencyKey
import json


def get_key(db: Session, key: str) -> Optional[IdempotencyKey]:
    """Fetch idempotency record, pruning expired entries in-line."""
    record = db.query(IdempotencyKey).filter(IdempotencyKey.key == key).first()
    if not record:
        return None
    expires_at = record.ttl_expires_at
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        db.delete(record)
        db.commit()
        return None
    if isinstance(record.response_body, str):
        try:
            record.response_body = json.loads(record.response_body)
        except Exception:
            pass
    return record


def save_key(
    db: Session,
    key: str,
    fingerprint: str,
    user_id: str,
    response_body: dict,
    ttl_seconds: int,
    status: str = "completed",
) -> IdempotencyKey:
    """Persist idempotent response for future replays."""
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
    is_sqlite = db.bind and db.bind.dialect.name == "sqlite"
    stored_body = (
        json.dumps(response_body, default=str) if is_sqlite else response_body
    )
    record = IdempotencyKey(
        key=key,
        request_fingerprint=fingerprint,
        user_id=user_id,
        response_body=stored_body,
        status=status,
        ttl_expires_at=expires_at,
    )
    db.merge(record)
    db.commit()
    return record


def cleanup_expired(db: Session, limit: int = 100):
    """Best-effort cleanup to avoid table bloat."""
    now = datetime.now(timezone.utc)
    expired = (
        db.query(IdempotencyKey)
        .filter(IdempotencyKey.ttl_expires_at < now)
        .limit(limit)
        .all()
    )
    if expired:
        for row in expired:
            db.delete(row)
        db.commit()
