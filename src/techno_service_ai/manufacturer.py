"""Manufacturer Engine — Document 02 §4.5, Phase 5.

Implements the pure-logic engine for the three Manufacturer Intelligence
Principal Agents:

  - Manufacturer Profiler Agent (§4.5.1) — produces a Manufacturer
    Profile (ENT-MAN-001).
  - Manufacturer Credibility Analyst Agent (§4.5.2) — produces a
    Credibility Assessment (ENT-MAN-002), a multi-dimensional
    scorecard.
  - Manufacturer Comparison Agent (§4.5.3) — produces a Manufacturer
    Comparison Report (ENT-MAN-003), a vendor-neutral, multi-criteria
    comparison. The agent does NOT select a Manufacturer; selection
    is a Human Authority decision.

The engine is PURE LOGIC — no database, no HTTP. The Service Layer
wires the engine to the data layer.

Constitutional source:
  - Document 02 §4.5 (Manufacturer Intelligence Office)
  - Document 05 §3.6 (ENT-MAN-001, 002, 003)
  - Constitution Article VII (multi-dimensional assessment)
  - Constitution Article VIII (Registers — the engine reports the
    representation status; the Service Layer queries the registers)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class CredibilityRating(str, Enum):
    """The overall classification of a Credibility Assessment.

    A Credibility Assessment MUST carry one of these classifications.
    A negative finding (ADVERSE, BELOW_THRESHOLD) requires Human
    Approval per Document 02 §4.5.2.
    """

    UNVERIFIED = "UNVERIFIED"
    ADVERSE = "ADVERSE"
    BELOW_THRESHOLD = "BELOW_THRESHOLD"
    CONDITIONALLY_CREDIBLE = "CONDITIONALLY_CREDIBLE"
    CREDIBLE = "CREDIBLE"
    HIGHLY_CREDIBLE = "HIGHLY_CREDIBLE"


class ScoreLevel(str, Enum):
    """Per-dimension score levels.

    The schema uses VARCHAR(32) so these are stored as text. Allowed
    values: UNKNOWN, LOW, MEDIUM, HIGH.
    """

    UNKNOWN = "UNKNOWN"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


# The 6 scorecard dimensions — per the Phase 2 schema (ENT-MAN-002).
# These are the constitutional defined dimensions for the test
# "REJECT if fewer than the defined dimensions" (AC-P5-002).
MANUFACTURER_CREDIBILITY_DIMENSIONS: Tuple[str, ...] = (
    "financial_stability",
    "quality_systems",
    "delivery_track_record",
    "after_sales_capability",
    "references",
    "reputation",
)


class KuwaitRepresentationStatus(str, Enum):
    """The Kuwait Representation status of a Manufacturer.

    Per Document 02 §4.5.1 and Article VIII §2:

      - REPRESENTED — the Manufacturer is on the Represented Principals
        register with an active, in-scope entry. Commercial action is
        allowed (subject to the other register checks).
      - UNRESOLVED — the Manufacturer is not on the register (or the
        entry is SUPERSEDED / outside scope). Commercial action is
        REJECTED at the Commercial Gate (per Article VIII §2).
      - SUPERSEDED — the Manufacturer's representation has been
        superseded by a newer entry. Commercial action is REJECTED.
    """

    REPRESENTED = "REPRESENTED"
    UNRESOLVED = "UNRESOLVED"
    SUPERSEDED = "SUPERSEDED"


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class ManufacturerEngineError(Exception):
    """Base for manufacturer engine errors."""


class ProfileMissingRequiredFieldError(ManufacturerEngineError):
    """A required field is missing from a Manufacturer Profile."""

    def __init__(self, field_name: str) -> None:
        self.field_name = field_name
        super().__init__(
            f"Manufacturer Profile is missing required field '{field_name}'. "
            f"Per Document 02 §4.5.1, every Manufacturer Profile must carry: "
            f"manufacturer_name, profile_date, source_citation."
        )


class CredibilityAssessmentIncompleteError(ManufacturerEngineError):
    """A Credibility Assessment is missing one or more required dimensions.

    Per Document 02 §4.5.2 and AC-P5-002, a Credibility Assessment
    MUST carry all defined dimensions. A single-dimension assessment
    is a Failure Condition.
    """

    def __init__(self, missing: Tuple[str, ...]) -> None:
        self.missing = missing
        super().__init__(
            f"Credibility Assessment is REJECTED: missing dimensions {list(missing)}. "
            f"Per Document 02 §4.5.2 and AC-P5-002, a Credibility Assessment MUST be "
            f"multi-dimensional. Single-dimension assessment is a Failure Condition."
        )


class ComparisonSingleCriterionError(ManufacturerEngineError):
    """A Manufacturer Comparison is single-criterion — REJECTED.

    Per Document 02 §4.5.3: "Single-criterion comparison; brand bias"
    is a Failure Condition. A comparison that does not enumerate at
    least 2 criteria is REJECTED.
    """

    def __init__(self, criteria_count: int) -> None:
        self.criteria_count = criteria_count
        super().__init__(
            f"Manufacturer Comparison is REJECTED: only {criteria_count} criteria. "
            f"Per Document 02 §4.5.3, a Comparison must be multi-criteria. "
            f"Single-criterion comparison is a Failure Condition."
        )


class ComparisonSelectionNotAllowedError(ManufacturerEngineError):
    """The Comparison Agent is constitutionally PROHIBITED from selecting
    a Manufacturer. Selection is a Human Authority decision.
    """

    def __init__(self) -> None:
        super().__init__(
            f"Manufacturer Comparison Agent is REJECTED: attempted to select a Manufacturer. "
            f"Per Document 02 §4.5.3 Prohibited Actions, the Agent 'may not select a Manufacturer; "
            f"may not bind Techno Service.' Selection is a Human Authority decision."
        )


# ---------------------------------------------------------------------------
# Inputs / Outputs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ManufacturerProfileSpec:
    """The input spec for a Manufacturer Profile.

    The Service Layer translates this into a ManufacturerProfile row.
    """

    manufacturer_name: str
    profile_date: str  # ISO 8601
    source_citation: str
    ownership: str = ""
    certifications: str = ""
    production_capacity: str = ""
    references: str = ""
    quality_indicators: str = ""
    after_sales_capability: str = ""
    global_reputation: str = ""


@dataclass(frozen=True)
class CredibilityDimensionScore:
    """A score for one dimension of the Credibility Assessment."""

    dimension: str
    score: ScoreLevel
    source_citation: str
    rationale: str = ""


@dataclass(frozen=True)
class CredibilityAssessmentSpec:
    """The input spec for a Credibility Assessment.

    The engine verifies that all 6 dimensions are present. A
    per-dimension score of UNKNOWN counts as present-but-unknown
    (constitutionally honest).
    """

    manufacturer_id: str
    assessment_date: str
    source_citation: str
    dimensions: Tuple[CredibilityDimensionScore, ...]


@dataclass(frozen=True)
class CredibilityAssessmentResult:
    """The result of a Credibility Assessment evaluation."""

    manufacturer_id: str
    assessment_date: str
    dimension_scores: Tuple[CredibilityDimensionScore, ...]
    overall_classification: CredibilityRating
    rationale: str
    requires_human_approval: bool  # True when classification is ADVERSE/BELOW_THRESHOLD
    missing_dimensions: Tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.missing_dimensions:
            raise CredibilityAssessmentIncompleteError(self.missing_dimensions)


@dataclass(frozen=True)
class ManufacturerComparisonSpec:
    """The input spec for a Manufacturer Comparison Report."""

    opportunity_id: str
    manufacturer_ids: Tuple[str, ...]  # The candidates being compared
    criteria: Tuple[str, ...]           # The criteria for comparison
    trade_offs: str
    comparison_date: str
    source_citation: str
    recommended_manufacturer_id: Optional[str] = None  # MUST be None per the Agent charter
    recommended_manufacturer_name: Optional[str] = None
    comparison_summary: str = ""


@dataclass(frozen=True)
class ManufacturerComparisonResult:
    """The result of a Manufacturer Comparison evaluation."""

    opportunity_id: str
    manufacturer_ids: Tuple[str, ...]
    criteria: Tuple[str, ...]
    trade_offs: str
    comparison_date: str
    overall_vendor_neutral: bool  # True if no Manufacturer was selected
    selection_violation: bool  # True if a selection was attempted
    criteria_count: int


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class ManufacturerEngine:
    """The pure-logic engine for the Manufacturer Intelligence Office.

    All three agents (Profiler, Credibility Analyst, Comparison) are
    represented as methods on this engine. The Service Layer calls
    these methods and persists the results.
    """

    # -----------------------------------------------------------------
    # Profiler (§4.5.1)
    # -----------------------------------------------------------------

    def validate_profile(self, spec: ManufacturerProfileSpec) -> None:
        """Validate a Manufacturer Profile spec.

        Raises ProfileMissingRequiredFieldError if a required field is
        missing. The Agent charter §4.5.1 lists Required Evidence:
        Source citation; date; scope. The schema requires
        manufacturer_name + profile_date.
        """
        if not spec.manufacturer_name or not spec.manufacturer_name.strip():
            raise ProfileMissingRequiredFieldError("manufacturer_name")
        if not spec.profile_date:
            raise ProfileMissingRequiredFieldError("profile_date")
        if not spec.source_citation or not spec.source_citation.strip():
            raise ProfileMissingRequiredFieldError("source_citation")

    # -----------------------------------------------------------------
    # Credibility Analyst (§4.5.2)
    # -----------------------------------------------------------------

    def evaluate_credibility(
        self, spec: CredibilityAssessmentSpec
    ) -> CredibilityAssessmentResult:
        """Evaluate a Credibility Assessment.

        Enforces:
          - All 6 defined dimensions are present (AC-P5-002).
          - Computes the overall classification from the per-dimension
            scores.
          - Returns whether Human Approval is required (for ADVERSE /
            BELOW_THRESHOLD).
        """
        # 1. Check that all 6 dimensions are present.
        present = {d.dimension for d in spec.dimensions}
        missing = tuple(d for d in MANUFACTURER_CREDIBILITY_DIMENSIONS if d not in present)
        if missing:
            raise CredibilityAssessmentIncompleteError(missing)

        # 2. Compute overall classification.
        #    All HIGH → HIGHLY_CREDIBLE
        #    All MEDIUM/HIGH, no LOW → CREDIBLE
        #    Mixed LOW+MEDIUM+HIGH, no ADVERSE → CONDITIONALLY_CREDIBLE
        #    Any ADVERSE (we treat LOW as ADVERSE for purposes of the
        #    overall classification) → ADVERSE
        #    If all UNKNOWN → UNVERIFIED
        scores = [d.score for d in spec.dimensions]
        high = sum(1 for s in scores if s == ScoreLevel.HIGH)
        medium = sum(1 for s in scores if s == ScoreLevel.MEDIUM)
        low = sum(1 for s in scores if s == ScoreLevel.LOW)
        unknown = sum(1 for s in scores if s == ScoreLevel.UNKNOWN)

        if unknown == len(scores):
            classification = CredibilityRating.UNVERIFIED
        elif low >= 2:
            # Two or more LOW dimensions → ADVERSE.
            classification = CredibilityRating.ADVERSE
        elif low == 1:
            # One LOW dimension → BELOW_THRESHOLD.
            classification = CredibilityRating.BELOW_THRESHOLD
        elif high == len(scores):
            classification = CredibilityRating.HIGHLY_CREDIBLE
        elif low == 0 and medium + high == len(scores):
            classification = CredibilityRating.CREDIBLE
        else:
            classification = CredibilityRating.CONDITIONALLY_CREDIBLE

        # 3. Human Approval is required for negative findings.
        requires_human_approval = classification in (
            CredibilityRating.ADVERSE,
            CredibilityRating.BELOW_THRESHOLD,
        )

        rationale = (
            f"Scorecard: HIGH={high}, MEDIUM={medium}, LOW={low}, UNKNOWN={unknown}. "
            f"Overall: {classification.value}."
        )

        return CredibilityAssessmentResult(
            manufacturer_id=spec.manufacturer_id,
            assessment_date=spec.assessment_date,
            dimension_scores=spec.dimensions,
            overall_classification=classification,
            rationale=rationale,
            requires_human_approval=requires_human_approval,
        )

    # -----------------------------------------------------------------
    # Comparison (§4.5.3)
    # -----------------------------------------------------------------

    def validate_comparison(self, spec: ManufacturerComparisonSpec) -> ManufacturerComparisonResult:
        """Validate a Manufacturer Comparison.

        Enforces:
          - At least 2 manufacturers are being compared.
          - At least 2 criteria (multi-criterion, not single).
          - The Agent did NOT select a Manufacturer (selection is
            constitutionally prohibited for the Agent).
        """
        # Multi-manufacturer
        if len(spec.manufacturer_ids) < 2:
            raise ComparisonSingleCriterionError(
                criteria_count=len(spec.manufacturer_ids)
            )

        # Multi-criteria
        if len(spec.criteria) < 2:
            raise ComparisonSingleCriterionError(
                criteria_count=len(spec.criteria)
            )

        # No selection
        selection_attempted = spec.recommended_manufacturer_id is not None
        if selection_attempted:
            raise ComparisonSelectionNotAllowedError()

        return ManufacturerComparisonResult(
            opportunity_id=spec.opportunity_id,
            manufacturer_ids=spec.manufacturer_ids,
            criteria=spec.criteria,
            trade_offs=spec.trade_offs,
            comparison_date=spec.comparison_date,
            overall_vendor_neutral=not selection_attempted,
            selection_violation=selection_attempted,
            criteria_count=len(spec.criteria),
        )

    # -----------------------------------------------------------------
    # Kuwait Representation — derived from the registers
    # -----------------------------------------------------------------

    @staticmethod
    def kuwait_representation_status(
        *, manufacturer_id: str, register_entries: tuple
    ) -> KuwaitRepresentationStatus:
        """Determine the Kuwait Representation status of a Manufacturer.

        The Service Layer passes the list of register entries that
        match this Manufacturer. The engine returns the status:
          - REPRESENTED: at least one ACTIVE RepresentedPrincipal entry.
          - SUPERSEDED: an entry exists but its status is SUPERSEDED.
          - UNRESOLVED: no entries at all.

        This is a derivation from the registers — the Manufacturer
        Profiler Agent does NOT declare representation status alone
        (Document 02 §4.5.1 Authority Limits).
        """
        represented = [e for e in register_entries if e.register_kind == "REPRESENTED_PRINCIPAL"]
        if not represented:
            return KuwaitRepresentationStatus.UNRESOLVED
        if any(e.status == "ACTIVE" for e in represented):
            return KuwaitRepresentationStatus.REPRESENTED
        return KuwaitRepresentationStatus.SUPERSEDED
