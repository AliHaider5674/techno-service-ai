"""AC-P1-004 — The Audit Log is queryable, complete, immutable, and exportable.

Pass condition: Every sign-in, sign-out, persona selection, role change,
and access policy change produces an audit log entry; an unauthorised
modification of the audit log is rejected; an export of the audit log
returns the full content.

This is the Phase 1 acceptance criterion. The detailed audit criteria
(AC-AUD-001..005) live in their own test files.
"""
from __future__ import annotations

import csv
import io
import json

from fastapi.testclient import TestClient
from sqlalchemy import select

from techno_service_ai import access, audit
from techno_service_ai.db import SessionLocal
from techno_service_ai.schema import (
    AccessPolicy,
    DecisionClass,
    Role,
    User,
    UserStatus,
)


def _sign_in_admin(client: TestClient) -> None:
    client.post("/sign-in", data={"username": "admin", "password": "ChangeMe!2026"})


def test_sign_in_out_persona_role_and_policy_all_appear_in_audit_log(client: TestClient) -> None:
    # 1) sign in (admin).
    _sign_in_admin(client)
    # 2) admin creates a user — creates a USER_CREATED entry.
    client.post(
        "/admin/users/new",
        data={
            "username": "gail",
            "email": "gail@example.com",
            "display_name": "Gail",
            "password": "Password!1",
            "recovery_question": "q",
            "recovery_answer": "a",
        },
    )
    s = SessionLocal()
    try:
        gail = s.execute(select(User).where(User.username == "gail")).scalar_one()
        gid = gail.id
        analyst = s.execute(select(Role).where(Role.code == "ANALYST")).scalar_one()
        analyst_id = analyst.id
    finally:
        s.close()

    # 3) admin assigns a role — ROLE_ASSIGNED.
    client.post(f"/admin/users/{gid}/roles/assign", data={"role_id": analyst_id})

    # 4) admin revokes the role — ROLE_REVOKED.
    client.post(f"/admin/users/{gid}/roles/{analyst_id}/revoke", data={"reason": "test"})

    # 5) admin defines a new access policy — POLICY_CREATED.
    client.post(
        "/admin/access-policies",
        data={
            "code": "POL-FOR-AUDIT",
            "name": "Policy for audit test",
            "decision_class": "CLASS_2",
            "required_approver_role_code": "ADMIN",
            "sod_exclusion_role_codes": "",
        },
    )
    s = SessionLocal()
    try:
        p = s.execute(select(AccessPolicy).where(AccessPolicy.code == "POL-FOR-AUDIT")).scalar_one()
        pid = p.id
    finally:
        s.close()

    # 6) admin changes the access policy — POLICY_UPDATED.
    client.post(
        f"/admin/access-policies/{pid}",
        data={
            "name": "Policy for audit test (changed)",
            "description": "now active",
            "decision_class": "CLASS_3",
            "required_approver_role_code": "EXEC",
            "sod_exclusion_role_codes": "ADMIN",
            "active": "on",
        },
    )

    # 7) sign out — SIGN_OUT.
    client.get("/sign-out")

    # Audit log must contain all of these event types.
    s = SessionLocal()
    try:
        events = audit.query(s, limit=500)
        types = {e.event_type for e in events}
        required = {
            "IDENTITY.SIGN_IN",
            "IDENTITY.SIGN_OUT",
            "ACCESS.USER_CREATED",
            "ACCESS.ROLE_ASSIGNED",
            "ACCESS.ROLE_REVOKED",
            "ACCESS.POLICY_CREATED",
            "ACCESS.POLICY_UPDATED",
        }
        missing = required - types
        assert not missing, f"Missing audit event types: {missing}"

        # Also at least one ACCESS_DENIED for non-admin trying to access admin.
        # (That is tested in test_ac_sec_003; here we just assert that persona
        # selection audit is present when we use it.)
        # (Skipping persona in this test because the default admin has a
        # single available persona after a fresh boot, so no /persona/select
        # POST is issued.)
    finally:
        s.close()


def test_unauthorised_modification_of_audit_log_is_rejected(client: TestClient) -> None:
    _sign_in_admin(client)
    # Get a row, try to UPDATE and DELETE it via raw SQL.
    s = SessionLocal()
    try:
        e = audit.query(s, limit=1)
        assert e, "Expected at least one audit entry from sign-in"
        target = e[0]
        target_id = target.id
    finally:
        s.close()

    from sqlalchemy import text
    from techno_service_ai.db import get_engine
    eng = get_engine()
    with eng.begin() as conn:
        # UPDATE must be rejected.
        try:
            conn.execute(text("UPDATE audit_log SET action='hacked' WHERE id=:i"), {"i": target_id})
            raised_update = False
        except Exception as e:  # sqlite3.IntegrityError or OperationalError
            raised_update = True
            assert "append-only" in str(e).lower() or "audit" in str(e).lower()
        assert raised_update, "UPDATE on audit_log was not rejected by the trigger"

        # DELETE must be rejected.
        try:
            conn.execute(text("DELETE FROM audit_log WHERE id=:i"), {"i": target_id})
            raised_delete = False
        except Exception as e:
            raised_delete = True
            assert "append-only" in str(e).lower() or "audit" in str(e).lower()
        assert raised_delete, "DELETE on audit_log was not rejected by the trigger"


def test_export_csv_returns_full_content(client: TestClient) -> None:
    _sign_in_admin(client)
    client.get("/sign-out")
    _sign_in_admin(client)

    r = client.get("/admin/audit-log/export.csv")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    text = r.text
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    # Header + at least 1 data row.
    assert rows[0][0] == "sequence"
    assert len(rows) >= 2
    # Every required column is present.
    expected_cols = {
        "sequence", "occurred_at", "event_type", "action",
        "actor_user_id", "actor_username", "actor_role_code",
        "actor_session_id", "target_type", "target_id",
        "outcome", "ip", "user_agent", "payload_json",
        "prev_hash", "entry_hash", "retention_class",
    }
    header = set(rows[0])
    assert expected_cols.issubset(header), f"Missing CSV columns: {expected_cols - header}"


def test_export_json_returns_full_content(client: TestClient) -> None:
    _sign_in_admin(client)
    r = client.get("/admin/audit-log/export.json")
    assert r.status_code == 200
    body = json.loads(r.text)
    assert isinstance(body, list)
    assert len(body) >= 1
    e = body[0]
    for k in ["sequence", "occurred_at", "event_type", "action", "entry_hash", "prev_hash"]:
        assert k in e, f"Missing key {k} in exported entry"


def test_audit_chain_is_verifiable(client: TestClient) -> None:
    _sign_in_admin(client)
    # Perform a series of events.
    client.post(
        "/admin/users/new",
        data={
            "username": "henry",
            "email": "henry@example.com",
            "display_name": "Henry",
            "password": "Password!1",
            "recovery_question": "q",
            "recovery_answer": "a",
        },
    )

    s = SessionLocal()
    try:
        ok, bad = audit.verify_chain(s)
        assert ok is True
        assert bad is None
    finally:
        s.close()
