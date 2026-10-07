"""
Pytest configuration fixtures.
Sets up an isolated SQLite test database and FastAPI TestClient.
"""
import pytest
import shutil
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.main import app
from app.db.database import Base, get_db
from app.config import settings

# Test database file in a temporary location
TEST_DB_PATH = settings.BASE_DIR / "test_certificates.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_PATH}"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Initializes tables before test session and cleans up db/files on teardown."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()
    if TEST_DB_PATH.exists():
        try:
            TEST_DB_PATH.unlink()
        except PermissionError:
            pass

    # Clean up test output in storage if any
    test_storage = settings.STORAGE_DIR
    for child in test_storage.iterdir():
        if child.is_dir() and child.name != ".gitkeep":
            shutil.rmtree(child, ignore_errors=True)


@pytest.fixture
def db_session():
    """Provides a fresh transactional session for test cases."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    """Overrides the get_db dependency with test database session."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
