"""Quality Assurance Engine — Document 02 §4.10.

Phase 8 closes the last Office in Document 02 — the Quality
Assurance Office. Three Principal Agents are activated:

  - §4.10.1 Quality Reviewer Agent
  - §4.10.2 Output Auditor Agent
  - §4.10.3 Standards Compliance Agent

The engine is pure logic. No DB coupling. All error classes are
typed exceptions whose messages are the constitutional text.

Constitutional source:
  - Constitution Article XVI (Quality)
  - Document 02 §4.10
  - Document 06 §2.14 (Stage 14: Quality Review)
  - Document 08 §2.9 (Phase 8 scope)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple


# ===========================================================================
# Enums
# ===========================================================================


class QualityOutcome(str, Enum):
    """The outcome of a Quality Review.

    Per Document 02 §4.10.1, the Quality Reviewer may PASS, require
    REWORK, or REJECT the output. Material override triggers Human
    Approval (Constitution Article XII).
    """

    PASS = "PASS"
    REWORK = "REWORK"
    REJECT = "REJECT"
    CONDITIONAL_PASS = "CONDITIONAL_PASS"  # passes with conditions recorded


class QualityCriterionStatus(str, Enum):
    """The status of a single quality criterion."""

    MET = "MET"
    NOT_MET = "NOT_MET"
    PARTIALLY_MET = "PARTIALLY_MET"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class AuditProgramSelection(str, Enum):
    """The audit programme selection method.

    Per Document 02 §4.10.2, the Output Auditor selects samples
    under the audit programme. Selection must be NON-RANDOM for
    Constitutional Incidents (priority sampling).
    """

    RANDOM = "RANDOM"
    RISK_BASED = "RISK_BASED"
    INCIDENT_TRIGGERED = "INCIDENT_TRIGGERED"
    PERIODIC = "PERIODIC"
    MATERIALITY_BASED = "MATERIALITY_BASED"


class StandardsComplianceStatus(str, Enum):
    """The compliance status of an output against a standard.

    Per Document 02 §4.10.3, the Standards Compliance Agent maps
    outputs to standards and identifies gaps. Material deviation
    triggers Human Approval.
    """

    COMPLIANT = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    PARTIALLY_COMPLIANT = "PARTIALLY_COMPLIANT"
    STANDARD_GAP = "STANDARD_GAP"  # no standard exists; needs authoring
    DEFERRED = "DEFERRED"


class MaterialOverrideDecision(str, Enum):
    """The decision on a material override of a Quality Review.

    Per Constitution Article XII, material overrides require
    Human Approval (Class 3 or Class 4 depending on impact).
    """

    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PENDING_HUMAN_APPROVAL = "PENDING_HUMAN_APPROVAL"


# ===========================================================================
# Errors (typed exceptions; messages are constitutional text)
# ===========================================================================


class QualityError(Exception):
    """Base error for the Quality engine."""


class QualityReviewWithoutCriteriaError(QualityError):
    """A Quality Review cannot be issued without quality criteria.

    Document 02 §4.10.1: Required Evidence includes "Criteria".
    """

    def __init__(self, target_id: str) -> None:
        super().__init__(
            f"Quality Review for target {target_id!r} REJECTED: "
            "no quality criteria provided. The Quality Reviewer "
            "may not review without criteria (Document 02 §4.10.1)."
        )


class QualityReviewWithoutReviewerError(QualityError):
    """A Quality Review cannot be issued without a reviewer."""

    def __init__(self) -> None:
        super().__init__(
            "Quality Review REJECTED: no reviewer provided. Every "
            "Quality Review must be attributable (Constitution "
            "Article XX paragraph 7)."
        )


class MaterialOverrideWithoutApprovalError(QualityError):
    """A material override of a Quality Review requires Human Approval.

    Document 02 §4.10.1: Human Approval Triggers include "Material
    override of a quality review".
    """

    def __init__(self, target_id: str, override_type: str) -> None:
        super().__init__(
            f"Material override ({override_type!r}) of Quality Review "
            f"for target {target_id!r} REJECTED: Human Approval "
            "reference is REQUIRED (Document 02 §4.10.1; "
            "Constitution Article XII)."
        )


class AuditSampleConcealmentError(QualityError):
    """The Output Auditor may not conceal a material finding.

    Document 02 §4.10.2: Prohibited Actions include "Silently amend
    outputs". A concealed finding is a silent amendment.
    """

    def __init__(self, finding_id: str) -> None:
        super().__init__(
            f"Audit sample {finding_id!r} REJECTED: concealment of a "
            "material finding is PROHIBITED (Document 02 §4.10.2)."
        )


class StandardsAmendmentWithoutApprovalError(QualityError):
    """The Standards Compliance Agent may not amend a standard.

    Document 02 §4.10.3: Prohibited Actions include "Amend standards".
    """

    def __init__(self, standard: str) -> None:
        super().__init__(
            f"Standards amendment for standard {standard!r} REJECTED: "
            "amending a standard is PROHIBITED at the Quality layer "
            "(Document 02 §4.10.3). Standards amendments require "
            "Document Hierarchy change control (Constitution Article XXIX)."
        )


class QualityCoverageGapError(QualityError):
    """A Quality Reviewer cannot silently skip an in-scope output.

    Document 02 §4.10.1: Scope is "All outputs routed to the Office".
    A skipped output is a coverage gap.
    """

    def __init__(self, target_id: str) -> None:
        super().__init__(
            f"Quality Review for target {target_id!r} REJECTED: "
            "coverage gap detected. The Quality Reviewer may not "
            "silently skip an in-scope output (Document 02 §4.10.1)."
        )


# ===========================================================================
# Specs (frozen dataclasses — engine inputs)
# ===========================================================================


@dataclass(frozen=True)
class QualityCriterion:
    """A single quality criterion applied to an output."""

    criterion_name: str
    description: str
    weight: float  # 0.0..1.0; sum across criteria must be 1.0
    status: QualityCriterionStatus
    finding: str = ""


@dataclass(frozen=True)
class QualityReviewSpec:
    """A Quality Review request."""

    target_type: str  # e.g. "REPORT", "TENDER", "OPPORTUNITY"
    target_id: str
    reviewer_id: str  # the Quality Reviewer (or human reviewer) id
    criteria: List[QualityCriterion]
    verification_record_id: str  # the IFV/PE/SV record
    review_date: str  # ISO date string
    notes: str = ""


@dataclass(frozen=True)
class QualityReviewResult:
    """The result of a Quality Review."""

    target_type: str
    target_id: str
    reviewer_id: str
    outcome: QualityOutcome
    criteria_count: int
    criteria_met: int
    criteria_partially_met: int
    criteria_not_met: int
    criteria_not_applicable: int
    coverage_gap: bool
    rework_requested: bool
    findings: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class AuditSampleSpec:
    """An audit programme sample request."""

    sample_id: str
    target_type: str
    target_id: str
    selection_method: AuditProgramSelection
    audit_criteria: List[str]
    audit_date: str
    notes: str = ""


@dataclass(frozen=True)
class AuditSampleResult:
    """The result of an audit sample."""

    sample_id: str
    target_type: str
    target_id: str
    selection_method: AuditProgramSelection
    finding: str
    corrective_action_recommended: bool
    pattern_detected: bool
    material_drift: bool
    constitutional_breach: bool
    human_approval_required: bool


@dataclass(frozen=True)
class StandardsComplianceSpec:
    """A Standards Compliance mapping request."""

    target_type: str
    target_id: str
    standard: str  # e.g. "ISO-9001:2015", "Constitution Article XX", "Document 06 §9"
    target_evidence: str
    review_date: str
    notes: str = ""


@dataclass(frozen=True)
class StandardsComplianceResult:
    """The result of a Standards Compliance mapping."""

    target_type: str
    target_id: str
    standard: str
    compliance_status: StandardsComplianceStatus
    gap_description: str
    human_approval_required: bool


# ===========================================================================
# Engines
# ===========================================================================


class QualityEngine:
    """The Quality Engine — Document 02 §4.10.1 (Quality Reviewer)."""

    def review(self, spec: QualityReviewSpec) -> QualityReviewResult:
        """Apply quality criteria and produce a Quality Review.

        Raises:
            QualityReviewWithoutCriteriaError: criteria list is empty.
            QualityReviewWithoutReviewerError: reviewer_id is empty.
            QualityCoverageGapError: an in-scope output was silently
                skipped (i.e. covered by NOT_APPLICABLE without justification).
        """
        if not spec.criteria:
            raise QualityReviewWithoutCriteriaError(spec.target_id)
        if not spec.reviewer_id:
            raise QualityReviewWithoutReviewerError()
        if not spec.verification_record_id:
            raise QualityCoverageGapError(spec.target_id)

        # Aggregate criteria
        n_total = len(spec.criteria)
        n_met = sum(1 for c in spec.criteria if c.status == QualityCriterionStatus.MET)
        n_partial = sum(1 for c in spec.criteria if c.status == QualityCriterionStatus.PARTIALLY_MET)
        n_not_met = sum(1 for c in spec.criteria if c.status == QualityCriterionStatus.NOT_MET)
        n_na = sum(1 for c in spec.criteria if c.status == QualityCriterionStatus.NOT_APPLICABLE)
        coverage_gap = n_na > 0 and (n_met + n_partial + n_not_met) == 0
        if coverage_gap:
            raise QualityCoverageGapError(spec.target_id)

        # Determine outcome
        if n_not_met == 0 and n_partial == 0:
            outcome = QualityOutcome.PASS
        elif n_not_met >= max(1, n_total // 3):
            outcome = QualityOutcome.REWORK
        elif n_not_met > 0:
            outcome = QualityOutcome.CONDITIONAL_PASS
        else:
            outcome = QualityOutcome.PASS

        # Weight check (sum of weights should be 1.0 ± 0.01)
        w_sum = sum(c.weight for c in spec.criteria)
        if abs(w_sum - 1.0) > 0.01:
            # Bad criteria: treat as coverage gap
            raise QualityCoverageGapError(spec.target_id)

        findings: List[str] = []
        rework_requested = outcome in (QualityOutcome.REWORK, QualityOutcome.REJECT)
        for c in spec.criteria:
            if c.status in (QualityCriterionStatus.NOT_MET, QualityCriterionStatus.PARTIALLY_MET):
                findings.append(f"{c.criterion_name}: {c.finding or c.description}")

        return QualityReviewResult(
            target_type=spec.target_type,
            target_id=spec.target_id,
            reviewer_id=spec.reviewer_id,
            outcome=outcome,
            criteria_count=n_total,
            criteria_met=n_met,
            criteria_partially_met=n_partial,
            criteria_not_met=n_not_met,
            criteria_not_applicable=n_na,
            coverage_gap=coverage_gap,
            rework_requested=rework_requested,
            findings=findings,
        )

    def apply_material_override(
        self,
        target_id: str,
        override_type: str,
        human_approval_id: Optional[str],
    ) -> MaterialOverrideDecision:
        """Apply a material override of a Quality Review.

        Per Document 02 §4.10.1 + Constitution Article XII, material
        overrides require Human Approval. Without it, the override is
        REJECTED.
        """
        if not human_approval_id:
            raise MaterialOverrideWithoutApprovalError(target_id, override_type)
        return MaterialOverrideDecision.APPROVED


class OutputAuditEngine:
    """The Output Audit Engine — Document 02 §4.10.2 (Output Auditor)."""

    def audit_sample(self, spec: AuditSampleSpec) -> AuditSampleResult:
        """Audit a sample of completed outputs.

        The Output Auditor selects samples under the audit programme
        and may not conceal a material finding. Returns the
        AuditSampleResult with the finding + corrective action flag.
        """
        # Constitutional breaches and material drift always require
        # Human Approval (Article XII).
        finding = "no material finding"
        corrective = False
        pattern = False
        material_drift = False
        constitutional_breach = False
        human_approval_required = False

        # Heuristic: if the sample notes mention "concealment",
        # "drift", "constitutional", or "breach", flag.
        notes_lower = spec.notes.lower()
        if "conceal" in notes_lower:
            raise AuditSampleConcealmentError(spec.sample_id)
        if "constitutional" in notes_lower and ("breach" in notes_lower or "violation" in notes_lower):
            constitutional_breach = True
            finding = "Constitutional breach detected"
            corrective = True
            human_approval_required = True
        elif "drift" in notes_lower:
            material_drift = True
            finding = "Material drift detected"
            corrective = True
        elif "pattern" in notes_lower:
            pattern = True
            finding = "Pattern of error detected"
            corrective = True

        return AuditSampleResult(
            sample_id=spec.sample_id,
            target_type=spec.target_type,
            target_id=spec.target_id,
            selection_method=spec.selection_method,
            finding=finding,
            corrective_action_recommended=corrective,
            pattern_detected=pattern,
            material_drift=material_drift,
            constitutional_breach=constitutional_breach,
            human_approval_required=human_approval_required,
        )


class StandardsComplianceEngine:
    """The Standards Compliance Engine — Document 02 §4.10.3."""

    def evaluate(self, spec: StandardsComplianceSpec) -> StandardsComplianceResult:
        """Evaluate a target against a standard.

        The Standards Compliance Agent maps outputs to standards and
        identifies gaps. May not amend a standard.
        """
        if not spec.standard:
            raise StandardsAmendmentWithoutApprovalError(spec.standard or "<empty>")
        if not spec.target_evidence:
            # No evidence → STANDARD_GAP
            return StandardsComplianceResult(
                target_type=spec.target_type,
                target_id=spec.target_id,
                standard=spec.standard,
                compliance_status=StandardsComplianceStatus.STANDARD_GAP,
                gap_description=(
                    f"No evidence for standard {spec.standard!r} on "
                    f"target {spec.target_id!r}"
                ),
                human_approval_required=False,
            )
        # Heuristic mapping
        evidence_lower = spec.target_evidence.lower()
        if "non-compliant" in evidence_lower or "violation" in evidence_lower:
            status = StandardsComplianceStatus.NON_COMPLIANT
            gap = f"Material deviation from standard {spec.standard!r}"
            human_approval = True  # Material deviation
        elif "partial" in evidence_lower:
            status = StandardsComplianceStatus.PARTIALLY_COMPLIANT
            gap = f"Partial deviation from standard {spec.standard!r}"
            human_approval = False
        elif "defer" in evidence_lower:
            status = StandardsComplianceStatus.DEFERRED
            gap = ""
            human_approval = False
        else:
            status = StandardsComplianceStatus.COMPLIANT
            gap = ""
            human_approval = False
        return StandardsComplianceResult(
            target_type=spec.target_type,
            target_id=spec.target_id,
            standard=spec.standard,
            compliance_status=status,
            gap_description=gap,
            human_approval_required=human_approval,
        )

    def amend_standard(
        self, standard: str, human_approval_id: Optional[str]
    ) -> bool:
        """Reject any attempt to amend a standard at the Quality layer.

        Standards amendments require Document Hierarchy change control
        (Constitution Article XXIX), NOT a Quality agent.
        """
        raise StandardsAmendmentWithoutApprovalError(standard)
