"""
Application Configuration
========================
All environment variables are validated at startup via pydantic-settings.
"""

from typing import List
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application Metadata
    APP_TITLE: str = "FinGuard API"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # Database (AsyncPG expected for production)
    # Default is SQLite for local development
    DATABASE_URL: str = "sqlite+aiosqlite:///./finance.db"
    
    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: str) -> str:
        """
        Render provides postgres:// URLs, but SQLAlchemy Async requires 
        postgresql+asyncpg:// format.
        """
        if isinstance(v, str) and v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+asyncpg://", 1)
        return v
    DB_ECHO: bool = False
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # Redis Caching
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_DEFAULT_TTL: int = 300  # 5 minutes

    # JWT Authentication
    JWT_SECRET: str = "finguard-access-secret-rajkaran-yadav-2025"
    JWT_REFRESH_SECRET: str = "finguard-refresh-secret-rajkaran-yadav-2025"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS & Security
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8080"
    BCRYPT_ROUNDS: int = 12

    # Logging
    LOG_LEVEL: str = "INFO"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
