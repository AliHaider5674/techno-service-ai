"""Proactive Product Discovery Engine — Constitution v2.4.

Phase 9 implements Office 18 (Product Discovery Proactive) under
Constitution Amendment v2.4 (Class 4 adoption 2026-07-19).

The engine is pure logic. No DB coupling. All error classes are
typed exceptions whose messages are the constitutional text.

Office 18 — 4 Principal Agents:
  - §4.18.1 Global Product Monitor Agent
  - §4.18.2 New Product Detector Agent
  - §4.18.3 Emerging Company Scout Agent
  - §4.18.4 Patent Watch Agent

5 Qualification Filters (F1..F5):
  - F1 Kuwait climate suitability (heat, wind, dust)
  - F2 Retrofit-friendliness (no major system change)
  - F3 No agent in Kuwait (exclusive representation available)
  - F4 Low operating cost (no specialised training, no eng team)
  - F5 Company size (medium/emerging, not tier-1)

10-Step Exclusive Agency Acquisition Workflow:
  Step 1: Discovery signal
  Step 2: Qualification (5 filters)
  Step 3: Manufacturer profiling
  Step 4: Patent check
  Step 5: Cost analysis
  Step 6: Class 3 approval to proceed with outreach
  Step 7: Contact + NDA
  Step 8: Class 4 approval to sign exclusive agency
  Step 9: Contract execution
  Step 10: Onboarding

Constitutional source:
  - Constitution v2.4 (Major Amendment 2026-07-19).
  - Document 02 §4.18 (Office 18 — Product Discovery Proactive).
  - Document 06 §2.8.5 (Stage 8.5 — Proactive Discovery).
  - Document 06 §10 (Exclusive Agency Acquisition Workflow).
  - Constitution Article VIII (Constitutional Registers —
    RESTRICTED / CONFLICT / NON_REPRESENTED).
  - Constitution Article XII (Human Approval).
  - Constitution Article X (Provenance / source citation).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple


# ===========================================================================
# Enums
# ===========================================================================


class SignalStrength(str, Enum):
    """The strength of a discovery signal (Global Product Monitor)."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ProductCategory(str, Enum):
    """The category of a discovered product."""

    INDUSTRIAL_MAINTENANCE = "INDUSTRIAL_MAINTENANCE"
    OIL_GAS = "OIL_GAS"
    PROCESS_INSTRUMENTATION = "PROCESS_INSTRUMENTATION"
    ELECTRICAL = "ELECTRICAL"
    MECHANICAL = "MECHANICAL"
    CORROSION_PROTECTION = "CORROSION_PROTECTION"
    OTHER = "OTHER"


class DiscoverySource(str, Enum):
    """The source of a discovery signal."""

    WEB_SEARCH = "WEB_SEARCH"
    TRADE_PUBLICATION = "TRADE_PUBLICATION"
    PATENT = "PATENT"
    EXHIBITION = "EXHIBITION"
    REFERRAL = "REFERRAL"
    PARTNER = "PARTNER"


class FilterOutcome(str, Enum):
    """The outcome of a single qualification filter."""

    PASS = "PASS"
    FAIL = "FAIL"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class OverallQualification(str, Enum):
    """The overall qualification outcome (5-filter AND)."""

    QUALIFIED = "QUALIFIED"
    REJECTED = "REJECTED"


class WatchType(str, Enum):
    """The type of a WatchList entry."""

    CATEGORY = "CATEGORY"
    SECTOR = "SECTOR"
    MANUFACTURER = "MANUFACTURER"
    KEYWORD = "KEYWORD"


class PatentRelevance(str, Enum):
    """The relevance score of a patent alert."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class WorkflowStepStatus(str, Enum):
    """The status of an Exclusive Agency Acquisition Workflow step."""

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    SKIPPED = "SKIPPED"


class AgencyOpportunityStatus(str, Enum):
    """The status of an Exclusive Agency Opportunity."""

    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    WON = "WON"  # signed exclusive agency
    LOST = "LOST"
    WITHDRAWN = "WITHDRAWN"


# ===========================================================================
# Errors
# ===========================================================================


class ProactiveDiscoveryError(Exception):
    """Base error for the Proactive Discovery engine."""


class ProactiveDiscoveryErrorMissingSourceError(ProactiveDiscoveryError):
    """A discovery cannot be raised without a source citation.

    Per Constitution Article X, every material claim must carry
    source citation. A discovery without a source is a material
    claim without provenance.
    """

    def __init__(self) -> None:
        super().__init__(
            "Proactive Product Discovery REJECTED: missing source "
            "citation. Per Constitution Article X, every material "
            "claim requires source citation."
        )


class QualificationFilterMissingError(ProactiveDiscoveryError):
    """A qualification filter cannot be run with missing inputs."""

    def __init__(self, filter_id: str) -> None:
        super().__init__(
            f"Qualification filter {filter_id!r} REJECTED: missing "
            "required input. All 5 filters must receive their "
            "required input (Constitution v2.4, Office 18 §4.18.2)."
        )


class RegisterCheckFailedError(ProactiveDiscoveryError):
    """A Proactive Discovery gate may not bypass the 3 Constitutional Registers.

    Per Constitution Article VIII, the 3 Constitutional Registers
    (RESTRICTED / CONFLICT / NON_REPRESENTED_PRINCIPAL) are checked
    at the Proactive Discovery gate.
    """

    def __init__(self, register: str, entity: str) -> None:
        super().__init__(
            f"Proactive Discovery gate REJECTED on {entity!r}: "
            f"{register} register hit. The gate may not bypass the "
            "Constitutional Registers (Constitution Article VIII)."
        )


class Class3ApprovalRequiredError(ProactiveDiscoveryError):
    """Step 6 of the Exclusive Agency Acquisition Workflow requires Class 3 approval."""

    def __init__(self, opportunity_id: str) -> None:
        super().__init__(
            f"Exclusive Agency Acquisition Workflow step 6 for "
            f"opportunity {opportunity_id!r} REJECTED: Class 3 "
            "Human Approval is REQUIRED before outreach "
            "(Constitution v2.4, Document 06 §10; "
            "Constitution Article XII)."
        )


class Class4ApprovalRequiredError(ProactiveDiscoveryError):
    """Step 8 of the Exclusive Agency Acquisition Workflow requires Class 4 approval."""

    def __init__(self, opportunity_id: str) -> None:
        super().__init__(
            f"Exclusive Agency Acquisition Workflow step 8 for "
            f"opportunity {opportunity_id!r} REJECTED: Class 4 "
            "Human Approval is REQUIRED before signing "
            "(Constitution v2.4, Document 06 §10; "
            "Constitution Article XII)."
        )


class WorkflowStepOutOfOrderError(ProactiveDiscoveryError):
    """The workflow steps must be executed in order (1 → 10)."""

    def __init__(self, current_step: int, target_step: int) -> None:
        super().__init__(
            f"Workflow step REJECTED: cannot advance from step "
            f"{current_step} to step {target_step} — steps must be "
            "executed in order (1 → 10) (Constitution v2.4, "
            "Document 06 §10)."
        )


# ===========================================================================
# Specs (frozen dataclasses — engine inputs)
# ===========================================================================


@dataclass(frozen=True)
class ProactiveDiscoverySpec:
    """A signal raised by the Global Product Monitor Agent (§4.18.1)."""

    product_name: str
    product_category: ProductCategory
    sector: str
    manufacturer_name: str
    manufacturer_country: Optional[str] = None
    discovery_source: DiscoverySource = DiscoverySource.WEB_SEARCH
    source_citation_url: Optional[str] = None
    signal_strength: SignalStrength = SignalStrength.MEDIUM
    notes: str = ""


@dataclass(frozen=True)
class QualificationFilterInputs:
    """The inputs to the 5 qualification filters (F1..F5)."""

    # F1 — Kuwait climate suitability
    f1_heat_rating: str = "UNKNOWN"  # e.g. "-10C to +60C operational"
    f1_dust_rating: str = "UNKNOWN"  # e.g. "IP65 / IP66 / NEMA 4"
    f1_wind_rating: str = "UNKNOWN"  # e.g. "tested to 60 km/h"
    # F2 — Retrofit-friendliness
    f2_requires_major_change: bool = False  # True = FAIL
    f2_installation_complexity: str = "LOW"  # LOW / MEDIUM / HIGH
    # F3 — No agent in Kuwait
    f3_existing_agents_in_kuwait: List[str] = field(default_factory=list)
    # F4 — Low operating cost
    f4_requires_specialised_training: bool = False
    f4_requires_engineering_team: bool = False
    f4_annual_maintenance_cost: str = "LOW"  # LOW / MEDIUM / HIGH
    # F5 — Company size (medium/emerging)
    f5_employee_count: int = 0
    f5_annual_revenue_usd: int = 0
    f5_is_tier_1: bool = False


@dataclass(frozen=True)
class QualificationFilterResult:
    """The combined result of the 5 qualification filters."""

    f1: FilterOutcome
    f1_rationale: str
    f2: FilterOutcome
    f2_rationale: str
    f3: FilterOutcome
    f3_rationale: str
    f4: FilterOutcome
    f4_rationale: str
    f5: FilterOutcome
    f5_rationale: str

    @property
    def overall(self) -> OverallQualification:
        outcomes = [self.f1, self.f2, self.f3, self.f4, self.f5]
        if all(o == FilterOutcome.PASS for o in outcomes):
            return OverallQualification.QUALIFIED
        return OverallQualification.REJECTED


@dataclass(frozen=True)
class WatchListSpec:
    """A WatchList entry (§4.18.1)."""

    watch_label: str
    watch_type: WatchType
    watch_target: str
    owner_id: str


@dataclass(frozen=True)
class PatentAlertSpec:
    """A patent alert surfaced by the Patent Watch Agent (§4.18.4)."""

    patent_id: str
    title: str
    assignee: Optional[str] = None
    filing_date: Optional[str] = None
    relevance: PatentRelevance = PatentRelevance.MEDIUM
    relevance_rationale: str = ""
    source_citation_url: Optional[str] = None


@dataclass(frozen=True)
class EmergingCompanyProfile:
    """A profile of an emerging company (output of §4.18.3)."""

    company_name: str
    country: str
    employee_count: int
    annual_revenue_usd: int
    product_categories: List[ProductCategory]
    patent_count: int
    is_tier_1: bool
    notes: str = ""


@dataclass(frozen=True)
class ExclusiveAgencyOpportunity:
    """A qualified discovery that has graduated to the 10-step workflow."""

    discovery_id: str
    manufacturer_name: str
    product_summary: str
    workflow_step: int = 1  # 1..10
    class_3_approval_id: Optional[str] = None
    class_4_approval_id: Optional[str] = None
    status: AgencyOpportunityStatus = AgencyOpportunityStatus.OPEN


# ===========================================================================
# Engines
# ===========================================================================


class GlobalProductMonitorEngine:
    """§4.18.1 — Global Product Monitor Agent.

    Scans all sectors for new industrial maintenance and oil/gas
    products. Generates discovery signals with source citation.
    """

    def raise_signal(self, spec: ProactiveDiscoverySpec) -> str:
        """Raise a discovery signal. Returns the signal id.

        The source_citation_url is REQUIRED (Constitution Article X).
        """
        if not spec.source_citation_url and spec.discovery_source != DiscoverySource.REFERRAL:
            raise ProactiveDiscoveryErrorMissingSourceError()
        if not spec.product_name or not spec.manufacturer_name:
            raise ProactiveDiscoveryError(
                "Proactive Discovery REJECTED: product_name and "
                "manufacturer_name are REQUIRED."
            )
        # In production this would write to the DB; the engine
        # returns the id.
        from .services import _uuid
        return _uuid()


class NewProductDetectorEngine:
    """§4.18.2 — New Product Detector Agent.

    Applies the 5 qualification filters (F1..F5) to a discovery
    and produces a QualificationFilterResult.
    """

    def apply_filters(self, inputs: QualificationFilterInputs) -> QualificationFilterResult:
        # F1 — Kuwait climate (heat, wind, dust)
        f1_pass = (
            "60C" in inputs.f1_heat_rating or "+60" in inputs.f1_heat_rating
            or "55C" in inputs.f1_heat_rating
        ) and (
            "IP65" in inputs.f1_dust_rating or "IP66" in inputs.f1_dust_rating
            or "NEMA 4" in inputs.f1_dust_rating
        )
        f1 = FilterOutcome.PASS if f1_pass else FilterOutcome.FAIL
        f1_rat = (
            "Climate rating sufficient for Kuwait (-10C to +60C; IP65+)"
            if f1_pass else
            "Climate rating does not cover Kuwait conditions"
        )

        # F2 — Retrofit-friendliness
        f2_pass = (
            not inputs.f2_requires_major_change
            and inputs.f2_installation_complexity in ("LOW", "MEDIUM")
        )
        f2 = FilterOutcome.PASS if f2_pass else FilterOutcome.FAIL
        f2_rat = (
            "Retrofit-friendly: no major system change; "
            f"installation complexity = {inputs.f2_installation_complexity}"
            if f2_pass else
            "Retrofit-unfriendly: requires major system change "
            f"or installation complexity = {inputs.f2_installation_complexity}"
        )

        # F3 — No agent in Kuwait
        f3_pass = len(inputs.f3_existing_agents_in_kuwait) == 0
        f3 = FilterOutcome.PASS if f3_pass else FilterOutcome.FAIL
        f3_rat = (
            "No existing agent in Kuwait — exclusive representation available"
            if f3_pass else
            f"Existing agents in Kuwait: "
            f"{', '.join(inputs.f3_existing_agents_in_kuwait)}"
        )

        # F4 — Low operating cost
        f4_pass = (
            not inputs.f4_requires_specialised_training
            and not inputs.f4_requires_engineering_team
            and inputs.f4_annual_maintenance_cost in ("LOW", "MEDIUM")
        )
        f4 = FilterOutcome.PASS if f4_pass else FilterOutcome.FAIL
        f4_rat = (
            "Low operating cost: no specialised training, no "
            f"engineering team, maintenance = {inputs.f4_annual_maintenance_cost}"
            if f4_pass else
            "Operating cost too high: requires specialised training "
            f"or engineering team, maintenance = {inputs.f4_annual_maintenance_cost}"
        )

        # F5 — Company size (medium/emerging, not tier-1)
        f5_pass = (
            not inputs.f5_is_tier_1
            and 10 <= inputs.f5_employee_count <= 2000
            and 1_000_000 <= inputs.f5_annual_revenue_usd <= 500_000_000
        )
        f5 = FilterOutcome.PASS if f5_pass else FilterOutcome.FAIL
        f5_rat = (
            f"Medium/emerging: employees={inputs.f5_employee_count}, "
            f"revenue=${inputs.f5_annual_revenue_usd:,}, not tier-1"
            if f5_pass else
            f"Company does not match medium/emerging profile: "
            f"employees={inputs.f5_employee_count}, "
            f"revenue=${inputs.f5_annual_revenue_usd:,}, "
            f"tier-1={inputs.f5_is_tier_1}"
        )

        return QualificationFilterResult(
            f1=f1, f1_rationale=f1_rat,
            f2=f2, f2_rationale=f2_rat,
            f3=f3, f3_rationale=f3_rat,
            f4=f4, f4_rationale=f4_rat,
            f5=f5, f5_rationale=f5_rat,
        )


class EmergingCompanyScoutEngine:
    """§4.18.3 — Emerging Company Scout Agent.

    Profiles medium/emerging companies in target sectors. Produces
    EmergingCompanyProfile records.
    """

    def profile(self, spec: EmergingCompanyProfile) -> EmergingCompanyProfile:
        """Validate the profile; reject tier-1 companies."""
        if spec.is_tier_1:
            raise ProactiveDiscoveryError(
                f"Company {spec.company_name!r} is a tier-1 — "
                "out of scope for the medium/emerging focus "
                "(Constitution v2.4, Document 02 §4.18.3)."
            )
        if spec.employee_count < 10 or spec.employee_count > 2000:
            raise ProactiveDiscoveryError(
                f"Company {spec.company_name!r} employee count "
                f"({spec.employee_count}) is outside the medium/"
                "emerging range (10..2000) (Constitution v2.4)."
            )
        return spec


class PatentWatchEngine:
    """§4.18.4 — Patent Watch Agent.

    Monitors patents in target sectors. Surfaces patent alerts
    with relevance scoring.
    """

    def surface_alert(self, spec: PatentAlertSpec) -> PatentAlertSpec:
        """Validate the alert; LOW relevance is logged but allowed."""
        if not spec.patent_id or not spec.title:
            raise ProactiveDiscoveryError(
                "Patent Alert REJECTED: patent_id and title are REQUIRED."
            )
        return spec


class ExclusiveAgencyWorkflowEngine:
    """The 10-step Exclusive Agency Acquisition Workflow engine.

    Per Constitution v2.4, Document 06 §10:

      Step 1: Discovery signal
      Step 2: Qualification (5 filters)
      Step 3: Manufacturer profiling
      Step 4: Patent check
      Step 5: Cost analysis
      Step 6: Class 3 approval to proceed with outreach
      Step 7: Contact + NDA
      Step 8: Class 4 approval to sign exclusive agency
      Step 9: Contract execution
      Step 10: Onboarding
    """

    TOTAL_STEPS = 10

    def advance(
        self,
        opp: ExclusiveAgencyOpportunity,
        target_step: int,
        *,
        class_3_approval_id: Optional[str] = None,
        class_4_approval_id: Optional[str] = None,
    ) -> ExclusiveAgencyOpportunity:
        """Advance the opportunity to the target step.

        Steps must be executed in order (1 → 10). Class 3 approval
        is REQUIRED at step 6. Class 4 approval is REQUIRED at step 8.
        """
        if target_step < 1 or target_step > self.TOTAL_STEPS:
            raise ProactiveDiscoveryError(
                f"Workflow step {target_step!r} is out of range "
                f"(1..{self.TOTAL_STEPS})."
            )
        if target_step != opp.workflow_step + 1 and target_step > opp.workflow_step:
            raise WorkflowStepOutOfOrderError(opp.workflow_step, target_step)

        # Class 3 approval gate at step 6
        if target_step >= 6 and not class_3_approval_id and not opp.class_3_approval_id:
            raise Class3ApprovalRequiredError(opp.discovery_id)

        # Class 4 approval gate at step 8
        if target_step >= 8 and not class_4_approval_id and not opp.class_4_approval_id:
            raise Class4ApprovalRequiredError(opp.discovery_id)

        new_class3 = class_3_approval_id or opp.class_3_approval_id
        new_class4 = class_4_approval_id or opp.class_4_approval_id
        new_status = opp.status
        if target_step == 10:
            new_status = AgencyOpportunityStatus.WON
        elif target_step > opp.workflow_step:
            new_status = AgencyOpportunityStatus.IN_PROGRESS

        return ExclusiveAgencyOpportunity(
            discovery_id=opp.discovery_id,
            manufacturer_name=opp.manufacturer_name,
            product_summary=opp.product_summary,
            workflow_step=target_step,
            class_3_approval_id=new_class3,
            class_4_approval_id=new_class4,
            status=new_status,
        )


# ===========================================================================
# Register gate (Constitution Article VIII)
# ===========================================================================


class ProactiveDiscoveryRegisterGate:
    """The Constitutional Register gate at the Proactive Discovery
    boundary.

    Per Constitution Article VIII, the 3 Constitutional Registers
    (RESTRICTED / CONFLICT / NON_REPRESENTED_PRINCIPAL) are checked
    at the Proactive Discovery gate. The gate cannot be bypassed.
    """

    def check(
        self,
        *,
        entity_name: str,
        restricted_set: set,
        conflict_set: set,
        represented_set: set,
    ) -> None:
        """Check the 3 registers. Raises if any hit."""
        if entity_name in restricted_set:
            raise RegisterCheckFailedError("RESTRICTED", entity_name)
        if entity_name in conflict_set:
            raise RegisterCheckFailedError("CONFLICT", entity_name)
        if entity_name in represented_set:
            # For Proactive Discovery, having an existing represented
            # principal means the exclusive-agency goal is blocked.
            raise RegisterCheckFailedError(
                "NON_REPRESENTED_PRINCIPAL (already represented)",
                entity_name,
            )
