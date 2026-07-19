"""Knowledge and Institutional Memory Engine — Document 02 §4.13, Phase 6.

Implements the pure-logic engine for the three Knowledge and
Institutional Memory Principal Agents activated in Phase 6:

  - Knowledge Base Curator Agent (§4.13.1) — Stage 22 (Knowledge
    Capture). Maintains the Knowledge Base; preserves provenance;
    enforces data quality. May NOT silently delete or overwrite
    records.
  - Institutional Memory Manager Agent (§4.13.2) — Stage 23
    (Institutional Memory). Maintains the Institutional Memory Index;
    coordinates retention. May NOT silently delete records.
  - Lessons Learned Analyst Agent (§4.13.3) — Stage 22 (Knowledge
    Capture). Extracts Lessons Learned from closed Opportunities;
    publishes the Lessons Learned Index. May NOT silently amend
    records.

Constitutional source:
  - Document 02 §4.13 (Knowledge and Institutional Memory Office)
  - Document 05 §3.15 (ENT-KNO-001..004)
  - Document 06 §2.22..2.23 (Stages 22-23)
  - Constitution Article XX §6 (No Silent Amendment)
  - Constitution Article XX (Institutional Memory)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class KnowledgeQualityStatus(str, Enum):
    DRAFT = "DRAFT"
    REVIEWED = "REVIEWED"
    PUBLISHED = "PUBLISHED"
    DEPRECATED = "DEPRECATED"


class InstitutionalMemoryRetentionClass(str, Enum):
    PERMANENT = "PERMANENT"
    LONG_TERM = "LONG_TERM"
    STANDARD = "STANDARD"
    SHORT_TERM = "SHORT_TERM"


class LessonLearnedOutcome(str, Enum):
    WON = "WON"
    LOST = "LOST"
    ON_HOLD = "ON_HOLD"
    CLOSED = "CLOSED"


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class KnowledgeEngineError(Exception):
    """Base for knowledge engine errors."""


class KnowledgeRecordMissingProvenanceError(KnowledgeEngineError):
    """A Knowledge Record is missing the provenance / source citation.

    Per Document 02 §4.13.1 Failure Conditions: "Unprovenanced record;
    stale record; quality drift." Every Knowledge Record MUST carry
    a source citation."""

    def __init__(self) -> None:
        super().__init__(
            f"Knowledge Record REJECTED: missing source citation / provenance. "
            f"Per Document 02 §4.13.1, every Knowledge Record must carry "
            f"a source citation. The Knowledge Base Curator Agent may NOT "
            f"silently amend records."
        )


class KnowledgeQualityStatusRejectionError(KnowledgeEngineError):
    """A Knowledge Record's quality status transition is REJECTED.

    Quality status transitions are governed (DRAFT → REVIEWED →
    PUBLISHED → DEPRECATED). A transition that skips the governance
    flow is REJECTED.
    """

    def __init__(self, from_status: str, to_status: str) -> None:
        self.from_status = from_status
        self.to_status = to_status
        super().__init__(
            f"Knowledge Record quality status transition REJECTED: "
            f"{from_status} → {to_status}. The governed flow is "
            f"DRAFT → REVIEWED → PUBLISHED → DEPRECATED. Skipping a "
            f"stage is REJECTED."
        )


class InstitutionalMemorySilentDeletionError(KnowledgeEngineError):
    """The Institutional Memory Manager is constitutionally PROHIBITED
    from silently deleting records."""

    def __init__(self) -> None:
        super().__init__(
            f"Institutional Memory silent deletion REJECTED. Per Document 02 "
            f"§4.13.2 Authority Limits: 'May not silently delete records; may "
            f"not bind Techno Service.' Every material deletion requires a "
           "Human Approval and a Decision Log Entry."
        )


class LessonLearnedMissingOutcomeError(KnowledgeEngineError):
    """A Lesson Learned is missing the outcome reference (the closed
    Opportunity it was extracted from)."""

    def __init__(self) -> None:
        super().__init__(
            f"Lesson Learned REJECTED: missing outcome reference. "
            f"Per Document 02 §4.13.3, every Lesson Learned is extracted "
            f"from a closed Opportunity or a Constitutional Incident "
            f"and must record the source."
        )


# ---------------------------------------------------------------------------
# Inputs / Outputs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class KnowledgeRecordSpec:
    """The input spec for a Knowledge Record."""

    title: str
    body: str
    domain: str
    tags: str = ""
    source_citation: str = ""
    quality_status: str = "DRAFT"


@dataclass(frozen=True)
class KnowledgeRecordResult:
    """The result of a Knowledge Record validation."""

    title: str
    body: str
    domain: str
    tags: str
    source_citation: str
    quality_status: KnowledgeQualityStatus
    has_provenance: bool


@dataclass(frozen=True)
class InstitutionalMemoryIndexSpec:
    """The input spec for an Institutional Memory Index entry."""

    target_type: str
    target_id: str
    retention_class: str = "PERMANENT"
    retention_until: Optional[str] = None
    human_approval_id: Optional[str] = None  # Required for any material deletion


@dataclass(frozen=True)
class InstitutionalMemoryIndexResult:
    """The result of an Institutional Memory Index entry."""

    target_type: str
    target_id: str
    retention_class: InstitutionalMemoryRetentionClass
    retention_until: Optional[str]
    deletion_authorized: bool


@dataclass(frozen=True)
class LessonLearnedSpec:
    """The input spec for a Lesson Learned."""

    title: str
    body: str
    outcome: str  # WON / LOST / ON_HOLD / CLOSED
    target_opportunity_id: Optional[str] = None
    source_citation: str = ""


@dataclass(frozen=True)
class LessonLearnedResult:
    """The result of a Lesson Learned validation."""

    title: str
    body: str
    outcome: LessonLearnedOutcome
    target_opportunity_id: Optional[str]
    source_citation: str
    has_source: bool


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class KnowledgeEngine:
    """The pure-logic engine for the Knowledge and Institutional
    Memory Office. All three agents (Knowledge Base Curator,
    Institutional Memory Manager, Lessons Learned Analyst) are
    methods on this engine."""

    # -----------------------------------------------------------------
    # Knowledge Base Curator (§4.13.1) — Stage 22
    # -----------------------------------------------------------------

    def validate_knowledge_record(
        self, spec: KnowledgeRecordSpec
    ) -> KnowledgeRecordResult:
        """Validate a Knowledge Record.

        Enforces:
          - title, body, domain are non-empty.
          - source_citation is non-empty (provenance).
          - quality_status is one of DRAFT / REVIEWED / PUBLISHED / DEPRECATED.
        """
        if not spec.title or not spec.title.strip():
            raise ValueError("title is required")
        if not spec.body or not spec.body.strip():
            raise ValueError("body is required")
        if not spec.domain or not spec.domain.strip():
            raise ValueError("domain is required")
        if not spec.source_citation or not spec.source_citation.strip():
            raise KnowledgeRecordMissingProvenanceError()
        valid = {"DRAFT", "REVIEWED", "PUBLISHED", "DEPRECATED"}
        if spec.quality_status.upper() not in valid:
            raise ValueError(
                f"quality_status must be one of: {sorted(valid)}; got {spec.quality_status!r}"
            )
        return KnowledgeRecordResult(
            title=spec.title,
            body=spec.body,
            domain=spec.domain,
            tags=spec.tags,
            source_citation=spec.source_citation,
            quality_status=KnowledgeQualityStatus(spec.quality_status.upper()),
            has_provenance=True,
        )

    def check_quality_status_transition(
        self, *, from_status: str, to_status: str
    ) -> None:
        """Check a quality status transition. The governed flow is
        DRAFT → REVIEWED → PUBLISHED → DEPRECATED.

        Skipping a stage is REJECTED. Backwards transitions are
        permitted only by Human Approval (out of scope here).
        """
        order = ["DRAFT", "REVIEWED", "PUBLISHED", "DEPRECATED"]
        try:
            from_idx = order.index(from_status.upper())
            to_idx = order.index(to_status.upper())
        except ValueError as e:
            raise ValueError(f"unknown quality status: {e}")
        # Allow forward single-step, equal, or backwards-to-DRAFT (deprecation).
        if to_idx == from_idx:
            return  # no-op
        if to_idx == from_idx + 1:
            return  # forward single-step
        if to_idx < from_idx:
            # backwards (e.g. PUBLISHED → DEPRECATED is forward; but
            # PUBLISHED → DRAFT would be a reversion — REJECTED
            # without Human Approval, which we model as "more than
            # 1 step backwards")
            if from_idx - to_idx > 1:
                raise KnowledgeQualityStatusRejectionError(from_status, to_status)
            return
        # more than 1 step forward
        raise KnowledgeQualityStatusRejectionError(from_status, to_status)

    # -----------------------------------------------------------------
    # Institutional Memory Manager (§4.13.2) — Stage 23
    # -----------------------------------------------------------------

    def validate_institutional_memory(
        self, spec: InstitutionalMemoryIndexSpec
    ) -> InstitutionalMemoryIndexResult:
        """Validate an Institutional Memory Index entry.

        Enforces:
          - target_type, target_id are non-empty.
          - retention_class is one of the 4 valid classes.
          - If retention_until is set (i.e. a deletion is implied),
            a Human Approval reference is REQUIRED.
        """
        if not spec.target_type or not spec.target_type.strip():
            raise ValueError("target_type is required")
        if not spec.target_id or not spec.target_id.strip():
            raise ValueError("target_id is required")
        valid = {"PERMANENT", "LONG_TERM", "STANDARD", "SHORT_TERM"}
        if spec.retention_class.upper() not in valid:
            raise ValueError(
                f"retention_class must be one of: {sorted(valid)}; got {spec.retention_class!r}"
            )
        # Material deletion requires Human Approval.
        deletion_authorized = bool(
            spec.retention_until and spec.human_approval_id and spec.human_approval_id.strip()
        )
        if spec.retention_until and not deletion_authorized:
            raise InstitutionalMemorySilentDeletionError()
        return InstitutionalMemoryIndexResult(
            target_type=spec.target_type,
            target_id=spec.target_id,
            retention_class=InstitutionalMemoryRetentionClass(spec.retention_class.upper()),
            retention_until=spec.retention_until,
            deletion_authorized=deletion_authorized,
        )

    # -----------------------------------------------------------------
    # Lessons Learned Analyst (§4.13.3) — Stage 22
    # -----------------------------------------------------------------

    def validate_lesson_learned(self, spec: LessonLearnedSpec) -> LessonLearnedResult:
        """Validate a Lesson Learned.

        Enforces:
          - title, body, outcome are non-empty.
          - outcome is one of WON / LOST / ON_HOLD / CLOSED.
          - Either target_opportunity_id (a closed Opportunity) or
            source_citation (a Constitutional Incident report) is
            present — the lesson must be sourced.
        """
        if not spec.title or not spec.title.strip():
            raise ValueError("title is required")
        if not spec.body or not spec.body.strip():
            raise ValueError("body is required")
        valid = {"WON", "LOST", "ON_HOLD", "CLOSED"}
        if spec.outcome.upper() not in valid:
            raise ValueError(
                f"outcome must be one of: {sorted(valid)}; got {spec.outcome!r}"
            )
        has_opp = bool(spec.target_opportunity_id and spec.target_opportunity_id.strip())
        has_source = bool(spec.source_citation and spec.source_citation.strip())
        if not has_opp and not has_source:
            raise LessonLearnedMissingOutcomeError()
        return LessonLearnedResult(
            title=spec.title,
            body=spec.body,
            outcome=LessonLearnedOutcome(spec.outcome.upper()),
            target_opportunity_id=spec.target_opportunity_id,
            source_citation=spec.source_citation,
            has_source=True,
        )
