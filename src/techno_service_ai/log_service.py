"""Log Service — Decision / Handoff / Escalation Log writers.

Closes GAP-PHASE3-003: every workflow event writes to the Decision
Log (ENT-APR / ENT-VER / ENT-OPP-ST), every handoff writes to the
Handoff Log (ENT-COLLAB-001), and every escalation writes to the
Escalation Log (ENT-COLLAB-002).

Constitutional source:
  - Constitution Article XIX Section E
  - Constitution Article XX paragraph 5
  - Document 06 §9.1, §9.3
  - Document 05 §3 (Information Domain 20: Cross-Office Collaboration)
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from .db import SessionLocal
from .phase2_schema import (
    DecisionLogEntry,
    EscalationLogEntry,
    HandoffLogEntry,
)


class LogService:
    """Service layer that writes to the 3 Log entities.

    Every write is a constitutional record. The Log entities are
    append-only (no silent amendment, no in-place UPDATE) per the
    triggers installed in Phase 2.
    """

    def write_decision_log(
        self,
        *,
        decision_type: str,
        decision_summary: str,
        decision_class: str,
        decided_by: str,
        decided_by_role: str,
        material_canonical_id: str,
        opportunity_canonical_id: Optional[str] = None,
        rationale: str = "",
        conditions: str = "",
        related_approval_id: Optional[str] = None,
        decided_at: str = "",
        session: Optional[Session] = None,
    ) -> DecisionLogEntry:
        """Append a Decision Log Entry.

        Phase 6 reconciliation (closes GAP-PHASE5-001): maps the
        LogService's field names to the schema's canonical
        DecisionLogEntry fields.

          - decision_type  → target_type
          - decision_summary → decision_summary (new in Phase 6)
          - decision_class  → decision_class (now String in Phase 6)
          - decision        → decision (built from decision_summary)
          - decided_by_role → decided_by_role (new in Phase 6)
          - material_canonical_id → material_canonical_id (new in P6)
          - opportunity_canonical_id → opportunity_canonical_id (new in P6)
          - rationale, conditions, related_approval_id → new in P6
        """
        # Build the legacy `decision` field from the summary so
        # historical queries continue to work.
        decision_text = decision_summary or ""
        # Phase 6 reconciliation: convert decided_at (ISO string) to
        # datetime so the schema accepts it. The schema's
        # DateTime(timezone=True) requires a datetime, not a string.
        from datetime import datetime
        if isinstance(decided_at, str):
            if decided_at:
                # Strip trailing Z and parse; treat as UTC.
                cleaned = decided_at.replace("Z", "+00:00")
                decided_at_dt = datetime.fromisoformat(cleaned)
            else:
                decided_at_dt = datetime.now(timezone.utc)
        else:
            decided_at_dt = decided_at or datetime.now(timezone.utc)
        rec = DecisionLogEntry(
            id=_uuid_str(),
            canonical_id=_uuid_str(),  # Phase 6: required NOT NULL
            target_type=decision_type,
            target_id=material_canonical_id or "",
            decision_class=decision_class,
            decision=decision_text,
            decided_by=decided_by,
            decided_at=decided_at_dt,
            decision_summary=decision_summary,
            decided_by_role=decided_by_role,
            material_canonical_id=material_canonical_id,
            opportunity_canonical_id=opportunity_canonical_id,
            rationale=rationale or None,
            conditions=conditions or None,
            related_approval_id=related_approval_id,
        )
        self._commit(rec, session)
        return rec

    def write_handoff_log(
        self,
        *,
        handoff_canonical_id: str,
        material_canonical_id: str,
        relinquishing_office: str,
        receiving_office: str,
        initiated_by: str,
        outcome: str,
        initiated_at: str = "",
        accepted_at: Optional[str] = None,
        accepted_by: Optional[str] = None,
        rejected_reason: Optional[str] = None,
        session: Optional[Session] = None,
    ) -> HandoffLogEntry:
        """Append a Handoff Log Entry (COLLAB-OWN-003)."""
        rec = HandoffLogEntry(
            id=_uuid_str(),
            handoff_canonical_id=handoff_canonical_id,
            material_canonical_id=material_canonical_id,
            relinquishing_office=relinquishing_office,
            receiving_office=receiving_office,
            initiated_by=initiated_by,
            outcome=outcome,
            initiated_at=initiated_at or _now_iso(),
            accepted_at=accepted_at,
            accepted_by=accepted_by,
            rejected_reason=rejected_reason,
        )
        self._commit(rec, session)
        return rec

    def write_escalation_log(
        self,
        *,
        escalation_canonical_id: str,
        trigger: str,
        channel: str,
        recipient: str,
        raised_by: str,
        raised_at: str = "",
        acknowledged_at: Optional[str] = None,
        outcome: Optional[str] = None,
        related_workflow_canonical_id: Optional[str] = None,
        session: Optional[Session] = None,
    ) -> EscalationLogEntry:
        """Append an Escalation Log Entry (Document 06 §9.3)."""
        rec = EscalationLogEntry(
            id=_uuid_str(),
            escalation_canonical_id=escalation_canonical_id,
            trigger=trigger,
            channel=channel,
            recipient=recipient,
            raised_by=raised_by,
            raised_at=raised_at or _now_iso(),
            acknowledged_at=acknowledged_at,
            outcome=outcome,
            related_workflow_canonical_id=related_workflow_canonical_id,
        )
        self._commit(rec, session)
        return rec

    def _commit(self, rec, session: Optional[Session] = None) -> None:
        if session is not None:
            session.add(rec)
            session.commit()
        else:
            with SessionLocal() as s:
                s.add(rec)
                s.commit()


def _uuid_str() -> str:
    import uuid
    return str(uuid.uuid4())


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
