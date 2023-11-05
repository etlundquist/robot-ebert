import os
import pytest

from fastapi.testclient import TestClient

from src.backend.app.main import app
from src.backend.app.database import metadata, get_test_engine


@pytest.fixture(scope="session")
def client():
    """fixture to generate an HTTPX test client"""

    client = TestClient(app)
    return client


@pytest.fixture(scope="session")
def test_engine():
    """fixture to create a SQLAlchemy engine backed by a local DuckDB database"""

    test_engine = get_test_engine(echo=True)
    metadata.create_all(test_engine)
    return test_engine


def pytest_sessionfinish(session, exitstatus):
    """run clean-up code at the end of the test session"""

    os.remove("database.duckdb")
    os.remove("database.duckdb.wal")
