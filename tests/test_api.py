"""API endpoint tests"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.models import User, Channel, Feed, ApiKey  # Import models
from app.config import settings

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

# Create test tables
Base.metadata.create_all(bind=engine)

client = TestClient(app)


def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "app_name" in data


def test_create_channel_no_auth():
    """Test creating channel without authentication"""
    # Temporarily disable auth for this test
    original_auth = settings.AUTH_ENABLED
    settings.AUTH_ENABLED = False
    
    response = client.post(
        "/api/channels",
        json={
            "name": "Test Channel",
            "description": "Test Description",
            "public": True,
            "timezone": "UTC"
        }
    )
    
    settings.AUTH_ENABLED = original_auth
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Channel"
    assert "id" in data


def test_get_channels():
    """Test getting list of channels"""
    response = client.get("/api/channels")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_home_page():
    """Test home page loads"""
    response = client.get("/")
    assert response.status_code == 200
    assert b"ThingSpeak" in response.content or settings.APP_NAME.encode() in response.content


def test_channels_page():
    """Test channels page loads"""
    response = client.get("/channels")
    assert response.status_code == 200


def test_api_docs():
    """Test API documentation is accessible"""
    response = client.get("/docs")
    assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

