"""
FinGuard FastAPI Application Factory
====================================
Main application entrypoint. Assembles the FastAPI instance,
configures CORS, registers routers, and sets up exception handling.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi import HTTPException
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.database import engine, Base
from app.core.logging import StructuredLoggingMiddleware
from app.core.rate_limit import limiter
from app.routers import auth, users, records, summary

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure tables are created (in production, use Alembic via CLI)
    Base.metadata.create_all(bind=engine)
    yield

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
    return JSONResponse(
        status_code=422,
        content={"error": "VALIDATION_FAILED", "detail": exc.errors()},
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "CLIENT_ERROR", "detail": exc.detail},
    )

@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": "SERVER_ERROR", "detail": "Internal server error. Please contact support."},
    )
