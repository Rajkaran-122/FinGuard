"""
Ownership Scope Resolver
=========================
Single source of truth for determining data visibility scope.
Used by all services that need ownership-aware data access.

DESIGN: Centralizing scope resolution means adding a new role
(e.g., "Auditor") requires zero code changes in services —
just update the role's permissions in the database.
"""

from typing import Optional
from app.models.user import User


def get_data_scope(user: User) -> Optional[str]:
    """
    Determine data scope based on user permissions.

    Returns None for admin-level users (no ownership filter),
    or the user's ID to scope queries to their own records.

    This is the SINGLE function that controls multi-tenancy behavior
    across all services (records, dashboard, summaries).
    """
    user_perms = user.permissions or []
    if "records:write" in user_perms or "users:manage" in user_perms:
        return None  # Admin-level: see all records
    return user.id  # Scoped: see only own records
