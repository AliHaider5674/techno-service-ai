"""Value Qualification Rule (VQR) — Constitution Article VII.

The VQR is a constitutional rule that gates every Opportunity at
Stage 9 (Replacement and Comparative Analysis) and at every
subsequent comparison.

Constitutional source:
  - Constitution Article VII (paragraphs 1-8)
  - Constitution Article X paragraph 6 (Verified-Only Output)
  - Constitution Article XII paragraph 2(e) (any exception to VQR
    requires explicit Human Approval)
  - Authority Matrix §4.16 (Strategic Exception to VQR is Class 4)
  - Document 06 §2.6 (Stage 6 — Commercial Value Case)
  - Document 06 §2.9 (Stage 9 — Replacement Analysis applies the VQR)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping


# ---------------------------------------------------------------------------
# VQR dimensions
# ---------------------------------------------------------------------------


class VQRDimension(str, Enum):
    """The 6 dimensions over which a measurable improvement is asserted.

    Per Constitution Article VII paragraph 1(a), an Opportunity must
    demonstrate a measurable improvement of NOT LESS THAN 25% in one
    or more of these dimensions.
    """

    COST = "COST"
    TIME = "TIME"
    LABOUR = "LABOUR"
    # The other 3 are named in the Constitution but the field is
    # abbreviated. The full Constitution text is cited in the rule
    # below.
    QUALITY = "QUALITY"
    RISK = "RISK"
    COMPLIANCE = "COMPLIANCE"


# The constitutional threshold (Article VII paragraph 1(a)):
# 25% measurable improvement in one or more dimensions.
VQR_THRESHOLD_PERCENT = 25


# ---------------------------------------------------------------------------
# VQR classification
# ---------------------------------------------------------------------------


class VQRClassification(str, Enum):
    """The 4 constitutional case statuses per Article VII paragraph 4.

    1. QUALIFIES — at least one dimension demonstrates >= 25% improvement
       (paragraph 1).
    2. UNVERIFIED_VALUE_HYPOTHESIS — the improvement has not yet been
       independently demonstrated (paragraph 4(a)).
    3. PILOT_VALIDATION_REQUIRED — the improvement is plausible but
       requires a pilot (paragraph 4(b)).
    4. CONDITIONAL_OPPORTUNITY — the improvement is conditional on
       external factors (paragraph 4(c)).
    5. STRATEGIC_EXCEPTION — a Human-Approved exception to the VQR
       (paragraph 8 / Authority Matrix §4.16 Class 4). Requires
       a documented Human Approval; the Strategic Exception carries
       the basis, the limitations, and the approval reference.
    """

    QUALIFIES = "QUALIFIES"
    UNVERIFIED_VALUE_HYPOTHESIS = "UNVERIFIED_VALUE_HYPOTHESIS"
    PILOT_VALIDATION_REQUIRED = "PILOT_VALIDATION_REQUIRED"
    CONDITIONAL_OPPORTUNITY = "CONDITIONAL_OPPORTUNITY"
    STRATEGIC_EXCEPTION = "STRATEGIC_EXCEPTION"


# Per Article VII paragraph 4, a case that does not qualify under
# paragraph 1 may be classified as one of the unverified statuses.
UNVERIFIED_CLASSIFICATIONS = frozenset({
    VQRClassification.UNVERIFIED_VALUE_HYPOTHESIS,
    VQRClassification.PILOT_VALIDATION_REQUIRED,
    VQRClassification.CONDITIONAL_OPPORTUNITY,
})


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class VQRError(Exception):
    """Generic VQR error."""


class VQRMissingClassification(VQRError):
    """A Comparative Analysis (or Value Case) is presented without a VQR classification.

    Per Article VII paragraph 1, every Opportunity must be subject to
    the VQR. A case that is not classified is REJECTED — not silently
    accepted.
    """

    def __init__(self, material_canonical_id: str) -> None:
        self.material_canonical_id = material_canonical_id
        super().__init__(
            f"Material '{material_canonical_id}' has NO VQR classification. "
            f"Per Constitution Article VII paragraph 1, every Opportunity must "
            f"be subject to the Value Qualification Rule. Presenting the case "
            f"without a classification is REJECTED."
        )


class VQRInsufficientEvidence(VQRError):
    """A QUALIFIES classification is asserted but the 25% improvement
    is not supported by Evidence.

    Per Article VII paragraph 3: "Insufficiency of Manufacturer
    Statements. Manufacturer marketing statements alone are
    insufficient Evidence under this Article."
    """

    def __init__(self, dimension: VQRDimension, asserted_pct: float, evidence_count: int) -> None:
        self.dimension = dimension
        self.asserted_pct = asserted_pct
        self.evidence_count = evidence_count
        super().__init__(
            f"VQR classification QUALIFIES for dimension {dimension.value} "
            f"asserts {asserted_pct:.1f}% improvement but is supported by "
            f"only {evidence_count} Evidence record(s). Per Article VII "
            f"paragraph 3, Manufacturer statements alone are insufficient."
        )


class VQRStrategicExceptionRequiresApproval(VQRError):
    """A STRATEGIC_EXCEPTION classification requires a Human Approval.

    Per Article XII paragraph 2(e): any exception to the VQR requires
    explicit Human Approval. The Approver is the Authorised Executive,
    per Authority Matrix §4.16 (Class 4).
    """

    def __init__(self) -> None:
        super().__init__(
            f"STRATEGIC_EXCEPTION to the VQR requires a documented Human Approval. "
            f"Per Constitution Article XII paragraph 2(e) and Authority Matrix "
            f"§4.16, the Approver is the Authorised Executive."
        )


# ---------------------------------------------------------------------------
# Improvement measurement
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ImprovementEvidence:
    """An evidence record for a measurable improvement in one dimension.

    The evidence carries a source citation, a date, and the
    measured/asserted percent improvement.
    """

    dimension: VQRDimension
    asserted_improvement_pct: float  # positive number; 25% threshold
    source_citation: str
    measurement_date: str
    independent: bool = True  # False = Manufacturer statement only


@dataclass(frozen=True)
class VQRResult:
    """The constitutional record of a VQR classification.

    A Comparative Analysis at Stage 9 must carry a `VQRResult`. Without
    it, the next stage is BLOCKED.
    """

    material_canonical_id: str
    classification: VQRClassification
    qualified_dimension: VQRDimension | None  # set if QUALIFIES
    measured_improvement_pct: float | None  # set if QUALIFIES
    evidence: tuple[ImprovementEvidence, ...]
    rationale: str
    strategic_exception_approval_id: str | None = None  # set if STRATEGIC_EXCEPTION
    classification_date: str = ""
    classified_by: str = ""


# ---------------------------------------------------------------------------
# VQR Engine
# ---------------------------------------------------------------------------


class VQREngine:
    """Pure-logic VQR engine.

    Methods:
      - evaluate: given the asserted improvements, return a VQRResult
      - validate_record: enforce that a VQRResult is present and
        constitutional (used by Stage 9 to gate Stage 10+)
    """

    def evaluate(
        self,
        *,
        material_canonical_id: str,
        asserted_improvements: tuple[ImprovementEvidence, ...],
        rationale: str,
        classified_by: str,
        classification_date: str = "",
        strategic_exception_approval_id: str | None = None,
        requested_classification: VQRClassification | None = None,
    ) -> VQRResult:
        """Evaluate the VQR for a material claim.

        Rules (Article VII):
          1. If any dimension has at least one INDEPENDENT evidence of
             >= 25% improvement, the classification is QUALIFIES.
          2. If the assertion is well-evidenced but the threshold is
             not met, the classification is one of the unverified
             statuses (UNVERIFIED_VALUE_HYPOTHESIS, etc.).
          3. A STRATEGIC_EXCEPTION requires a Human Approval.
        """
        if not asserted_improvements:
            # No assertions at all. The classification depends on the
            # request.
            if requested_classification == VQRClassification.STRATEGIC_EXCEPTION:
                if not strategic_exception_approval_id:
                    raise VQRStrategicExceptionRequiresApproval()
                return VQRResult(
                    material_canonical_id=material_canonical_id,
                    classification=VQRClassification.STRATEGIC_EXCEPTION,
                    qualified_dimension=None,
                    measured_improvement_pct=None,
                    evidence=(),
                    rationale=rationale or "Strategic exception to the VQR",
                    strategic_exception_approval_id=strategic_exception_approval_id,
                    classification_date=classification_date or _now_iso(),
                    classified_by=classified_by,
                )
            return VQRResult(
                material_canonical_id=material_canonical_id,
                classification=VQRClassification.UNVERIFIED_VALUE_HYPOTHESIS,
                qualified_dimension=None,
                measured_improvement_pct=None,
                evidence=(),
                rationale=rationale or "No asserted improvements",
                strategic_exception_approval_id=None,
                classification_date=classification_date or _now_iso(),
                classified_by=classified_by,
            )
        # Find the best qualified dimension (independent + >= 25%).
        best: tuple[VQRDimension, float] | None = None
        for ev in asserted_improvements:
            if ev.independent and ev.asserted_improvement_pct >= VQR_THRESHOLD_PERCENT:
                if best is None or ev.asserted_improvement_pct > best[1]:
                    best = (ev.dimension, ev.asserted_improvement_pct)
        # Determine the classification.
        if best is not None:
            classification = VQRClassification.QUALIFIES
            qualified_dimension, measured_pct = best
        elif requested_classification == VQRClassification.STRATEGIC_EXCEPTION:
            if not strategic_exception_approval_id:
                raise VQRStrategicExceptionRequiresApproval()
            classification = VQRClassification.STRATEGIC_EXCEPTION
            qualified_dimension = None
            measured_pct = None
        elif requested_classification in UNVERIFIED_CLASSIFICATIONS:
            classification = requested_classification
            qualified_dimension = None
            measured_pct = None
        else:
            # Default to unverified value hypothesis.
            classification = VQRClassification.UNVERIFIED_VALUE_HYPOTHESIS
            qualified_dimension = None
            measured_pct = None
        # QUALIFIES requires at least one independent evidence.
        if classification == VQRClassification.QUALIFIES:
            independent_count = sum(1 for ev in asserted_improvements if ev.independent)
            if independent_count == 0 and best is not None:
                raise VQRInsufficientEvidence(
                    dimension=best[0],
                    asserted_pct=best[1],
                    evidence_count=0,
                )
        return VQRResult(
            material_canonical_id=material_canonical_id,
            classification=classification,
            qualified_dimension=qualified_dimension,
            measured_improvement_pct=measured_pct,
            evidence=asserted_improvements,
            rationale=rationale,
            strategic_exception_approval_id=strategic_exception_approval_id,
            classification_date=classification_date or _now_iso(),
            classified_by=classified_by,
        )

    def validate_record(self, result: VQRResult | None) -> None:
        """Validate that a VQRResult exists and is constitutional.

        Used by Stage 9 to gate Stage 10. Raises VQRMissingClassification
        if the result is None.
        """
        if result is None:
            raise VQRMissingClassification(material_canonical_id="(unknown)")
        if result.classification == VQRClassification.STRATEGIC_EXCEPTION and not result.strategic_exception_approval_id:
            raise VQRStrategicExceptionRequiresApproval()
        if result.classification == VQRClassification.QUALIFIES and not result.evidence:
            raise VQRInsufficientEvidence(
                dimension=result.qualified_dimension or VQRDimension.COST,
                asserted_pct=result.measured_improvement_pct or 0.0,
                evidence_count=0,
            )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
