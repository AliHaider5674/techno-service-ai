"""Shared pytest fixtures.

Each test gets a fresh temporary SQLite database file (so SQLite triggers
survive across the same TestClient) with the schema applied and the
default roles, policies, and admin user seeded.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from typing import Iterator

import pytest
from fastapi.testclient import TestClient

# Make `src/` importable so `import techno_service_ai` works without a
# full editable install. (A pyproject.toml is included for production.)
_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# Ensure the test environment uses a temp DB and a fixed JWT secret.
_TMP = Path(tempfile.mkdtemp(prefix="tsai-tests-"))
os.environ["TSAI_DATABASE_URL"] = f"sqlite:///{(_TMP / 'test.db').as_posix()}"
os.environ["TSAI_JWT_SECRET"] = "test-secret-key-for-pytest-only-do-not-use-in-prod"
os.environ["TSAI_DEFAULT_ADMIN_PASSWORD"] = "ChangeMe!2026"

# Imports must come AFTER env vars are set, so the config module picks them up.
from techno_service_ai import bootstrap  # noqa: E402
from techno_service_ai.app import create_app  # noqa: E402
from techno_service_ai.db import SessionLocal, reset_schema  # noqa: E402


@pytest.fixture()
def app():
    """Yield a FastAPI app with a freshly bootstrapped database.

    The audit log is append-only (Constitution Article XX), so we cannot
    truncate rows between tests. We drop and recreate all tables and
    re-seed the default roles/policies/admin for each test.
    """
    reset_schema()
    bootstrap.seed()
    return create_app()


@pytest.fixture()
def client(app) -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def db_session() -> Iterator:
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()
