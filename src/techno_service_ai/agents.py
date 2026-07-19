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

