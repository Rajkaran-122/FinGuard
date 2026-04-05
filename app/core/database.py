"""
Database Configuration
=====================
SQLAlchemy engine with WAL mode and FK enforcement for SQLite.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import settings

connect_args = {}
# Removed check_same_thread for SQLite

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False,
    pool_pre_ping=True,
)

# Removed SQLite PRAGMA event listener


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass
