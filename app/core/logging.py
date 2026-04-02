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
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        client_ip = request.client.host if request.client else "unknown"
        
        try:
            response = await call_next(request)
            process_time_ms = (time.time() - start_time) * 1000
            
            log_dict = {
                "request_id": request_id,
                "client_ip": client_ip,
                "method": request.method,
                "url": str(request.url.path),
                "status_code": response.status_code,
                "process_time_ms": round(process_time_ms, 2)
            }
            logger.info(json.dumps(log_dict))
            
            response.headers["X-Request-ID"] = request_id
            return response
            
        except Exception as exc:
            process_time_ms = (time.time() - start_time) * 1000
            log_dict = {
                "request_id": request_id,
                "client_ip": client_ip,
                "method": request.method,
                "url": str(request.url.path),
                "status_code": 500,
                "process_time_ms": round(process_time_ms, 2),
                "error": str(exc)
            }
            logger.error(json.dumps(log_dict))
            raise
