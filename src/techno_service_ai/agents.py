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
