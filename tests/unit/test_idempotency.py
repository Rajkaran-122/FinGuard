"""
Unit Tests — Idempotency Module
=================================
Tests Fingerprint generation and Idempotency logic in isolation context.
"""

from app.core.idempotency import make_fingerprint


class TestFingerprintGeneration:
    """Verify deterministic request hashing."""

    def test_same_payload_same_fingerprint(self):
        f1 = make_fingerprint("POST", "/api", {"amount": 100}, "user-1")
        f2 = make_fingerprint("POST", "/api", {"amount": 100}, "user-1")
        assert f1 == f2

    def test_different_amount_different_fingerprint(self):
        f1 = make_fingerprint("POST", "/api", {"amount": 100}, "user-1")
        f2 = make_fingerprint("POST", "/api", {"amount": 101}, "user-1")
        assert f1 != f2

    def test_different_user_different_fingerprint(self):
        f1 = make_fingerprint("POST", "/api", {"amount": 100}, "user-1")
        f2 = make_fingerprint("POST", "/api", {"amount": 100}, "user-2")
        assert f1 != f2

    def test_dict_ordering_does_not_matter(self):
        """Standardizes dict key order so {'a':1,'b':2} produces same hash as {'b':2,'a':1}"""
        f1 = make_fingerprint("POST", "/api", {"a": 1, "b": 2}, "user-1")
        f2 = make_fingerprint("POST", "/api", {"b": 2, "a": 1}, "user-1")
        assert f1 == f2
