"""
Unit Tests — Security Module
==============================
Tests JWT creation/validation and password hashing without database dependencies.
"""

from datetime import timedelta
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)


class TestPasswordHashing:
    """Verify bcrypt hashing produces irreversible, verifiable hashes."""

    def test_hash_is_not_plaintext(self):
        hashed = hash_password("MySecret123")
        assert hashed != "MySecret123"

    def test_verify_correct_password(self):
        hashed = hash_password("CorrectPassword")
        assert verify_password("CorrectPassword", hashed) is True

    def test_verify_wrong_password(self):
        hashed = hash_password("CorrectPassword")
        assert verify_password("WrongPassword", hashed) is False

    def test_different_hashes_for_same_input(self):
        """bcrypt uses random salts, so hashes differ even for same input."""
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2
        assert verify_password("same", h1) is True
        assert verify_password("same", h2) is True


class TestJWT:
    """Verify JWT token lifecycle: creation, decoding, and expiry."""

    def test_create_and_decode_token(self):
        token = create_access_token({"sub": "user-123", "role": "admin"})
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == "user-123"
        assert payload["role"] == "admin"

    def test_token_contains_expiry(self):
        token = create_access_token({"sub": "user-456"})
        payload = decode_access_token(token)
        assert "exp" in payload
        assert "iat" in payload

    def test_expired_token_returns_none(self):
        token = create_access_token(
            {"sub": "user-789"},
            expires_delta=timedelta(seconds=-1),
        )
        payload = decode_access_token(token)
        assert payload is None

    def test_tampered_token_returns_none(self):
        token = create_access_token({"sub": "user-abc"})
        tampered = token[:-5] + "XXXXX"
        payload = decode_access_token(tampered)
        assert payload is None

    def test_custom_expiry_delta(self):
        token = create_access_token(
            {"sub": "user-delta"},
            expires_delta=timedelta(hours=48),
        )
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == "user-delta"
