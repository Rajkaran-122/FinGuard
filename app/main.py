"""
FinGuard FastAPI Application Factory
====================================
Main application entrypoint. Assembles the FastAPI instance,
configures CORS, registers routers, and sets up exception handling.
"""

from contextlib import asynccontextmanager, suppress
import asyncio

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi import HTTPException
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import os
from alembic import command
from alembic.config import Config
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine, Base, SessionLocal
from app.core.logging import StructuredLoggingMiddleware
from app.core.rate_limit import limiter
from app.core.idempotency import idempotency_manager
from app.core.cache import cache_service
from app.core.dependencies import get_db
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
def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint to verify system status.

    DESIGN: Actually pings the database rather than returning a
    hardcoded 'connected' string. This allows load balancers and
    monitoring systems to detect real outages.
    """
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "disconnected"

    cache_metrics = cache_service.snapshot_metrics()

    return {
        "status": "ok" if db_status == "connected" else "degraded",
        "database": db_status,
        "cache": cache_metrics,
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
