"""AC-P1-002 — A user can select a persona.

Pass condition: A multi-role user selects each available persona and
the system context changes accordingly.
"""
from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select

from techno_service_ai import access, audit
from techno_service_ai.db import SessionLocal
from techno_service_ai.schema import Persona, Role, User


def _make_user_with_two_roles(username: str) -> None:
    """Create a user with two roles that share the same sod_class so SoD allows both."""
    from techno_service_ai import security
    s = SessionLocal()
    try:
        # Two roles in the same sod_class 'DEFAULT' = no SoD conflict.
        biz_role = s.execute(select(Role).where(Role.code == "BIZDEV")).scalar_one()
        viewer_role = s.execute(select(Role).where(Role.code == "VIEWER")).scalar_one()
        # BIZDEV has sod_class='BIZDEV' and VIEWER has sod_class='VIEWER' — they would
        # conflict. Use BIZDEV + ANALYST, both DEFAULT? No, BIZDEV is 'BIZDEV'. Add a
        # new role for this test.
        r = Role(code="OPS_ASST", name="Operations Assistant", sod_class="DEFAULT", description="")
        s.add(r)
        s.flush()

        u = User(
            username=username,
            email=f"{username}@example.com",
            display_name=username.title(),
            password_hash=security.hash_password("Password!1"),
            recovery_question="q",
            recovery_answer_hash=security.hash_recovery_answer("a"),
        )
        s.add(u)
        s.flush()

        admin = s.execute(select(User).where(User.username == "admin")).scalar_one()
        admin_role_code = "ADMIN"
        access.assign_role(s, user=u, role=biz_role, actor=admin, actor_role_code=admin_role_code)
        access.assign_role(s, user=u, role=r, actor=admin, actor_role_code=admin_role_code)
        s.commit()
    finally:
        s.close()


def test_user_with_multiple_personas_can_select_each(client: TestClient) -> None:
    _make_user_with_two_roles("multi")
    # Sign in.
    r = client.post("/sign-in", data={"username": "multi", "password": "Password!1"}, follow_redirects=False)
    assert r.status_code == 303
    # The user has multiple personas, so we are routed to persona selection.
    assert r.headers["location"] == "/persona/select"

    # The page shows both personas.
    r = client.get("/persona/select")
    assert r.status_code == 200
    body = r.text
    assert "BIZDEV" in body
    assert "OPS_ASST" in body

    # Read available personas and switch to one.
    s = SessionLocal()
    try:
        u = s.execute(select(User).where(User.username == "multi")).scalar_one()
        personas = s.execute(select(Persona).where(Persona.user_id == u.id).order_by(Persona.label)).scalars().all()
        first = personas[0]
    finally:
        s.close()

    r = client.post("/persona/select", data={"persona_id": first.id}, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/home"

    # The home page reflects the selected persona.
    r = client.get("/home")
    assert r.status_code == 200
    assert first.label in r.text

    # Now switch to the second persona.
    r = client.get("/persona/select")
    assert r.status_code == 200
    s = SessionLocal()
    try:
        u = s.execute(select(User).where(User.username == "multi")).scalar_one()
        personas = s.execute(select(Persona).where(Persona.user_id == u.id).order_by(Persona.label)).scalars().all()
        second = [p for p in personas if p.id != first.id][0]
    finally:
        s.close()

    r = client.post("/persona/select", data={"persona_id": second.id}, follow_redirects=False)
    assert r.status_code == 303
    r = client.get("/home")
    assert r.status_code == 200
    assert second.label in r.text


def test_single_persona_user_skips_selection(client: TestClient) -> None:
    # The default admin has ADMIN + AUDITOR. ADMIN has sod_class='ADMIN' and
    # AUDITOR has sod_class='AUDITOR' — different buckets! SoD would reject
    # the dual-assignment. Let's just check that the default admin is routed
    # correctly when there is only one active persona available. Create a
    # fresh user with a single role.
    from techno_service_ai import security
    s = SessionLocal()
    try:
        viewer = s.execute(select(Role).where(Role.code == "VIEWER")).scalar_one()
        u = User(
            username="lonesome",
            email="lonesome@example.com",
            display_name="Lonesome",
            password_hash=security.hash_password("Password!1"),
            recovery_question="q",
            recovery_answer_hash=security.hash_recovery_answer("a"),
        )
        s.add(u)
        s.flush()
        admin = s.execute(select(User).where(User.username == "admin")).scalar_one()
        access.assign_role(s, user=u, role=viewer, actor=admin, actor_role_code="ADMIN")
        s.commit()
    finally:
        s.close()

    r = client.post("/sign-in", data={"username": "lonesome", "password": "Password!1"}, follow_redirects=False)
    assert r.status_code == 303
    # Single persona → straight to home.
    assert r.headers["location"] == "/home"


def test_persona_selection_is_audited(client: TestClient) -> None:
    _make_user_with_two_roles("audited_multi")
    client.post("/sign-in", data={"username": "audited_multi", "password": "Password!1"})
    s = SessionLocal()
    try:
        u = s.execute(select(User).where(User.username == "audited_multi")).scalar_one()
        personas = s.execute(select(Persona).where(Persona.user_id == u.id)).scalars().all()
        first = personas[0]
    finally:
        s.close()
    client.post("/persona/select", data={"persona_id": first.id})

    s = SessionLocal()
    try:
        u = s.execute(select(User).where(User.username == "audited_multi")).scalar_one()
        events = audit.query(s, actor_user_id=u.id, event_type="PERSONA.SELECTED")
        assert len(events) >= 1
        e = events[0]
        assert e.target_id == first.id
        assert e.payload_json  # carries persona_label and role_id
    finally:
        s.close()
