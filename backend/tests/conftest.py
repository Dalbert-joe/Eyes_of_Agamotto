import os

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["JWT_SECRET"] = "test-secret-012345678901234567890123"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models import User
from app.security import hash_password

engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


@pytest.fixture
def db():
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db):
    def override_db():
        yield db
    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def users(db):
    records = [
        User(email="organizer@example.com", name="Organizer", role="organizer", password_hash=hash_password("password123")),
        User(email="judge1@example.com", name="Judge One", role="judge", password_hash=hash_password("password123")),
        User(email="judge2@example.com", name="Judge Two", role="judge", password_hash=hash_password("password123")),
        User(email="participant1@example.com", name="Participant One", role="participant", password_hash=hash_password("password123"), college="College A"),
        User(email="participant2@example.com", name="Participant Two", role="participant", password_hash=hash_password("password123"), college="College B"),
    ]
    db.add_all(records)
    db.commit()
    return {u.email: u for u in records}


def login(client, email, password="password123"):
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["accessToken"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def rubric():
    return [
        {"id": "innovation", "name": "Innovation", "description": "", "weight": 60, "maxScore": 10},
        {"id": "technical", "name": "Technical", "description": "", "weight": 40, "maxScore": 10},
    ]


def event_payload(code="TEST-001"):
    return {
        "title": "Test Hackathon",
        "tagline": "Test",
        "description": "Integration test",
        "eventCode": code,
        "status": "registration",
        "isPublic": True,
        "registrationMode": "open",
        "editingPolicy": "allow-until-deadline",
        "versioningEnabled": True,
        "minTeamSize": 1,
        "maxTeamSize": 4,
        "judgesPerProject": 2,
        "tracks": ["General"],
        "rubric": rubric(),
        "normalizationMethod": "z_score",
        "prizes": "",
    }
