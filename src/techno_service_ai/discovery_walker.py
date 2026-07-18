"""DiscoveryOrderWalker — end-to-end S01..S24 walk with VQR + KSR.

The Walker is the end-to-end orchestrator for the 24-stage Discovery
Order. It walks stages sequentially, calling the appropriate
Principal Agent at each stage. It enforces the constitutional
invariants:

  - Discovery Order: S_N may only begin after S_(N-1) is complete
    (WF-PRIN-007, ORCH-SEQ-003).
  - VQR at Stage 9: the Comparative Analysis carries a VQRResult;
    the next stage (S10) is BLOCKED if the VQR is missing.
  - KSR at Stage 10: a KuwaitSuitabilityReview record is required
    before the next stage (S11) is allowed.
  - Independence: the producer != the verifier (verified by the
    Independence Tracker — the Walker is the PRODUCER side; the
    Verification Office is the VERIFIER).

Constitutional source:
  - Constitution Article VI (Discovery Order)
  - Constitution Article VII (Value Qualification Rule)
  - Document 06 §2.1..2.24 (24 Stages)
  - Document 06 §3.1 (Sequential Execution)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from .agents import (
    CommercialValueDefinitionAgent,
    IndustrialActivityDetectionAgent,
    IndustrialEnvironmentMonitorAgent,
    KuwaitSuitabilityReviewerAgent,
    ProblemAndNeedDefinitionAgent,
    ProductAnalystAgent,
    ReplacementAndComparativeAnalysisAgent,
    RootCauseAnalysisAgent,
    TechnologyCategoryAnalystAgent,
    ValidatedSignalAgent,
)
from .db import SessionLocal
from .phase2_schema import (
    ComparativeAnalysis,
    IndustrialActivity,
    IndustrialEnvironmentProfile,
    KuwaitSuitabilityReview,
    Opportunity,
    ProblemOrNeed,
    ProductAnalysis,
    RootCause,
    TechnologyCategoryAnalysis,
    ValidatedSignal,
    ValueCase,
)
from .services import WorkflowService
from .stages import DISCOVERY_ORDER, StageNumber
from .vqr import ImprovementEvidence, VQRClassification, VQRDimension, VQRResult


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class DiscoveryOrderViolation(Exception):
    """A stage was attempted out of order (skipped, abbreviated, reordered)."""
    def __init__(self, from_stage: StageNumber, to_stage: StageNumber) -> None:
        self.from_stage = from_stage
        self.to_stage = to_stage
        super().__init__(
            f"Invalid Discovery Order progression: {from_stage.name} -> {to_stage.name}. "
            f"Per Document 06 §3.1 ORCH-SEQ-003 and WF-PRIN-007, a stage may not be "
            f"skipped, abbreviated, or reordered. The only valid forward transition "
            f"is current_stage -> next_stage(current_stage)."
        )


class VQRGateNotSatisfied(Exception):
    """The Comparative Analysis (Stage 9) is presented without a VQR.

    Per Constitution Article VII paragraph 1, every Opportunity must
    be subject to the Value Qualification Rule. Without a VQRResult,
    the next stage (S10) is BLOCKED.
    """
    def __init__(self, comparative_analysis_id: str) -> None:
        self.comparative_analysis_id = comparative_analysis_id
        super().__init__(
            f"Comparative Analysis '{comparative_analysis_id}' has no VQR classification. "
            f"Per Constitution Article VII paragraph 1, the Value Qualification Rule "
            f"must be applied. The next stage (S10 Kuwait Suitability) is BLOCKED until "
            f"a VQR classification is recorded."
        )


class KSRGateNotSatisfied(Exception):
    """The Kuwait Suitability Review (Stage 10) is missing.

    Per Document 06 §2.10, the Suitability Review is the Entry
    Condition for Stage 11 (Manufacturer Intelligence). Without a
    KSR record, the next stage is BLOCKED.
    """
    def __init__(self, comparative_analysis_id: str) -> None:
        self.comparative_analysis_id = comparative_analysis_id
        super().__init__(
            f"No Kuwait Suitability Review for Comparative Analysis "
            f"'{comparative_analysis_id}'. Per Document 06 §2.10, the Suitability "
            f"Review is the Entry Condition for Stage 11 (Manufacturer Intelligence). "
            f"The next stage is BLOCKED until a KSR record is recorded."
        )


# ---------------------------------------------------------------------------
# DiscoveryOrderWalker
# ---------------------------------------------------------------------------


class DiscoveryOrderWalker:
    """End-to-end walker for the 24-stage Discovery Order.

    One Walker per Opportunity. The Walker holds the canonical IDs
    of the produced entities and uses the WorkflowService to advance
    through the stages.

    Usage:
        walker = DiscoveryOrderWalker(opportunity_id="opp-1", actor_id="agent-1", role_code="ANALYST")
        walker.execute_s01_to_s10(...)
    """

    def __init__(self, *, actor_id: str, role_code: str, service: Optional[WorkflowService] = None) -> None:
        self.actor_id = actor_id
        self.role_code = role_code
        self.service = service or WorkflowService()
        # Canonical IDs of the produced entities
        self.profile_id: Optional[str] = None
        self.activity_id: Optional[str] = None
        self.signal_id: Optional[str] = None
        self.problem_id: Optional[str] = None
        self.root_cause_id: Optional[str] = None
        self.value_case_id: Optional[str] = None
        self.opportunity_id: Optional[str] = None
        self.tech_category_id: Optional[str] = None
        self.product_id: Optional[str] = None
        self.comparative_id: Optional[str] = None
        self.ksr_id: Optional[str] = None
        # Track the last completed stage.
        self.last_completed_stage: Optional[StageNumber] = None
        # Collected entity records.
        self.entities: dict[str, object] = {}

    def _ensure_order(self, target: StageNumber) -> None:
        """Ensure the target stage is the immediate next stage."""
        if self.last_completed_stage is None:
            if target != StageNumber.S01_INDUSTRIAL_ENVIRONMENT:
                raise DiscoveryOrderViolation(StageNumber.S01_INDUSTRIAL_ENVIRONMENT, target)
            return
        # Check immediate next
        from .stages import next_stage
        expected = next_stage(self.last_completed_stage)
        if expected != target:
            raise DiscoveryOrderViolation(self.last_completed_stage, target)

    def execute_s01_environment(
        self, *, sector: str = "Oil & Gas", geography: str = "Kuwait", **kwargs
    ) -> IndustrialEnvironmentProfile:
        self._ensure_order(StageNumber.S01_INDUSTRIAL_ENVIRONMENT)
        agent = IndustrialEnvironmentMonitorAgent(self.service)
        rec = agent.execute(
            actor_id=self.actor_id, role_code=self.role_code,
            sector=sector, geography=geography, **kwargs,
        )
        self.profile_id = rec.id
        self.last_completed_stage = StageNumber.S01_INDUSTRIAL_ENVIRONMENT
        self.entities["S01"] = rec
        return rec

    def execute_s02_activity(
        self, *, sector: str = "Oil & Gas", geography: str = "Kuwait",
        activity_description: str = "Refinery maintenance turnaround",
        classification: str = "CONFIRMED",
        activity_date: str = "2026-01-01",
        **kwargs,
    ) -> IndustrialActivity:
        self._ensure_order(StageNumber.S02_INDUSTRIAL_ACTIVITY_DETECTION)
        agent = IndustrialActivityDetectionAgent(self.service)
        rec = agent.execute(
            actor_id=self.actor_id, role_code=self.role_code,
            sector=sector, geography=geography,
            activity_description=activity_description, classification=classification,
            activity_date=activity_date, profile_id=self.profile_id, **kwargs,
        )
        self.activity_id = rec.id
        self.last_completed_stage = StageNumber.S02_INDUSTRIAL_ACTIVITY_DETECTION
        self.entities["S02"] = rec
        return rec

    def execute_s03_signal(
        self, *, preliminary_reviewer_id: Optional[str] = None, **kwargs
    ) -> ValidatedSignal:
        self._ensure_order(StageNumber.S03_VALIDATED_SIGNAL)
        agent = ValidatedSignalAgent(self.service)
        rec = agent.execute(
            actor_id=self.actor_id, role_code=self.role_code,
            activity_id=self.activity_id,
            preliminary_review_outcome="VALIDATED",
            preliminary_reviewer_id=preliminary_reviewer_id or self.actor_id, **kwargs,
        )
        self.signal_id = rec.id
        self.last_completed_stage = StageNumber.S03_VALIDATED_SIGNAL
        self.entities["S03"] = rec
        return rec

    def execute_s04_problem(
        self, *, problem_description: str = "Aging heat exchangers", **kwargs
    ) -> ProblemOrNeed:
        self._ensure_order(StageNumber.S04_PROBLEM_DEFINITION)
        agent = ProblemAndNeedDefinitionAgent(self.service)
        rec = agent.execute(
            actor_id=self.actor_id, role_code=self.role_code,
            validated_signal_id=self.signal_id,
            problem_description=problem_description, **kwargs,
        )
        self.problem_id = rec.id
        self.last_completed_stage = StageNumber.S04_PROBLEM_DEFINITION
        self.entities["S04"] = rec
        return rec

    def execute_s04_opportunity(
        self, *, opportunity_title: str = "Refurbish HX-101", **kwargs
    ) -> Opportunity:
        """Create the Opportunity from the Validated Signal.

        Per Document 06 §2.4, the Opportunity is the constitutional
        root entity that anchors the workflow.
        """
        # The Opportunity is created from the Validated Signal.
        rec = self.service.create_opportunity(
            actor_id=self.actor_id, role_code=self.role_code,
            validated_signal_id=self.signal_id,
            opportunity_title=opportunity_title, **kwargs,
        )
        self.opportunity_id = rec.id
        # Do NOT advance last_completed_stage — the Opportunity is a
        # sub-record of S04, not a stage of its own.
        return rec

    def execute_s05_root_cause(
        self, *, root_cause_description: str = "Tube wall thinning from corrosion",
        method_used: str = "Root cause analysis", **kwargs,
    ) -> RootCause:
        self._ensure_order(StageNumber.S05_ROOT_CAUSE)
        agent = RootCauseAnalysisAgent(self.service)
        rec = agent.execute(
            actor_id=self.actor_id, role_code=self.role_code,
            problem_id=self.problem_id,
            root_cause_description=root_cause_description,
            method_used=method_used, **kwargs,
        )
        self.root_cause_id = rec.id
        self.last_completed_stage = StageNumber.S05_ROOT_CAUSE
        self.entities["S05"] = rec
        return rec

    def execute_s06_value_case(
        self, *, value_description: str = "Avoid unplanned shutdown", **kwargs,
    ) -> ValueCase:
        self._ensure_order(StageNumber.S06_COMMERCIAL_VALUE_CASE)
        agent = CommercialValueDefinitionAgent(self.service)
        rec = agent.execute(
            actor_id=self.actor_id, role_code=self.role_code,
            root_cause_id=self.root_cause_id,
            value_description=value_description, **kwargs,
        )
        self.value_case_id = rec.id
        self.last_completed_stage = StageNumber.S06_COMMERCIAL_VALUE_CASE
        self.entities["S06"] = rec
        return rec

    def execute_s07_tech_category(
        self, *, category: str = "Heat Exchanger Refurbishment", **kwargs,
    ) -> TechnologyCategoryAnalysis:
        self._ensure_order(StageNumber.S07_TECHNOLOGY_CATEGORY)
        agent = TechnologyCategoryAnalystAgent(self.service)
        rec = agent.execute(
            actor_id=self.actor_id, role_code=self.role_code,
            value_case_id=self.value_case_id, category=category, **kwargs,
        )
        self.tech_category_id = rec.id
        self.last_completed_stage = StageNumber.S07_TECHNOLOGY_CATEGORY
        self.entities["S07"] = rec
        return rec

    def execute_s08_product(
        self, *, product_name: str = "Inconel-clad HX-101 tube bundle", **kwargs,
    ) -> ProductAnalysis:
        self._ensure_order(StageNumber.S08_PRODUCT_DISCOVERY)
        agent = ProductAnalystAgent(self.service)
        rec = agent.execute(
            actor_id=self.actor_id, role_code=self.role_code,
            technology_category_id=self.tech_category_id, product_name=product_name, **kwargs,
        )
        self.product_id = rec.id
        self.last_completed_stage = StageNumber.S08_PRODUCT_DISCOVERY
        self.entities["S08"] = rec
        return rec

    def execute_s09_comparative(
        self,
        *,
        incumbent_solution: str = "Carbon steel tube bundle (3-year life)",
        vqr_asserted_improvements: tuple[ImprovementEvidence, ...] = (),
        vqr_requested_classification: Optional[VQRClassification] = None,
        vqr_rationale: str = "",
        vqr_strategic_exception_approval_id: Optional[str] = None,
        **kwargs,
    ) -> ComparativeAnalysis:
        """Stage 9 — VQR is APPLIED here.

        If no VQR is recorded, the next stage (S10) is BLOCKED.
        """
        self._ensure_order(StageNumber.S09_REPLACEMENT_ANALYSIS)
        agent = ReplacementAndComparativeAnalysisAgent(self.service)
        rec = agent.execute(
            actor_id=self.actor_id, role_code=self.role_code,
            product_analysis_id=self.product_id,
            incumbent_solution=incumbent_solution,
            vqr_asserted_improvements=vqr_asserted_improvements,
            vqr_requested_classification=vqr_requested_classification,
            vqr_rationale=vqr_rationale,
            vqr_strategic_exception_approval_id=vqr_strategic_exception_approval_id,
            **kwargs,
        )
        # Verify VQR is present (the service has already applied it,
        # but we double-check the gate).
        if not rec.intelligence_status:
            raise VQRGateNotSatisfied(rec.id)
        self.comparative_id = rec.id
        self.last_completed_stage = StageNumber.S09_REPLACEMENT_ANALYSIS
        self.entities["S09"] = rec
        return rec

    def execute_s10_ksr(
        self, *, regulatory_references: str = "KOC standards; KNPC specifications",
        environmental_data: str = "Ambient T 45C; humidity 60%", **kwargs,
    ) -> KuwaitSuitabilityReview:
        """Stage 10 — Kuwait Suitability Review.

        Without this record, the next stage (S11) is BLOCKED.
        """
        # VQR must be present (constitutionally enforced).
        if not self.comparative_id:
            raise VQRGateNotSatisfied("(no Comparative Analysis)")
        agent = KuwaitSuitabilityReviewerAgent(self.service)
        rec = agent.execute(
            actor_id=self.actor_id, role_code=self.role_code,
            comparative_analysis_id=self.comparative_id,
            regulatory_references=regulatory_references,
            environmental_data=environmental_data, **kwargs,
        )
        self.ksr_id = rec.id
        self.last_completed_stage = StageNumber.S10_KUWAIT_SUITABILITY
        self.entities["S10"] = rec
        return rec

    # -----------------------------------------------------------------
    # 24-stage walk: S01..S24 (Phases 4-7 cover S11-S24 in later phases)
    # -----------------------------------------------------------------

    def walk_s01_to_s10(
        self,
        *,
        sector: str = "Oil & Gas",
        geography: str = "Kuwait",
        activity_description: str = "Refinery maintenance turnaround",
        classification: str = "CONFIRMED",
        opportunity_title: str = "Refurbish HX-101",
        problem_description: str = "Aging heat exchangers",
        root_cause_description: str = "Tube wall thinning from corrosion",
        method_used: str = "Root cause analysis",
        value_description: str = "Avoid unplanned shutdown",
        category: str = "Heat Exchanger Refurbishment",
        product_name: str = "Inconel-clad HX-101 tube bundle",
        incumbent_solution: str = "Carbon steel tube bundle (3-year life)",
        vqr_asserted_improvements: tuple[ImprovementEvidence, ...] = (),
        vqr_requested_classification: Optional[VQRClassification] = None,
        vqr_rationale: str = "",
        vqr_strategic_exception_approval_id: Optional[str] = None,
        regulatory_references: str = "KOC standards",
        environmental_data: str = "Ambient T 45C; humidity 60%",
    ) -> dict[str, object]:
        """Walk S01..S10 in order. Returns the produced entities."""
        self.execute_s01_environment(sector=sector, geography=geography)
        self.execute_s02_activity(
            sector=sector, geography=geography,
            activity_description=activity_description, classification=classification,
        )
        self.execute_s03_signal()
        self.execute_s04_problem(problem_description=problem_description)
        self.execute_s04_opportunity(opportunity_title=opportunity_title)
        self.execute_s05_root_cause(
            root_cause_description=root_cause_description, method_used=method_used,
        )
        self.execute_s06_value_case(value_description=value_description)
        self.execute_s07_tech_category(category=category)
        self.execute_s08_product(product_name=product_name)
        self.execute_s09_comparative(
            incumbent_solution=incumbent_solution,
            vqr_asserted_improvements=vqr_asserted_improvements,
            vqr_requested_classification=vqr_requested_classification,
            vqr_rationale=vqr_rationale,
            vqr_strategic_exception_approval_id=vqr_strategic_exception_approval_id,
        )
        self.execute_s10_ksr(
            regulatory_references=regulatory_references,
            environmental_data=environmental_data,
        )
        return dict(self.entities)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def assert_discovery_order_invariant(from_stage: StageNumber, to_stage: StageNumber) -> None:
    """Helper: raise DiscoveryOrderViolation if the transition is invalid."""
    from .stages import next_stage
    if next_stage(from_stage) != to_stage:
        raise DiscoveryOrderViolation(from_stage, to_stage)
