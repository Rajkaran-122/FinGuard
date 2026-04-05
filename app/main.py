"""
FinGuard FastAPI Application Factory
====================================
Main application entrypoint. Assembles the FastAPI instance,
configures CORS, registers routers, and sets up exception handling.
"""

from contextlib import asynccontextmanager, suppress
import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi import HTTPException
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import os
from alembic import command
from alembic.config import Config

from app.core.config import settings
from app.core.database import engine, Base, SessionLocal
from app.core.logging import StructuredLoggingMiddleware
from app.core.rate_limit import limiter
from app.core.idempotency import idempotency_manager
from app.routers import auth, users, records, summary

@asynccontextmanager
async def lifespan(app: FastAPI):
    run_migrations()
    cleanup_task = asyncio.create_task(_idempotency_cleanup_loop())
    try:
        yield
    finally:
        cleanup_task.cancel()
        with suppress(asyncio.CancelledError):
            await cleanup_task

app = FastAPI(
    title=settings.APP_TITLE,
    version=settings.APP_VERSION,
    description="Finance Data Processing and Access Control Backend",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Structured JSON Logging
app.add_middleware(StructuredLoggingMiddleware)

# Rate Limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Include Routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(records.router)
app.include_router(summary.router)

@app.get("/health", tags=["Utility"])
def health_check():
    """Health check endpoint to verify system status."""
    return {
        "status": "ok",
        "database": "connected",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    """Standardized validation error payload."""
    return JSONResponse(
        status_code=422,
        content={
            "status": "error",
            "message": "Validation failed",
            "error": "VALIDATION_FAILED",
            "data": exc.errors()
        },
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """Standardized HTTP error payload."""
    detail = exc.detail
    if isinstance(detail, dict):
        message = detail.get("message", "Request failed")
        code = detail.get("code", "CLIENT_ERROR")
        data = detail.get("details")
    else:
        message = detail
        code = "CLIENT_ERROR"
        data = None
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "message": message,
            "error": code,
            "data": data
        },
    )

@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception):
    """Standardized 500 error payload (avoids leaking stack traces)."""
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "Internal server error. Please contact support.",
            "error": "SERVER_ERROR",
            "data": None
        },
    )


def run_migrations():
    """
    Run Alembic migrations on startup for Postgres; fallback to metadata create on SQLite.
    Skips tests/in-memory SQLite to avoid interfering with fixtures.
    """
    backend = engine.url.get_backend_name()
    if backend.startswith("sqlite"):
        Base.metadata.create_all(bind=engine)
        return

    alembic_ini = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    script_location = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "alembic"))
    alembic_cfg = Config(alembic_ini)
    alembic_cfg.set_main_option("script_location", script_location)
    command.upgrade(alembic_cfg, "head")


async def _idempotency_cleanup_loop():
    """Background cleanup for expired idempotency records."""
    while True:
        db = SessionLocal()
        try:
            idempotency_manager.cleanup_expired(db, limit=200)
        finally:
            db.close()
        await asyncio.sleep(settings.IDEMPOTENCY_CLEANUP_INTERVAL_SECONDS)
