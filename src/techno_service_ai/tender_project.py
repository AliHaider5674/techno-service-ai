"""Tender and Project Engine — Document 02 §4.8, Phase 6.

Implements the pure-logic engine for the four Tender and Project
Intelligence Principal Agents:

  - Tender Monitor Agent (§4.8.1) — Stage 19 entry. Monitors tenders
    and records them. Does NOT submit bids.
  - Tender Qualification Agent (§4.8.2) — Stage 19. Produces the
    Tender Qualification Report (ENT-TEN-002). Does NOT decide to bid.
  - Quotation Support Agent (§4.8.4) — Stage 19. Produces the
    Quotation Dossier (ENT-TEN-003). Does NOT submit; does NOT commit
    prices; does NOT bind Techno Service.
  - Project Monitor Agent (§4.8.3) — Stage 20. Produces the
    Project Status Report (ENT-TEN-004). Does NOT modify commitments.

Constitutional source:
  - Document 02 §4.8 (Tender and Project Intelligence Office)
  - Document 05 §3.10 (ENT-TEN-001..004)
  - Document 06 §2.19..2.20 (Stages 19-20)
  - Document 06 §4.7 (Tender Gate), §4.8 (Project Gate)
  - Constitution Article XII (Human Approval for submission)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class TenderStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    AWARDED = "AWARDED"
    LOST = "LOST"
    CANCELLED = "CANCELLED"


class TenderQualificationOutcome(str, Enum):
    QUALIFIED = "QUALIFIED"
    CONDITIONALLY_QUALIFIED = "CONDITIONALLY_QUALIFIED"
    NOT_QUALIFIED = "NOT_QUALIFIED"


class ProjectStatus(str, Enum):
    AWARDED = "AWARDED"
    IN_PROGRESS = "IN_PROGRESS"
    ON_HOLD = "ON_HOLD"
    COMPLETED = "COMPLETED"
    DISPUTED = "DISPUTED"
    CLOSED = "CLOSED"


class AfterSalesStatus(str, Enum):
    """The status of an after-sales opportunity (ENT-COM-006)."""

    IDENTIFIED = "IDENTIFIED"
    ENGAGED = "ENGAGED"
    CONVERTED = "CONVERTED"
    CLOSED = "CLOSED"


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class TenderProjectEngineError(Exception):
    """Base for tender_project engine errors."""


class TenderBidWithoutApprovalError(TenderProjectEngineError):
    """A bid submission is attempted without Human Approval.

    Per Document 02 §4.8.1 / §4.8.4, the Tender Monitor and
    Quotation Support agents are constitutionally PROHIBITED from
    submitting bids. Every submission REQUIRES Human Approval
    (Constitution Article XII, Class 3 or Class 4)."""

    def __init__(self) -> None:
        super().__init__(
            f"Tender submission REJECTED: no Human Approval reference. "
            f"Per Document 02 §4.8.1 / §4.8.4 and Constitution Article XII, "
            f"every bid submission REQUIRES Class 3 (or higher) Human Approval. "
            f"The Tender Monitor and Quotation Support agents are PROHIBITED "
            f"from submitting bids or binding Techno Service."
        )


class QuotationSubmissionWithoutApprovalError(TenderProjectEngineError):
    """A Quotation Dossier is submitted without Human Approval."""

    def __init__(self) -> None:
        super().__init__(
            f"Quotation submission REJECTED: no Human Approval reference. "
            f"Per Document 02 §4.8.4 Authority Limits: 'May not submit; may not "
            f"commit prices, margins, or terms; may not bind Techno Service.'"
        )


class QuotationMissingRequiredFieldError(TenderProjectEngineError):
    """A Quotation Dossier is missing a required field."""

    def __init__(self, field_name: str) -> None:
        self.field_name = field_name
        super().__init__(
            f"Quotation Dossier is REJECTED: missing required field "
            f"'{field_name}'. Per Document 02 §4.8.4, a Quotation Dossier "
            f"must include pricing model, technical content, and source "
            f"citation."
        )


class ProjectCommitmentChangeError(TenderProjectEngineError):
    """A project commitment change is attempted without Human Approval.

    Per Document 06 §4.8 GATE-PJ-002: the Project Gate is invoked at
    every Project commitment change."""

    def __init__(self) -> None:
        super().__init__(
            f"Project commitment change REJECTED: no Human Approval "
            f"reference. Per Document 06 §4.8 GATE-PJ-002 and "
            f"Constitution Article XII, every project commitment change "
            f"REQUIRES Human Approval. The Project Monitor Agent may "
            f"NOT modify commitments or bind Techno Service."
        )


class TenderQualificationMissingError(TenderProjectEngineError):
    """A Tender is missing the qualification_report_id or has an
    unqualified qualification outcome."""

    def __init__(self, tender_id: str) -> None:
        self.tender_id = tender_id
        super().__init__(
            f"Tender {tender_id} is REJECTED: no qualification outcome or "
            f"the qualification is NOT_QUALIFIED. Per Document 02 §4.8.2, "
            f"a Tender may not be submitted to Quotation Support without "
            f"a qualified Tender Qualification Report."
        )


# ---------------------------------------------------------------------------
# Inputs / Outputs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TenderSpec:
    """The input spec for a Tender record."""

    tender_reference: str
    issuer: str
    issue_date: str
    closing_date: str
    description: str = ""
    opportunity_id: Optional[str] = None


@dataclass(frozen=True)
class TenderQualificationSpec:
    """The input spec for a Tender Qualification Report."""

    tender_id: str
    qualification_outcome: str  # QUALIFIED / CONDITIONALLY_QUALIFIED / NOT_QUALIFIED
    rationale: str = ""
    fit_assessment: str = ""
    risk_assessment: str = ""
    commercial_assessment: str = ""


@dataclass(frozen=True)
class QuotationDossierSpec:
    """The input spec for a Quotation Dossier."""

    tender_id: str
    document_type: str
    content: str
    pricing_model: str = ""
    technical_content: str = ""
    submission_date: Optional[str] = None
    human_approval_id: Optional[str] = None


@dataclass(frozen=True)
class ProjectStatusReportSpec:
    """The input spec for a Project Status Report."""

    project_name: str
    status: str = "AWARDED"
    issues: str = ""
    opportunity_id: Optional[str] = None


@dataclass(frozen=True)
class AfterSalesReportSpec:
    """The input spec for an After-Sales Intelligence Report."""

    opportunity_id: str
    report_text: str
    recurring_opportunity: str = ""


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class TenderProjectEngine:
    """The pure-logic engine for the Tender and Project Intelligence
    Office. All four agents (Tender Monitor, Tender Qualification,
    Quotation Support, Project Monitor) are methods on this engine."""

    # -----------------------------------------------------------------
    # Tender Monitor (§4.8.1)
    # -----------------------------------------------------------------

    def validate_tender(self, spec: TenderSpec) -> None:
        """Validate a Tender record. The Tender Monitor is PROHIBITED
        from submitting bids (per the Agent's charter). This validation
        is for the record only — the submission is gated separately."""
        if not spec.tender_reference or not spec.tender_reference.strip():
            raise ValueError("tender_reference is required")
        if not spec.issuer or not spec.issuer.strip():
            raise ValueError("issuer is required")
        if not spec.issue_date:
            raise ValueError("issue_date is required")
        if not spec.closing_date:
            raise ValueError("closing_date is required")

    # -----------------------------------------------------------------
    # Tender Qualification (§4.8.2)
    # -----------------------------------------------------------------

    def evaluate_qualification(
        self, spec: TenderQualificationSpec
    ) -> TenderQualificationOutcome:
        """Evaluate a Tender Qualification Report.

        Per Document 02 §4.8.2, the Agent may issue a Tender
        Qualification Report; it may NOT decide to bid.
        """
        outcome_upper = spec.qualification_outcome.upper()
        if outcome_upper not in ("QUALIFIED", "CONDITIONALLY_QUALIFIED", "NOT_QUALIFIED"):
            raise ValueError(
                f"qualification_outcome must be QUALIFIED, "
                f"CONDITIONALLY_QUALIFIED, or NOT_QUALIFIED; got {spec.qualification_outcome!r}"
            )
        return TenderQualificationOutcome(outcome_upper)

    # -----------------------------------------------------------------
    # Quotation Support (§4.8.4)
    # -----------------------------------------------------------------

    def validate_quotation_dossier(
        self, spec: QuotationDossierSpec
    ) -> None:
        """Validate a Quotation Dossier.

        Enforces:
          - document_type is non-empty
          - content is non-empty
          - pricing_model is non-empty (Required Evidence per §4.8.4)
          - technical_content is non-empty (Required Evidence per §4.8.4)
          - If submission_date is set (i.e. the dossier is being
            submitted), a Human Approval reference is REQUIRED.
        """
        if not spec.document_type or not spec.document_type.strip():
            raise QuotationMissingRequiredFieldError("document_type")
        if not spec.content or not spec.content.strip():
            raise QuotationMissingRequiredFieldError("content")
        if not spec.pricing_model or not spec.pricing_model.strip():
            raise QuotationMissingRequiredFieldError("pricing_model")
        if not spec.technical_content or not spec.technical_content.strip():
            raise QuotationMissingRequiredFieldError("technical_content")

        if spec.submission_date and (
            not spec.human_approval_id or not spec.human_approval_id.strip()
        ):
            raise QuotationSubmissionWithoutApprovalError()

    # -----------------------------------------------------------------
    # Project Monitor (§4.8.3)
    # -----------------------------------------------------------------

    def validate_project_status(
        self, spec: ProjectStatusReportSpec
    ) -> None:
        """Validate a Project Status Report.

        Per Document 02 §4.8.3, the Agent may issue a Project Status
        Report; it may NOT modify project commitments or bind
        Techno Service. The Project Gate (GATE-PJ-002) is invoked at
        every commitment change. This validation is for the status
        record only — commitment changes are gated separately.
        """
        if not spec.project_name or not spec.project_name.strip():
            raise ValueError("project_name is required")
        valid = {"AWARDED", "IN_PROGRESS", "ON_HOLD", "COMPLETED", "DISPUTED", "CLOSED"}
        if spec.status.upper() not in valid:
            raise ValueError(
                f"status must be one of: {sorted(valid)}; got {spec.status!r}"
            )

    def check_commitment_change(
        self, *, has_commitment_change: bool, human_approval_id: Optional[str]
    ) -> None:
        """Check a project commitment change. REJECTED without Human
        Approval per Document 06 §4.8 GATE-PJ-002."""
        if has_commitment_change and (
            not human_approval_id or not human_approval_id.strip()
        ):
            raise ProjectCommitmentChangeError()

    # -----------------------------------------------------------------
    # After-Sales Intelligence (§4.6.6) — listed in the deferred list
    # but the entity already exists. Activated in Phase 6.
    # -----------------------------------------------------------------

    def validate_after_sales(
        self, spec: AfterSalesReportSpec
    ) -> None:
        """Validate an After-Sales Intelligence Report.

        Per Document 02 §4.6.6, the Agent may issue an After-Sales
        Intelligence Report; it may NOT contact customer without
        Human Approval. The Report itself does not require
        approval to be issued (it is intelligence, not engagement).
        """
        if not spec.report_text or not spec.report_text.strip():
            raise ValueError("report_text is required")
        if not spec.opportunity_id or not spec.opportunity_id.strip():
            raise ValueError("opportunity_id is required")
