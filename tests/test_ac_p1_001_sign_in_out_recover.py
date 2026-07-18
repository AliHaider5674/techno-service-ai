"""AC-P1-001 — A user can sign in, sign out, and recover.

Pass condition: A user signs in successfully, signs out successfully,
and recovers the account through the defined recovery flow.
"""
from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select

from techno_service_ai import audit
from techno_service_ai.db import SessionLocal
from techno_service_ai.schema import User


def test_sign_in_success(client: TestClient) -> None:
    r = client.post("/sign-in", data={"username": "admin", "password": "ChangeMe!2026"}, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] in ("/home", "/persona/select")
    assert "tsai_session" in r.cookies


def test_sign_in_with_bad_password_is_rejected(client: TestClient) -> None:
    r = client.post("/sign-in", data={"username": "admin", "password": "wrong"}, follow_redirects=False)
    assert r.status_code == 401
    assert "tsai_session" not in r.cookies


def test_sign_in_with_unknown_user_is_rejected(client: TestClient) -> None:
    r = client.post("/sign-in", data={"username": "ghost", "password": "anything"}, follow_redirects=False)
    assert r.status_code == 401


def test_sign_out_invalidates_session(client: TestClient) -> None:
    client.post("/sign-in", data={"username": "admin", "password": "ChangeMe!2026"})
    # We are signed in.
    r = client.get("/home")
    assert r.status_code == 200

    # Sign out.
    r = client.get("/sign-out", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/sign-in"

    # Now protected routes must fail.
    r = client.get("/home")
    assert r.status_code == 401


def test_recover_resets_password_and_invalidates_sessions(client: TestClient) -> None:
    # Sign in first to establish a session.
    client.post("/sign-in", data={"username": "admin", "password": "ChangeMe!2026"})
    r = client.get("/home")
    assert r.status_code == 200

    # Recover with the right answer.
    r = client.post(
        "/recover",
        data={
            "username": "admin",
            "recovery_answer": "Kuwait City",
            "new_password": "BrandNew!Pass9",
            "new_password_confirm": "BrandNew!Pass9",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert r.headers["location"] == "/sign-in?recovered=1"

    # Old session must be invalidated — protected route returns 401.
    r = client.get("/home")
    assert r.status_code == 401

    # New password works.
    r = client.post("/sign-in", data={"username": "admin", "password": "BrandNew!Pass9"}, follow_redirects=False)
    assert r.status_code == 303
    assert "tsai_session" in r.cookies


def test_recover_with_wrong_answer_is_rejected(client: TestClient) -> None:
    r = client.post(
        "/recover",
        data={
            "username": "admin",
            "recovery_answer": "NotTheRightAnswer",
            "new_password": "Whatever!1",
            "new_password_confirm": "Whatever!1",
        },
        follow_redirects=False,
    )
    assert r.status_code == 400

    # Old password still works.
    r = client.post("/sign-in", data={"username": "admin", "password": "ChangeMe!2026"}, follow_redirects=False)
    assert r.status_code == 303


def test_audit_records_sign_in_and_recovery(client: TestClient) -> None:
    client.post("/sign-in", data={"username": "admin", "password": "ChangeMe!2026"})
    client.post(
        "/recover",
        data={
            "username": "admin",
            "recovery_answer": "kuwait city",
            "new_password": "Another!1Pass",
            "new_password_confirm": "Another!1Pass",
        },
    )
    s = SessionLocal()
    try:
        admin = s.execute(select(User).where(User.username == "admin")).scalar_one()
        events = audit.query(s, actor_user_id=admin.id, limit=50)
        types = [e.event_type for e in events]
        assert "IDENTITY.SIGN_IN" in types
        assert "IDENTITY.RECOVERY_INITIATED" in types
        assert "IDENTITY.RECOVERY_COMPLETED" in types
    finally:
        s.close()
