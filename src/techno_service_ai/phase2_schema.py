"""Phase 2 Schema — Constitutional Reference, Industrial Intelligence,
Opportunity Intelligence, Technology Intelligence, Manufacturer
Intelligence, Commercial Intelligence, Registration, Tender, Verification,
Quality, Risk, Security, Knowledge, Approval, Notification, Reporting,
Performance, Cross-Office Collaboration, Logs, Relationship, and the three
Constitutional Registers.

Source of truth: Document 05 — Database and Information Model Design v1.0.

Constitutional principles enforced here:

  - Article XX paragraph 6 / DB-PRIN-018 / DB-PRIN-004 — No Silent Amendment.
    Every constitutional table is protected by BEFORE UPDATE and BEFORE
    DELETE triggers (installed by `db.install_constitutional_triggers`).
    "Update" is implemented by INSERTing a new versioned row.

  - Article XIX / DB-PRIN-014 — Independence of the three Status dimensions.
    The three statuses are stored as INDEPENDENT writeable columns. No
    trigger, view, or computed column couples them.

  - Article VIII / DB-PRIN-013 — Independence of the three Registers.
    Represented Principal, Conflict/Do-Not-Pursue, and Restricted/Prohibited
    are three independent tables. They are NOT views or derived. They
    are not merged.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .constitutional import (
    ApprovalStatus,
    CommercialStatus,
    ConstitutionalMixin,
    IntelligenceStatus,
    _utcnow,
    _uuid,
)
from .schema import Base


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return _utcnow()


# ---------------------------------------------------------------------------
# Three Constitutional Registers (Article VIII)
# ---------------------------------------------------------------------------
# Each register is an INDEPENDENT TABLE. They are not merged, not views,
# not derived. Each entry has its own canonical_id, version, and audit
# fields. All three are constitutional (BEFORE UPDATE/DELETE triggers).


class RegisterStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    REJECTED = "REJECTED"


class RegisterScope(str, enum.Enum):
    GLOBAL = "GLOBAL"
    REGIONAL = "REGIONAL"
    SECTOR = "SECTOR"
    CUSTOMER = "CUSTOMER"
    PRODUCT_LINE = "PRODUCT_LINE"


class RepresentedPrincipal(ConstitutionalMixin, Base):
    """Constitution Article VIII §2 — Represented Principals Register."""

    __tablename__ = "represented_principals_register"
    __constitutional__ = True  # type: ignore[attr-defined]

    manufacturer_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    brand: Mapped[str] = mapped_column(String(255), nullable=False)
    product_line: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    scope: Mapped[str] = mapped_column(String(64), nullable=False, default="GLOBAL")
    effective_from: Mapped[str] = mapped_column(String(64), nullable=False)
    effective_to: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    responsible_human_authority: Mapped[str] = mapped_column(String(64), nullable=False)
    review_date: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    source_citation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class ConflictDoNotPursueEntity(ConstitutionalMixin, Base):
    """Constitution Article VIII §3 — Conflict and Do-Not-Pursue Register."""

    __tablename__ = "conflict_register"
    __constitutional__ = True  # type: ignore[attr-defined]

    entity_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    entity_name: Mapped[str] = mapped_column(String(255), nullable=False)
    conflict_type: Mapped[str] = mapped_column(String(64), nullable=False)
    scope: Mapped[str] = mapped_column(String(64), nullable=False, default="GLOBAL")
    effective_from: Mapped[str] = mapped_column(String(64), nullable=False)
    effective_to: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    responsible_human_authority: Mapped[str] = mapped_column(String(64), nullable=False)
    review_date: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    source_citation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class RestrictedProhibitedEntity(ConstitutionalMixin, Base):
    """Constitution Article VIII §4 — Restricted and Prohibited Entities Register."""

    __tablename__ = "restricted_register"
    __constitutional__ = True  # type: ignore[attr-defined]

    entity_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    entity_name: Mapped[str] = mapped_column(String(255), nullable=False)
    restriction_type: Mapped[str] = mapped_column(String(64), nullable=False)
    scope: Mapped[str] = mapped_column(String(64), nullable=False, default="GLOBAL")
    effective_from: Mapped[str] = mapped_column(String(64), nullable=False)
    effective_to: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    responsible_human_authority: Mapped[str] = mapped_column(String(64), nullable=False)
    review_date: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    source_citation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


# ---------------------------------------------------------------------------
# Information Domain 1 — Constitutional Reference
# ---------------------------------------------------------------------------


class ConstitutionalDocument(ConstitutionalMixin, Base):
    """ENT-CON-001 — Constitution, Charter, Interaction Matrix, Authority
    Matrix, SRS, Architecture, Database Model, Workflow, UI/UX as
    read-only references within the System."""

    __tablename__ = "constitutional_document"
    __constitutional__ = True  # type: ignore[attr-defined]

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    document_code: Mapped[str] = mapped_column(String(64), nullable=False)
    version_label: Mapped[str] = mapped_column(String(32), nullable=False)
    effective_date: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    supersedes_version_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rank: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    checksum: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)


class Office(ConstitutionalMixin, Base):
    """ENT-CON-002 / ENT-HO-001 — Office (the 17 constitutional Offices).

    Phase 1 already used the concept; Phase 2 persists it."""

    __tablename__ = "office"
    __constitutional__ = True  # type: ignore[attr-defined]

    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parent_office_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("office.id"), nullable=True)


class AgentCharter(ConstitutionalMixin, Base):
    """ENT-CON-003 — A Principal Agent's Charter (per Constitution Article XV)."""

    __tablename__ = "agent_charter"
    __constitutional__ = True  # type: ignore[attr-defined]

    agent_code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_functional_domain: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    purpose: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mission: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    office_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("office.id"), nullable=True)


# ---------------------------------------------------------------------------
# Information Domain 4 — Industrial Intelligence
# ---------------------------------------------------------------------------


class IndustrialEnvironmentProfile(ConstitutionalMixin, Base):
    """ENT-IND-ENV-001 — Environmental Profile for a sector or geography."""

    __tablename__ = "industrial_environment_profile"
    __constitutional__ = True  # type: ignore[attr-defined]

    sector: Mapped[str] = mapped_column(String(128), nullable=False)
    geography: Mapped[str] = mapped_column(String(128), nullable=False)
    regulatory_context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    economic_context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sector_structure: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_refreshed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class EnvironmentalUpdate(ConstitutionalMixin, Base):
    """ENT-IND-ENV-002 — A material change in the environment."""

    __tablename__ = "environmental_update"
    __constitutional__ = True  # type: ignore[attr-defined]

    profile_id: Mapped[str] = mapped_column(String(36), ForeignKey("industrial_environment_profile.id"), nullable=False)
    change_description: Mapped[str] = mapped_column(Text, nullable=False)
    effective_date: Mapped[str] = mapped_column(String(64), nullable=False)


class IndustrialActivity(ConstitutionalMixin, Base):
    """ENT-IND-ACT-001 — Detected Industrial Activity (with classification)."""

    __tablename__ = "industrial_activity"
    __constitutional__ = True  # type: ignore[attr-defined]

    sector: Mapped[str] = mapped_column(String(128), nullable=False)
    geography: Mapped[str] = mapped_column(String(128), nullable=False)
    activity_description: Mapped[str] = mapped_column(Text, nullable=False)
    classification: Mapped[str] = mapped_column(String(32), nullable=False)  # Confirmed/Announced/Probable/Speculative
    activity_date: Mapped[str] = mapped_column(String(64), nullable=False)
    speculative: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="CLASSIFIED")
    profile_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("industrial_environment_profile.id"), nullable=True)


class ValidatedSignal(ConstitutionalMixin, Base):
    """ENT-IND-ACT-002 — Activity that has cleared Preliminary Evidence Review."""

    __tablename__ = "validated_signal"
    __constitutional__ = True  # type: ignore[attr-defined]

    activity_id: Mapped[str] = mapped_column(String(36), ForeignKey("industrial_activity.id"), nullable=False)
    preliminary_review_outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    preliminary_reviewer_id: Mapped[str] = mapped_column(String(36), nullable=False)
    preliminary_review_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="VALIDATED")


# ---------------------------------------------------------------------------
# Information Domain 5 — Opportunity Intelligence (with 3 status dimensions)
# ---------------------------------------------------------------------------


class ProblemOrNeed(ConstitutionalMixin, Base):
    """ENT-OPP-001 — Defined Problem or Need."""

    __tablename__ = "problem_or_need"
    __constitutional__ = True  # type: ignore[attr-defined]

    validated_signal_id: Mapped[str] = mapped_column(String(36), ForeignKey("validated_signal.id"), nullable=False)
    problem_description: Mapped[str] = mapped_column(Text, nullable=False)
    stakeholder_attribution: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    definition_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DEFINED")


class RootCause(ConstitutionalMixin, Base):
    """ENT-OPP-002 — Established Root Cause."""

    __tablename__ = "root_cause"
    __constitutional__ = True  # type: ignore[attr-defined]

    problem_id: Mapped[str] = mapped_column(String(36), ForeignKey("problem_or_need.id"), nullable=False)
    root_cause_description: Mapped[str] = mapped_column(Text, nullable=False)
    method_used: Mapped[str] = mapped_column(String(128), nullable=False)
    data_sources: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    alternatives_considered: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    establishment_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ESTABLISHED")


class ValueCase(ConstitutionalMixin, Base):
    """ENT-OPP-003 — Commercial Value Case (baseline, measurement, uncertainty)."""

    __tablename__ = "value_case"
    __constitutional__ = True  # type: ignore[attr-defined]

    root_cause_id: Mapped[str] = mapped_column(String(36), ForeignKey("root_cause.id"), nullable=False)
    value_description: Mapped[str] = mapped_column(Text, nullable=False)
    baseline: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    measurement_method: Mapped[str] = mapped_column(Text, nullable=False)
    assumptions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    uncertainty: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    beneficiary: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="VALUE_HYPOTHESIS")


class Opportunity(ConstitutionalMixin, Base):
    """ENT-OPP-004 — The constitutional root entity.

    Holds the three INDEPENDENT Status dimensions per Constitution Article XIX.
    Each status is its own column; no view, trigger, or computed column
    couples them. This is the canonical proof of DB-PRIN-014 / AC-P2-003.
    """

    __tablename__ = "opportunity"
    __constitutional__ = True  # type: ignore[attr-defined]

    validated_signal_id: Mapped[str] = mapped_column(String(36), ForeignKey("validated_signal.id"), nullable=False)
    opportunity_title: Mapped[str] = mapped_column(String(255), nullable=False)
    creation_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    final_disposition: Mapped[str] = mapped_column(String(32), nullable=False, default="OPEN")
    final_disposition_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # The three INDEPENDENT Status dimensions (Article XIX).
    intelligence_status: Mapped[str] = mapped_column(
        String(64), nullable=False, default=IntelligenceStatus.SIGNAL_DETECTED.value,
    )
    approval_status: Mapped[str] = mapped_column(
        String(64), nullable=False, default=ApprovalStatus.NOT_SUBMITTED.value,
    )
    commercial_status: Mapped[str] = mapped_column(
        String(64), nullable=False, default=CommercialStatus.MANUFACTURER_IDENTIFICATION.value,
    )

    # The Last-Changed tracking for each Status dimension. Each is
    # independent: changing intelligence_status does NOT update the others.
    intelligence_status_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    approval_status_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    commercial_status_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


# ---------------------------------------------------------------------------
# Information Domain 6 — Technology Intelligence
# ---------------------------------------------------------------------------


class TechnologyCategoryAnalysis(ConstitutionalMixin, Base):
    """ENT-TEC-001 — Technology Category Analysis."""

    __tablename__ = "technology_category_analysis"
    __constitutional__ = True  # type: ignore[attr-defined]

    value_case_id: Mapped[str] = mapped_column(String(36), ForeignKey("value_case.id"), nullable=False)
    technology_category: Mapped[str] = mapped_column(String(255), nullable=False)
    category_fit_rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    alternatives_considered: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ISSUED")


class ProductAnalysis(ConstitutionalMixin, Base):
    """ENT-TEC-002 — Product or Solution Analysis."""

    __tablename__ = "product_analysis"
    __constitutional__ = True  # type: ignore[attr-defined]

    technology_category_analysis_id: Mapped[str] = mapped_column(String(36), ForeignKey("technology_category_analysis.id"), nullable=False)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    product_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evaluation_criteria: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    performance_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    standards_and_certifications: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ISSUED")


class ComparativeAnalysis(ConstitutionalMixin, Base):
    """ENT-TEC-003 — Replacement and Comparative Analysis.

    Carries the Value Qualification Rule classification and the Kuwait
    Suitability status. Has its own status dimension; intelligence_status
    defaults to QUALIFIED once Verified.
    """

    __tablename__ = "comparative_analysis"
    __constitutional__ = True  # type: ignore[attr-defined]

    product_analysis_id: Mapped[str] = mapped_column(String(36), ForeignKey("product_analysis.id"), nullable=False)
    current_solution_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    baseline: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    measurement_method: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    comparative_case_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    value_qualification_classification: Mapped[str] = mapped_column(String(64), nullable=False, default="UNVERIFIED_VALUE_HYPOTHESIS")
    assumptions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    uncertainty: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    twenty_five_percent_threshold_result: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    strategic_exception_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="UNVERIFIED_VALUE_HYPOTHESIS")
    # The Opportunity status mirror — this entity has its own intelligence
    # status, INDEPENDENT of the parent Opportunity's status.
    intelligence_status: Mapped[str] = mapped_column(
        String(64), nullable=False, default=IntelligenceStatus.UNDER_INVESTIGATION.value,
    )
    approval_status: Mapped[str] = mapped_column(
        String(64), nullable=False, default=ApprovalStatus.NOT_SUBMITTED.value,
    )
    commercial_status: Mapped[str] = mapped_column(
        String(64), nullable=False, default=CommercialStatus.MANUFACTURER_IDENTIFICATION.value,
    )


class KuwaitSuitabilityReview(ConstitutionalMixin, Base):
    """ENT-TEC-004 — Kuwait Suitability Review."""

    __tablename__ = "kuwait_suitability_review"
    __constitutional__ = True  # type: ignore[attr-defined]

    comparative_analysis_id: Mapped[str] = mapped_column(String(36), ForeignKey("comparative_analysis.id"), nullable=False)
    suitability_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    standards_and_certifications: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    environmental_assessment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    suitability_gap: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    gap_resolution_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="CLEARED")


# ---------------------------------------------------------------------------
# Information Domain 7 — Manufacturer Intelligence
# ---------------------------------------------------------------------------


class ManufacturerProfile(ConstitutionalMixin, Base):
    """ENT-MAN-001 — Manufacturer Profile."""

    __tablename__ = "manufacturer_profile"
    __constitutional__ = True  # type: ignore[attr-defined]

    manufacturer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    ownership: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    certifications: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    production_capacity: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    references: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    quality_indicators: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    after_sales_capability: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    global_reputation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    profile_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    register_reference: Mapped[str] = mapped_column(String(64), nullable=False, default="UNRESOLVED")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class ManufacturerCredibilityAssessment(ConstitutionalMixin, Base):
    """ENT-MAN-002 — Multi-dimensional Credibility Assessment."""

    __tablename__ = "manufacturer_credibility_assessment"
    __constitutional__ = True  # type: ignore[attr-defined]

    manufacturer_id: Mapped[str] = mapped_column(String(36), ForeignKey("manufacturer_profile.id"), nullable=False)
    financial_stability: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    quality_systems: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    delivery_track_record: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    after_sales_capability: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    references: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    reputation: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    assessment_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    overall_classification: Mapped[str] = mapped_column(String(32), nullable=False, default="UNVERIFIED")


class ManufacturerComparisonReport(ConstitutionalMixin, Base):
    """ENT-MAN-003 — Manufacturer Comparison Report (per Opportunity)."""

    __tablename__ = "manufacturer_comparison_report"
    __constitutional__ = True  # type: ignore[attr-defined]

    opportunity_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    comparison_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recommended_manufacturer_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("manufacturer_profile.id"), nullable=True)
    recommended_manufacturer_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    comparison_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


# ---------------------------------------------------------------------------
# Information Domain 8 — Commercial Intelligence
# ---------------------------------------------------------------------------


class CommercialEvaluation(ConstitutionalMixin, Base):
    """ENT-COM-001 — Commercial Evaluation (CommercialEvaluation)."""

    __tablename__ = "commercial_evaluation"
    __constitutional__ = True  # type: ignore[attr-defined]

    opportunity_id: Mapped[str] = mapped_column(String(36), ForeignKey("opportunity.id"), nullable=False)
    commercial_case_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    margin_estimate: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    pricing_basis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evaluation_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ISSUED")


class CommercialModelOption(ConstitutionalMixin, Base):
    """ENT-COM-002 — Commercial Model Option (representation, distribution, etc.)."""

    __tablename__ = "commercial_model_option"
    __constitutional__ = True  # type: ignore[attr-defined]

    opportunity_id: Mapped[str] = mapped_column(String(36), ForeignKey("opportunity.id"), nullable=False)
    model_type: Mapped[str] = mapped_column(String(64), nullable=False)
    model_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    selected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class BusinessDevelopmentEngagement(ConstitutionalMixin, Base):
    """ENT-COM-003 — Business Development Engagement record."""

    __tablename__ = "business_development_engagement"
    __constitutional__ = True  # type: ignore[attr-defined]

    opportunity_id: Mapped[str] = mapped_column(String(36), ForeignKey("opportunity.id"), nullable=False)
    engagement_type: Mapped[str] = mapped_column(String(64), nullable=False)
    counterpart: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    engagement_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class NegotiationAnalysis(ConstitutionalMixin, Base):
    """ENT-COM-004 — Negotiation Analysis."""

    __tablename__ = "negotiation_analysis"
    __constitutional__ = True  # type: ignore[attr-defined]

    opportunity_id: Mapped[str] = mapped_column(String(36), ForeignKey("opportunity.id"), nullable=False)
    scenario: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    constraints: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    analysis_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PricingAnalysis(ConstitutionalMixin, Base):
    """ENT-COM-005 — Pricing Analysis."""

    __tablename__ = "pricing_analysis"
    __constitutional__ = True  # type: ignore[attr-defined]

    opportunity_id: Mapped[str] = mapped_column(String(36), ForeignKey("opportunity.id"), nullable=False)
    pricing_basis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    margin_scenarios: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    analysis_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AfterSalesIntelligenceReport(ConstitutionalMixin, Base):
    """ENT-COM-006 — After-Sales Intelligence Report."""

    __tablename__ = "after_sales_intelligence_report"
    __constitutional__ = True  # type: ignore[attr-defined]

    opportunity_id: Mapped[str] = mapped_column(String(36), ForeignKey("opportunity.id"), nullable=False)
    report_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recurring_opportunity_identification: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


# ---------------------------------------------------------------------------
# Information Domain 9 — Registration and Market Entry
# ---------------------------------------------------------------------------


class RegistrationStatusReport(ConstitutionalMixin, Base):
    """ENT-REG-001 — Registration Status Report."""

    __tablename__ = "registration_status_report"
    __constitutional__ = True  # type: ignore[attr-defined]

    opportunity_id: Mapped[str] = mapped_column(String(36), ForeignKey("opportunity.id"), nullable=False)
    registration_type: Mapped[str] = mapped_column(String(64), nullable=False)
    authority: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class RegistrationDossier(ConstitutionalMixin, Base):
    """ENT-REG-002 — Registration Dossier (the supporting evidence)."""

    __tablename__ = "registration_dossier"
    __constitutional__ = True  # type: ignore[attr-defined]

    registration_status_report_id: Mapped[str] = mapped_column(String(36), ForeignKey("registration_status_report.id"), nullable=False)
    document_type: Mapped[str] = mapped_column(String(64), nullable=False)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class PrequalificationStatusReport(ConstitutionalMixin, Base):
    """ENT-REG-003 — Prequalification Status Report."""

    __tablename__ = "prequalification_status_report"
    __constitutional__ = True  # type: ignore[attr-defined]

    opportunity_id: Mapped[str] = mapped_column(String(36), ForeignKey("opportunity.id"), nullable=False)
    authority: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class ApprovedVendorListStatusReport(ConstitutionalMixin, Base):
    """ENT-REG-004 — Approved Vendor List Status Report (Phase 2 mapping
    for canonical ENT-REG-003)."""

    __tablename__ = "approved_vendor_list_status_report"
    __constitutional__ = True  # type: ignore[attr-defined]

    opportunity_id: Mapped[str] = mapped_column(String(36), ForeignKey("opportunity.id"), nullable=False)
    authority: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    renewal_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class MarketEntryOptionsReport(ConstitutionalMixin, Base):
    """ENT-REG-005 — Market Entry Options Report (Phase 5 addition).

    Per Document 05 §3.9 (canonical ENT-REG-004) and Document 02 §4.7.3
    (Market Entry Strategy Agent). The report is the Output of Stage 18
    (Market Entry). It records the multi-path options set, the
    stakeholder map, and the risk map. The Agent does NOT select a
    path; selection is a Human Approval decision.

    This entity was missing from the Phase 2 implementation (it was
    declared in Document 05 but not added to the schema). It is
    constitutional — append-only via the BEFORE UPDATE/DELETE triggers
    installed by `db.install_constitutional_triggers`.
    """

    __tablename__ = "market_entry_options_report"
    __constitutional__ = True  # type: ignore[attr-defined]

    opportunity_id: Mapped[str] = mapped_column(String(36), ForeignKey("opportunity.id"), nullable=False)
    manufacturer_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("manufacturer_profile.id"), nullable=True)
    options_set: Mapped[str] = mapped_column(Text, nullable=False)  # JSON-encoded list of path options
    stakeholder_map: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    risk_map: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    selected_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Set only by Human Approval
    report_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_citation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


# ---------------------------------------------------------------------------
# Information Domain 10 — Tender and Project
# ---------------------------------------------------------------------------


class Tender(ConstitutionalMixin, Base):
    """ENT-TEN-001 — Tender record."""

    __tablename__ = "tender"
    __constitutional__ = True  # type: ignore[attr-defined]

    opportunity_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("opportunity.id"), nullable=True)
    tender_reference: Mapped[str] = mapped_column(String(128), nullable=False)
    issuer: Mapped[str] = mapped_column(String(255), nullable=False)
    issue_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closing_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="OPEN")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class TenderQualificationReport(ConstitutionalMixin, Base):
    """ENT-TEN-002 — Tender Qualification Report."""

    __tablename__ = "tender_qualification_report"
    __constitutional__ = True  # type: ignore[attr-defined]

    tender_id: Mapped[str] = mapped_column(String(36), ForeignKey("tender.id"), nullable=False)
    qualification_outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    report_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class QuotationDossier(ConstitutionalMixin, Base):
    """ENT-TEN-003 — Quotation Dossier / Tender Submission Dossier."""

    __tablename__ = "quotation_dossier"
    __constitutional__ = True  # type: ignore[attr-defined]

    tender_id: Mapped[str] = mapped_column(String(36), ForeignKey("tender.id"), nullable=False)
    document_type: Mapped[str] = mapped_column(String(64), nullable=False)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    submission_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class ProjectStatusReport(ConstitutionalMixin, Base):
    """ENT-TEN-004 — Project Status Report."""

    __tablename__ = "project_status_report"
    __constitutional__ = True  # type: ignore[attr-defined]

    opportunity_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("opportunity.id"), nullable=True)
    project_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="AWARDED")
    issues: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


# ---------------------------------------------------------------------------
# Information Domain 11 — Verification
# ---------------------------------------------------------------------------


class PreliminaryReview(ConstitutionalMixin, Base):
    """ENT-VER-001 — Preliminary Evidence Review record."""

    __tablename__ = "preliminary_review"
    __constitutional__ = True  # type: ignore[attr-defined]

    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    reviewer_id: Mapped[str] = mapped_column(String(36), nullable=False)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    review_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SpecialistVerification(ConstitutionalMixin, Base):
    """ENT-VER-002 — Specialist Verification record."""

    __tablename__ = "specialist_verification"
    __constitutional__ = True  # type: ignore[attr-defined]

    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    specialist_id: Mapped[str] = mapped_column(String(36), nullable=False)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    review_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class IndependentFinalVerification(ConstitutionalMixin, Base):
    """ENT-VER-003 — Independent Final Verification record."""

    __tablename__ = "independent_final_verification"
    __constitutional__ = True  # type: ignore[attr-defined]

    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    verifier_id: Mapped[str] = mapped_column(String(36), nullable=False)
    # Producer-Verifier Independence per Article XVII.
    producer_id: Mapped[str] = mapped_column(String(36), nullable=False)
    independence_asserted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    review_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SecondReviewerVerification(ConstitutionalMixin, Base):
    """ENT-VER-004 — Second Reviewer for material claims."""

    __tablename__ = "second_reviewer_verification"
    __constitutional__ = True  # type: ignore[attr-defined]

    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    second_reviewer_id: Mapped[str] = mapped_column(String(36), nullable=False)
    primary_reviewer_id: Mapped[str] = mapped_column(String(36), nullable=False)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    review_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ClaimClassification(ConstitutionalMixin, Base):
    """ENT-VER-005 — Claim Classification (Verified Fact / Supported Estimate / ...)."""

    __tablename__ = "claim_classification"
    __constitutional__ = True  # type: ignore[attr-defined]

    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    classification: Mapped[str] = mapped_column(String(32), nullable=False)  # VERIFIED_FACT, SUPPORTED_ESTIMATE, ...
    target_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    target_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    classifier_id: Mapped[str] = mapped_column(String(36), nullable=False)
    classification_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class VerificationIndependenceTracker(ConstitutionalMixin, Base):
    """ENT-VER-006 — Producer-Verifier Independence tracker."""

    __tablename__ = "verification_independence_tracker"
    __constitutional__ = True  # type: ignore[attr-defined]

    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    producer_id: Mapped[str] = mapped_column(String(36), nullable=False)
    verifier_id: Mapped[str] = mapped_column(String(36), nullable=False)
    independence_status: Mapped[str] = mapped_column(String(32), nullable=False, default="ASSERTED")


class EvidenceItem(ConstitutionalMixin, Base):
    """ENT-VER-007 — Evidence Item (a Source / Citation / Evidence record)."""

    __tablename__ = "evidence_item"
    __constitutional__ = True  # type: ignore[attr-defined]

    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    evidence_type: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_citation: Mapped[str] = mapped_column(Text, nullable=False)
    collected_by: Mapped[str] = mapped_column(String(36), nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


# ---------------------------------------------------------------------------
# Information Domain 12 — Quality Assurance
# ---------------------------------------------------------------------------


class QualityReview(ConstitutionalMixin, Base):
    """ENT-QA-001 — Quality Review record."""

    __tablename__ = "quality_review"
    __constitutional__ = True  # type: ignore[attr-defined]

    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    reviewer_id: Mapped[str] = mapped_column(String(36), nullable=False)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    review_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class StandardsComplianceReport(ConstitutionalMixin, Base):
    """ENT-QA-002 — Standards Compliance Report."""

    __tablename__ = "standards_compliance_report"
    __constitutional__ = True  # type: ignore[attr-defined]

    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    standard: Mapped[str] = mapped_column(String(255), nullable=False)
    compliance_status: Mapped[str] = mapped_column(String(32), nullable=False)
    report_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


# ---------------------------------------------------------------------------
# Information Domain 13 — Risk and Compliance
# ---------------------------------------------------------------------------


class EnterpriseRisk(ConstitutionalMixin, Base):
    """ENT-RIS-001 — Enterprise Risk."""

    __tablename__ = "enterprise_risk"
    __constitutional__ = True  # type: ignore[attr-defined]

    risk_category: Mapped[str] = mapped_column(String(64), nullable=False)  # Strategic/Commercial/Technical/Operational/Regulatory/Cyber/Reputational
    risk_description: Mapped[str] = mapped_column(Text, nullable=False)
    impact: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    likelihood: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    mitigation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    review_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="OPEN")


class ComplianceReviewReport(ConstitutionalMixin, Base):
    """ENT-RIS-002 — Compliance Review Report."""

    __tablename__ = "compliance_review_report"
    __constitutional__ = True  # type: ignore[attr-defined]

    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    reviewer_id: Mapped[str] = mapped_column(String(36), nullable=False)
    compliance_status: Mapped[str] = mapped_column(String(32), nullable=False)
    findings: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    review_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ConstitutionalIncident(ConstitutionalMixin, Base):
    """ENT-RIS-003 — Constitutional Incident record."""

    __tablename__ = "constitutional_incident"
    __constitutional__ = True  # type: ignore[attr-defined]

    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    reported_by: Mapped[str] = mapped_column(String(36), nullable=False)
    remediation_plan: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="OPEN")


class RegisterEntryCrossReference(ConstitutionalMixin, Base):
    """ENT-RIS-004 — Cross-reference between an entity and a register entry."""

    __tablename__ = "register_entry_cross_reference"
    __constitutional__ = True  # type: ignore[attr-defined]

    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    register_type: Mapped[str] = mapped_column(String(32), nullable=False)  # REPRESENTED / CONFLICT / RESTRICTED
    register_entry_id: Mapped[str] = mapped_column(String(36), nullable=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_to: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


# ---------------------------------------------------------------------------
# Information Domain 14 — Security and Data Governance
# ---------------------------------------------------------------------------


class SecurityEvent(ConstitutionalMixin, Base):
    """ENT-SEC-001 — Security Event record."""

    __tablename__ = "security_event"
    __constitutional__ = True  # type: ignore[attr-defined]

    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    target_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    target_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    detected_by: Mapped[str] = mapped_column(String(36), nullable=False)
    event_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AccessControlEntry(ConstitutionalMixin, Base):
    """ENT-SEC-002 — Access Control Entry."""

    __tablename__ = "access_control_entry"
    __constitutional__ = True  # type: ignore[attr-defined]

    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    subject_type: Mapped[str] = mapped_column(String(64), nullable=False)  # USER, AGENT
    subject_id: Mapped[str] = mapped_column(String(36), nullable=False)
    permission: Mapped[str] = mapped_column(String(64), nullable=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_to: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class ContinuityPlan(ConstitutionalMixin, Base):
    """ENT-SEC-003 — Continuity Plan."""

    __tablename__ = "continuity_plan"
    __constitutional__ = True  # type: ignore[attr-defined]

    plan_name: Mapped[str] = mapped_column(String(255), nullable=False)
    rto_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Recovery Time Objective
    rpo_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Recovery Point Objective
    scope: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_tested_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class RecoveryTestReport(ConstitutionalMixin, Base):
    """ENT-SEC-004 — Recovery Test Report."""

    __tablename__ = "recovery_test_report"
    __constitutional__ = True  # type: ignore[attr-defined]

    continuity_plan_id: Mapped[str] = mapped_column(String(36), ForeignKey("continuity_plan.id"), nullable=False)
    test_outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    findings: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    test_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RecoveryReport(ConstitutionalMixin, Base):
    """ENT-SEC-005 — Recovery Report (when recovery was actually invoked)."""

    __tablename__ = "recovery_report"
    __constitutional__ = True  # type: ignore[attr-defined]

    continuity_plan_id: Mapped[str] = mapped_column(String(36), ForeignKey("continuity_plan.id"), nullable=False)
    recovery_outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recovery_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ContinuityEvent(ConstitutionalMixin, Base):
    """ENT-SEC-006 — Continuity Event (an incident that triggered continuity)."""

    __tablename__ = "continuity_event"
    __constitutional__ = True  # type: ignore[attr-defined]

    continuity_plan_id: Mapped[str] = mapped_column(String(36), ForeignKey("continuity_plan.id"), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    event_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AgentIdentity(ConstitutionalMixin, Base):
    """ENT-SEC-007 — An AI Agent's identity record (per Article XIV/XV)."""

    __tablename__ = "agent_identity"
    __constitutional__ = True  # type: ignore[attr-defined]

    agent_code: Mapped[str] = mapped_column(String(64), nullable=False)
    agent_name: Mapped[str] = mapped_column(String(255), nullable=False)
    charter_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("agent_charter.id"), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class AccessAuditReport(ConstitutionalMixin, Base):
    """ENT-SEC-008 — Access Audit Report (periodic review of who accessed what)."""

    __tablename__ = "access_audit_report"
    __constitutional__ = True  # type: ignore[attr-defined]

    report_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    report_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    findings: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    produced_by: Mapped[str] = mapped_column(String(36), nullable=False)


class DataClassificationEntry(ConstitutionalMixin, Base):
    """ENT-SEC-009 — Data Classification Entry (Confidentiality / Integrity / Availability)."""

    __tablename__ = "data_classification_entry"
    __constitutional__ = True  # type: ignore[attr-defined]

    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    confidentiality: Mapped[str] = mapped_column(String(32), nullable=False, default="INTERNAL")
    integrity: Mapped[str] = mapped_column(String(32), nullable=False, default="STANDARD")
    availability: Mapped[str] = mapped_column(String(32), nullable=False, default="STANDARD")


# ---------------------------------------------------------------------------
# Information Domain 15 — Knowledge and Institutional Memory
# ---------------------------------------------------------------------------


class KnowledgeRecord(ConstitutionalMixin, Base):
    """ENT-KNO-001 — Knowledge Base Record."""

    __tablename__ = "knowledge_record"
    __constitutional__ = True  # type: ignore[attr-defined]

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    domain: Mapped[str] = mapped_column(String(64), nullable=False)
    tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    quality_status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")


class LessonLearned(ConstitutionalMixin, Base):
    """ENT-KNO-002 — Lesson Learned."""

    __tablename__ = "lesson_learned"
    __constitutional__ = True  # type: ignore[attr-defined]

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)  # Won, Lost, On Hold, etc.
    target_opportunity_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("opportunity.id"), nullable=True)


class InstitutionalMemoryIndex(ConstitutionalMixin, Base):
    """ENT-KNO-003 — Institutional Memory Index entry."""

    __tablename__ = "institutional_memory_index"
    __constitutional__ = True  # type: ignore[attr-defined]

    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    retention_class: Mapped[str] = mapped_column(String(32), nullable=False, default="PERMANENT")
    retention_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class KnowledgeBaseInventory(ConstitutionalMixin, Base):
    """ENT-KNO-004 — Knowledge Base Inventory entry (catalog of knowledge records)."""

    __tablename__ = "knowledge_base_inventory"
    __constitutional__ = True  # type: ignore[attr-defined]

    knowledge_record_id: Mapped[str] = mapped_column(String(36), ForeignKey("knowledge_record.id"), nullable=False)
    classification: Mapped[str] = mapped_column(String(32), nullable=False, default="INTERNAL")
    review_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


# ---------------------------------------------------------------------------
# Information Domain 16 — Approval and Decision
# ---------------------------------------------------------------------------


class ApprovalRequest(ConstitutionalMixin, Base):
    """ENT-APR-001 — Approval Request."""

    __tablename__ = "approval_request"
    __constitutional__ = True  # type: ignore[attr-defined]

    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    decision_class: Mapped[int] = mapped_column(Integer, nullable=False)  # 1, 2, 3, 4
    required_approver_role_code: Mapped[str] = mapped_column(String(64), nullable=False)
    requester_id: Mapped[str] = mapped_column(String(36), nullable=False)
    request_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")


class ApprovalPackage(ConstitutionalMixin, Base):
    """ENT-APR-002 — Approval Package (the material that goes to the approver)."""

    __tablename__ = "approval_package"
    __constitutional__ = True  # type: ignore[attr-defined]

    approval_request_id: Mapped[str] = mapped_column(String(36), ForeignKey("approval_request.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    attached_evidence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class ApprovalDecision(ConstitutionalMixin, Base):
    """ENT-APR-003 — Approval Decision (APPROVED / REJECTED / CONDITIONAL)."""

    __tablename__ = "approval_decision"
    __constitutional__ = True  # type: ignore[attr-defined]

    approval_request_id: Mapped[str] = mapped_column(String(36), ForeignKey("approval_request.id"), nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)  # APPROVED, REJECTED, CONDITIONAL
    approver_id: Mapped[str] = mapped_column(String(36), nullable=False)
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decision_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ApprovalAuthority(ConstitutionalMixin, Base):
    """ENT-APR-004 — The Authority that may approve a Decision Class."""

    __tablename__ = "approval_authority"
    __constitutional__ = True  # type: ignore[attr-defined]

    role_code: Mapped[str] = mapped_column(String(64), nullable=False)
    decision_class: Mapped[int] = mapped_column(Integer, nullable=False)
    authority_scope: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class StandingAuthorisation(ConstitutionalMixin, Base):
    """ENT-APR-005 — Standing Authorisation (a pre-approved, narrow, revocable)."""

    __tablename__ = "standing_authorisation"
    __constitutional__ = True  # type: ignore[attr-defined]

    role_code: Mapped[str] = mapped_column(String(64), nullable=False)
    scope: Mapped[str] = mapped_column(Text, nullable=False)
    recipients: Mapped[str] = mapped_column(Text, nullable=False)
    approved_content: Mapped[str] = mapped_column(Text, nullable=False)
    duration: Mapped[str] = mapped_column(String(64), nullable=False)
    responsible_human_owner: Mapped[str] = mapped_column(String(36), nullable=False)
    revocation_conditions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class EmergencyApproval(ConstitutionalMixin, Base):
    """ENT-APR-006 — Emergency Approval (time-limited, per Article XXIX §6)."""

    __tablename__ = "emergency_approval"
    __constitutional__ = True  # type: ignore[attr-defined]

    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    approver_id: Mapped[str] = mapped_column(String(36), nullable=False)
    justification: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    review_status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")


class ConditionalApproval(ConstitutionalMixin, Base):
    """ENT-APR-007 — Conditional Approval."""

    __tablename__ = "conditional_approval"
    __constitutional__ = True  # type: ignore[attr-defined]

    approval_decision_id: Mapped[str] = mapped_column(String(36), ForeignKey("approval_decision.id"), nullable=False)
    conditions: Mapped[str] = mapped_column(Text, nullable=False)
    satisfaction_status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")


class ApprovalRevocation(ConstitutionalMixin, Base):
    """ENT-APR-008 — Approval Revocation."""

    __tablename__ = "approval_revocation"
    __constitutional__ = True  # type: ignore[attr-defined]

    approval_decision_id: Mapped[str] = mapped_column(String(36), ForeignKey("approval_decision.id"), nullable=False)
    revoker_id: Mapped[str] = mapped_column(String(36), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    revoked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


# ---------------------------------------------------------------------------
# Information Domain 17 — Notification
# ---------------------------------------------------------------------------


class NotificationRecord(ConstitutionalMixin, Base):
    """ENT-NOT-001 — Notification."""

    __tablename__ = "notification_record"
    __constitutional__ = True  # type: ignore[attr-defined]

    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)  # Alert/Approval/Escalation/...
    channel: Mapped[str] = mapped_column(String(32), nullable=False)  # in-app/push/email/SMS/voice
    recipient_id: Mapped[str] = mapped_column(String(36), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class NotificationChannel(ConstitutionalMixin, Base):
    """ENT-NOT-002 — A delivery channel."""

    __tablename__ = "notification_channel"
    __constitutional__ = True  # type: ignore[attr-defined]

    channel_code: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class NotificationPreference(ConstitutionalMixin, Base):
    """ENT-NOT-003 — A recipient's notification preferences."""

    __tablename__ = "notification_preference"
    __constitutional__ = True  # type: ignore[attr-defined]

    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


# ---------------------------------------------------------------------------
# Information Domain 18 — Reporting
# ---------------------------------------------------------------------------


class Report(ConstitutionalMixin, Base):
    """ENT-REP-001 — Report."""

    __tablename__ = "report"
    __constitutional__ = True  # type: ignore[attr-defined]

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    report_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    target_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    constitutional_compliance_attested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    claim_classification: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    produced_by: Mapped[str] = mapped_column(String(36), nullable=False)


class ReportTemplate(ConstitutionalMixin, Base):
    """ENT-REP-002 — Report Template."""

    __tablename__ = "report_template"
    __constitutional__ = True  # type: ignore[attr-defined]

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    template_body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class ReportExportRecord(ConstitutionalMixin, Base):
    """ENT-REP-003 — Report Export record."""

    __tablename__ = "report_export_record"
    __constitutional__ = True  # type: ignore[attr-defined]

    report_id: Mapped[str] = mapped_column(String(36), ForeignKey("report.id"), nullable=False)
    format: Mapped[str] = mapped_column(String(32), nullable=False)  # PDF, Excel, etc.
    exported_by: Mapped[str] = mapped_column(String(36), nullable=False)


class BoardReport(ConstitutionalMixin, Base):
    """ENT-REP-004 — Board Report (a special report with stricter access)."""

    __tablename__ = "board_report"
    __constitutional__ = True  # type: ignore[attr-defined]

    report_id: Mapped[str] = mapped_column(String(36), ForeignKey("report.id"), nullable=False)
    board_meeting_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


# ---------------------------------------------------------------------------
# Information Domain 19 — Performance and Learning
# ---------------------------------------------------------------------------


class PerformanceRecord(ConstitutionalMixin, Base):
    """ENT-PER-001 — Performance Record."""

    __tablename__ = "performance_record"
    __constitutional__ = True  # type: ignore[attr-defined]

    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(64), nullable=False)
    metric_value: Mapped[str] = mapped_column(String(64), nullable=False)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CommercialOutcomeReport(ConstitutionalMixin, Base):
    """ENT-PER-002 — Commercial Outcome Report."""

    __tablename__ = "commercial_outcome_report"
    __constitutional__ = True  # type: ignore[attr-defined]

    opportunity_id: Mapped[str] = mapped_column(String(36), ForeignKey("opportunity.id"), nullable=False)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)  # Won/Lost/Closed
    revenue: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    margin: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    lessons_learned: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class LearningUpdate(ConstitutionalMixin, Base):
    """ENT-PER-003 — Learning Update (with constitutional-impact flag)."""

    __tablename__ = "learning_update"
    __constitutional__ = True  # type: ignore[attr-defined]

    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    constitutional_impact: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    approved_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    audit_inputs: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


# ---------------------------------------------------------------------------
# Information Domain 20 — Cross-Office Collaboration
# ---------------------------------------------------------------------------


class HandoffRecord(ConstitutionalMixin, Base):
    """ENT-COLLAB-001 — Cross-Office Handoff."""

    __tablename__ = "handoff_record"
    __constitutional__ = True  # type: ignore[attr-defined]

    from_office_id: Mapped[str] = mapped_column(String(36), ForeignKey("office.id"), nullable=False)
    to_office_id: Mapped[str] = mapped_column(String(36), ForeignKey("office.id"), nullable=False)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    handoff_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class EscalationRecord(ConstitutionalMixin, Base):
    """ENT-COLLAB-002 — Cross-Office Escalation."""

    __tablename__ = "escalation_record"
    __constitutional__ = True  # type: ignore[attr-defined]

    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    from_office_id: Mapped[str] = mapped_column(String(36), ForeignKey("office.id"), nullable=False)
    to_office_id: Mapped[str] = mapped_column(String(36), ForeignKey("office.id"), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    escalated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


# ---------------------------------------------------------------------------
# Information Domain 3 — Audit (high-level Decision / Handoff / Escalation logs)
# ---------------------------------------------------------------------------
# Per Document 05 Section 3, ENT-LOG-001..003 are the Decision, Handoff,
# and Escalation Logs. These are the business-level logs; the granular
# AuditLog (Constitution Article XX) lives in `schema.py`.


class DecisionLogEntry(ConstitutionalMixin, Base):
    """ENT-LOG-001 — Decision Log Entry (a business-level decision).

    Phase 6 reconciliation (closes GAP-PHASE5-001):
    - decision_class is now a String (was Integer). The LogService
      passes the canonical class names ('CLASS_1'..'CLASS_4'); the
      schema now accepts them directly. The Integer-to-String
      transition is backward-compatible (no existing data is
      invalidated because the field is part of a constitutional
      append-only table — there are no UPDATE statements that would
      break).
    - Added 7 LogService fields: decision_summary, decided_by_role,
      material_canonical_id, opportunity_canonical_id, rationale,
      conditions, related_approval_id. All nullable so the schema
      remains backward-compatible.
    """

    __tablename__ = "decision_log_entry"
    __constitutional__ = True  # type: ignore[attr-defined]

    # Legacy / canonical schema fields (Phase 2).
    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    decision_class: Mapped[str] = mapped_column(String(16), nullable=False)
    decision: Mapped[str] = mapped_column(Text, nullable=False)
    decided_by: Mapped[str] = mapped_column(String(36), nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Phase 6 reconciliation: LogService fields (nullable for
    # backward compatibility with Phase 2/3 writers).
    decision_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decided_by_role: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    material_canonical_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    opportunity_canonical_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    conditions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    related_approval_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)


class HandoffLogEntry(ConstitutionalMixin, Base):
    """ENT-LOG-002 — Handoff Log Entry (business-level handoff)."""

    __tablename__ = "handoff_log_entry"
    __constitutional__ = True  # type: ignore[attr-defined]

    handoff_id: Mapped[str] = mapped_column(String(36), ForeignKey("handoff_record.id"), nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class EscalationLogEntry(ConstitutionalMixin, Base):
    """ENT-LOG-003 — Escalation Log Entry (business-level escalation)."""

    __tablename__ = "escalation_log_entry"
    __constitutional__ = True  # type: ignore[attr-defined]

    escalation_id: Mapped[str] = mapped_column(String(36), ForeignKey("escalation_record.id"), nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


# ---------------------------------------------------------------------------
# Information Domain 1 (relationship sub-domain) — ENT-REL-001..010
# ---------------------------------------------------------------------------


class CustomerProfile(ConstitutionalMixin, Base):
    """ENT-REL-001 — Customer Profile."""

    __tablename__ = "customer_profile"
    __constitutional__ = True  # type: ignore[attr-defined]

    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    sector: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    geography: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class PartnerProfile(ConstitutionalMixin, Base):
    """ENT-REL-002 — Partner Profile."""

    __tablename__ = "partner_profile"
    __constitutional__ = True  # type: ignore[attr-defined]

    partner_name: Mapped[str] = mapped_column(String(255), nullable=False)
    partner_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class GovernmentEntityProfile(ConstitutionalMixin, Base):
    """ENT-REL-003 — Government Entity Profile."""

    __tablename__ = "government_entity_profile"
    __constitutional__ = True  # type: ignore[attr-defined]

    entity_name: Mapped[str] = mapped_column(String(255), nullable=False)
    jurisdiction: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)


class ContractorProfile(ConstitutionalMixin, Base):
    """ENT-REL-004 — Contractor Profile."""

    __tablename__ = "contractor_profile"
    __constitutional__ = True  # type: ignore[attr-defined]

    contractor_name: Mapped[str] = mapped_column(String(255), nullable=False)
    specialty: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)


class CounterpartContact(ConstitutionalMixin, Base):
    """ENT-REL-005 — Counterpart Contact with Disclosure Permission."""

    __tablename__ = "counterpart_contact"
    __constitutional__ = True  # type: ignore[attr-defined]

    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    contact_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    disclosure_permission: Mapped[str] = mapped_column(String(32), nullable=False, default="INTERNAL_ONLY")


class RelationshipInteraction(ConstitutionalMixin, Base):
    """ENT-REL-006 — Relationship Interaction (a logged interaction)."""

    __tablename__ = "relationship_interaction"
    __constitutional__ = True  # type: ignore[attr-defined]

    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    interaction_type: Mapped[str] = mapped_column(String(64), nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    interaction_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DisclosurePermission(ConstitutionalMixin, Base):
    """ENT-REL-007 — Disclosure Permission."""

    __tablename__ = "disclosure_permission"
    __constitutional__ = True  # type: ignore[attr-defined]

    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    permission: Mapped[str] = mapped_column(String(32), nullable=False)


class CustomerRelationshipHistory(ConstitutionalMixin, Base):
    """ENT-REL-008 — Customer Relationship History."""

    __tablename__ = "customer_relationship_history"
    __constitutional__ = True  # type: ignore[attr-defined]

    customer_id: Mapped[str] = mapped_column(String(36), ForeignKey("customer_profile.id"), nullable=False)
    event: Mapped[str] = mapped_column(String(64), nullable=False)
    event_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PartnerRelationshipHistory(ConstitutionalMixin, Base):
    """ENT-REL-009 — Partner Relationship History."""

    __tablename__ = "partner_relationship_history"
    __constitutional__ = True  # type: ignore[attr-defined]

    partner_id: Mapped[str] = mapped_column(String(36), ForeignKey("partner_profile.id"), nullable=False)
    event: Mapped[str] = mapped_column(String(64), nullable=False)
    event_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ManufacturerRelationshipRecord(ConstitutionalMixin, Base):
    """ENT-REL-010 — Manufacturer Relationship Record."""

    __tablename__ = "manufacturer_relationship_record"
    __constitutional__ = True  # type: ignore[attr-defined]

    manufacturer_id: Mapped[str] = mapped_column(String(36), ForeignKey("manufacturer_profile.id"), nullable=False)
    event: Mapped[str] = mapped_column(String(64), nullable=False)
    event_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
