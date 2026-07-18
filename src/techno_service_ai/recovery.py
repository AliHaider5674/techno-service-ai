"""Recovery Orchestration — Document 06 Section 12.

Implements the Recovery Model:

  12.1 Interrupted Workflows (REC-INT-001..002)
  12.2 Restart Rules (REC-RES-001..002)
  12.3 Resume Rules (REC-RESUME-001..003)
  12.4 Rollback Policy (REC-ROLL-001..003)
  12.5 Recovery Audit (REC-AUD-001..002)

This is a pure-logic module. The Recovery Engine integrates with the
Orchestration State Machine and the Workflow Engine.

Constitutional source:
  - Constitution Article XXV
  - Document 06 §12
  - REQ-FN-SEC-004, REQ-ERR-006
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class RecoveryAction(str, Enum):
    INTERRUPTED = "INTERRUPTED"
    RESTART = "RESTART"
    RESUME = "RESUME"
    ROLLBACK = "ROLLBACK"
    RECOVERY_AUDIT = "RECOVERY_AUDIT"


@dataclass
class RecoveryRecord:
    canonical_id: str
    workflow_canonical_id: str
    action: RecoveryAction
    description: str
    continuity_plan_reference: str
    responsible_authority: str
    date: str
    preserved_state: str
    restart_at_stage: str | None = None
    rollback_to_stage: str | None = None


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class RollbackRequiresApproval(Exception):
    """A rollback was attempted without explicit Human Approval.

    Per REC-ROLL-001: "A rollback is permitted only by a documented
    Human Approval."
    """

    def __init__(self) -> None:
        super().__init__(
            "Rollback REJECTED: a documented Human Approval is required. "
            "Per Document 06 §12.4 REC-ROLL-001, a rollback is permitted "
            "only by a documented Human Approval."
        )


class Class3Or4ResumeRequiresApproval(Exception):
    """A Resume that affects a Class 3 or Class 4 Decision requires approval.

    Per REC-RESUME-003.
    """

    def __init__(self, decision_class: str) -> None:
        self.decision_class = decision_class
        super().__init__(
            f"Resume REJECTED: a Resume that affects a {decision_class} "
            f"Decision requires Human Approval. Per Document 06 §12.3 "
            f"REC-RESUME-003."
        )


# ---------------------------------------------------------------------------
# Recovery Engine
# ---------------------------------------------------------------------------


class RecoveryEngine:
    """Pure-logic recovery orchestration.

    Methods:
      - interrupt: mark a workflow as interrupted (REC-INT-001)
      - restart: confirm operational state and integrity (REC-RES-001)
      - resume: resume at the appropriate stage (REC-RESUME-001)
      - rollback: rollback (requires Human Approval per REC-ROLL-001)
      - audit: record a recovery audit event
    """

    def __init__(self) -> None:
        self.records: list[RecoveryRecord] = []

    def interrupt(
        self,
        *,
        workflow_canonical_id: str,
        description: str,
        continuity_plan_reference: str,
        responsible_authority: str,
        preserved_state: str,
        date: str = "",
    ) -> RecoveryRecord:
        r = RecoveryRecord(
            canonical_id=_uuid_str(),
            workflow_canonical_id=workflow_canonical_id,
            action=RecoveryAction.INTERRUPTED,
            description=description,
            continuity_plan_reference=continuity_plan_reference,
            responsible_authority=responsible_authority,
            date=date or _now_iso(),
            preserved_state=preserved_state,
        )
        self.records.append(r)
        return r

    def restart(
        self,
        *,
        workflow_canonical_id: str,
        description: str,
        continuity_plan_reference: str,
        responsible_authority: str,
        preserved_state: str,
        date: str = "",
    ) -> RecoveryRecord:
        r = RecoveryRecord(
            canonical_id=_uuid_str(),
            workflow_canonical_id=workflow_canonical_id,
            action=RecoveryAction.RESTART,
            description=description,
            continuity_plan_reference=continuity_plan_reference,
            responsible_authority=responsible_authority,
            date=date or _now_iso(),
            preserved_state=preserved_state,
        )
        self.records.append(r)
        return r

    def resume(
        self,
        *,
        workflow_canonical_id: str,
        restart_at_stage: str,
        description: str,
        continuity_plan_reference: str,
        responsible_authority: str,
        preserved_state: str,
        affects_class_3_or_4: bool = False,
        decision_class: str = "",
        human_approval_recorded: bool = False,
        date: str = "",
    ) -> RecoveryRecord:
        """Resume a workflow at the appropriate stage.

        If the resume affects a Class 3 External Action or a Class 4
        Binding Decision, the human_approval_recorded flag must be
        True, otherwise Class3Or4ResumeRequiresApproval is raised.
        """
        if affects_class_3_or_4 and not human_approval_recorded:
            raise Class3Or4ResumeRequiresApproval(decision_class or "CLASS_3_OR_4")
        r = RecoveryRecord(
            canonical_id=_uuid_str(),
            workflow_canonical_id=workflow_canonical_id,
            action=RecoveryAction.RESUME,
            description=description,
            continuity_plan_reference=continuity_plan_reference,
            responsible_authority=responsible_authority,
            date=date or _now_iso(),
            preserved_state=preserved_state,
            restart_at_stage=restart_at_stage,
        )
        self.records.append(r)
        return r

    def rollback(
        self,
        *,
        workflow_canonical_id: str,
        rollback_to_stage: str,
        description: str,
        continuity_plan_reference: str,
        responsible_authority: str,
        preserved_state: str,
        human_approval_recorded: bool = False,
        date: str = "",
    ) -> RecoveryRecord:
        """Rollback a workflow. REQUIRES Human Approval per REC-ROLL-001."""
        if not human_approval_recorded:
            raise RollbackRequiresApproval()
        r = RecoveryRecord(
            canonical_id=_uuid_str(),
            workflow_canonical_id=workflow_canonical_id,
            action=RecoveryAction.ROLLBACK,
            description=description,
            continuity_plan_reference=continuity_plan_reference,
            responsible_authority=responsible_authority,
            date=date or _now_iso(),
            preserved_state=preserved_state,
            rollback_to_stage=rollback_to_stage,
        )
        self.records.append(r)
        return r

    def audit(
        self,
        *,
        workflow_canonical_id: str,
        description: str,
        continuity_plan_reference: str,
        responsible_authority: str,
        preserved_state: str,
        date: str = "",
    ) -> RecoveryRecord:
        r = RecoveryRecord(
            canonical_id=_uuid_str(),
            workflow_canonical_id=workflow_canonical_id,
            action=RecoveryAction.RECOVERY_AUDIT,
            description=description,
            continuity_plan_reference=continuity_plan_reference,
            responsible_authority=responsible_authority,
            date=date or _now_iso(),
            preserved_state=preserved_state,
        )
        self.records.append(r)
        return r

    def audit_trail(self, workflow_canonical_id: str) -> list[RecoveryRecord]:
        return [r for r in self.records if r.workflow_canonical_id == workflow_canonical_id]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _uuid_str() -> str:
    import uuid
    return str(uuid.uuid4())


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
