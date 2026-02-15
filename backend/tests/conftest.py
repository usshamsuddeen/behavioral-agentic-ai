"""
Pytest Configuration
Shared fixtures and configuration for all tests
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db


# Create in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def test_db():
    """Create fresh database tables for each test"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(test_db):
    """Create test client with overridden database"""
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_conversation():
    """Sample conversation data for testing"""
    return {
        "customer_name": "Test Customer",
        "customer_email": "test@example.com",
        "subject": "Test Support Request",
        "channel": "chat",
        "language": "en"
    }


@pytest.fixture
def sample_message():
    """Sample message data for testing"""
    return {
        "content": "I am very frustrated with your service!",
        "sender_type": "customer"
    }


@pytest.fixture
def sample_positive_message():
    """Sample positive message for testing"""
    return {
        "content": "Thank you so much! This is excellent service!",
        "sender_type": "customer"
    }


@pytest.fixture
def sample_spanish_message():
    """Sample Spanish message for testing"""
    return {
        "content": "Estoy muy enojado con este servicio terrible!",
        "sender_type": "customer"
    }
