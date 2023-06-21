import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api import app
from app.database import SessionLocal, engine
from app import schemas, services

# Create a test database and override the default database dependency


# Initialize the test client
client = TestClient(app)


@pytest.fixture
def db():
    # Use a transactional database session for each test
    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture(autouse=True)
def cleanup(db):
    yield
    services.delete_user_by_email("test@example.com", db)


def test_create_user(db):
    user_data = {
        "email": "test@example.com",
        "password": "testpassword",
    }

    response = client.post("/api/users", json=user_data)
    assert response.status_code == status.HTTP_200_OK
    assert "access_token" in response.json()


# def test_generate_token(db):
#     user_data = {
#         "username": "test@example.com",
#         "password": "testpassword",
#     }

#     response = client.post("/api/token", data=user_data)
#     assert response.status_code == status.HTTP_200_OK
#     assert "access_token" in response.json()


# def test_get_user(db):
#     # Create a test user in the database
#     user = schemas.User(email="test@example.com", password="testpassword")
#     db.add(user)
#     db.commit()

#     # Get the access token for the test user
#     token_data = {
#         "username": "test@example.com",
#         "password": "testpassword",
#     }
#     token_response = client.post("/api/token", data=token_data)
#     access_token = token_response.json()["access_token"]

#     headers = {"Authorization": f"Bearer {access_token}"}
#     response = client.get("/api/users/my-profile", headers=headers)

#     assert response.status_code == status.HTTP_200_OK
#     assert response.json()["email"] == "test@example.com"

# Write tests for the remaining endpoints in a similar manner
