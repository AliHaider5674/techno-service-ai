"""ORCH-COND Path — Document 06 §3.3 (closes GAP-PHASE3-002).

A stage of the Constitutional Discovery Order may be marked as one of:

  1. NOT_APPLICABLE — the stage is not relevant to the specific
     Opportunity (e.g. Kuwait Suitability for a non-Kuwait market).
  2. DEFERRED — the stage is postponed to a later date with a
     defined reason and a defined re-entry date.
  3. SKIPPED_BY_AUTHORIZED_HUMAN_DECISION — an authorised human
     has decided to skip the stage with a documented reason and
     approval.
  4. REPLACED_BY_EQUIVALENT_CONTROL — the stage is replaced by a
     documented Equivalent Control. The Equivalent Control is NOT
     a waiver; it provides equivalent assurance. The record carries
     the Equivalent Control's reference and the assurance statement.

Per ORCH-COND-001..003 (Document 06 §3.3) and Constitution Article
XI paragraph 5:
  - The Applicability is determined by the originating Office and
    recorded in the Stage Omission Record.
  - The marker records: reason, responsible authority, date, any
    conditions, and an audit trail.
  - A stage marked Replaced by an Equivalent Control is NOT a
    waiver; the Equivalent Control provides equivalent assurance.

Constitutional source:
  - Constitution Article XI paragraph 5
  - Document 06 §3.3 (ORCH-COND-001..003)
  - Interaction Matrix Section 7
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .stages import StageNumber


class OmissionType(str, Enum):
    """The 4 constitutional omission types."""

    NOT_APPLICABLE = "NOT_APPLICABLE"
    DEFERRED = "DEFERRED"
    SKIPPED_BY_AUTHORIZED_HUMAN_DECISION = "SKIPPED_BY_AUTHORIZED_HUMAN_DECISION"
    REPLACED_BY_EQUIVALENT_CONTROL = "REPLACED_BY_EQUIVALENT_CONTROL"


# Omissions that REQUIRE a Human Approval per Constitution Article XI
# paragraph 5 and Document 06 §3.3.
APPROVAL_REQUIRED_OMISSIONS: frozenset[OmissionType] = frozenset({
    OmissionType.SKIPPED_BY_AUTHORIZED_HUMAN_DECISION,
    OmissionType.REPLACED_BY_EQUIVALENT_CONTROL,
})


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class ORCHCONDMissingApproval(Exception):
    """An omission that requires a Human Approval is missing the approval.

    Per Constitution Article XI paragraph 5: a stage may be marked
    Skipped by Authorized Human Decision or Replaced by an
    Equivalent Control only with a documented Human Approval.
    """

    def __init__(self, omission_type: OmissionType) -> None:
        self.omission_type = omission_type
        super().__init__(
            f"ORCH-COND {omission_type.value} requires a documented Human Approval. "
            f"Per Constitution Article XI paragraph 5 and Document 06 §3.3 "
            f"ORCH-COND-002, the marker records the reason, the responsible "
            f"authority, the date, any conditions, and an audit trail."
        )


class EquivalentControlNotEquivalent(Exception):
    """An Equivalent Control is asserted but the assurance statement is empty.

    Per Document 06 §3.3 ORCH-COND-003: "A stage marked Replaced by
    an Equivalent Control shall not be a waiver of constitutional
    controls. The Equivalent Control shall provide equivalent
    assurance."
    """

    def __init__(self) -> None:
        super().__init__(
            "Equivalent Control is asserted but the assurance statement is "
            "empty. Per Document 06 §3.3 ORCH-COND-003, the Equivalent Control "
            "shall provide equivalent assurance; an empty assurance is a "
            "waiver, not an equivalent control."
        )


# ---------------------------------------------------------------------------
# Stage Omission Record
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StageOmissionRecord:
    """The constitutional record of a stage omission.

    Per ORCH-COND-002, the record carries: type, stage, reason,
    responsible authority, date, any conditions, and an audit trail.
    """

    canonical_id: str
    opportunity_canonical_id: str
    stage: StageNumber
    omission_type: OmissionType
    reason: str
    responsible_authority: str  # who decided the omission
    recorded_at: str
    # Required for SKIPPED_BY_AUTHORIZED_HUMAN_DECISION and
    # REPLACED_BY_EQUIVALENT_CONTROL:
    human_approval_id: str | None = None
    # Required for REPLACED_BY_EQUIVALENT_CONTROL:
    equivalent_control_reference: str | None = None  # the control's id
    equivalent_control_assurance: str | None = None  # the assurance statement
    # For DEFERRED:
    re_entry_date: str | None = None
    # Optional conditions:
    conditions: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# ORCH-COND Engine
# ---------------------------------------------------------------------------


class ORCHCONDMissingHumanApproval(Exception):
    """Alias for ORCHCONDMissingApproval (kept for symmetry)."""

    def __init__(self, omission_type: OmissionType) -> None:
        super().__init__(omission_type)


class ORCHCONDMissingEquivalentControlAssurance(EquivalentControlNotEquivalent):
    """Alias."""


class ORCHCONDMissingReEntry(Exception):
    """DEFERRED omission requires a re_entry_date."""

    def __init__(self) -> None:
        super().__init__(
            "DEFERRED omission requires a re_entry_date. Per Document 06 §3.3 "
            "ORCH-COND-002, the marker records the reason, the responsible "
            "authority, the date, any conditions, and an audit trail."
        )


class ORCHCONDMissingReason(Exception):
    """All omissions require a reason."""

    def __init__(self) -> None:
        super().__init__(
            "Every ORCH-COND marker requires a reason. Per Document 06 §3.3 "
            "ORCH-COND-002, the reason is recorded."
        )


class ORCHCONDEngine:
    """Pure-logic ORCH-COND engine.

    Methods:
      - mark: validate and record a stage omission
      - has_omission: check if a stage has an omission
    """

    def __init__(self) -> None:
        self.records: list[StageOmissionRecord] = []

    def mark(
        self,
        *,
        opportunity_canonical_id: str,
        stage: StageNumber,
        omission_type: OmissionType,
        reason: str,
        responsible_authority: str,
        recorded_at: str = "",
        human_approval_id: str | None = None,
        equivalent_control_reference: str | None = None,
        equivalent_control_assurance: str | None = None,
        re_entry_date: str | None = None,
        conditions: tuple[str, ...] = (),
        canonical_id: str = "",
    ) -> StageOmissionRecord:
        """Mark a stage as omitted under one of the 4 types.

        Per Constitution Article XI paragraph 5 and Document 06 §3.3:
          - SKIPPED_BY_AUTHORIZED_HUMAN_DECISION and
            REPLACED_BY_EQUIVALENT_CONTROL require a Human Approval.
          - REPLACED_BY_EQUIVALENT_CONTROL requires an assurance
            statement (not a waiver).
          - DEFERRED requires a re_entry_date.
        """
        if not reason or not reason.strip():
            raise ORCHCONDMissingReason()
        if omission_type in APPROVAL_REQUIRED_OMISSIONS and not human_approval_id:
            raise ORCHCONDMissingApproval(omission_type)
        if omission_type == OmissionType.REPLACED_BY_EQUIVALENT_CONTROL:
            if not equivalent_control_assurance or not equivalent_control_assurance.strip():
                raise EquivalentControlNotEquivalent()
            if not equivalent_control_reference:
                # The Equivalent Control must be referenced (its id or
                # other identifier).
                raise EquivalentControlNotEquivalent()
        if omission_type == OmissionType.DEFERRED and not re_entry_date:
            raise ORCHCONDMissingReEntry()
        rec = StageOmissionRecord(
            canonical_id=canonical_id or _uuid_str(),
            opportunity_canonical_id=opportunity_canonical_id,
            stage=stage,
            omission_type=omission_type,
            reason=reason,
            responsible_authority=responsible_authority,
            recorded_at=recorded_at or _now_iso(),
            human_approval_id=human_approval_id,
            equivalent_control_reference=equivalent_control_reference,
            equivalent_control_assurance=equivalent_control_assurance,
            re_entry_date=re_entry_date,
            conditions=conditions,
        )
        self.records.append(rec)
        return rec

    def has_omission(self, opportunity_canonical_id: str, stage: StageNumber) -> bool:
        return any(
            r.opportunity_canonical_id == opportunity_canonical_id and r.stage == stage
            for r in self.records
        )

    def get_omission(
        self, opportunity_canonical_id: str, stage: StageNumber
    ) -> StageOmissionRecord | None:
        for r in self.records:
            if r.opportunity_canonical_id == opportunity_canonical_id and r.stage == stage:
                return r
        return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _uuid_str() -> str:
    import uuid
    return str(uuid.uuid4())


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
