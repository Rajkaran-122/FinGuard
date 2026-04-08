"""
FinGuard FastAPI Application Factory
====================================
Main application entrypoint. Configures middleware, registers v1 router, 
and manages global exception handling with structured logging.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.database import engine, Base
from app.core.logging import setup_logging, logger
from app.api.v1.router import api_router
from app.services.cache_service import cache_service
from app.core.middleware import RequestIDMiddleware, LoggingMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages application startup and shutdown events.
    Enables async database table creation and cache connection.
    """
    # Startup
    setup_logging()
    logger.info(f"app: starting_up name={settings.APP_TITLE} version={settings.APP_VERSION}")
    
    # Connect to Redis
    await cache_service.connect()
    
    # Tables are created via Alembic in production, 
    # but we can ensure them here for local/dev.
    async with engine.begin() as conn:
        # await conn.run_sync(Base.metadata.create_all) # Optional if using Alembic
        pass
        
    yield
    
    # Shutdown
    await engine.dispose()
    logger.info("app: shutting_down")


app = FastAPI(
    title=settings.APP_TITLE,
    version=settings.APP_VERSION,
    description="Enterprise-grade Finance Data Processing and Access Control Backend",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# --- Middleware ---
app.add_middleware(RequestIDMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate Limiter integration
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- Routers ---
app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["Utility"])
async def health_check():
    """Simple connectivity check."""
    return {
        "status": "healthy", 
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT
    }


# --- Global Exception Handling ---

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Structured 500 error handler avoiding internal leak."""
    logger.error(f"app: unhandled_exception error={str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "Internal server error. Our engineers have been notified.",
            "error": "SERVER_ERROR"
        },
    )
