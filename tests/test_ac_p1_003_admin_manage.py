"""AC-P1-003 — An Administrator can manage users, roles, and access policy.

Pass condition: An Administrator creates, updates, suspends, and archives
a user; assigns and revokes a role; defines and changes an access policy.
"""
from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select

from techno_service_ai.db import SessionLocal
from techno_service_ai.schema import AccessPolicy, Role, User, UserStatus


def _admin_sign_in(client: TestClient) -> None:
    client.post("/sign-in", data={"username": "admin", "password": "ChangeMe!2026"})


def test_admin_creates_user(client: TestClient) -> None:
    _admin_sign_in(client)
    r = client.post(
        "/admin/users/new",
        data={
            "username": "alice",
            "email": "alice@example.com",
            "display_name": "Alice",
            "password": "Password!1",
            "recovery_question": "q",
            "recovery_answer": "a",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert r.headers["location"].startswith("/admin/users/")

    s = SessionLocal()
    try:
        u = s.execute(select(User).where(User.username == "alice")).scalar_one()
        assert u.status == UserStatus.ACTIVE
        assert u.email == "alice@example.com"
    finally:
        s.close()


def test_admin_updates_user(client: TestClient) -> None:
    _admin_sign_in(client)
    r = client.post(
        "/admin/users/new",
        data={
            "username": "bob",
            "email": "bob@example.com",
            "display_name": "Bob",
            "password": "Password!1",
            "recovery_question": "q",
            "recovery_answer": "a",
        },
    )
    s = SessionLocal()
    try:
        u = s.execute(select(User).where(User.username == "bob")).scalar_one()
        uid = u.id
    finally:
        s.close()

    r = client.post(
        f"/admin/users/{uid}",
        data={
            "display_name": "Robert",
            "email": "robert@example.com",
            "status_value": "ACTIVE",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303

    s = SessionLocal()
    try:
        u = s.execute(select(User).where(User.username == "bob")).scalar_one()
        assert u.display_name == "Robert"
        assert u.email == "robert@example.com"
    finally:
        s.close()


def test_admin_suspends_and_archives_user(client: TestClient) -> None:
    _admin_sign_in(client)
    client.post(
        "/admin/users/new",
        data={
            "username": "carol",
            "email": "carol@example.com",
            "display_name": "Carol",
            "password": "Password!1",
            "recovery_question": "q",
            "recovery_answer": "a",
        },
    )
    s = SessionLocal()
    try:
        u = s.execute(select(User).where(User.username == "carol")).scalar_one()
        uid = u.id
    finally:
        s.close()

    # Suspend.
    r = client.post(
        f"/admin/users/{uid}",
        data={"display_name": "Carol", "email": "carol@example.com", "status_value": "SUSPENDED"},
        follow_redirects=False,
    )
    assert r.status_code == 303
    s = SessionLocal()
    try:
        u = s.execute(select(User).where(User.username == "carol")).scalar_one()
        assert u.status == UserStatus.SUSPENDED
    finally:
        s.close()

    # Archive.
    r = client.post(
        f"/admin/users/{uid}",
        data={"display_name": "Carol", "email": "carol@example.com", "status_value": "ARCHIVED"},
        follow_redirects=False,
    )
    assert r.status_code == 303
    s = SessionLocal()
    try:
        u = s.execute(select(User).where(User.username == "carol")).scalar_one()
        assert u.status == UserStatus.ARCHIVED
    finally:
        s.close()


def test_admin_assigns_and_revokes_role(client: TestClient) -> None:
    _admin_sign_in(client)
    client.post(
        "/admin/users/new",
        data={
            "username": "dave",
            "email": "dave@example.com",
            "display_name": "Dave",
            "password": "Password!1",
            "recovery_question": "q",
            "recovery_answer": "a",
        },
    )
    s = SessionLocal()
    try:
        u = s.execute(select(User).where(User.username == "dave")).scalar_one()
        uid = u.id
        analyst = s.execute(select(Role).where(Role.code == "ANALYST")).scalar_one()
        rid = analyst.id
    finally:
        s.close()

    # Assign.
    r = client.post(
        f"/admin/users/{uid}/roles/assign",
        data={"role_id": rid},
        follow_redirects=False,
    )
    assert r.status_code == 303

    s = SessionLocal()
    try:
        from techno_service_ai import access as acc
        roles = acc.user_active_roles(s, uid)
        assert any(r.code == "ANALYST" for r in roles)
    finally:
        s.close()

    # Revoke.
    r = client.post(
        f"/admin/users/{uid}/roles/{rid}/revoke",
        data={"reason": "Test revocation"},
        follow_redirects=False,
    )
    assert r.status_code == 303

    s = SessionLocal()
    try:
        from techno_service_ai import access as acc
        roles = acc.user_active_roles(s, uid)
        assert not any(r.code == "ANALYST" for r in roles)
    finally:
        s.close()


def test_admin_defines_and_changes_access_policy(client: TestClient) -> None:
    _admin_sign_in(client)
    r = client.post(
        "/admin/access-policies",
        data={
            "code": "POL-TEST",
            "name": "Test Policy",
            "description": "A test policy",
            "decision_class": "CLASS_3",
            "required_approver_role_code": "EXEC",
            "sod_exclusion_role_codes": "ADMIN,ANALYST",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303
    s = SessionLocal()
    try:
        p = s.execute(select(AccessPolicy).where(AccessPolicy.code == "POL-TEST")).scalar_one()
        pid = p.id
        assert p.decision_class.value == 3
        assert p.required_approver_role_code == "EXEC"
        assert "ADMIN" in p.sod_exclusion_role_codes
    finally:
        s.close()

    # Change it.
    r = client.post(
        f"/admin/access-policies/{pid}",
        data={
            "name": "Test Policy (updated)",
            "description": "Now Class 4",
            "decision_class": "CLASS_4",
            "required_approver_role_code": "EXEC",
            "sod_exclusion_role_codes": "ADMIN",
            "active": "on",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303

    s = SessionLocal()
    try:
        p = s.execute(select(AccessPolicy).where(AccessPolicy.id == pid)).scalar_one()
        assert p.name == "Test Policy (updated)"
        assert p.decision_class.value == 4
        assert p.sod_exclusion_role_codes == "ADMIN"
        assert p.active is True
    finally:
        s.close()


def test_non_admin_cannot_create_user(client: TestClient) -> None:
    # Create a non-admin user.
    from techno_service_ai import access, security
    s = SessionLocal()
    try:
        viewer = s.execute(select(Role).where(Role.code == "VIEWER")).scalar_one()
        u = User(
            username="eve",
            email="eve@example.com",
            display_name="Eve",
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

    client.post("/sign-in", data={"username": "eve", "password": "Password!1"})
    r = client.get("/admin/users")
    assert r.status_code == 403

    r = client.post(
        "/admin/users/new",
        data={
            "username": "frank",
            "email": "frank@example.com",
            "display_name": "Frank",
            "password": "Password!1",
            "recovery_question": "q",
            "recovery_answer": "a",
        },
    )
    assert r.status_code == 403
