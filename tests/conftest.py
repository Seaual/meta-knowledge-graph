"""
Root-level pytest configuration for MKG backend tests.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Pre-inject mock mkg.llm so tests can run without langchain installed
sys.modules["mkg.llm"] = MagicMock()

import pytest

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from mkg.database import Database


@pytest.fixture
def test_db():
    """Create an in-memory SQLite database for testing."""
    db = Database(":memory:")
    db.connect()
    yield db
    db.close()


@pytest.fixture
def app(test_db):
    """Create FastAPI test app with test database."""
    from backend.main import app

    original_deps = app.dependency_overrides.copy()

    yield app

    app.dependency_overrides = original_deps


@pytest.fixture
def client(app):
    """Create test client."""
    with TestClient(app) as c:
        yield c
