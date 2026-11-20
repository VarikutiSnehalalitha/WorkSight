"""Pytest Fixtures for Isolated WorkSight Integration & Unit Tests."""

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure backend root is importable
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ["DATABASE_URL"] = "sqlite:///./test_worksight.db"
os.environ["ALLOW_SIMULATED_FEEDS"] = "true"

from app.core.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.services.seed import seed_demo_data  # noqa: E402

TEST_DB_PATH = BACKEND_DIR / "test_worksight.db"
TEST_ENGINE = create_engine(
    f"sqlite:///{TEST_DB_PATH}",
    connect_args={"check_same_thread": False},
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
    Base.metadata.create_all(bind=TEST_ENGINE)
    db = TestSessionLocal()
    try:
        seed_demo_data(db)
    finally:
        db.close()

    def override_get_db():
        session = TestSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()
    TEST_ENGINE.dispose()
    if TEST_DB_PATH.exists():
        try:
            TEST_DB_PATH.unlink()
        except OSError:
            pass


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


def _login_headers(client: TestClient, email: str) -> dict:
    resp = client.post("/api/auth/login", json={"email": email, "password": "WorkSight2026!"})
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def owner_headers(client):
    return _login_headers(client, "owner@worksight.io")


@pytest.fixture(scope="session")
def hr_headers(client):
    return _login_headers(client, "hr@worksight.io")


@pytest.fixture(scope="session")
def manager_headers(client):
    return _login_headers(client, "manager@worksight.io")


@pytest.fixture(scope="session")
def employee_headers(client):
    return _login_headers(client, "employee@worksight.io")
