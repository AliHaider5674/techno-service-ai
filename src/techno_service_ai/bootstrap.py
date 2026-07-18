"""Bootstrap — create schema, seed default roles, create default admin.

Idempotent. Safe to run repeatedly.

Run with:
    python -m techno_service_ai.bootstrap
"""
from __future__ import annotations

import sys
from pathlib import Path

# Allow running as a script.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import select

from techno_service_ai import access, security
from techno_service_ai.config import SETTINGS
from techno_service_ai.db import apply_schema, get_engine, session_scope
from techno_service_ai.schema import (
    AccessPolicy,
    DecisionClass,
    Role,
    User,
)


# The seven roles that exist in Phase 1. Names mirror the personas in
# the Master Build Specification §4 (User Personas and Authority Model).
# SoD classes are configured to enforce Article XVII in Phase 1.
DEFAULT_ROLES: list[dict] = [
    {"code": "ADMIN",       "name": "System Administrator",        "sod_class": "ADMIN",       "description": "Configures the system; manages users, roles, access policy, audit, and incidents."},
    {"code": "EXEC",        "name": "Executive Management",        "sod_class": "EXEC",        "description": "Class 4 binding decisions, board reports, strategic direction."},
    {"code": "OPS",         "name": "Operations Manager",          "sod_class": "OPS",         "description": "Operational dashboards, escalations, operational approvals."},
    {"code": "BIZDEV",      "name": "Business Development",        "sod_class": "BIZDEV",      "description": "Engagement, quotation, account management, customer communication."},
    {"code": "VERIFIER",    "name": "Verification Team",           "sod_class": "VERIFIER",    "description": "Preliminary, specialist, and independent final verification; claim classification."},
    {"code": "ANALYST",     "name": "Analyst",                     "sod_class": "ANALYST",     "description": "Industrial, opportunity, technology, manufacturer, commercial, risk, reporting analysis."},
    {"code": "VIEWER",      "name": "Viewer",                      "sod_class": "VIEWER",      "description": "Read-only access within assigned scope."},
    {"code": "COMPLIANCE",  "name": "Compliance",                  "sod_class": "COMPLIANCE",  "description": "Read access to audit log, access policy review, compliance reports."},
    {"code": "AUDITOR",     "name": "Auditor",                     "sod_class": "AUDITOR",     "description": "Read access to audit log, access policy review, audit reports."},
]


DEFAULT_POLICIES: list[dict] = [
    {
        "code": "POL-USER-MGMT",
        "name": "User management operations",
        "description": "Create, update, suspend, archive users.",
        "decision_class": DecisionClass.CLASS_2,
        "required_approver_role_code": "ADMIN",
        "sod_exclusion_role_codes": "",
    },
    {
        "code": "POL-ROLE-ASSIGN",
        "name": "Role assignment",
        "description": "Grant or revoke a role on a user.",
        "decision_class": DecisionClass.CLASS_2,
        "required_approver_role_code": "ADMIN",
        "sod_exclusion_role_codes": "",
    },
    {
        "code": "POL-ACCESS-EDIT",
        "name": "Access policy change",
        "description": "Modify an AccessPolicy (decision class, approver, SoD exclusions).",
        "decision_class": DecisionClass.CLASS_3,
        "required_approver_role_code": "EXEC",
        "sod_exclusion_role_codes": "ADMIN",
    },
    {
        "code": "POL-AUDIT-EXPORT",
        "name": "Audit log export",
        "description": "Export the audit log in CSV or JSON.",
        "decision_class": DecisionClass.CLASS_2,
        "required_approver_role_code": "COMPLIANCE",
        "sod_exclusion_role_codes": "",
    },
]


def seed() -> None:
    apply_schema()
    with session_scope() as s:
        # --- Roles ---
        existing = {r.code for r in s.execute(select(Role)).scalars()}
        for spec in DEFAULT_ROLES:
            if spec["code"] in existing:
                continue
            s.add(Role(**spec))
        s.flush()

        # --- Access policies ---
        existing_p = {p.code for p in s.execute(select(AccessPolicy)).scalars()}
        for spec in DEFAULT_POLICIES:
            if spec["code"] in existing_p:
                continue
            s.add(AccessPolicy(
                code=spec["code"],
                name=spec["name"],
                description=spec["description"],
                decision_class=spec["decision_class"],
                required_approver_role_code=spec["required_approver_role_code"],
                sod_exclusion_role_codes=spec["sod_exclusion_role_codes"],
            ))

        # --- Default admin user ---
        admin = s.execute(select(User).where(User.username == SETTINGS.default_admin_username)).scalar_one_or_none()
        if admin is None:
            admin = User(
                username=SETTINGS.default_admin_username,
                email="admin@technoservice.local",
                display_name="Default Administrator",
                password_hash=security.hash_password(SETTINGS.default_admin_password),
                recovery_question="What is the default city of the headquarters?",
                recovery_answer_hash=security.hash_recovery_answer("kuwait city"),
            )
            s.add(admin)
            s.flush()
            # Assign the ADMIN role only. Per Article XVII SoD Rule 1, a user
            # may not hold two roles from different sod_class buckets, so we
            # do NOT also assign AUDITOR here. The ADMIN role alone is
            # sufficient to read the audit log (the /admin/audit-log route
            # accepts ADMIN, COMPLIANCE, or AUDITOR).
            admin_role = s.execute(select(Role).where(Role.code == "ADMIN")).scalar_one()
            access.assign_role(
                s, user=admin, role=admin_role, actor=admin, actor_role_code="ADMIN",
                scope="GLOBAL",
            )

    print(f"[bootstrap] schema applied at {SETTINGS.database_url}")
    print(f"[bootstrap] seeded {len(DEFAULT_ROLES)} roles, {len(DEFAULT_POLICIES)} access policies")
    print(f"[bootstrap] default admin: {SETTINGS.default_admin_username} / {SETTINGS.default_admin_password}")
    print("[bootstrap] CHANGE THE DEFAULT ADMIN PASSWORD IN ANY NON-TEST ENVIRONMENT.")


def main() -> None:
    seed()


if __name__ == "__main__":
    main()
