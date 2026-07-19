"""10 Principal Agents — Document 02 §4.2, 4.3, 4.4.

Phase 4 activates the 10 Principal Agents of the first three
Intelligence Offices:

  Industrial Intelligence Office (§4.2, 3 agents)
    - 4.2.1 Industrial Environment Monitor Agent
    - 4.2.2 Industrial Activity Detection Agent
    - 4.2.3 Validated Signal Agent

  Opportunity Intelligence Office (§4.3, 3 agents)
    - 4.3.1 Problem and Need Definition Agent
    - 4.3.2 Root Cause Analysis Agent
    - 4.3.3 Commercial Value Definition Agent

  Technology Intelligence Office (§4.4, 4 agents)
    - 4.4.1 Technology Category Analyst Agent
    - 4.4.2 Product Analyst Agent
    - 4.4.3 Replacement and Comparative Analysis Agent
    - 4.4.4 Kuwait Suitability Reviewer Agent

Each agent wraps the WorkflowService methods. The agents are the
PRODUCERS; the Verification Office is the VERIFIER (producer != verifier
is enforced).

Constitutional source:
  - Constitution Article VI (Discovery Order)
  - Document 02 §4.2, §4.3, §4.4
  - Document 06 §2.1..2.24 (24 Stages)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .services import WorkflowService
from .vqr import (
    ImprovementEvidence,
    VQRClassification,
    VQRDimension,
)


# ---------------------------------------------------------------------------
# Base Agent
# ---------------------------------------------------------------------------


@dataclass
class Agent:
    """Base class for the 10 Principal Agents of Phase 4.

    Each agent has a name, a charter (Constitutional Purpose,
    Prohibited Actions), and an `execute` method that calls the
    appropriate WorkflowService method.
    """

    name: str
    constitutional_purpose: str
    prohibited_actions: tuple[str, ...]
    office: str
    charter_section: str  # e.g. "Document 02 §4.2.1"
    service: WorkflowService

    def charter_summary(self) -> str:
        return (
            f"{self.name} ({self.charter_section})\n"
            f"  Office: {self.office}\n"
            f"  Constitutional Purpose: {self.constitutional_purpose}\n"
            f"  Prohibited Actions: {', '.join(self.prohibited_actions)}"
        )


# ---------------------------------------------------------------------------
# Industrial Intelligence Office (3 agents)
# ---------------------------------------------------------------------------


class IndustrialEnvironmentMonitorAgent(Agent):
    """Document 02 §4.2.1 — Industrial Environment Monitor Agent.

    Drives Stage 1 (Industrial Environment). Maintains the
    Environmental Profile.
    """

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="Industrial Environment Monitor Agent",
            constitutional_purpose="Characterise the Industrial Environment.",
            prohibited_actions=(
                "Declare Industrial Activity",
                "Bind Techno Service",
                "Amend the Constitution",
            ),
            office="Industrial Intelligence Office",
            charter_section="Document 02 §4.2.1",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, sector: str, geography: str, **kwargs):
        return self.service.create_environmental_profile(
            actor_id=actor_id, role_code=role_code, sector=sector, geography=geography, **kwargs
        )


class IndustrialActivityDetectionAgent(Agent):
    """Document 02 §4.2.2 — Industrial Activity Detection Agent.

    Drives Stage 2 (Industrial Activity Detection). Classifies
    activity as Confirmed/Announced/Probable/Speculative.
    """

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="Industrial Activity Detection Agent",
            constitutional_purpose="Detect and characterise Industrial Activity.",
            prohibited_actions=(
                "Estimate value",
                "Declare Opportunity",
                "Promote Speculative to Announced without evidence",
            ),
            office="Industrial Intelligence Office",
            charter_section="Document 02 §4.2.2",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, sector: str, geography: str, activity_description: str,
                classification: str, activity_date: str, profile_id: Optional[str] = None, **kwargs):
        return self.service.create_industrial_activity(
            actor_id=actor_id, role_code=role_code, sector=sector, geography=geography,
            activity_description=activity_description, classification=classification,
            activity_date=activity_date, profile_id=profile_id, **kwargs
        )


class ValidatedSignalAgent(Agent):
    """Document 02 §4.2.3 — Validated Signal Agent.

    Drives Stage 3 (Validated Signal). Confirms that an activity
    has cleared the Preliminary Evidence Review.
    """

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="Validated Signal Agent",
            constitutional_purpose=(
                "Confirm that a detected Industrial Activity has cleared "
                "the Preliminary Evidence Review of Stage 6 of the Discovery Order."
            ),
            prohibited_actions=(
                "Certify value",
                "Declare Opportunity",
                "Approve external action",
            ),
            office="Industrial Intelligence Office",
            charter_section="Document 02 §4.2.3",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, activity_id: str, preliminary_review_outcome: str,
                preliminary_reviewer_id: str, **kwargs):
        return self.service.create_validated_signal(
            actor_id=actor_id, role_code=role_code, activity_id=activity_id,
            preliminary_review_outcome=preliminary_review_outcome,
            preliminary_reviewer_id=preliminary_reviewer_id, **kwargs
        )


# ---------------------------------------------------------------------------
# Opportunity Intelligence Office (3 agents)
# ---------------------------------------------------------------------------


class ProblemAndNeedDefinitionAgent(Agent):
    """Document 02 §4.3.1 — Problem and Need Definition Agent.

    Drives Stage 4 (Problem Definition).
    """

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="Problem and Need Definition Agent",
            constitutional_purpose="Convert a Validated Signal into a defined Problem or Need.",
            prohibited_actions=(
                "Recommend a solution",
                "Declare value",
                "Promote unverified material",
            ),
            office="Opportunity Intelligence Office",
            charter_section="Document 02 §4.3.1",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, validated_signal_id: str, problem_description: str, **kwargs):
        return self.service.create_problem_or_need(
            actor_id=actor_id, role_code=role_code, validated_signal_id=validated_signal_id,
            problem_description=problem_description, **kwargs
        )


class RootCauseAnalysisAgent(Agent):
    """Document 02 §4.3.2 — Root Cause Analysis Agent.

    Drives Stage 5 (Root Cause).
    """

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="Root Cause Analysis Agent",
            constitutional_purpose="Establish the underlying Root Cause of a defined Problem or Need.",
            prohibited_actions=(
                "Recommend a solution",
                "Declare an Opportunity",
                "Treat symptom as cause",
            ),
            office="Opportunity Intelligence Office",
            charter_section="Document 02 §4.3.2",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, problem_id: str, root_cause_description: str,
                method_used: str, **kwargs):
        return self.service.create_root_cause(
            actor_id=actor_id, role_code=role_code, problem_id=problem_id,
            root_cause_description=root_cause_description, method_used=method_used, **kwargs
        )


class CommercialValueDefinitionAgent(Agent):
    """Document 02 §4.3.3 — Commercial Value Definition Agent.

    Drives Stage 6 (Commercial Value Case).
    """

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="Commercial Value Definition Agent",
            constitutional_purpose="Convert a defined Problem and Root Cause into a Commercial Value Case.",
            prohibited_actions=(
                "Recommend a solution",
                "Select a Technology",
                "Manufacture value claims",
                "Bypass the Value Qualification Rule",
            ),
            office="Opportunity Intelligence Office",
            charter_section="Document 02 §4.3.3",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, root_cause_id: str, value_description: str, **kwargs):
        return self.service.create_value_case(
            actor_id=actor_id, role_code=role_code, root_cause_id=root_cause_id,
            value_description=value_description, **kwargs
        )


# ---------------------------------------------------------------------------
# Technology Intelligence Office (4 agents)
# ---------------------------------------------------------------------------


class TechnologyCategoryAnalystAgent(Agent):
    """Document 02 §4.4.1 — Technology Category Analyst Agent.

    Drives Stage 7 (Technology Category).
    """

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="Technology Category Analyst Agent",
            constitutional_purpose="Identify the Technology Category capable of addressing an established Value Case.",
            prohibited_actions=(
                "Select a Product",
                "Promote a Manufacturer",
                "Declare an Opportunity",
            ),
            office="Technology Intelligence Office",
            charter_section="Document 02 §4.4.1",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, value_case_id: str, category: str, **kwargs):
        return self.service.create_technology_category_analysis(
            actor_id=actor_id, role_code=role_code, value_case_id=value_case_id, category=category, **kwargs
        )


class ProductAnalystAgent(Agent):
    """Document 02 §4.4.2 — Product Analyst Agent.

    Drives Stage 8 (Product Discovery).
    """

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="Product Analyst Agent",
            constitutional_purpose="Identify candidate Products or Solutions within a defined Technology Category.",
            prohibited_actions=(
                "Establish Manufacturer credibility",
                "Promote a brand",
                "Bind Techno Service",
            ),
            office="Technology Intelligence Office",
            charter_section="Document 02 §4.4.2",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, technology_category_id: str, product_name: str, **kwargs):
        return self.service.create_product_analysis(
            actor_id=actor_id, role_code=role_code, technology_category_id=technology_category_id,
            product_name=product_name, **kwargs
        )


class ReplacementAndComparativeAnalysisAgent(Agent):
    """Document 02 §4.4.3 — Replacement and Comparative Analysis Agent.

    Drives Stage 9 (Replacement Analysis). The Value Qualification
    Rule (Constitution Article VII) is APPLIED here.
    """

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="Replacement and Comparative Analysis Agent",
            constitutional_purpose=(
                "Determine what current equipment, process, Product, service, or method "
                "the proposed solution replaces or supplements, and establish the comparative case."
            ),
            prohibited_actions=(
                "Override the Value Qualification Rule",
                "Manufacture the comparative case",
            ),
            office="Technology Intelligence Office",
            charter_section="Document 02 §4.4.3",
            service=service or WorkflowService(),
        )

    def execute(
        self,
        *,
        actor_id: str,
        role_code: str,
        product_analysis_id: str,
        incumbent_solution: str,
        vqr_asserted_improvements: tuple[ImprovementEvidence, ...] = (),
        vqr_requested_classification: Optional[VQRClassification] = None,
        vqr_rationale: str = "",
        vqr_strategic_exception_approval_id: Optional[str] = None,
        **kwargs,
    ):
        return self.service.create_comparative_analysis(
            actor_id=actor_id, role_code=role_code, product_analysis_id=product_analysis_id,
            incumbent_solution=incumbent_solution, vqr_asserted_improvements=vqr_asserted_improvements,
            vqr_requested_classification=vqr_requested_classification, vqr_rationale=vqr_rationale,
            vqr_strategic_exception_approval_id=vqr_strategic_exception_approval_id, **kwargs
        )


class KuwaitSuitabilityReviewerAgent(Agent):
    """Document 02 §4.4.4 — Kuwait Suitability Reviewer Agent.

    Drives Stage 10 (Kuwait Suitability). The KSR record is the
    prerequisite for Stage 11 (Manufacturer Intelligence).
    """

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="Kuwait Suitability Reviewer Agent",
            constitutional_purpose=(
                "Review the proposed solution for technical, standards, environmental, "
                "and Kuwait-specific suitability."
            ),
            prohibited_actions=(
                "Bind Techno Service",
                "Override regulatory authority",
            ),
            office="Technology Intelligence Office",
            charter_section="Document 02 §4.4.4",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, comparative_analysis_id: str, **kwargs):
        return self.service.create_kuwait_suitability_review(
            actor_id=actor_id, role_code=role_code, comparative_analysis_id=comparative_analysis_id, **kwargs
        )


# ---------------------------------------------------------------------------
# Roster factory — 10 Principal Agents
# ---------------------------------------------------------------------------


def ten_agent_roster(service: WorkflowService | None = None) -> list[Agent]:
    """Return the 10 Principal Agents of Phase 4 (3 Offices).

    Industrial Intelligence: 3
    Opportunity Intelligence: 3
    Technology Intelligence: 4
    Total: 10.
    """
    svc = service or WorkflowService()
    return [
        # Industrial Intelligence (3)
        IndustrialEnvironmentMonitorAgent(svc),
        IndustrialActivityDetectionAgent(svc),
        ValidatedSignalAgent(svc),
        # Opportunity Intelligence (3)
        ProblemAndNeedDefinitionAgent(svc),
        RootCauseAnalysisAgent(svc),
        CommercialValueDefinitionAgent(svc),
        # Technology Intelligence (4)
        TechnologyCategoryAnalystAgent(svc),
        ProductAnalystAgent(svc),
        ReplacementAndComparativeAnalysisAgent(svc),
        KuwaitSuitabilityReviewerAgent(svc),
    ]


def assert_total_agents() -> int:
    """Assert the 10-agent roster is complete. Returns the count."""
    roster = ten_agent_roster()
    assert len(roster) == 10, f"Phase 4 must have 10 Principal Agents, got {len(roster)}"
    return 10


# ---------------------------------------------------------------------------
# Phase 5 — Manufacturer Intelligence Office (§4.5)
# ---------------------------------------------------------------------------


class ManufacturerProfilerAgent(Agent):
    """Document 02 §4.5.1 — Manufacturer Profiler Agent.

    Drives Stage 11 (Manufacturer Intelligence). Maintains the
    Manufacturer Profile (ENT-MAN-001). Does NOT declare representation
    status (that comes from the Registers).
    """

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="Manufacturer Profiler Agent",
            constitutional_purpose="Maintain constitutional profiles of Manufacturers.",
            prohibited_actions=(
                "Declare representation status alone",
                "Promote a Manufacturer",
                "Bind Techno Service",
            ),
            office="Manufacturer Intelligence Office",
            charter_section="Document 02 §4.5.1",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, **kwargs):
        return self.service.create_manufacturer_profile(
            actor_id=actor_id, role_code=role_code, **kwargs
        )


class ManufacturerCredibilityAnalystAgent(Agent):
    """Document 02 §4.5.2 — Manufacturer Credibility Analyst Agent.

    Drives Stage 11. Produces the multi-dimensional Credibility
    Assessment (ENT-MAN-002). ADVERSE / BELOW_THRESHOLD findings
    require Human Approval.
    """

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="Manufacturer Credibility Analyst Agent",
            constitutional_purpose="Assess Manufacturer credibility against constitutional criteria.",
            prohibited_actions=(
                "Declare representation status alone",
                "Promote a Manufacturer",
            ),
            office="Manufacturer Intelligence Office",
            charter_section="Document 02 §4.5.2",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, manufacturer_id: str, **kwargs):
        return self.service.create_credibility_assessment(
            actor_id=actor_id, role_code=role_code, manufacturer_id=manufacturer_id, **kwargs
        )


class ManufacturerComparisonAgent(Agent):
    """Document 02 §4.5.3 — Manufacturer Comparison Agent.

    Drives Stage 11. Produces the Manufacturer Comparison Report
    (ENT-MAN-003). Vendor-neutral by design. Does NOT select a
    Manufacturer.
    """

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="Manufacturer Comparison Agent",
            constitutional_purpose="Compare candidate Manufacturers objectively.",
            prohibited_actions=(
                "Select a Manufacturer",
                "Promote a brand",
            ),
            office="Manufacturer Intelligence Office",
            charter_section="Document 02 §4.5.3",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, opportunity_id: str, **kwargs):
        return self.service.create_manufacturer_comparison(
            actor_id=actor_id, role_code=role_code, opportunity_id=opportunity_id, **kwargs
        )


# ---------------------------------------------------------------------------
# Phase 5 — Commercial Development Office (§4.6) — selected agents
# ---------------------------------------------------------------------------


class CommercialEvaluationAgent(Agent):
    """Document 02 §4.6.1 — Commercial Evaluation Agent.

    Drives Stage 12. Produces the Commercial Evaluation (ENT-COM-001)
    with a multi-dimensional scorecard, assumptions, and uncertainty.
    Does NOT approve pursuit.
    """

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="Commercial Evaluation Agent",
            constitutional_purpose="Evaluate the commercial case for an Opportunity.",
            prohibited_actions=(
                "Approve pursuit",
                "Bind Techno Service",
            ),
            office="Commercial Development Office",
            charter_section="Document 02 §4.6.1",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, opportunity_id: str, **kwargs):
        return self.service.create_commercial_evaluation(
            actor_id=actor_id, role_code=role_code, opportunity_id=opportunity_id, **kwargs
        )


class PricingAndMarginAnalystAgent(Agent):
    """Document 02 §4.6.5 — Pricing and Margin Analyst Agent.

    Drives Stage 12. Produces the Pricing Analysis (ENT-COM-005).
    Flags margin floors. Does NOT set or commit prices.
    """

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="Pricing and Margin Analyst Agent",
            constitutional_purpose="Analyse pricing, cost, and margin.",
            prohibited_actions=(
                "Set or commit prices",
                "Bind Techno Service",
            ),
            office="Commercial Development Office",
            charter_section="Document 02 §4.6.5",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, opportunity_id: str, **kwargs):
        return self.service.create_pricing_analysis(
            actor_id=actor_id, role_code=role_code, opportunity_id=opportunity_id, **kwargs
        )


class BusinessDevelopmentAgent(Agent):
    """Document 02 §4.6.3 — Business Development Agent.

    Drives Stage 16. Prepares engagement materials. Constitutionally
    REQUIRES Human Approval AND register clearance for any external
    contact. Does NOT contact a counterparty without Human Approval.
    """

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="Business Development Agent",
            constitutional_purpose="Prepare business development engagement for an Opportunity.",
            prohibited_actions=(
                "Contact without Human Approval",
                "Commit prices or margins",
                "Promise exclusivity",
                "Bind Techno Service",
            ),
            office="Commercial Development Office",
            charter_section="Document 02 §4.6.3",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, opportunity_id: str, **kwargs):
        return self.service.create_bd_engagement(
            actor_id=actor_id, role_code=role_code, opportunity_id=opportunity_id, **kwargs
        )


# ---------------------------------------------------------------------------
# Phase 5 — Registration and Market Entry Office (§4.7) — selected agents
# ---------------------------------------------------------------------------


class RegistrationCoordinatorAgent(Agent):
    """Document 02 §4.7.1 — Registration Coordinator Agent.

    Drives Stage 17. Maintains the Registration Status Report
    (ENT-REG-001). Does NOT file or commit without Human Approval.
    """

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="Registration Coordinator Agent",
            constitutional_purpose="Govern manufacturer, partner, and product registration processes.",
            prohibited_actions=(
                "File without Human Approval",
                "Misrepresent registration status",
                "Bind Techno Service",
            ),
            office="Registration and Market Entry Office",
            charter_section="Document 02 §4.7.1",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, opportunity_id: str, **kwargs):
        return self.service.create_registration_status(
            actor_id=actor_id, role_code=role_code, opportunity_id=opportunity_id, **kwargs
        )


class PrequalificationAgent(Agent):
    """Document 02 §4.7.2 — Prequalification Agent.

    Drives Stage 17. Maintains the Prequalification Status Report
    (ENT-REG-002). Does NOT submit or commit without Human Approval.
    """

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="Prequalification Agent",
            constitutional_purpose="Govern prequalification with customers and authorities.",
            prohibited_actions=(
                "Submit without Human Approval",
                "Misrepresent status",
                "Bind Techno Service",
            ),
            office="Registration and Market Entry Office",
            charter_section="Document 02 §4.7.2",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, opportunity_id: str, **kwargs):
        return self.service.create_prequalification_status(
            actor_id=actor_id, role_code=role_code, opportunity_id=opportunity_id, **kwargs
        )


class MarketEntryStrategyAgent(Agent):
    """Document 02 §4.7.3 — Market Entry Strategy Agent.

    Drives Stage 18. Produces the Market Entry Options Report
    (ENT-REG-004). Does NOT select a path; selection is a Human
    Authority decision.
    """

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="Market Entry Strategy Agent",
            constitutional_purpose="Design market-entry strategies for new Manufacturers, products, or territories.",
            prohibited_actions=(
                "Select a market-entry path",
                "Bind Techno Service",
            ),
            office="Registration and Market Entry Office",
            charter_section="Document 02 §4.7.3",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, opportunity_id: str, **kwargs):
        return self.service.create_market_entry_options(
            actor_id=actor_id, role_code=role_code, opportunity_id=opportunity_id, **kwargs
        )


# ---------------------------------------------------------------------------
# Phase 5 Roster — 9 Principal Agents (3 Manufacturer + 3 Commercial + 3 Registration)
# ---------------------------------------------------------------------------


def nine_agent_roster(service: WorkflowService | None = None) -> list[Agent]:
    """Return the 9 Principal Agents activated in Phase 5 (3 Offices).

    Manufacturer Intelligence: 3
    Commercial Development: 3
    Registration and Market Entry: 3
    Total: 9.

    Per Document 02 §4.5, §4.6, §4.7 — Phase 5 activates 3 of the 5
    Commercial Development agents and 3 of the 4 Registration/Market
    Entry agents. The remaining agents (Commercial Model Designer,
    Negotiation Support, After-Sales Intelligence, Approved Vendor
    List Manager) are deferred to Phase 6+.
    """
    svc = service or WorkflowService()
    return [
        # Manufacturer Intelligence (3)
        ManufacturerProfilerAgent(svc),
        ManufacturerCredibilityAnalystAgent(svc),
        ManufacturerComparisonAgent(svc),
        # Commercial Development (3)
        CommercialEvaluationAgent(svc),
        PricingAndMarginAnalystAgent(svc),
        BusinessDevelopmentAgent(svc),
        # Registration and Market Entry (3)
        RegistrationCoordinatorAgent(svc),
        PrequalificationAgent(svc),
        MarketEntryStrategyAgent(svc),
    ]


def assert_phase5_agents() -> int:
    """Assert the 9-agent Phase 5 roster is complete. Returns the count."""
    roster = nine_agent_roster()
    assert len(roster) == 9, f"Phase 5 must have 9 Principal Agents, got {len(roster)}"
    return 9


# ---------------------------------------------------------------------------
# Phase 6 — Tender and Project Intelligence Office (§4.8)
# ---------------------------------------------------------------------------


class TenderMonitorAgent(Agent):
    """Document 02 §4.8.1 — Tender Monitor Agent.

    Drives Stage 19 (Tender Support). Monitors tenders; classifies
    opportunities; flags material opportunities. Does NOT submit bids.
    """

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="Tender Monitor Agent",
            constitutional_purpose=(
                "Continuously monitor tenders, requests for information, "
                "requests for quotation, expressions of interest, and "
                "framework agreements."
            ),
            prohibited_actions=(
                "Submit bids",
                "Represent Techno Service",
                "Bind Techno Service",
            ),
            office="Tender and Project Intelligence Office",
            charter_section="Document 02 §4.8.1",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, **kwargs):
        return self.service.create_tender(
            actor_id=actor_id, role_code=role_code, **kwargs
        )


class TenderQualificationAgent(Agent):
    """Document 02 §4.8.2 — Tender Qualification Agent.

    Qualifies tenders. Issues the Tender Qualification Report. Does
    NOT decide to bid.
    """

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="Tender Qualification Agent",
            constitutional_purpose=(
                "Qualify tenders against the Constitutional Commercial "
                "Principles and the Value Qualification Rule."
            ),
            prohibited_actions=(
                "Decide to bid",
                "Bind Techno Service",
            ),
            office="Tender and Project Intelligence Office",
            charter_section="Document 02 §4.8.2",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, tender_id: str, **kwargs):
        return self.service.create_tender_qualification(
            actor_id=actor_id, role_code=role_code, tender_id=tender_id, **kwargs
        )


class QuotationSupportAgent(Agent):
    """Document 02 §4.8.4 — Quotation Support Agent.

    Prepares the Quotation Dossier and the Tender Submission Dossier.
    Every submission REQUIRES Human Approval. Does NOT submit.
    """

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="Quotation Support Agent",
            constitutional_purpose=(
                "Support the preparation of quotations and tender "
                "submissions."
            ),
            prohibited_actions=(
                "Submit",
                "Commit prices, margins, or terms",
                "Bind Techno Service",
            ),
            office="Tender and Project Intelligence Office",
            charter_section="Document 02 §4.8.4",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, tender_id: str, **kwargs):
        return self.service.create_quotation_dossier(
            actor_id=actor_id, role_code=role_code, tender_id=tender_id, **kwargs
        )


class ProjectMonitorAgent(Agent):
    """Document 02 §4.8.3 — Project Monitor Agent.

    Drives Stage 20 (Project Support). Tracks performance, milestones,
    and after-sales opportunities. Does NOT modify commitments.
    """

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="Project Monitor Agent",
            constitutional_purpose=(
                "Monitor awarded projects through execution."
            ),
            prohibited_actions=(
                "Modify commitments",
                "Bind Techno Service",
            ),
            office="Tender and Project Intelligence Office",
            charter_section="Document 02 §4.8.3",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, project_name: str, **kwargs):
        return self.service.create_project_status_report(
            actor_id=actor_id, role_code=role_code, project_name=project_name, **kwargs
        )


# ---------------------------------------------------------------------------
# Phase 6 — Knowledge and Institutional Memory Office (§4.13)
# ---------------------------------------------------------------------------


class KnowledgeBaseCuratorAgent(Agent):
    """Document 02 §4.13.1 — Knowledge Base Curator Agent.

    Drives Stage 22 (Knowledge Capture). Curates the Knowledge Base.
    Enforces data quality and provenance. Does NOT silently delete
    or overwrite records.
    """

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="Knowledge Base Curator Agent",
            constitutional_purpose="Curate the Knowledge Base.",
            prohibited_actions=(
                "Silently delete or overwrite records",
                "Bind Techno Service",
            ),
            office="Knowledge and Institutional Memory Office",
            charter_section="Document 02 §4.13.1",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, title: str, **kwargs):
        return self.service.create_knowledge_record(
            actor_id=actor_id, role_code=role_code, title=title, **kwargs
        )


class InstitutionalMemoryManagerAgent(Agent):
    """Document 02 §4.13.2 — Institutional Memory Manager Agent.

    Drives Stage 23 (Institutional Memory). Governs Institutional
    Memory; preserves records; coordinates retention. Does NOT
    silently delete records.
    """

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="Institutional Memory Manager Agent",
            constitutional_purpose="Govern Institutional Memory.",
            prohibited_actions=(
                "Silently delete records",
                "Bind Techno Service",
            ),
            office="Knowledge and Institutional Memory Office",
            charter_section="Document 02 §4.13.2",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, target_type: str, target_id: str, **kwargs):
        return self.service.create_institutional_memory_index(
            actor_id=actor_id, role_code=role_code,
            target_type=target_type, target_id=target_id, **kwargs
        )


class LessonsLearnedAnalystAgent(Agent):
    """Document 02 §4.13.3 — Lessons Learned Analyst Agent.

    Extracts Lessons Learned from closed Opportunities. Publishes
    the Lessons Learned Index. Does NOT silently amend records.
    """

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="Lessons Learned Analyst Agent",
            constitutional_purpose=(
                "Convert experience into institutional lessons."
            ),
            prohibited_actions=(
                "Silently amend records",
                "Bind Techno Service",
            ),
            office="Knowledge and Institutional Memory Office",
            charter_section="Document 02 §4.13.3",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, title: str, **kwargs):
        return self.service.create_lesson_learned(
            actor_id=actor_id, role_code=role_code, title=title, **kwargs
        )


# ---------------------------------------------------------------------------
# Phase 6 — Deferred Commercial Development agents (Phase 5 → Phase 6)
# ---------------------------------------------------------------------------


class CommercialModelDesignerAgent(Agent):
    """Document 02 §4.6.2 — Commercial Model Designer Agent.

    Design candidate commercial models. Does NOT approve a model.
    """

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="Commercial Model Designer Agent",
            constitutional_purpose=(
                "Design commercial models for an Opportunity."
            ),
            prohibited_actions=(
                "Approve a model",
                "Bind Techno Service",
            ),
            office="Commercial Development Office",
            charter_section="Document 02 §4.6.2",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, opportunity_id: str, model_type: str, **kwargs):
        return self.service.create_commercial_model_option(
            actor_id=actor_id, role_code=role_code,
            opportunity_id=opportunity_id, model_type=model_type, **kwargs
        )


class NegotiationSupportAgent(Agent):
    """Document 02 §4.6.4 — Negotiation Support Agent.

    Supports a human-led negotiation. Does NOT accept, reject, or
    commit.
    """

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="Negotiation Support Agent",
            constitutional_purpose=(
                "Support human-led negotiation without conducting it."
            ),
            prohibited_actions=(
                "Accept or reject terms",
                "Commit prices",
                "Promise exclusivity",
                "Bind Techno Service",
            ),
            office="Commercial Development Office",
            charter_section="Document 02 §4.6.4",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, opportunity_id: str, **kwargs):
        return self.service.create_negotiation_analysis(
            actor_id=actor_id, role_code=role_code, opportunity_id=opportunity_id, **kwargs
        )


class AfterSalesIntelligenceAgent(Agent):
    """Document 02 §4.6.6 — After-Sales Intelligence Agent.

    Tracks after-sales performance. Does NOT contact customer without
    Human Approval.
    """

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="After-Sales Intelligence Agent",
            constitutional_purpose=(
                "Track after-sales performance, recurring spares and "
                "service opportunities, and renewal or expansion potential."
            ),
            prohibited_actions=(
                "Contact customer without Human Approval",
                "Bind Techno Service",
            ),
            office="Commercial Development Office",
            charter_section="Document 02 §4.6.6",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, opportunity_id: str, report_text: str, **kwargs):
        return self.service.create_after_sales_report(
            actor_id=actor_id, role_code=role_code,
            opportunity_id=opportunity_id, report_text=report_text, **kwargs
        )


# ---------------------------------------------------------------------------
# Phase 6 — Approved Vendor List Manager (Phase 5 → Phase 6)
# ---------------------------------------------------------------------------


class ApprovedVendorListManagerAgent(Agent):
    """Document 02 §4.7.4 — Approved Vendor List Manager Agent.

    Maintains Techno Service's standing on approved-vendor lists.
    Submissions require Human Approval.
    """

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="Approved Vendor List Manager Agent",
            constitutional_purpose=(
                "Maintain Techno Service's standing on customer and "
                "authority approved-vendor lists."
            ),
            prohibited_actions=(
                "Submit without Human Approval",
                "Misrepresent status",
                "Bind Techno Service",
            ),
            office="Registration and Market Entry Office",
            charter_section="Document 02 §4.7.4",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, opportunity_id: str, authority: str, **kwargs):
        return self.service.create_avl_status(
            actor_id=actor_id, role_code=role_code,
            opportunity_id=opportunity_id, authority=authority, **kwargs
        )


# ---------------------------------------------------------------------------
# Phase 6 Roster — 11 Principal Agents (4 Tender/Project + 3 Knowledge + 4 deferred)
# ---------------------------------------------------------------------------


def eleven_agent_roster(service: WorkflowService | None = None) -> list[Agent]:
    """Return the 11 Principal Agents activated in Phase 6.

    Tender and Project Intelligence: 4
    Knowledge and Institutional Memory: 3
    Deferred agents (from Phase 5 → Phase 6): 4
        (Commercial Model Designer §4.6.2,
         Negotiation Support §4.6.4,
         After-Sales Intelligence §4.6.6,
         Approved Vendor List Manager §4.7.4)
    Total: 11.
    """
    svc = service or WorkflowService()
    return [
        # Tender and Project (4)
        TenderMonitorAgent(svc),
        TenderQualificationAgent(svc),
        QuotationSupportAgent(svc),
        ProjectMonitorAgent(svc),
        # Knowledge (3)
        KnowledgeBaseCuratorAgent(svc),
        InstitutionalMemoryManagerAgent(svc),
        LessonsLearnedAnalystAgent(svc),
        # Deferred (4)
        CommercialModelDesignerAgent(svc),
        NegotiationSupportAgent(svc),
        AfterSalesIntelligenceAgent(svc),
        ApprovedVendorListManagerAgent(svc),
    ]


def assert_phase6_agents() -> int:
    """Assert the 11-agent Phase 6 roster is complete. Returns the count."""
    roster = eleven_agent_roster()
    assert len(roster) == 11, f"Phase 6 must have 11 Principal Agents, got {len(roster)}"
    return 11


# ---------------------------------------------------------------------------
# Phase 7 — Performance and Learning Office (§4.17)
# ---------------------------------------------------------------------------


class CommercialOutcomesAnalystAgent(Agent):
    """Document 02 §4.17.2 — Commercial Outcomes Analyst Agent.

    Drives the realization of Commercial Outcomes (WON / LOST /
    CLOSED). Records the outcome, revenue, margin, and lessons
    learned.
    """

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="Commercial Outcomes Analyst Agent",
            constitutional_purpose=(
                "Analyse realised commercial outcomes and surface lessons learned."
            ),
            prohibited_actions=("Bind Techno Service",),
            office="Performance and Learning Office",
            charter_section="Document 02 §4.17.2",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, opportunity_id: str, outcome: str, **kwargs):
        return self.service.create_commercial_outcome(
            actor_id=actor_id, role_code=role_code,
            opportunity_id=opportunity_id, outcome=outcome, **kwargs
        )


class PerformanceMeasurementAgent(Agent):
    """Document 02 §4.17.1 — Performance Measurement Agent.

    Records Performance metrics (KPIs, trends).
    """

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="Performance Measurement Agent",
            constitutional_purpose="Measure and report system performance.",
            prohibited_actions=("Bind Techno Service",),
            office="Performance and Learning Office",
            charter_section="Document 02 §4.17.1",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, metric_name: str, metric_value: str, **kwargs):
        return self.service.create_performance_record(
            actor_id=actor_id, role_code=role_code,
            metric_name=metric_name, metric_value=metric_value, **kwargs
        )


class LearningCoordinationAgent(Agent):
    """Document 02 §4.17.3 — Learning Coordination Agent.

    Drives Stage 24 (Continuous Learning). Reviews every Learning
    Update proposal against the Constitution.
    """

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="Learning Coordination Agent",
            constitutional_purpose=(
                "Coordinate the system's continuous learning cycle with "
                "Constitutional Impact Review."
            ),
            prohibited_actions=(
                "Amend the Constitution",
                "Bind Techno Service",
            ),
            office="Performance and Learning Office",
            charter_section="Document 02 §4.17.3",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, proposal, **kwargs):
        return self.service.review_learning_update(
            actor_id=actor_id, role_code=role_code, proposal=proposal, **kwargs
        )


class ConstitutionalLearningAgent(Agent):
    """Document 02 §4.17.4 — Compliance Review Agent
    (Constitutional Learning Agent).

    Ensures that no Learning update violates the Constitution.
    Performs a constitutional review of every Learning proposal.
    """

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="Constitutional Learning Agent",
            constitutional_purpose=(
                "Ensure that no system learning violates the Constitution."
            ),
            prohibited_actions=(
                "Amend the Constitution",
                "Bind Techno Service",
            ),
            office="Performance and Learning Office",
            charter_section="Document 02 §4.17.4",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, office: str, status: str, **kwargs):
        return self.service.create_compliance_review(
            actor_id=actor_id, role_code=role_code,
            office=office, status=status, **kwargs
        )


# ---------------------------------------------------------------------------
# Phase 7 — Reporting and Decision Support Office (§4.15)
# ---------------------------------------------------------------------------


class ReportAuthorAgent(Agent):
    """Document 02 §4.15.3 — Detailed Report Composer Agent
    (Report Author). Composes every Report."""

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="Report Author Agent",
            constitutional_purpose="Compose every system Report.",
            prohibited_actions=("Bind Techno Service",),
            office="Reporting and Decision Support Office",
            charter_section="Document 02 §4.15.3",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, title: str, **kwargs):
        return self.service.create_report(
            actor_id=actor_id, role_code=role_code,
            title=title, **kwargs
        )


class BoardReportAgent(Agent):
    """Document 02 §4.15.2 — Board Report Composer Agent.

    Composes board-grade reports with Constitutional Compliance
    Attestation.
    """

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="Board Report Agent",
            constitutional_purpose=(
                "Compose board-grade reports with Constitutional "
                "Compliance Attestation."
            ),
            prohibited_actions=("Bind Techno Service",),
            office="Reporting and Decision Support Office",
            charter_section="Document 02 §4.15.2",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, title: str, **kwargs):
        return self.service.create_report(
            actor_id=actor_id, role_code=role_code,
            title=title, report_type="BOARD", **kwargs
        )


class OperationalReportAgent(Agent):
    """Document 02 §4.15.3 — Detailed Report Composer Agent
    (Operational Report). Operational dashboards and reports."""

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="Operational Report Agent",
            constitutional_purpose="Operational dashboards and reports.",
            prohibited_actions=("Bind Techno Service",),
            office="Reporting and Decision Support Office",
            charter_section="Document 02 §4.15.3",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, title: str, **kwargs):
        return self.service.create_report(
            actor_id=actor_id, role_code=role_code,
            title=title, report_type="OPERATIONAL", **kwargs
        )


class ComplianceReportAgent(Agent):
    """Document 02 §4.15.1 — Executive Report Composer Agent
    (Compliance Report). Constitutional compliance reports."""

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="Compliance Report Agent",
            constitutional_purpose="Constitutional compliance reports.",
            prohibited_actions=("Bind Techno Service",),
            office="Reporting and Decision Support Office",
            charter_section="Document 02 §4.15.1",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, title: str, **kwargs):
        return self.service.create_report(
            actor_id=actor_id, role_code=role_code,
            title=title, report_type="COMPLIANCE", **kwargs
        )


class CommercialReportAgent(Agent):
    """Document 02 §4.15.3 — Detailed Report Composer Agent
    (Commercial Report). Commercial reports."""

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="Commercial Report Agent",
            constitutional_purpose="Commercial reports.",
            prohibited_actions=("Bind Techno Service",),
            office="Reporting and Decision Support Office",
            charter_section="Document 02 §4.15.3",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, title: str, **kwargs):
        return self.service.create_report(
            actor_id=actor_id, role_code=role_code,
            title=title, report_type="COMMERCIAL", **kwargs
        )


# ---------------------------------------------------------------------------
# Phase 7 — Notification and Monitoring Office (§4.16)
# ---------------------------------------------------------------------------


class NotificationComposerAgent(Agent):
    """Document 02 §4.16.1 — Notification Router Agent
    (Notification Composer). Composes 6 categories of notifications."""

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="Notification Composer Agent",
            constitutional_purpose=(
                "Compose and route Notifications across 6 categories "
                "and 5 channels."
            ),
            prohibited_actions=("Suppress Class 3/4 notifications",),
            office="Notification and Monitoring Office",
            charter_section="Document 02 §4.16.1",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, **kwargs):
        return self.service.route_notification(
            actor_id=actor_id, role_code=role_code, **kwargs
        )


class EscalationCoordinatorAgent(Agent):
    """Document 02 §4.16.2 — Monitoring Agent (Escalation
    Coordinator). Routes escalations."""

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="Escalation Coordinator Agent",
            constitutional_purpose="Route escalations.",
            prohibited_actions=("Bind Techno Service",),
            office="Notification and Monitoring Office",
            charter_section="Document 02 §4.16.2",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, workflow_canonical_id: str, event_type: str, **kwargs):
        return self.service.create_workflow_event(
            actor_id=actor_id, role_code=role_code,
            workflow_canonical_id=workflow_canonical_id,
            event_type=event_type, **kwargs
        )


class WorkflowMonitorAgent(Agent):
    """Document 02 §4.16.2 — Monitoring Agent (Workflow Monitor).
    Monitors workflow state."""

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="Workflow Monitor Agent",
            constitutional_purpose="Monitor workflow state.",
            prohibited_actions=("Bind Techno Service",),
            office="Notification and Monitoring Office",
            charter_section="Document 02 §4.16.2",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, workflow_canonical_id: str, event_type: str = "STATE_CHANGE", **kwargs):
        return self.service.create_workflow_event(
            actor_id=actor_id, role_code=role_code,
            workflow_canonical_id=workflow_canonical_id,
            event_type=event_type, **kwargs
        )


class BottleneckDetectorAgent(Agent):
    """Document 02 §4.16.2 — Monitoring Agent (Bottleneck Detector).
    Detects bottlenecks."""

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="Bottleneck Detector Agent",
            constitutional_purpose="Detect workflow bottlenecks.",
            prohibited_actions=("Bind Techno Service",),
            office="Notification and Monitoring Office",
            charter_section="Document 02 §4.16.2",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, stage_name: str, avg_cycle_hours: float, threshold_hours: float):
        return self.service.detect_bottleneck(
            actor_id=actor_id, role_code=role_code,
            stage_name=stage_name,
            avg_cycle_hours=avg_cycle_hours,
            threshold_hours=threshold_hours,
        )


class SLAMonitorAgent(Agent):
    """Document 02 §4.16.2 — Monitoring Agent (SLA Monitor). Monitors
    SLAs."""

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="SLA Monitor Agent",
            constitutional_purpose="Monitor SLAs.",
            prohibited_actions=("Bind Techno Service",),
            office="Notification and Monitoring Office",
            charter_section="Document 02 §4.16.2",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, sla_name: str, target_hours: float, actual_hours: float):
        return self.service.check_sla(
            actor_id=actor_id, role_code=role_code,
            sla_name=sla_name, target_hours=target_hours, actual_hours=actual_hours,
        )


class ChiefOrchestrationAgent(Agent):
    """Document 02 §4.16 (Phase 7 scope) — Chief Orchestration Agent.
    Top-level orchestrator across all Offices."""

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="Chief Orchestration Agent",
            constitutional_purpose=(
                "Top-level orchestrator across all Offices and the "
                "constitutional workflow."
            ),
            prohibited_actions=("Bind Techno Service",),
            office="Notification and Monitoring Office",
            charter_section="Document 02 §4.1.1 (canonical) / Phase 7 §4.16",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, **kwargs):
        # The Chief Orchestration Agent delegates to the WorkflowService
        # for cross-office orchestration. The exact orchestration
        # logic is owned by the WorkflowEngine (Phase 3) and the
        # DiscoveryOrderWalker.
        return {"status": "delegated", "actor_id": actor_id}


# ---------------------------------------------------------------------------
# Phase 7 — Risk and Compliance Office (§4.11)
# ---------------------------------------------------------------------------


class RiskAnalystAgent(Agent):
    """Document 02 §4.11.1 — Enterprise Risk Manager Agent
    (Risk Analyst). Maintains the risk register."""

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="Risk Analyst Agent",
            constitutional_purpose="Maintain the risk register.",
            prohibited_actions=("Bind Techno Service",),
            office="Risk and Compliance Office",
            charter_section="Document 02 §4.11.1",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, title: str, **kwargs):
        return self.service.create_enterprise_risk(
            actor_id=actor_id, role_code=role_code, title=title, **kwargs
        )


class ComplianceMonitorAgent(Agent):
    """Document 02 §4.11.2 — Compliance Officer Agent (Compliance
    Monitor). Monitors compliance."""

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="Compliance Monitor Agent",
            constitutional_purpose="Monitor compliance.",
            prohibited_actions=("Bind Techno Service",),
            office="Risk and Compliance Office",
            charter_section="Document 02 §4.11.2",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, office: str, status: str, evidence: str):
        return self.service.evaluate_compliance(
            actor_id=actor_id, role_code=role_code,
            office=office, status=status, evidence=evidence,
        )


class RegisterStewardAgent(Agent):
    """Document 02 §4.11.2 — Compliance Officer Agent (Register
    Steward). Manages the three Constitutional Registers."""

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="Register Steward Agent",
            constitutional_purpose="Manage the three Constitutional Registers.",
            prohibited_actions=("Silently amend Registers",),
            office="Risk and Compliance Office",
            charter_section="Document 02 §4.11.2",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, office: str, status: str, evidence: str):
        # The Register Steward uses the Compliance evaluation as its
        # primary action. A fuller register-management implementation
        # is out of Phase 7 scope.
        return self.service.evaluate_compliance(
            actor_id=actor_id, role_code=role_code,
            office=office, status=status, evidence=evidence,
        )


class ConstitutionalIncidentInvestigatorAgent(Agent):
    """Document 02 §4.11.3 — Constitutional Incident Investigator
    Agent. Investigates Constitutional Incidents."""

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="Constitutional Incident Investigator Agent",
            constitutional_purpose=(
                "Investigate, escalate, and remediate Constitutional Incidents."
            ),
            prohibited_actions=("Bind Techno Service",),
            office="Risk and Compliance Office",
            charter_section="Document 02 §4.11.3",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, title: str, **kwargs):
        return self.service.investigate_constitutional_incident(
            actor_id=actor_id, role_code=role_code, title=title, **kwargs
        )


# ---------------------------------------------------------------------------
# Phase 7 — Security and Data Governance Office (§4.12)
# ---------------------------------------------------------------------------


class SecurityOperationsAgent(Agent):
    """Document 02 §4.12.1 — Security Operations Agent. Security
    monitoring."""

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="Security Operations Agent",
            constitutional_purpose="Security monitoring.",
            prohibited_actions=("Bind Techno Service",),
            office="Security and Data Governance Office",
            charter_section="Document 02 §4.12.1",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, event_type: str, severity: str, description: str):
        return self.service.create_security_event(
            actor_id=actor_id, role_code=role_code,
            event_type=event_type, severity=severity, description=description,
        )


class AccessControlAgent(Agent):
    """Document 02 §4.12.3 — Access Control Agent. Access control
    enforcement."""

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="Access Control Agent",
            constitutional_purpose="Access control enforcement.",
            prohibited_actions=("Bind Techno Service",),
            office="Security and Data Governance Office",
            charter_section="Document 02 §4.12.3",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, user_id: str, target_resource: str, action: str):
        return self.service.evaluate_access_control(
            actor_id=actor_id, role_code=role_code,
            user_id=user_id, target_resource=target_resource, action=action,
        )


class DataGovernanceAgent(Agent):
    """Document 02 §4.12.2 — Data Governance Steward Agent (Data
    Governance). Data governance."""

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="Data Governance Agent",
            constitutional_purpose="Data governance.",
            prohibited_actions=("Silently delete records",),
            office="Security and Data Governance Office",
            charter_section="Document 02 §4.12.2",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, data_canonical_id: str, classification: str, **kwargs):
        return self.service.classify_data(
            actor_id=actor_id, role_code=role_code,
            data_canonical_id=data_canonical_id, classification=classification, **kwargs
        )


class ContinuityAndRecoveryAgent(Agent):
    """Document 02 §4.12.4 — Continuity and Recovery Agent.
    Continuity, backup, recovery."""

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="Continuity and Recovery Agent",
            constitutional_purpose="Continuity, backup, recovery.",
            prohibited_actions=("Bind Techno Service",),
            office="Security and Data Governance Office",
            charter_section="Document 02 §4.12.4",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, event_type: str, description: str):
        return self.service.create_continuity_event(
            actor_id=actor_id, role_code=role_code,
            event_type=event_type, description=description,
        )


# ---------------------------------------------------------------------------
# Phase 7 — Relationship Management Office (§4.14)
# ---------------------------------------------------------------------------


class CustomerRelationshipAgent(Agent):
    """Document 02 §4.14.2 — Customer Relationship Agent. Maintains
    customer profiles and history."""

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="Customer Relationship Agent",
            constitutional_purpose="Maintain customer profiles and history.",
            prohibited_actions=("Contact without Human Approval",),
            office="Relationship Management Office",
            charter_section="Document 02 §4.14.2",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, customer_name: str, **kwargs):
        return self.service.create_customer_relationship(
            actor_id=actor_id, role_code=role_code,
            customer_name=customer_name, **kwargs
        )


class PartnerRelationshipAgent(Agent):
    """Document 02 §4.14.3 — Partner and Channel Relationship Agent
    (Partner Relationship). Maintains partner profiles."""

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="Partner Relationship Agent",
            constitutional_purpose="Maintain partner profiles.",
            prohibited_actions=("Bind Techno Service",),
            office="Relationship Management Office",
            charter_section="Document 02 §4.14.3",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, partner_name: str, **kwargs):
        return self.service.create_partner_relationship(
            actor_id=actor_id, role_code=role_code,
            partner_name=partner_name, **kwargs
        )


class ManufacturerRelationshipAgent(Agent):
    """Document 02 §4.14.1 — Manufacturer Relationship Agent.
    Maintains manufacturer relationships."""

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="Manufacturer Relationship Agent",
            constitutional_purpose="Maintain manufacturer relationships.",
            prohibited_actions=("Bind Techno Service",),
            office="Relationship Management Office",
            charter_section="Document 02 §4.14.1",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, manufacturer_id: str, **kwargs):
        return self.service.create_manufacturer_relationship(
            actor_id=actor_id, role_code=role_code,
            manufacturer_id=manufacturer_id, **kwargs
        )


# ---------------------------------------------------------------------------
# Phase 7 — Executive AI Office (§4.1)
# ---------------------------------------------------------------------------


class ConstitutionalCoordinationAgent(Agent):
    """Document 02 §4.1.1 — Chief Orchestration Agent (Constitutional
    Coordination). Coordinates constitutional workflow."""

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="Constitutional Coordination Agent",
            constitutional_purpose=(
                "Coordinate the constitutional workflow across all "
                "Offices and Agents."
            ),
            prohibited_actions=("Bind Techno Service",),
            office="Executive AI Office",
            charter_section="Document 02 §4.1.1",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, **kwargs):
        return {"status": "coordinating", "actor_id": actor_id}


class ConstitutionalComplianceCoordinationAgent(Agent):
    """Document 02 §4.1.2 — Constitutional Compliance Coordination
    Agent. Coordinates constitutional compliance reviews."""

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="Constitutional Compliance Coordination Agent",
            constitutional_purpose=(
                "Coordinate constitutional compliance reviews across "
                "all Offices."
            ),
            prohibited_actions=("Bind Techno Service",),
            office="Executive AI Office",
            charter_section="Document 02 §4.1.2",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, office: str, status: str, **kwargs):
        return self.service.create_compliance_review(
            actor_id=actor_id, role_code=role_code,
            office=office, status=status, **kwargs
        )


class ConstitutionalDiscoveryCoordinationAgent(Agent):
    """Document 02 §4.1.1 — Chief Orchestration Agent (Constitutional
    Discovery Coordination). Coordinates the Discovery Order."""

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="Constitutional Discovery Coordination Agent",
            constitutional_purpose=(
                "Coordinate the constitutional Discovery Order across "
                "all 24 stages."
            ),
            prohibited_actions=("Bind Techno Service",),
            office="Executive AI Office",
            charter_section="Document 02 §4.1.1",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, workflow_canonical_id: str, event_type: str = "DISCOVERY_EVENT", **kwargs):
        return self.service.create_workflow_event(
            actor_id=actor_id, role_code=role_code,
            workflow_canonical_id=workflow_canonical_id,
            event_type=event_type, **kwargs
        )


class ConstitutionalDecisionSupportAgent(Agent):
    """Document 02 §4.15.4 — Decision Support Analyst Agent
    (Constitutional Decision Support). Provides decision support."""

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="Constitutional Decision Support Agent",
            constitutional_purpose="Provide constitutional decision support.",
            prohibited_actions=("Bind Techno Service",),
            office="Executive AI Office",
            charter_section="Document 02 §4.15.4",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, title: str, **kwargs):
        return self.service.create_report(
            actor_id=actor_id, role_code=role_code,
            title=title, report_type="EXECUTIVE", **kwargs
        )


class HumanEscalationCoordinationAgent(Agent):
    """Document 02 §4.1.3 — Human Escalation Coordination Agent.
    Coordinates human escalations."""

    def __init__(self, service: WorkflowService | None = None) -> None:
        super().__init__(
            name="Human Escalation Coordination Agent",
            constitutional_purpose="Coordinate human escalations.",
            prohibited_actions=("Bypass Human Approval",),
            office="Executive AI Office",
            charter_section="Document 02 §4.1.3",
            service=service or WorkflowService(),
        )

    def execute(self, *, actor_id: str, role_code: str, workflow_canonical_id: str, event_type: str = "ESCALATION", **kwargs):
        return self.service.create_workflow_event(
            actor_id=actor_id, role_code=role_code,
            workflow_canonical_id=workflow_canonical_id,
            event_type=event_type, **kwargs
        )


# ---------------------------------------------------------------------------
# Phase 7 Roster — 31 Principal Agents
# ---------------------------------------------------------------------------


def thirty_one_agent_roster(service: WorkflowService | None = None) -> list[Agent]:
    """Return the 31 Principal Agents activated in Phase 7.

    Performance and Learning Office (§4.17): 4
    Reporting and Decision Support Office (§4.15): 5
    Notification and Monitoring Office (§4.16): 6
    Risk and Compliance Office (§4.11): 4
    Security and Data Governance Office (§4.12): 4
    Relationship Management Office (§4.14): 3
    Executive AI Office (§4.1): 5
    Total: 31.
    """
    svc = service or WorkflowService()
    return [
        # Performance and Learning Office (§4.17) — 4
        CommercialOutcomesAnalystAgent(svc),
        PerformanceMeasurementAgent(svc),
        LearningCoordinationAgent(svc),
        ConstitutionalLearningAgent(svc),
        # Reporting and Decision Support Office (§4.15) — 5
        ReportAuthorAgent(svc),
        BoardReportAgent(svc),
        OperationalReportAgent(svc),
        ComplianceReportAgent(svc),
        CommercialReportAgent(svc),
        # Notification and Monitoring Office (§4.16) — 6
        NotificationComposerAgent(svc),
        EscalationCoordinatorAgent(svc),
        WorkflowMonitorAgent(svc),
        BottleneckDetectorAgent(svc),
        SLAMonitorAgent(svc),
        ChiefOrchestrationAgent(svc),
        # Risk and Compliance Office (§4.11) — 4
        RiskAnalystAgent(svc),
        ComplianceMonitorAgent(svc),
        RegisterStewardAgent(svc),
        ConstitutionalIncidentInvestigatorAgent(svc),
        # Security and Data Governance Office (§4.12) — 4
        SecurityOperationsAgent(svc),
        AccessControlAgent(svc),
        DataGovernanceAgent(svc),
        ContinuityAndRecoveryAgent(svc),
        # Relationship Management Office (§4.14) — 3
        CustomerRelationshipAgent(svc),
        PartnerRelationshipAgent(svc),
        ManufacturerRelationshipAgent(svc),
        # Executive AI Office (§4.1) — 5
        ConstitutionalCoordinationAgent(svc),
        ConstitutionalComplianceCoordinationAgent(svc),
        ConstitutionalDiscoveryCoordinationAgent(svc),
        ConstitutionalDecisionSupportAgent(svc),
        HumanEscalationCoordinationAgent(svc),
    ]


def assert_phase7_agents() -> int:
    """Assert the 31-agent Phase 7 roster is complete. Returns the count."""
    roster = thirty_one_agent_roster()
    assert len(roster) == 31, f"Phase 7 must have 31 Principal Agents, got {len(roster)}"
    return 31

