"""
Pytest configuration and shared async fixtures for tests.
Uses in-memory aiosqlite database for fast, isolated, async testing.
"""

import pytest
import pytest_asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.models.user import User, UserRole, UserStatus
from app.core.security import security_manager

# --- Async Test Database Configuration ---
TEST_SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    TEST_SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def db_schema():
    """Create all tables in the in-memory database."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional scoped session for tests."""
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Async test client overriding the get_db dependency."""
    
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(
        transport=ASGITransport(app=app), 
        base_url="http://test"
    ) as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def admin_user(db_session: AsyncSession) -> User:
    """Creates a mock admin user in DB."""
    user = User(
        first_name="Admin",
        last_name="Test",
        email="admin_test@finance.dev",
        hashed_password=security_manager.get_password_hash("Admin@123"),
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def admin_token(admin_user: User) -> str:
    """Returns JWT access token for the admin user."""
    return security_manager.create_access_token({
        "sub": str(admin_user.id), 
        "email": admin_user.email,
        "role": admin_user.role.value
    })


@pytest_asyncio.fixture(scope="function")
def admin_headers(admin_token: str):
    """Returns Auth headers block for test client."""
    return {"Authorization": f"Bearer {admin_token}"}
