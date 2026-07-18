"""Handoff Service — Interaction Matrix Section 4.

Implements the Handoff Service:

  - Handoff Initiation: the relinquishing Office records the handoff.
  - Handoff Acceptance: the receiving Office accepts.
  - Handoff Audit: every event is recorded.

A handoff that fails acceptance criteria is REJECTED, RETURNED for
rework, or ESCALATED (COLLAB-HO-002, Interaction Matrix Section 4).

This is a pure-logic module.

Constitutional source:
  - Constitution Article XVIII
  - Document 06 §9.1, §9.6 (COLLAB-OWN-001..003, COLLAB-HO-001..002)
  - Interaction Matrix Section 4
  - REQ-LOG-001
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Mapping


class HandoffStatus(str, Enum):
    INITIATED = "INITIATED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    RETURNED = "RETURNED"
    ESCALATED = "ESCALATED"


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class HandoffRejected(Exception):
    """A handoff that failed acceptance criteria was REJECTED.

    The receiving Office did not accept the material; the relinquishing
    Office is informed. Per COLLAB-HO-002, the handoff may be
    REJECTED, RETURNED for rework, or ESCALATED.
    """

    def __init__(self, handoff_canonical_id: str, reason: str) -> None:
        self.handoff_canonical_id = handoff_canonical_id
        self.reason = reason
        super().__init__(
            f"Handoff {handoff_canonical_id} REJECTED: {reason}. "
            f"Per Document 06 §9.6 COLLAB-HO-002, a handoff that fails "
            f"validation is rejected, returned for rework, or escalated."
        )


# ---------------------------------------------------------------------------
# Handoff record
# ---------------------------------------------------------------------------


@dataclass
class Handoff:
    canonical_id: str
    material_canonical_id: str
    relinquishing_office: str
    receiving_office: str
    initiated_by: str
    initiated_at: str
    acceptance_criteria: tuple[str, ...]
    status: HandoffStatus = HandoffStatus.INITIATED
    accepted_at: str | None = None
    accepted_by: str | None = None
    rejected_at: str | None = None
    rejected_reason: str | None = None
    returned_at: str | None = None
    returned_reason: str | None = None
    escalated_at: str | None = None
    audit: list[dict] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Handoff Service
# ---------------------------------------------------------------------------


class HandoffService:
    """Pure-logic handoff service.

    Methods:
      - initiate: the relinquishing Office records the handoff
      - accept: the receiving Office accepts (verifies acceptance
        criteria against the supplied facts)
      - reject: the receiving Office rejects (fails criteria)
      - return_for_rework: the receiving Office returns
      - escalate: the receiving Office escalates
      - audit_log: the audit trail of the handoff
    """

    def __init__(self) -> None:
        self.handoffs: dict[str, Handoff] = {}

    def initiate(
        self,
        *,
        material_canonical_id: str,
        relinquishing_office: str,
        receiving_office: str,
        initiated_by: str,
        acceptance_criteria: tuple[str, ...],
        initiated_at: str = "",
        canonical_id: str = "",
    ) -> Handoff:
        """Initiate a handoff. The relinquishing Office records it."""
        h = Handoff(
            canonical_id=canonical_id or _uuid_str(),
            material_canonical_id=material_canonical_id,
            relinquishing_office=relinquishing_office,
            receiving_office=receiving_office,
            initiated_by=initiated_by,
            initiated_at=initiated_at or _now_iso(),
            acceptance_criteria=acceptance_criteria,
        )
        h.audit.append({"event": "INITIATED", "by": initiated_by, "at": h.initiated_at})
        self.handoffs[h.canonical_id] = h
        return h

    def accept(
        self,
        *,
        handoff_canonical_id: str,
        accepted_by: str,
        facts: Mapping[str, object] | None = None,
        accepted_at: str = "",
    ) -> Handoff:
        """Accept the handoff. All acceptance criteria must be satisfied.

        Each acceptance criterion is treated as a key in `facts`; the
        value must be truthy. If a criterion is missing or its value is
        falsy, the handoff is REJECTED and HandoffRejected is raised.
        """
        h = self._get(handoff_canonical_id)
        if h.status != HandoffStatus.INITIATED:
            raise ValueError(f"Handoff {handoff_canonical_id} is not in INITIATED state (status={h.status.value})")
        facts = facts or {}
        missing = [c for c in h.acceptance_criteria if not facts.get(c)]
        if missing:
            self._reject_internal(h, reason=f"acceptance criteria not satisfied: {missing}")
            raise HandoffRejected(handoff_canonical_id, f"missing: {missing}")
        h.accepted_at = accepted_at or _now_iso()
        h.accepted_by = accepted_by
        h.status = HandoffStatus.ACCEPTED
        h.audit.append({"event": "ACCEPTED", "by": accepted_by, "at": h.accepted_at})
        return h

    def reject(
        self,
        *,
        handoff_canonical_id: str,
        reason: str,
        rejected_at: str = "",
    ) -> Handoff:
        h = self._get(handoff_canonical_id)
        self._reject_internal(h, reason)
        raise HandoffRejected(handoff_canonical_id, reason)

    def _reject_internal(self, h: Handoff, reason: str) -> None:
        h.rejected_at = _now_iso()
        h.rejected_reason = reason
        h.status = HandoffStatus.REJECTED
        h.audit.append({"event": "REJECTED", "reason": reason, "at": h.rejected_at})

    def return_for_rework(
        self,
        *,
        handoff_canonical_id: str,
        reason: str,
        returned_at: str = "",
    ) -> Handoff:
        h = self._get(handoff_canonical_id)
        h.returned_at = returned_at or _now_iso()
        h.returned_reason = reason
        h.status = HandoffStatus.RETURNED
        h.audit.append({"event": "RETURNED", "reason": reason, "at": h.returned_at})
        return h

    def escalate(
        self,
        *,
        handoff_canonical_id: str,
        escalated_at: str = "",
    ) -> Handoff:
        h = self._get(handoff_canonical_id)
        h.escalated_at = escalated_at or _now_iso()
        h.status = HandoffStatus.ESCALATED
        h.audit.append({"event": "ESCALATED", "at": h.escalated_at})
        return h

    def _get(self, canonical_id: str) -> Handoff:
        h = self.handoffs.get(canonical_id)
        if h is None:
            raise ValueError(f"Unknown handoff: {canonical_id}")
        return h

    def audit_log(self, handoff_canonical_id: str) -> list[dict]:
        return list(self.handoffs[handoff_canonical_id].audit)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _uuid_str() -> str:
    import uuid
    return str(uuid.uuid4())


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
