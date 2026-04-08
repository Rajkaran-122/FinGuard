"""
Custom FastAPI Middleware
=========================
Implements Request ID tracking and structured logging for all incoming requests.
"""

import time
import uuid
import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.logging import logger

# Get a sub-logger for middleware
log = structlog.get_logger("middleware.logging")


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Enriches requests with a unique ID for traceability across logs.
    """
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        # Store in state for other middleware/routers to access
        request.state.request_id = request_id
        
        # Add to structlog context
        structlog.contextvars.bind_contextvars(request_id=request_id)
        
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Logs every request and response with latency and status codes.
    """
    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()
        
        method = request.method
        path = request.url.path
        
        response = await call_next(request)
        
        process_time = time.perf_counter() - start_time
        status_code = response.status_code
        
        log.info(
            "request_completed",
            method=method,
            path=path,
            status_code=status_code,
            latency_ms=round(process_time * 1000, 2)
        )
        
        return response
