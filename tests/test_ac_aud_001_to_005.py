"""AC-AUD-001..005 — detailed audit acceptance criteria.

AC-AUD-001 — Audit Log is complete.
AC-AUD-002 — Audit Log is immutable.
AC-AUD-003 — Audit Log is exportable.
AC-AUD-004 — Audit Log is queryable.
AC-AUD-005 — Audit Retention is in place.
"""
from __future__ import annotations

import csv
import io
import json

from fastapi.testclient import TestClient
from sqlalchemy import select, text

from techno_service_ai import audit
from techno_service_ai.db import SessionLocal, get_engine
from techno_service_ai.schema import AuditLog, User


def _sign_in_admin(client: TestClient) -> None:
    client.post("/sign-in", data={"username": "admin", "password": "ChangeMe!2026"})


# AC-AUD-001 — Complete --------------------------------------------------------


def test_ac_aud_001_sign_in_produces_audit_entry(client: TestClient) -> None:
    _sign_in_admin(client)
    s = SessionLocal()
    try:
        c = audit.count(s, event_type="IDENTITY.SIGN_IN")
        assert c >= 1
    finally:
        s.close()


def test_ac_aud_001_sign_out_produces_audit_entry(client: TestClient) -> None:
    _sign_in_admin(client)
    client.get("/sign-out")
    s = SessionLocal()
    try:
        c = audit.count(s, event_type="IDENTITY.SIGN_OUT")
        assert c >= 1
    finally:
        s.close()


def test_ac_aud_001_role_change_produces_audit_entry(client: TestClient) -> None:
    _sign_in_admin(client)
    client.post(
        "/admin/users/new",
        data={
            "username": "ivy",
            "email": "ivy@example.com",
            "display_name": "Ivy",
            "password": "Password!1",
            "recovery_question": "q",
            "recovery_answer": "a",
        },
    )
    s = SessionLocal()
    try:
        ivy = s.execute(select(User).where(User.username == "ivy")).scalar_one()
        from techno_service_ai.schema import Role
        viewer = s.execute(select(Role).where(Role.code == "VIEWER")).scalar_one()
        access_user = s.execute(select(User).where(User.username == "admin")).scalar_one()
        from techno_service_ai import access
        access.assign_role(s, user=ivy, role=viewer, actor=access_user, actor_role_code="ADMIN")
    finally:
        s.close()
    s = SessionLocal()
    try:
        c = audit.count(s, event_type="ACCESS.ROLE_ASSIGNED")
        assert c >= 1
    finally:
        s.close()


def test_ac_aud_001_policy_change_produces_audit_entry(client: TestClient) -> None:
    _sign_in_admin(client)
    client.post(
        "/admin/access-policies",
        data={
            "code": "POL-AUD",
            "name": "Audit policy",
            "decision_class": "CLASS_1",
            "required_approver_role_code": "ADMIN",
            "sod_exclusion_role_codes": "",
        },
    )
    s = SessionLocal()
    try:
        c = audit.count(s, event_type="ACCESS.POLICY_CREATED")
        assert c >= 1
    finally:
        s.close()


# AC-AUD-002 — Immutable ------------------------------------------------------


def test_ac_aud_002_update_is_rejected_by_trigger(client: TestClient) -> None:
    _sign_in_admin(client)
    eng = get_engine()
    with eng.begin() as conn:
        try:
            conn.execute(text("UPDATE audit_log SET action='x' WHERE 1=1"))
            raised = False
        except Exception as e:
            raised = True
            assert "append-only" in str(e).lower() or "forbidden" in str(e).lower()
        assert raised


def test_ac_aud_002_delete_is_rejected_by_trigger(client: TestClient) -> None:
    _sign_in_admin(client)
    eng = get_engine()
    with eng.begin() as conn:
        try:
            conn.execute(text("DELETE FROM audit_log WHERE 1=1"))
            raised = False
        except Exception as e:
            raised = True
            assert "append-only" in str(e).lower() or "forbidden" in str(e).lower()
        assert raised


# AC-AUD-003 — Exportable -----------------------------------------------------


def test_ac_aud_003_csv_export_round_trip(client: TestClient) -> None:
    _sign_in_admin(client)
    # Generate a few events.
    client.post(
        "/admin/users/new",
        data={
            "username": "jane",
            "email": "jane@example.com",
            "display_name": "Jane",
            "password": "Password!1",
            "recovery_question": "q",
            "recovery_answer": "a",
        },
    )
    r = client.get("/admin/audit-log/export.csv")
    assert r.status_code == 200
    rows = list(csv.reader(io.StringIO(r.text)))
    # The export records its own AUDIT_EXPORT entry AFTER it has read the
    # rows, so the export contains all entries that existed before the
    # call. The post-export entry is in the DB but not in this CSV.
    s = SessionLocal()
    try:
        export_count = audit.count(s, event_type="SECURITY.AUDIT_EXPORT")
    finally:
        s.close()
    assert export_count == 1
    # The CSV has every non-export entry.
    s = SessionLocal()
    try:
        non_export_count = audit.count(s) - export_count
    finally:
        s.close()
    # Rows = header + non_export_count.
    assert len(rows) - 1 == non_export_count


def test_ac_aud_003_json_export_round_trip(client: TestClient) -> None:
    _sign_in_admin(client)
    client.get("/sign-out")
    _sign_in_admin(client)
    r = client.get("/admin/audit-log/export.json")
    assert r.status_code == 200
    data = json.loads(r.text)
    s = SessionLocal()
    try:
        export_count = audit.count(s, event_type="SECURITY.AUDIT_EXPORT")
        non_export_count = audit.count(s) - export_count
    finally:
        s.close()
    # The JSON export has every non-export entry; the export's own entry
    # is committed after the read.
    assert len(data) == non_export_count


# AC-AUD-004 — Queryable ------------------------------------------------------


def test_ac_aud_004_filter_by_event_type(client: TestClient) -> None:
    _sign_in_admin(client)
    s = SessionLocal()
    try:
        all_count = audit.count(s)
        sign_in_count = audit.count(s, event_type="IDENTITY.SIGN_IN")
        only_sign_in = audit.query(s, event_type="IDENTITY.SIGN_IN", limit=1000)
        assert all(e.event_type == "IDENTITY.SIGN_IN" for e in only_sign_in)
        assert len(only_sign_in) == sign_in_count
        assert sign_in_count <= all_count
    finally:
        s.close()


def test_ac_aud_004_filter_by_actor(client: TestClient) -> None:
    _sign_in_admin(client)
    s = SessionLocal()
    try:
        admin = s.execute(select(User).where(User.username == "admin")).scalar_one()
        by_admin = audit.query(s, actor_user_id=admin.id, limit=1000)
        assert all(e.actor_user_id == admin.id for e in by_admin)
        assert len(by_admin) >= 1
    finally:
        s.close()


# AC-AUD-005 — Retention ------------------------------------------------------


def test_ac_aud_005_all_entries_carry_retention_class(client: TestClient) -> None:
    _sign_in_admin(client)
    s = SessionLocal()
    try:
        all_entries = audit.query(s, limit=1000)
        assert all(e.retention_class == "PERMANENT" for e in all_entries)
    finally:
        s.close()


def test_ac_aud_005_retention_class_is_persistent_field(client: TestClient) -> None:
    _sign_in_admin(client)
    s = SessionLocal()
    try:
        cols = {c.name for c in AuditLog.__table__.columns}
        assert "retention_class" in cols
    finally:
        s.close()
