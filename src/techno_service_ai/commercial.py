"""Commercial Engine — Document 02 §4.6, Phase 5.

Implements the pure-logic engine for the three Commercial Development
Principal Agents activated in Phase 5:

  - Commercial Evaluation Agent (§4.6.1) — produces a Commercial
    Evaluation (ENT-COM-001) with a multi-dimensional scorecard,
    assumptions, and uncertainty.
  - Pricing and Margin Analyst Agent (§4.6.5) — produces a Pricing
    Analysis (ENT-COM-005) with a margin floor check.
  - Business Development Agent (§4.6.3) — produces a Business
    Development Engagement record (ENT-COM-003). Constitutionally
    REQUIRES (a) Human Approval reference and (b) register clearance
    (Constitution Article VIII) before any external contact.

The engine is PURE LOGIC — no database, no HTTP. The Service Layer
wires the engine to the data layer, the Register Compliance engine,
and the Approval engine.

Constitutional source:
  - Document 02 §4.6 (Commercial Development Office)
  - Document 05 §3.7 (ENT-COM-001, 003, 005)
  - Constitution Article VIII (registers at every commercial gate)
  - Constitution Article XII (Human Approval for Class 3 / Class 4)
  - Document 06 §4.5 GATE-CO-002 (Commercial Gate)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class CommercialViability(str, Enum):
    """The overall viability classification of a Commercial Evaluation.

    Per Document 02 §4.6.1 Escalation Triggers: "Return below the
    approved probability-of-success threshold; commercial viability
    gap."
    """

    COMMERCIALLY_VIABLE = "COMMERCIALLY_VIABLE"
    CONDITIONALLY_VIABLE = "CONDITIONALLY_VIABLE"
    NOT_VIABLE = "NOT_VIABLE"
    UNVERIFIED = "UNVERIFIED"


class CommercialEvaluationDimension(str, Enum):
    """The dimensions of a Commercial Evaluation.

    Per Document 02 §4.6.1 Responsibilities, the Agent assesses:
      - return on investment
      - market fit
      - competitive advantage
      - agency opportunity
      - profitability
      - risk
      - commercial feasibility

    We store these as 7 dimensions in the engine. The Service Layer
    maps them to the schema's commercial_evaluation record (which
    uses free-text fields; the engine is the source of truth for the
    multi-dimensional requirement).
    """

    ROI = "ROI"
    MARKET_FIT = "MARKET_FIT"
    COMPETITIVE_ADVANTAGE = "COMPETITIVE_ADVANTAGE"
    AGENCY_OPPORTUNITY = "AGENCY_OPPORTUNITY"
    PROFITABILITY = "PROFITABILITY"
    RISK = "RISK"
    COMMERCIAL_FEASIBILITY = "COMMERCIAL_FEASIBILITY"


COMMERCIAL_EVALUATION_DIMENSIONS: Tuple[str, ...] = tuple(d.value for d in CommercialEvaluationDimension)


class PricingStatus(str, Enum):
    """The status of a Pricing Analysis output.

    The Agent (Document 02 §4.6.5) flags margin floors and deviation
    from approved price cards.
    """

    WITHIN_FLOOR = "WITHIN_FLOOR"
    AT_FLOOR = "AT_FLOOR"
    BELOW_FLOOR = "BELOW_FLOOR"  # Requires Human Approval
    UNVERIFIED = "UNVERIFIED"


class EngagementType(str, Enum):
    """The engagement type of a Business Development Activity."""

    ENGAGEMENT_MATERIAL = "ENGAGEMENT_MATERIAL"
    MEETING_BRIEF = "MEETING_BRIEF"
    FOLLOW_UP_PLAN = "FOLLOW_UP_PLAN"
    PIPELINE_UPDATE = "PIPELINE_UPDATE"


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class CommercialEngineError(Exception):
    """Base for commercial engine errors."""


class CommercialEvaluationIncompleteError(CommercialEngineError):
    """A Commercial Evaluation is missing one or more required dimensions.

    Per Document 02 §4.6.1 and AC-P5-004, a Commercial Evaluation
    MUST be multi-dimensional. A single-dimension evaluation is a
    Failure Condition.
    """

    def __init__(self, missing: Tuple[str, ...]) -> None:
        self.missing = missing
        super().__init__(
            f"Commercial Evaluation is REJECTED: missing dimensions {list(missing)}. "
            f"Per Document 02 §4.6.1, a Commercial Evaluation MUST be multi-dimensional. "
            f"Single-dimension evaluation is a Failure Condition. "
            f"Required dimensions: {COMMERCIAL_EVALUATION_DIMENSIONS}."
        )


class CommercialEvaluationMissingAssumptionsError(CommercialEngineError):
    """A Commercial Evaluation is missing the Assumptions and Uncertainty
    fields. Per Document 02 §4.6.1, both are Required Evidence."""

    def __init__(self, field_name: str) -> None:
        self.field_name = field_name
        super().__init__(
            f"Commercial Evaluation is REJECTED: missing field '{field_name}'. "
            f"Per Document 02 §4.6.1 Required Evidence, every Commercial Evaluation "
            f"must record assumptions and uncertainty."
        )


class PricingBelowFloorError(CommercialEngineError):
    """A pricing scenario is below the approved margin floor — REJECTED
    without Human Approval.

    Per Document 02 §4.6.5 Escalation Triggers: "Margin below approved
    floor; price outside market range." Pricing below the floor
    requires explicit Human Approval to proceed.
    """

    def __init__(self, proposed_margin: float, floor: float) -> None:
        self.proposed_margin = proposed_margin
        self.floor = floor
        super().__init__(
            f"Pricing REJECTED: proposed margin {proposed_margin} is below the "
            f"approved margin floor {floor}. Per Document 02 §4.6.5, pricing "
            f"below the floor is an Escalation Trigger and requires Human "
            f"Approval (Class 4, Authority Matrix §4.13)."
        )


class BDEngagementMissingApprovalError(CommercialEngineError):
    """A Business Development Engagement is missing the Human Approval
    reference. Per Document 02 §4.6.3, the Agent is constitutionally
    PROHIBITED from initiating contact without Human Approval.
    """

    def __init__(self) -> None:
        super().__init__(
            f"Business Development Engagement REJECTED: no Human Approval reference. "
            f"Per Document 02 §4.6.3 Authority Limits: 'May not contact a counterparty "
            f"without Human Approval; may not bind Techno Service; may not commit prices, "
            f"margins, or terms.' Every BD engagement REQUIRES Human Approval."
        )


class BDEngagementRegisterBlockedError(CommercialEngineError):
    """A Business Development Engagement is blocked by the Register
    Compliance Gate. The actual register-rejection exception (from
    register_compliance) is raised by the Service Layer; this exception
    is a wrapper that carries the BD context."""

    def __init__(self, register_outcome: str) -> None:
        self.register_outcome = register_outcome
        super().__init__(
            f"Business Development Engagement BLOCKED by Register Compliance Gate: "
            f"register outcome '{register_outcome}'. Per Constitution Article VIII and "
            f"Document 06 §4.5 GATE-CO-002, no commercial action may proceed without "
            f"a clear register check."
        )


# ---------------------------------------------------------------------------
# Inputs / Outputs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CommercialDimensionScore:
    """A score for one dimension of the Commercial Evaluation."""

    dimension: str  # One of COMMERCIAL_EVALUATION_DIMENSIONS
    score: str  # 'HIGH' / 'MEDIUM' / 'LOW' / 'UNKNOWN'
    rationale: str = ""


@dataclass(frozen=True)
class CommercialEvaluationSpec:
    """The input spec for a Commercial Evaluation."""

    opportunity_id: str
    evaluation_date: str
    source_citation: str
    dimensions: Tuple[CommercialDimensionScore, ...]
    assumptions: str
    uncertainty: str
    margin_estimate: str = ""
    pricing_basis: str = ""


@dataclass(frozen=True)
class CommercialEvaluationResult:
    """The result of a Commercial Evaluation evaluation."""

    opportunity_id: str
    evaluation_date: str
    dimension_scores: Tuple[CommercialDimensionScore, ...]
    overall_viability: CommercialViability
    assumptions: str
    uncertainty: str
    rationale: str
    missing_dimensions: Tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.missing_dimensions:
            raise CommercialEvaluationIncompleteError(self.missing_dimensions)
        if not self.assumptions or not self.assumptions.strip():
            raise CommercialEvaluationMissingAssumptionsError("assumptions")
        if not self.uncertainty or not self.uncertainty.strip():
            raise CommercialEvaluationMissingAssumptionsError("uncertainty")


@dataclass(frozen=True)
class PricingAnalysisSpec:
    """The input spec for a Pricing Analysis."""

    opportunity_id: str
    analysis_date: str
    source_citation: str
    pricing_basis: str
    margin_scenarios: str
    margin_floor: Optional[float] = None  # If set, the proposed margin is checked against the floor


@dataclass(frozen=True)
class PricingAnalysisResult:
    """The result of a Pricing Analysis evaluation."""

    opportunity_id: str
    analysis_date: str
    pricing_basis: str
    margin_scenarios: str
    status: PricingStatus
    margin_floor: Optional[float]
    proposed_margin: Optional[float]
    requires_human_approval: bool  # True if below the floor


@dataclass(frozen=True)
class BDEngagementSpec:
    """The input spec for a Business Development Engagement record."""

    opportunity_id: str
    engagement_type: EngagementType
    counterpart: str
    summary: str
    engagement_date: str
    # The Human Approval reference — REQUIRED for any contact.
    human_approval_id: Optional[str] = None
    # The Register Compliance result — REQUIRED for any contact.
    register_outcome: Optional[str] = None  # 'CLEARED' / 'REJECTED_*'


@dataclass(frozen=True)
class BDEngagementResult:
    """The result of a BD Engagement evaluation."""

    opportunity_id: str
    engagement_type: EngagementType
    counterpart: str
    summary: str
    engagement_date: str
    human_approval_id: Optional[str]
    register_outcome: Optional[str]
    is_authorized: bool  # True when both human approval and register clearance are present
    missing_approval: bool
    register_blocked: bool


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class CommercialEngine:
    """The pure-logic engine for the Commercial Development Office."""

    # -----------------------------------------------------------------
    # Commercial Evaluation (§4.6.1)
    # -----------------------------------------------------------------

    def evaluate(self, spec: CommercialEvaluationSpec) -> CommercialEvaluationResult:
        """Evaluate a Commercial Evaluation.

        Enforces:
          - All 7 dimensions are present (AC-P5-004 — multi-dimensional).
          - Assumptions and Uncertainty are recorded (Required Evidence).
          - Computes the overall viability classification.
        """
        # 1. Check that all 7 dimensions are present.
        present = {d.dimension for d in spec.dimensions}
        missing = tuple(d for d in COMMERCIAL_EVALUATION_DIMENSIONS if d not in present)
        if missing:
            raise CommercialEvaluationIncompleteError(missing)

        # 2. Check assumptions and uncertainty.
        if not spec.assumptions or not spec.assumptions.strip():
            raise CommercialEvaluationMissingAssumptionsError("assumptions")
        if not spec.uncertainty or not spec.uncertainty.strip():
            raise CommercialEvaluationMissingAssumptionsError("uncertainty")

        # 3. Compute overall viability.
        scores = [d.score.upper() for d in spec.dimensions]
        high = sum(1 for s in scores if s == "HIGH")
        low = sum(1 for s in scores if s == "LOW")
        unknown = sum(1 for s in scores if s == "UNKNOWN")
        if unknown == len(scores):
            viability = CommercialViability.UNVERIFIED
        elif low >= 3:
            viability = CommercialViability.NOT_VIABLE
        elif low >= 1:
            viability = CommercialViability.CONDITIONALLY_VIABLE
        elif high == len(scores):
            viability = CommercialViability.COMMERCIALLY_VIABLE
        else:
            viability = CommercialViability.CONDITIONALLY_VIABLE

        rationale = (
            f"Scorecard: HIGH={high}, LOW={low}, UNKNOWN={unknown}. "
            f"Overall: {viability.value}."
        )

        return CommercialEvaluationResult(
            opportunity_id=spec.opportunity_id,
            evaluation_date=spec.evaluation_date,
            dimension_scores=spec.dimensions,
            overall_viability=viability,
            assumptions=spec.assumptions,
            uncertainty=spec.uncertainty,
            rationale=rationale,
        )

    # -----------------------------------------------------------------
    # Pricing Analysis (§4.6.5)
    # -----------------------------------------------------------------

    def evaluate_pricing(self, spec: PricingAnalysisSpec) -> PricingAnalysisResult:
        """Evaluate a Pricing Analysis.

        If a margin_floor is set, parses the proposed margin from
        margin_scenarios and checks it against the floor. Below the
        floor requires Human Approval (PricingBelowFloorError).
        """
        proposed_margin = self._parse_margin(spec.margin_scenarios)
        status = PricingStatus.UNVERIFIED
        requires_human_approval = False

        if spec.margin_floor is not None and proposed_margin is not None:
            if proposed_margin < spec.margin_floor:
                status = PricingStatus.BELOW_FLOOR
                requires_human_approval = True
            elif proposed_margin == spec.margin_floor:
                status = PricingStatus.AT_FLOOR
            else:
                status = PricingStatus.WITHIN_FLOOR

        return PricingAnalysisResult(
            opportunity_id=spec.opportunity_id,
            analysis_date=spec.analysis_date,
            pricing_basis=spec.pricing_basis,
            margin_scenarios=spec.margin_scenarios,
            status=status,
            margin_floor=spec.margin_floor,
            proposed_margin=proposed_margin,
            requires_human_approval=requires_human_approval,
        )

    @staticmethod
    def _parse_margin(margin_scenarios: str) -> Optional[float]:
        """Extract a numeric margin from the margin_scenarios text.

        Recognises "margin=X", "margin: X", "margin=X.X%". Returns the
        numeric value (in the same units as the input — typically a
        percent like 12.5). If the margin cannot be parsed, returns
        None (the caller treats this as UNVERIFIED).
        """
        if not margin_scenarios:
            return None
        import re
        # Look for "margin=NN", "margin: NN", "margin=NN%", "margin NN%"
        patterns = [
            r"margin\s*[=:]\s*([-+]?\d+(?:\.\d+)?)\s*%?",
            r"margin\s+([-+]?\d+(?:\.\d+)?)\s*%",
        ]
        for pat in patterns:
            m = re.search(pat, margin_scenarios, re.IGNORECASE)
            if m:
                try:
                    return float(m.group(1))
                except ValueError:
                    continue
        return None

    # -----------------------------------------------------------------
    # Business Development Engagement (§4.6.3)
    # -----------------------------------------------------------------

    def evaluate_engagement(self, spec: BDEngagementSpec) -> BDEngagementResult:
        """Evaluate a Business Development Engagement.

        Enforces (per AC-P5-005):
          - A Human Approval reference is present.
          - The Register Compliance result is CLEARED.

        A BD engagement is "authorized" only when BOTH conditions are
        met. The Service Layer raises the appropriate typed exception
        when the engagement is not authorized.
        """
        missing_approval = not spec.human_approval_id or not spec.human_approval_id.strip()
        register_blocked = spec.register_outcome is None or spec.register_outcome != "CLEARED"
        is_authorized = (not missing_approval) and (not register_blocked)

        if missing_approval:
            raise BDEngagementMissingApprovalError()
        if register_blocked:
            raise BDEngagementRegisterBlockedError(spec.register_outcome or "ABSENT")

        return BDEngagementResult(
            opportunity_id=spec.opportunity_id,
            engagement_type=spec.engagement_type,
            counterpart=spec.counterpart,
            summary=spec.summary,
            engagement_date=spec.engagement_date,
            human_approval_id=spec.human_approval_id,
            register_outcome=spec.register_outcome,
            is_authorized=is_authorized,
            missing_approval=missing_approval,
            register_blocked=register_blocked,
        )

    # -----------------------------------------------------------------
    # Phase 6 — Deferred Commercial agents (Document 02 §4.6.2, 4.6.4, 4.6.6)
    # -----------------------------------------------------------------

    def validate_commercial_model_option(
        self, *, model_type: str, model_description: str, selected: bool
    ) -> None:
        """Commercial Model Designer Agent (§4.6.2).

        Per Document 02 §4.6.2: 'Authority: May issue Commercial
        Model Options; may not approve a model.'

        The Agent is PROHIBITED from selecting a model. Selection
        is a Human Authority decision.
        """
        if not model_type or not model_type.strip():
            raise ValueError("model_type is required")
        if selected:
            raise CommercialModelSelectionNotAllowedError()

    def validate_negotiation_analysis(
        self, *, scenario: str, constraints: str, analysis_date: str
    ) -> None:
        """Negotiation Support Agent (§4.6.4).

        Per Document 02 §4.6.4: 'Authority: May issue negotiation
        analysis; may not accept, reject, or commit.' The Agent
        does NOT conduct negotiation; it supports a human-led one.
        """
        if not scenario or not scenario.strip():
            raise ValueError("scenario is required")
        if not constraints or not constraints.strip():
            raise ValueError("constraints is required")
        if not analysis_date:
            raise ValueError("analysis_date is required")

    def validate_after_sales_report(
        self, *, opportunity_id: str, report_text: str
    ) -> None:
        """After-Sales Intelligence Agent (§4.6.6).

        Per Document 02 §4.6.6: 'Authority: May issue After-Sales
        Intelligence Report; may not contact customer without
        Human Approval.' The report itself is intelligence; the
        Agent is PROHIBITED from contacting the customer.
        """
        if not opportunity_id or not opportunity_id.strip():
            raise ValueError("opportunity_id is required")
        if not report_text or not report_text.strip():
            raise ValueError("report_text is required")


class CommercialModelSelectionNotAllowedError(CommercialEngineError):
    """The Commercial Model Designer Agent is constitutionally
    PROHIBITED from selecting a model. Selection is a Human
    Authority decision (Document 02 §4.6.2)."""

    def __init__(self) -> None:
        super().__init__(
            f"Commercial Model Designer Agent is REJECTED: attempted to "
            f"select a model. Per Document 02 §4.6.2 Prohibited Actions, "
            f"the Agent 'may not approve a model.' Selection is a Human "
            f"Authority decision (Constitution Article XII)."
        )
