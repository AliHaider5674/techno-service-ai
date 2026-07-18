"""AI Recommendation — Constitution Article X + UI/UX §9 (AIW-001..009).

AI Recommendations are constitutional objects that must be:
  1. Sourced — every Recommendation has source citations
     (Constitution Article X paragraph 8 "No Fabrication").
  2. Evidenced — the Recommendation has at least one Evidence record
     (Article X paragraph 6 "Verified-Only Output").
  3. Confident — the Recommendation has a confidence score
     (UI/UX AIW-003).
  4. Explainable — the Recommendation has a reasoning record
     (UI/UX AIW-006).

A Recommendation without ANY of these is REJECTED. A Recommendation
that is presented as Human Authority is REJECTED (Constitution
Article X paragraph 6: AI is a co-pilot, not a replacement;
Constitution Article XIV: Human Corporate Authority is absolute).

This is a pure-logic module. The presentation layer (SCR-AI-001..004)
displays the Recommendation with its source, evidence, confidence,
and explainability, and makes the constitutional role of AI visible.

Constitutional source:
  - Constitution Articles V, X, XIV, XXI, XXVII
  - Document 06 §9 (Cross-Office Collaboration)
  - UI/UX §9 (AIW-001..009)
  - Document 04 §1.4 (AI Orchestration Service)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping


# ---------------------------------------------------------------------------
# Recommendation outcome
# ---------------------------------------------------------------------------


class RecommendationOutcome(str, Enum):
    """The possible outcomes of an AI Recommendation.

    The user (or the workflow) can ACCEPT, REJECT, REQUEST_HUMAN
    (escalate to a human authority), or DEFER (record for later).
    """

    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    REQUESTED_HUMAN = "REQUESTED_HUMAN"
    DEFERRED = "DEFERRED"
    PENDING = "PENDING"


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class AIRecommendationError(Exception):
    """Generic AI Recommendation error."""


class AIRecommendationNotConstitutional(AIRecommendationError):
    """A Recommendation is missing one of the 4 mandatory properties.

    Per Constitution Article X paragraph 8 and UI/UX §9, every
    Recommendation must carry: source, evidence, confidence,
    explainability. A Recommendation without any of these is REJECTED.
    """

    def __init__(self, missing: str) -> None:
        self.missing = missing
        super().__init__(
            f"AI Recommendation REJECTED: missing {missing}. "
            f"Per Constitution Article X paragraph 8 and UI/UX §9 "
            f"(AIW-002..006), every AI Recommendation must carry: "
            f"source, evidence, confidence, explainability. A "
            f"Recommendation without any of these is REJECTED."
        )


class AIRecommendationPresentsAsHumanAuthority(AIRecommendationError):
    """A Recommendation is presented as Human Authority.

    Per Constitution Article X paragraph 6: AI is a co-pilot, not
    a replacement. Per Article XIV: Human Corporate Authority is
    absolute. Per UI/UX §9 AIW-007: "The AI Workspace does not
    present AI Recommendations as Human Decisions."
    """

    def __init__(self) -> None:
        super().__init__(
            "AI Recommendation REJECTED: presented as Human Authority. "
            "Per Constitution Article X paragraph 6, Article XIV, and "
            "UI/UX §9 AIW-007, AI Recommendations do not constitute "
            "Human Decisions, Human Approvals, or authoritative material. "
            "The constitutional role of AI is co-pilot, not replacement."
        )


class AIConfidenceOutOfRange(AIRecommendationError):
    """A Recommendation's confidence is out of the [0, 1] range."""

    def __init__(self, confidence: float) -> None:
        self.confidence = confidence
        super().__init__(
            f"AI Recommendation confidence must be in [0, 1], got {confidence}"
        )


# ---------------------------------------------------------------------------
# AI Recommendation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AIRecommendation:
    """An AI Recommendation per Constitution Article X + UI/UX §9.

    The Recommendation is a constitutional record. It is hash-chained
    to the audit log via the service layer.
    """

    canonical_id: str
    producer_agent_id: str
    producer_agent_role: str  # The Principal Agent that produced the Recommendation
    target_entity_type: str  # e.g. "Opportunity", "Manufacturer"
    target_entity_canonical_id: str
    recommendation_text: str
    # The 4 mandatory properties (per Constitution Article X + UI/UX §9):
    source_citations: tuple[str, ...]  # at least 1
    evidence_canonical_ids: tuple[str, ...]  # at least 1
    confidence: float  # 0..1
    explainability: str  # reasoning text
    # Optional:
    constitutional_role_acknowledged: bool = True  # must be True (the Recommendation
    # acknowledges that AI is co-pilot, not replacement)
    presented_as_human_authority: bool = False  # must be False
    office: str = ""
    issued_at: str = ""
    outcome: RecommendationOutcome = RecommendationOutcome.PENDING
    outcome_by: str = ""
    outcome_at: str = ""


# ---------------------------------------------------------------------------
# AI Recommendation Engine
# ---------------------------------------------------------------------------


class AIRecommendationEngine:
    """Pure-logic AI Recommendation engine.

    Methods:
      - issue: validate and record a Recommendation
      - set_outcome: record the user's outcome (ACCEPT/REJECT/REQUEST_HUMAN)
    """

    def __init__(self) -> None:
        self.recommendations: dict[str, AIRecommendation] = {}
        self.rejections: list[AIRecommendationError] = []

    def issue(
        self,
        *,
        producer_agent_id: str,
        producer_agent_role: str,
        target_entity_type: str,
        target_entity_canonical_id: str,
        recommendation_text: str,
        source_citations: tuple[str, ...] = (),
        evidence_canonical_ids: tuple[str, ...] = (),
        confidence: float = 0.0,
        explainability: str = "",
        office: str = "",
        issued_at: str = "",
        constitutional_role_acknowledged: bool = True,
        presented_as_human_authority: bool = False,
        canonical_id: str = "",
    ) -> AIRecommendation:
        """Issue a Recommendation. Enforces the 4 mandatory properties.

        Per Constitution Article X + UI/UX §9 AIW-002..006, every
        Recommendation must carry:
          1. source (at least one source citation)
          2. evidence (at least one Evidence record reference)
          3. confidence (in [0, 1])
          4. explainability (a reasoning text)
        """
        # Enforce the 4 mandatory properties.
        if not source_citations:
            err = AIRecommendationNotConstitutional("source (at least one source citation)")
            self.rejections.append(err)
            raise err
        if not evidence_canonical_ids:
            err = AIRecommendationNotConstitutional("evidence (at least one Evidence record reference)")
            self.rejections.append(err)
            raise err
        if not (0.0 <= confidence <= 1.0):
            raise AIConfidenceOutOfRange(confidence)
        if not explainability or not explainability.strip():
            err = AIRecommendationNotConstitutional("explainability (reasoning text)")
            self.rejections.append(err)
            raise err
        if presented_as_human_authority:
            err = AIRecommendationPresentsAsHumanAuthority()
            self.rejections.append(err)
            raise err
        if not constitutional_role_acknowledged:
            err = AIRecommendationNotConstitutional(
                "constitutional_role_acknowledged (must acknowledge AI is co-pilot, not replacement)"
            )
            self.rejections.append(err)
            raise err
        rec = AIRecommendation(
            canonical_id=canonical_id or _uuid_str(),
            producer_agent_id=producer_agent_id,
            producer_agent_role=producer_agent_role,
            target_entity_type=target_entity_type,
            target_entity_canonical_id=target_entity_canonical_id,
            recommendation_text=recommendation_text,
            source_citations=source_citations,
            evidence_canonical_ids=evidence_canonical_ids,
            confidence=confidence,
            explainability=explainability,
            constitutional_role_acknowledged=constitutional_role_acknowledged,
            presented_as_human_authority=presented_as_human_authority,
            office=office,
            issued_at=issued_at or _now_iso(),
        )
        self.recommendations[rec.canonical_id] = rec
        return rec

    def set_outcome(
        self,
        canonical_id: str,
        outcome: RecommendationOutcome,
        outcome_by: str,
        outcome_at: str = "",
    ) -> AIRecommendation:
        """Record the user's outcome (ACCEPT / REJECT / REQUEST_HUMAN / DEFER)."""
        rec = self.recommendations.get(canonical_id)
        if rec is None:
            raise ValueError(f"Unknown AI Recommendation: {canonical_id}")
        from dataclasses import replace
        new_rec = replace(
            rec,
            outcome=outcome,
            outcome_by=outcome_by,
            outcome_at=outcome_at or _now_iso(),
        )
        self.recommendations[canonical_id] = new_rec
        return new_rec

    def by_office(self, office: str) -> list[AIRecommendation]:
        return [r for r in self.recommendations.values() if r.office == office]

    def by_target(self, target_entity_canonical_id: str) -> list[AIRecommendation]:
        return [r for r in self.recommendations.values() if r.target_entity_canonical_id == target_entity_canonical_id]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _uuid_str() -> str:
    import uuid
    return str(uuid.uuid4())


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
