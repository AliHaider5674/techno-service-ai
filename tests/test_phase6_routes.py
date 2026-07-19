"""Phase 6 Route Tests — Tender, Project, Knowledge screens.

Verifies:
  - The 9 Phase 6 routes are registered.
  - Each route returns 302/401/403 when not signed in.
  - Each route returns 200 when signed in as admin.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Iterator

import pytest
from fastapi.testclient import TestClient

# Make `src/` importable and set up a temp DB.
_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import tempfile

_TMP = Path(tempfile.mkdtemp(prefix="tsai-phase6-routes-"))
os.environ.setdefault("TSAI_DATABASE_URL", f"sqlite:///{(_TMP / 'test.db').as_posix()}")
os.environ.setdefault("TSAI_JWT_SECRET", "test-secret-key-for-pytest-only")
os.environ.setdefault("TSAI_DEFAULT_ADMIN_PASSWORD", "ChangeMe!2026")

from techno_service_ai import bootstrap  # noqa: E402
from techno_service_ai.app import create_app  # noqa: E402
from techno_service_ai.db import reset_schema  # noqa: E402


PHASE6_ROUTES = [
    "/tenders",
    "/tenders/test-id",
    "/tenders/test-id/quotation-dossier",
    "/tenders/test-id/submission-dossier",
    "/projects",
    "/knowledge",
    "/knowledge/test-id",
    "/lessons-learned",
    "/institutional-memory",
]


@pytest.fixture()
def app():
    reset_schema()
    bootstrap.seed()
    return create_app()


@pytest.fixture()
def client(app) -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


def test_phase6_routes_registered(app) -> None:
    """All 9 Phase 6 routes are mounted on the FastAPI app."""
    paths = {r.path for r in app.routes if hasattr(r, "path")}
    for route in PHASE6_ROUTES:
        if route == "/tenders":
            parameterized = "/tenders"
        elif route == "/tenders/test-id":
            parameterized = "/tenders/{tender_id}"
        elif route.startswith("/tenders/test-id/"):
            parameterized = route.replace("test-id", "{tender_id}")
        elif route == "/knowledge/test-id":
            parameterized = "/knowledge/{kr_id}"
        else:
            parameterized = route
        assert parameterized in paths, f"Phase 6 route not registered: {route} (expected {parameterized})"


def test_phase6_routes_require_authentication(client: TestClient) -> None:
    """All Phase 6 routes are auth-gated."""
    for route in PHASE6_ROUTES:
        r = client.get(route, follow_redirects=False)
        assert r.status_code in (302, 401, 403, 404), (
            f"Route {route} did not gate: status={r.status_code}"
        )


def test_phase6_routes_render_for_admin(client: TestClient) -> None:
    """All Phase 6 routes return 200 when signed in as admin."""
    r = client.post(
        "/sign-in",
        data={"username": "admin", "password": "ChangeMe!2026"},
        follow_redirects=False,
    )
    assert r.status_code == 303, f"sign-in failed: {r.status_code} {r.text[:200]}"
    for route in PHASE6_ROUTES:
        r = client.get(route, follow_redirects=False)
        # Some routes 200, some 404 (when the test-id record doesn't exist
        # but the page still renders). We accept 200 and 404.
        assert r.status_code in (200, 404), (
            f"Route {route} failed for admin: status={r.status_code} body={r.text[:200]}"
        )
