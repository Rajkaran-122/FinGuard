"""
Unit Tests — Scope Module
===========================
Tests the ownership scope resolver in isolation.
"""

from unittest.mock import MagicMock
from app.core.scope import get_data_scope


class TestGetDataScope:
    """Verify scope resolution based on user permissions."""

    def _make_user(self, user_id: str, permissions: list):
        user = MagicMock()
        user.id = user_id
        user.permissions = permissions
        return user

    def test_admin_sees_all(self):
        """Users with records:write get None scope (see all records)."""
        user = self._make_user("admin-1", ["records:write", "records:read", "dashboard:view", "users:manage"])
        assert get_data_scope(user) is None

    def test_user_manager_sees_all(self):
        """Users with users:manage get None scope (see all records)."""
        user = self._make_user("mgr-1", ["users:manage", "dashboard:view"])
        assert get_data_scope(user) is None

    def test_viewer_sees_own(self):
        """Viewer without admin permissions gets scoped to own ID."""
        user = self._make_user("viewer-1", ["dashboard:view", "records:read"])
        assert get_data_scope(user) == "viewer-1"

    def test_analyst_sees_own(self):
        """Analyst without write permissions gets scoped to own ID."""
        user = self._make_user("analyst-1", ["dashboard:view", "records:read"])
        assert get_data_scope(user) == "analyst-1"

    def test_no_permissions_sees_own(self):
        """User with empty permissions gets scoped to own ID."""
        user = self._make_user("empty-1", [])
        assert get_data_scope(user) == "empty-1"

    def test_none_permissions_sees_own(self):
        """User with None permissions gets scoped to own ID."""
        user = self._make_user("none-1", None)
        assert get_data_scope(user) == "none-1"
