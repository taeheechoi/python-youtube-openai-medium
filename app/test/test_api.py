import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import patch

from app.api import app
from app import services, models, schemas


@pytest.fixture(scope="module")
def test_client():
    client = TestClient(app)
    return client


@pytest.fixture(scope="module")
def test_db():
    db = services.get_db()
    yield db

    # Clear records created during testing
    with db.connect() as conn:
        conn.execute(schemas.User.__table__.delete())


def test_create_user(test_client):
    user_data = {
        "email": "test@example.com",
        "password": "testpassword"
    }

    response = test_client.post("/api/users", json=user_data)
    assert response.status_code == 200

    user = response.json()
    assert user["email"] == user_data["email"]
    assert "access_token" in user
