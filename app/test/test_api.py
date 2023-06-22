import os
import pytest
from datetime import datetime, timedelta
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import create_engine

from app.api import app
from app import services


@pytest.fixture(scope="module")
def client():
    client = TestClient(app)
    yield client


@pytest.fixture(scope="module")
def db():
    engine = create_engine("sqlite:///./test.db", connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture(scope="module")
def access_token(db):
    test_user = {
        "email": "test@example.com",
        "password": "testpassword"
    }
    services.create_user(test_user, db)
    token = services.create_token(test_user)
    return token


def test_create_user(client, db):
    test_user = {
        "email": "test@example.com",
        "password": "testpassword"
    }
    response = client.post("/api/users", json=test_user)
    assert response.status_code == status.HTTP_200_OK
    assert "access_token" in response.json()
    # Clean up the test user from the database
    db_user = services.get_user_by_email(test_user["email"], db)
    db.delete(db_user)
    db.commit()


def test_generate_token(client, db):
    test_user = {
        "email": "test@example.com",
        "password": "testpassword"
    }
    services.create_user(test_user, db)
    response = client.post("/api/token", data=test_user)
    assert response.status_code == status.HTTP_200_OK
    assert "access_token" in response.json()
    # Clean up the test user from the database
    db_user = services.get_user_by_email(test_user["email"], db)
    db.delete(db_user)
    db.commit()


def test_get_user(client, access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.get("/api/users/my-profile", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["email"] == "test@example.com"


# def test_get_youtube_videos(client, access_token):
#     headers = {"Authorization": f"Bearer {access_token}"}
#     search_params = {"q": "test query"}
#     response = client.post("/api/youtube-videos", json=search_params, headers=headers)
#     assert response.status_code == status.HTTP_200_OK
#     assert "video_ids" in response.json()


# def test_get_video_transcript(client, access_token):
#     headers = {"Authorization": f"Bearer {access_token}"}
#     video_id = "test_video_id"
#     response = client.post(f"/api/transcript/{video_id}", headers=headers)
#     assert response.status_code == status.HTTP_200_OK
#     assert "video_id" in response.json()
#     assert "transcript" in response.json()


# def test_generate_summaries(client, access_token):
#     headers = {"Authorization": f"Bearer {access_token}"}
#     transcript = {
#         "transcript": "This is a test transcript."
#     }
#     response = client.post("/api/summarize-transcript", json=transcript, headers=headers)
#     assert response.status_code == status.HTTP_200_OK
#     assert "summary" in response.json()


# def test_publish_summaries(client, access_token):
#     headers = {"Authorization": f"Bearer {access_token}"}
#     summary = {
#         "summary": "This is a test summary."
#     }
#     response = client.post("/api/publish-medium", json=summary, headers=headers)
#     assert response.status_code == status.HTTP_200_OK
#     assert "message" in response.json()


# # Clean up the test user from the database after all tests are completed
# def pytest_sessionfinish(session, exitstatus):
#     db = services.get_test_db()
#     test_user = services.get_user_by_email("test@example.com", db)
#     if test_user:
#         db.delete(test_user)
#         db.commit()
#         db.close()
