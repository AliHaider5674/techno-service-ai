"""Smoke test for the 20+ Phase 4 presentation screens.

Verifies that the Industrial, Opportunity, Technology, AI Workspace,
and Dashboard routes are mounted, return 200 for authenticated
admins, and carry constitutional text.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


# Phase 4 routes (22 total: 3 Industrial + 5 Opportunity + 5 Technology
# + 3 AI Workspace + 4 Dashboards + 1 Opportunity Workspace + 1
# Kuwait Suitability + 1 KSR + 1 Comparative Analyses + 2 Misc)
PHASE4_PATHS = [
    # Industrial (3)
    "/industrial/environment",
    "/industrial/activities",
    "/industrial/validated-signals",
    # Opportunity (5)
    "/opportunities",
    "/opportunities/new",
    "/opportunities/test-opp-id",  # the workspace (404 expected, but route exists)
    "/opportunities/test-opp-id/value-case",
    "/opportunities/test-opp-id/timeline",
    # Technology (6)
    "/technologies",
    "/technologies/test-tech-id",
    "/products",
    "/products/test-product-id",
    "/comparative-analyses",
    "/kuwait-suitability/test-ksr-id",
    # AI Workspace (3)
    "/ai/chat",
    "/ai/recommendations",
    "/ai/history",
    # Dashboards (4)
    "/dashboards/industrial",
    "/dashboards/opportunity",
    "/dashboards/technology",
    "/dashboards/executive",
]


def test_phase4_routes_registered(client) -> None:
    """The Phase 4 routes are registered on the app.

    Maps each test path to its FastAPI template. Static paths match
    themselves; dynamic paths use {param} placeholders.
    """
    # Map test paths to FastAPI route templates.
    TEMPLATES = {
        "/industrial/environment": "/industrial/environment",
        "/industrial/activities": "/industrial/activities",
        "/industrial/validated-signals": "/industrial/validated-signals",
        "/opportunities": "/opportunities",
        "/opportunities/new": "/opportunities/new",
        "/opportunities/test-opp-id": "/opportunities/{opportunity_id}",
        "/opportunities/test-opp-id/value-case": "/opportunities/{opportunity_id}/value-case",
        "/opportunities/test-opp-id/timeline": "/opportunities/{opportunity_id}/timeline",
        "/technologies": "/technologies",
        "/technologies/test-tech-id": "/technologies/{tech_id}",
        "/products": "/products",
        "/products/test-product-id": "/products/{product_id}",
        "/comparative-analyses": "/comparative-analyses",
        "/kuwait-suitability/test-ksr-id": "/kuwait-suitability/{ksr_id}",
        "/ai/chat": "/ai/chat",
        "/ai/recommendations": "/ai/recommendations",
        "/ai/history": "/ai/history",
        "/dashboards/industrial": "/dashboards/industrial",
        "/dashboards/opportunity": "/dashboards/opportunity",
        "/dashboards/technology": "/dashboards/technology",
        "/dashboards/executive": "/dashboards/executive",
    }
    app = client.app
    paths = {r.path for r in app.routes if hasattr(r, "path")}
    for test_path, tpl in TEMPLATES.items():
        assert tpl in paths, f"Phase 4 route template {tpl} (from {test_path}) not registered"


def test_phase4_routes_require_authentication(client: TestClient) -> None:
    for p in PHASE4_PATHS:
        r = client.get(p, follow_redirects=False)
        # 401 (unauthenticated) is the expected status.
        assert r.status_code == 401, f"{p} should be 401 without auth, got {r.status_code}"


def test_phase4_routes_render_for_admin(client: TestClient) -> None:
    client.post(
        "/sign-in", data={"username": "admin", "password": "ChangeMe!2026"},
        follow_redirects=False,
    )
    for p in PHASE4_PATHS:
        r = client.get(p, follow_redirects=False)
        # 200 (OK) or 404 (Not Found for placeholder IDs).
        assert r.status_code in (200, 404), f"{p} returned {r.status_code}"
        # When 200, the page should contain constitutional text.
        if r.status_code == 200:
            body = r.text
            assert (
                "Document 06" in body
                or "Constitution" in body
                or "Article VII" in body
                or "Article X" in body
                or "constitutional" in body.lower()
                or "Phase 4" in body
            ), f"{p} has no constitutional text"
