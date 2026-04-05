"""
Structured JSON Logging Middleware
==================================
Intercepts HTTP requests and logs execution details as JSON for observability platforms.
"""

import time
import uuid
import logging
import json
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.cache import cache_service

# Configure custom logger
logger = logging.getLogger("finguard")
logger.setLevel(logging.INFO)
logger.propagate = False  # Prevent duplicate logs from root logger

if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)

class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        start_time = time.time()

        client_ip = request.client.host if request.client else "unknown"
        request.state.correlation_id = correlation_id

        try:
            response = await call_next(request)
            process_time_ms = (time.time() - start_time) * 1000

            cache_metrics = cache_service.snapshot_metrics()
            log_dict = {
                "correlation_id": correlation_id,
                "client_ip": client_ip,
                "method": request.method,
                "url": str(request.url.path),
                "status_code": response.status_code,
                "process_time_ms": round(process_time_ms, 2),
                "cache_hits": cache_metrics["hits"],
                "cache_misses": cache_metrics["misses"],
                "cache_size": cache_metrics["size"],
            }
            logger.info(json.dumps(log_dict))

            response.headers["X-Request-ID"] = correlation_id
            response.headers["X-Correlation-ID"] = correlation_id
            return response

        except Exception as exc:
            process_time_ms = (time.time() - start_time) * 1000
            log_dict = {
                "correlation_id": correlation_id,
                "client_ip": client_ip,
                "method": request.method,
                "url": str(request.url.path),
                "status_code": 500,
                "process_time_ms": round(process_time_ms, 2),
                "error": str(exc)
            }
            logger.error(json.dumps(log_dict))
            raise
