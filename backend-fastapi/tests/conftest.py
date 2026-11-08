import os
import sys
import pytest
from fastapi.testclient import TestClient

# Ensure backend-fastapi directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import app
from database import SessionLocal
from config import settings


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session")
def consultant_password():
    return (
        os.getenv("SEED_CONSULTANT_PASSWORD")
        or settings.SEED_CONSULTANT_PASSWORD
        or os.getenv("SEED_PASSWORD")
        or settings.SEED_PASSWORD
        or "ConsultantDevPass#2026"
    )


@pytest.fixture(scope="session")
def viewer_password():
    return (
        os.getenv("SEED_CLIENT_VIEWER_PASSWORD")
        or settings.SEED_CLIENT_VIEWER_PASSWORD
        or os.getenv("SEED_PASSWORD")
        or settings.SEED_PASSWORD
        or "ViewerDevPass#2026"
    )
