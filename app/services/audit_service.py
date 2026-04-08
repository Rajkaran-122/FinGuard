"""
Audit Logging Service
=====================
Handles asynchronous recording of system events and data changes.
Ensures security compliance and traceability.
"""

from typing import Optional, Any, Dict
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit_log import AuditLog
from app.core.logging import logger


class AuditService:
    """
    Service for writing to the audit trail.
    """

    async def log_event(
        self,
        db: AsyncSession,
        action: str,
        module: str,
        user_id: Optional[int] = None,
        old_state: Optional[Dict[str, Any]] = None,
        new_state: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """
        Creates a new audit log entry.
        """
        try:
            log_entry = AuditLog(
                user_id=user_id,
                action=action,
                module=module,
                old_state=old_state,
                new_state=new_state,
                ip_address=ip_address,
                user_agent=user_agent,
                created_at=datetime.now(timezone.utc)
            )
            db.add(log_entry)
            await db.commit()
            logger.info(f"audit: logged_event module={module} action={action} user_id={user_id}")
        except Exception as e:
            logger.error(f"audit: logging_failed module={module} action={action} error={str(e)}")


audit_service = AuditService()
