"""HD-PHASE8-003 — Production Audit Log Initialisation.

Writes the baseline record via the constitutional audit API, against the
production PostgreSQL database (TSAI_DATABASE_URL).

Strict scope: ONE record, then exit.
"""
from __future__ import annotations

import sys
import os
import json

# Set the production database URL BEFORE importing the app modules.
os.environ.setdefault(
    "TSAI_DATABASE_URL",
    "postgresql://tsai_app:Techno2026@localhost:5432/tsai_prod",
)

sys.path.insert(0, "src")

from techno_service_ai.audit import record
from techno_service_ai.db import session_scope


def main() -> int:
    print("=" * 60)
    print("HD-PHASE8-003 — Production Audit Log Initialisation")
    print("Backend: PostgreSQL (production)")
    print("=" * 60)

    with session_scope() as session:
        entry = record(
            session,
            event_type="HD-PHASE8-003.INITIALISATION",
            action="PRODUCTION_AUDIT_LOG_INIT",
            actor_username="Constitutional Owner",
            actor_role_code="CONSTITUTIONAL_OWNER",
            target_type="audit_log",
            target_id="production-baseline",
            outcome="SUCCESS",
            ip="127.0.0.1",
            user_agent="hd-phase8-003-initialiser",
            payload={
                "phase": "HD-PHASE8-003",
                "state": "INITIALISED",
                "production_grade": True,
                "predecessor": "HD-PHASE8-002",
                "predecessor_event": "PostgreSQL 15+ production migration complete",
                "constitution_v23": "unchanged",
                "constitution_v24": "in force (Phase 9 Charter + Proactive Discovery PRs)",
                "constitutional_basis": [
                    "Constitution v2.3, Article XX (Audit)",
                    "Constitution v2.4, Article XX (Audit, additive)",
                    "Document 04 §Audit (Audit and Evidence)",
                    "ASS-PHASE8-002 (PostgreSQL production migration)",
                ],
                "immutability_guarantee": {
                    "trigger_no_update": "audit_log_no_update BEFORE UPDATE",
                    "trigger_no_delete": "audit_log_no_delete BEFORE DELETE",
                    "raised_message": "Constitution Article XX",
                },
                "objectives_remaining": [
                    "HD-PHASE8-004 (TDE encryption at rest)",
                    "HD-PHASE8-005 (Production UAT with named personas)",
                    "HD-PHASE8-006 (Production SLO verification, 30-day window)",
                    "HD-PHASE9-001 (APScheduler migration for in-process threading scheduler)",
                    "HD-PHASE9-002 (Real data sources: USPTO, OpenCorporates)",
                ],
                "operator": "Constitutional Owner (Class 4)",
                "operator_role": "Implementation Lead + Constitutional Compliance",
            },
        )

    print()
    print(f"OK: audit entry written")
    print(f"  id          = {entry.id}")
    print(f"  sequence    = {entry.sequence}")
    print(f"  event_type  = {entry.event_type}")
    print(f"  action      = {entry.action}")
    print(f"  actor       = {entry.actor_username} ({entry.actor_role_code})")
    print(f"  occurred_at = {entry.occurred_at}")
    print(f"  prev_hash   = {entry.prev_hash[:16]}...")
    print(f"  entry_hash  = {entry.entry_hash[:16]}...")
    print(f"  retention   = {entry.retention_class}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
