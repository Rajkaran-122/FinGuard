"""
Rate Limiting Configuration
===========================
Configures in-memory rate limiting to prevent brute-force attacks.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Initialize limiter using client IP address with a global fallback limit
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])
