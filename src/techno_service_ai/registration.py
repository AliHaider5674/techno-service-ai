"""Registration Engine — Document 02 §4.7, Phase 5.

Implements the pure-logic engine for the three Registration and Market
Entry Principal Agents activated in Phase 5:

  - Registration Coordinator Agent (§4.7.1) — produces a Registration
    Status Report (ENT-REG-001). The Agent does NOT file or commit
    on Techno Service's behalf without Human Approval.
  - Prequalification Agent (§4.7.2) — produces a Prequalification
    Status Report (ENT-REG-002 → schema ENT-REG-003). The Agent
    does NOT submit or commit without Human Approval.
  - Market Entry Strategy Agent (§4.7.3) — produces a Market Entry
    Options Report (ENT-REG-004). The Agent does NOT select a
    market-entry path; selection is a Human Authority decision.

Constitutional source:
  - Document 02 §4.7 (Registration and Market Entry Office)
  - Document 05 §3.9 (ENT-REG-001..004)
  - Constitution Article VIII (Registers at every Registration Gate)
  - Constitution Article XII (Human Approval for Class 3 / Class 4)
  - Document 06 §4.6 GATE-RG-002 (Registration Gate)
  - Document 06 §4.5 GATE-CO-002 (Commercial Gate — Market Entry
    is at the entry of Stage 18)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class RegistrationStatus(str, Enum):
    """The status of a Registration Status Report."""

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    REGISTERED = "REGISTERED"
    EXPIRED = "EXPIRED"
    REJECTED = "REJECTED"


class PrequalificationStatus(str, Enum):
    """The status of a Prequalification Status Report."""

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    QUALIFIED = "QUALIFIED"
    EXPIRED = "EXPIRED"
    REJECTED = "REJECTED"


class MarketEntryPathStatus(str, Enum):
    """The status of a Market Entry Options Report.

    The Agent does NOT select a path. The path is selected only by
    Human Approval (Constitution Article XII).
    """

    DRAFT = "DRAFT"            # Options under preparation
    ISSUED = "ISSUED"          # Options presented to human
    SELECTED = "SELECTED"      # Set ONLY via Human Approval
    REJECTED = "REJECTED"


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class RegistrationEngineError(Exception):
    """Base for registration engine errors."""


class RegistrationMissingApprovalError(RegistrationEngineError):
    """A Registration filing is attempted without Human Approval.

    Per Document 02 §4.7.1 Prohibited Actions: "File without Human
    Approval; misrepresent registration status; bind Techno Service."
    """

    def __init__(self) -> None:
        super().__init__(
            f"Registration REJECTED: filing or status update attempted without "
            f"Human Approval. Per Document 02 §4.7.1, the Agent 'may not file or "
            f"commit on Techno Service's behalf without Human Approval; may not "
            f"bind Techno Service.' Every filing REQUIRES Class 3/4 Human Approval."
        )


class PrequalificationMissingApprovalError(RegistrationEngineError):
    """A Prequalification submission is attempted without Human Approval."""

    def __init__(self) -> None:
        super().__init__(
            f"Prequalification REJECTED: submission attempted without Human Approval. "
            f"Per Document 02 §4.7.2, the Agent 'may not submit without Human "
            f"Approval; may not bind Techno Service.'"
        )


class MarketEntryPathSelectionNotAllowedError(RegistrationEngineError):
    """The Market Entry Strategy Agent is constitutionally PROHIBITED
    from selecting a path. Selection is a Human Authority decision.
    """

    def __init__(self) -> None:
        super().__init__(
            f"Market Entry Strategy Agent is REJECTED: attempted to select a path. "
            f"Per Document 02 §4.7.3 Prohibited Actions, the Agent 'may not select a "
            f"path; may not bind Techno Service.' Selection is a Human Authority "
            f"decision (Constitution Article XII, Class 3 / Class 4)."
        )


class MarketEntryOptionsIncompleteError(RegistrationEngineError):
    """A Market Entry Options Report is incomplete.

    Per Document 02 §4.7.3 Required Evidence: "Source citation;
    stakeholder map; risk map." A single-path report is a Failure
    Condition. The options set must enumerate at least 2 paths.
    """

    def __init__(self, missing: Tuple[str, ...]) -> None:
        self.missing = missing
        super().__init__(
            f"Market Entry Options Report REJECTED: missing fields {list(missing)}. "
            f"Per Document 02 §4.7.3, the report must include source citation, "
            f"stakeholder map, risk map, and at least 2 path options."
        )


# ---------------------------------------------------------------------------
# Inputs / Outputs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RegistrationStatusReportSpec:
    """The input spec for a Registration Status Report."""

    opportunity_id: str
    registration_type: str  # e.g. 'VENDOR_REGISTRATION', 'PRODUCT_REGISTRATION'
    authority: str
    status: RegistrationStatus
    notes: str = ""
    human_approval_id: Optional[str] = None


@dataclass(frozen=True)
class RegistrationStatusReportResult:
    """The result of a Registration Status Report evaluation."""

    opportunity_id: str
    registration_type: str
    authority: str
    status: RegistrationStatus
    notes: str
    human_approval_id: Optional[str]
    requires_human_approval: bool  # True when status is REGISTERED (i.e. a filing was made)


@dataclass(frozen=True)
class PrequalificationStatusReportSpec:
    """The input spec for a Prequalification Status Report."""

    opportunity_id: str
    authority: str
    status: PrequalificationStatus
    notes: str = ""
    human_approval_id: Optional[str] = None


@dataclass(frozen=True)
class PrequalificationStatusReportResult:
    """The result of a Prequalification Status Report evaluation."""

    opportunity_id: str
    authority: str
    status: PrequalificationStatus
    notes: str
    human_approval_id: Optional[str]
    requires_human_approval: bool


@dataclass(frozen=True)
class MarketEntryOptionsSpec:
    """The input spec for a Market Entry Options Report."""

    opportunity_id: str
    manufacturer_id: Optional[str]
    options_set: Tuple[str, ...]  # At least 2 paths
    stakeholder_map: str
    risk_map: str
    report_date: str
    source_citation: str
    selected_path: Optional[str] = None  # MUST be None for the Agent


@dataclass(frozen=True)
class MarketEntryOptionsResult:
    """The result of a Market Entry Options evaluation."""

    opportunity_id: str
    manufacturer_id: Optional[str]
    options_set: Tuple[str, ...]
    stakeholder_map: str
    risk_map: str
    report_date: str
    options_count: int
    selection_violation: bool


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class RegistrationEngine:
    """The pure-logic engine for the Registration and Market Entry Office."""

    # -----------------------------------------------------------------
    # Registration Coordinator (§4.7.1)
    # -----------------------------------------------------------------

    def evaluate_registration(
        self, spec: RegistrationStatusReportSpec
    ) -> RegistrationStatusReportResult:
        """Evaluate a Registration Status Report.

        If the status is REGISTERED (i.e. a filing was made), a Human
        Approval reference is REQUIRED.
        """
        requires_human_approval = spec.status in (
            RegistrationStatus.REGISTERED,
            RegistrationStatus.REJECTED,  # A negative status may also need approval
        )
        if requires_human_approval and (
            not spec.human_approval_id or not spec.human_approval_id.strip()
        ):
            raise RegistrationMissingApprovalError()

        return RegistrationStatusReportResult(
            opportunity_id=spec.opportunity_id,
            registration_type=spec.registration_type,
            authority=spec.authority,
            status=spec.status,
            notes=spec.notes,
            human_approval_id=spec.human_approval_id,
            requires_human_approval=requires_human_approval,
        )

    # -----------------------------------------------------------------
    # Prequalification (§4.7.2)
    # -----------------------------------------------------------------

    def evaluate_prequalification(
        self, spec: PrequalificationStatusReportSpec
    ) -> PrequalificationStatusReportResult:
        """Evaluate a Prequalification Status Report.

        If the status is QUALIFIED (i.e. a submission was made), a Human
        Approval reference is REQUIRED.
        """
        requires_human_approval = spec.status in (
            PrequalificationStatus.QUALIFIED,
            PrequalificationStatus.REJECTED,
        )
        if requires_human_approval and (
            not spec.human_approval_id or not spec.human_approval_id.strip()
        ):
            raise PrequalificationMissingApprovalError()

        return PrequalificationStatusReportResult(
            opportunity_id=spec.opportunity_id,
            authority=spec.authority,
            status=spec.status,
            notes=spec.notes,
            human_approval_id=spec.human_approval_id,
            requires_human_approval=requires_human_approval,
        )

    # -----------------------------------------------------------------
    # Market Entry Strategy (§4.7.3)
    # -----------------------------------------------------------------

    def evaluate_market_entry(self, spec: MarketEntryOptionsSpec) -> MarketEntryOptionsResult:
        """Evaluate a Market Entry Options Report.

        Enforces:
          - All 4 required fields are present (source_citation, options_set,
            stakeholder_map, risk_map).
          - At least 2 path options.
          - The Agent did NOT select a path (selected_path is None).
        """
        missing = []
        if not spec.options_set or len(spec.options_set) < 2:
            missing.append("options_set (need ≥ 2 paths)")
        if not spec.stakeholder_map or not spec.stakeholder_map.strip():
            missing.append("stakeholder_map")
        if not spec.risk_map or not spec.risk_map.strip():
            missing.append("risk_map")
        if not spec.source_citation or not spec.source_citation.strip():
            missing.append("source_citation")
        if missing:
            raise MarketEntryOptionsIncompleteError(tuple(missing))

        # No selection
        if spec.selected_path is not None:
            raise MarketEntryPathSelectionNotAllowedError()

        return MarketEntryOptionsResult(
            opportunity_id=spec.opportunity_id,
            manufacturer_id=spec.manufacturer_id,
            options_set=spec.options_set,
            stakeholder_map=spec.stakeholder_map,
            risk_map=spec.risk_map,
            report_date=spec.report_date,
            options_count=len(spec.options_set),
            selection_violation=False,
        )
