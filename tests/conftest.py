"""
Pytest configuration and shared fixtures for tests.
Uses in-memory SQLite database for fast, isolated testing.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base
from app.core.dependencies import get_db
from app.models.user import User, UserRole
from app.core.security import hash_password, create_access_token

# In-Memory SQLite configuration
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session")
def db_engine():
    """Create all tables in the in-memory database."""
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db_session(db_engine):
    """Provide a transactional scoped session for tests."""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="function")
def client(db_session):
    """Test client overriding the get_db dependency."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
def admin_user(db_session):
    """Creates a mock admin user in DB with full permissions."""
    user = User(
        name="Admin Test",
        email="admin_test@finance.dev",
        password_hash=hash_password("Admin@123"),
        role=UserRole.ADMIN,
        permissions=["dashboard:view", "records:read", "records:write", "users:manage"]
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture(scope="function")
def admin_token(admin_user):
    """Returns JWT token for the admin user."""
    return create_access_token({"sub": admin_user.id, "role": admin_user.role.value})

@pytest.fixture(scope="function")
def admin_headers(admin_token):
    """Returns Auth headers block for test client."""
    return {"Authorization": f"Bearer {admin_token}"}

# --- IDOR Test Fixtures ---

@pytest.fixture(scope="function")
def viewer_user(db_session):
    """Creates a restricted viewer user with read-only permissions."""
    user = User(
        name="Viewer Test",
        email="viewer_test@finance.dev",
        password_hash=hash_password("Viewer@123"),
        role=UserRole.VIEWER,
        permissions=["dashboard:view", "records:read"]
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture(scope="function")
def viewer_token(viewer_user):
    """Returns JWT token for the viewer user."""
    return create_access_token({"sub": viewer_user.id, "role": viewer_user.role.value})

@pytest.fixture(scope="function")
def viewer_headers(viewer_token):
    """Returns Auth headers for viewer user."""
    return {"Authorization": f"Bearer {viewer_token}"}
