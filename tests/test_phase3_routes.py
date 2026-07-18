"""Smoke test for the 11 Phase 3 presentation screens.

Verifies that each of the 10 verification / approval screens from
UI/UX §4.6 and §4.7, plus the notification inbox from §10, renders
successfully for an authenticated admin.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


PHASE3_PATHS = [
    "/verification/preliminary-queue",
    "/verification/specialist-queue",
    "/verification/independent-final-queue",
    "/verification/workspace?claim_id=test-claim",
    "/verification/claim-classification",
    "/verification/independence-tracker",
    "/approvals/inbox",
    "/approvals/request?request_id=test-request",
    "/approvals/records",
    "/approvals/authority-matrix",
    "/notifications/inbox",
]


def test_phase3_11_routes_registered(client) -> None:
    """All 11 Phase 3 routes are registered on the app."""
    app = client.app
    paths = {r.path for r in app.routes if hasattr(r, "path")}
    for p in PHASE3_PATHS:
        # Strip query string for the path match
        path = p.split("?")[0]
        assert path in paths, f"Phase 3 route {p} not registered"


def test_phase3_routes_render_for_admin(client: TestClient) -> None:
    """All 11 Phase 3 routes return 200 for an authenticated admin."""
    # Sign in.
    r = client.post(
        "/sign-in", data={"username": "admin", "password": "ChangeMe!2026"},
        follow_redirects=False,
    )
    assert r.status_code in (200, 303), f"sign-in failed: {r.status_code}"
    for p in PHASE3_PATHS:
        r = client.get(p, follow_redirects=False)
        assert r.status_code == 200, f"{p} returned {r.status_code}"
        # The page contains the Phase 3 base.
        body = r.text
        assert "Phase 3" in body or "phase3" in body.lower() or "Constitution" in body


def test_phase3_routes_require_authentication(client: TestClient) -> None:
    """The 11 Phase 3 routes require authentication (return 401 without a session)."""
    for p in PHASE3_PATHS:
        r = client.get(p, follow_redirects=False)
        # 401 is the expected status for unauthenticated.
        assert r.status_code == 401, f"{p} should be 401 without auth, got {r.status_code}"


def test_phase3_routes_have_constitutional_text(client: TestClient) -> None:
    """Each rendered Phase 3 page contains a constitutional reference."""
    # Sign in.
    client.post(
        "/sign-in", data={"username": "admin", "password": "ChangeMe!2026"},
        follow_redirects=False,
    )
    for p in PHASE3_PATHS:
        r = client.get(p, follow_redirects=False)
        body = r.text
        # Every page carries a "Document 06" or "Constitution" reference.
        assert (
            "Document 06" in body
            or "Constitution" in body
            or "Authority Matrix" in body
            or "constitutional" in body.lower()
        ), f"{p} has no constitutional text"
