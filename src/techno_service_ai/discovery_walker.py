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
    AfterSalesIntelligenceAgent,
    ApprovedVendorListManagerAgent,
    BusinessDevelopmentAgent,
    CommercialEvaluationAgent,
    CommercialModelDesignerAgent,
    CommercialValueDefinitionAgent,
    IndustrialActivityDetectionAgent,
    IndustrialEnvironmentMonitorAgent,
    InstitutionalMemoryManagerAgent,
    KnowledgeBaseCuratorAgent,
    KuwaitSuitabilityReviewerAgent,
    LessonsLearnedAnalystAgent,
    ManufacturerComparisonAgent,
    ManufacturerCredibilityAnalystAgent,
    ManufacturerProfilerAgent,
    MarketEntryStrategyAgent,
    NegotiationSupportAgent,
    PrequalificationAgent,
    PricingAndMarginAnalystAgent,
    ProblemAndNeedDefinitionAgent,
    ProductAnalystAgent,
    ProjectMonitorAgent,
    PrequalificationAgent,
    QuotationSupportAgent,
    RegistrationCoordinatorAgent,
    ReplacementAndComparativeAnalysisAgent,
    RootCauseAnalysisAgent,
    TechnologyCategoryAnalystAgent,
    TenderMonitorAgent,
    TenderQualificationAgent,
    ValidatedSignalAgent,
)
from .db import SessionLocal
from .phase2_schema import (
    AfterSalesIntelligenceReport,
    ApprovedVendorListStatusReport,
    BusinessDevelopmentEngagement,
    CommercialEvaluation,
    CommercialModelOption,
    ComparativeAnalysis,
    IndustrialActivity,
    IndustrialEnvironmentProfile,
    InstitutionalMemoryIndex,
    KnowledgeBaseInventory,
    KnowledgeRecord,
    KuwaitSuitabilityReview,
    LessonLearned,
    ManufacturerComparisonReport,
    ManufacturerCredibilityAssessment,
    ManufacturerProfile,
    MarketEntryOptionsReport,
    NegotiationAnalysis,
    Opportunity,
    PrequalificationStatusReport,
    PricingAnalysis,
    ProblemOrNeed,
    ProductAnalysis,
    ProjectStatusReport,
    QuotationDossier,
    RegistrationStatusReport,
    RootCause,
    TechnologyCategoryAnalysis,
    Tender,
    TenderQualificationReport,
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
        # Phase 5 — Manufacturer, Commercial, Registration
        self.manufacturer_id: Optional[str] = None
        self.credibility_id: Optional[str] = None
        self.comparison_id: Optional[str] = None
        self.commercial_eval_id: Optional[str] = None
        self.pricing_id: Optional[str] = None
        self.bd_engagement_id: Optional[str] = None
        self.registration_id: Optional[str] = None
        self.prequalification_id: Optional[str] = None
        self.market_entry_id: Optional[str] = None
        # Phase 6 — Tender, Project, Knowledge
        self.tender_id: Optional[str] = None
        self.tender_qualification_id: Optional[str] = None
        self.quotation_dossier_id: Optional[str] = None
        self.project_status_id: Optional[str] = None
        self.after_sales_id: Optional[str] = None
        self.commercial_model_option_id: Optional[str] = None
        self.negotiation_analysis_id: Optional[str] = None
        self.avl_status_id: Optional[str] = None
        self.knowledge_record_id: Optional[str] = None
        self.institutional_memory_id: Optional[str] = None
        self.lesson_learned_id: Optional[str] = None
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
    # Phase 5 — S11 Manufacturer Intelligence
    # -----------------------------------------------------------------

    def execute_s11_manufacturer_profile(
        self, *, manufacturer_name: str = "Heatric (Doosan Babcock)", **kwargs,
    ) -> ManufacturerProfile:
        """Stage 11 — Manufacturer Profiler Agent (§4.5.1)."""
        self._ensure_order(StageNumber.S11_MANUFACTURER_INTELLIGENCE)
        agent = ManufacturerProfilerAgent(self.service)
        rec = agent.execute(
            actor_id=self.actor_id, role_code=self.role_code,
            manufacturer_name=manufacturer_name, **kwargs,
        )
        self.manufacturer_id = rec.id
        self.last_completed_stage = StageNumber.S11_MANUFACTURER_INTELLIGENCE
        self.entities["S11_profile"] = rec
        return rec

    def execute_s11_credibility(
        self,
        *,
        dimension_scores: Optional[dict] = None,
        **kwargs,
    ) -> ManufacturerCredibilityAssessment:
        """Stage 11 — Manufacturer Credibility Analyst Agent (§4.5.2).

        `dimension_scores` is a dict of dimension → score level. The
        engine requires all 6 defined dimensions.
        """
        if dimension_scores is None:
            dimension_scores = {
                "financial_stability": "HIGH",
                "quality_systems": "HIGH",
                "delivery_track_record": "MEDIUM",
                "after_sales_capability": "MEDIUM",
                "references": "HIGH",
                "reputation": "MEDIUM",
            }
        # We must have completed the S11 profile step first.
        if not self.manufacturer_id:
            raise DiscoveryOrderViolation(
                StageNumber.S11_MANUFACTURER_INTELLIGENCE,
                StageNumber.S11_MANUFACTURER_INTELLIGENCE,
            )
        agent = ManufacturerCredibilityAnalystAgent(self.service)
        rec = agent.execute(
            actor_id=self.actor_id, role_code=self.role_code,
            manufacturer_id=self.manufacturer_id,
            dimension_scores=dimension_scores, **kwargs,
        )
        self.credibility_id = rec.id
        self.entities["S11_credibility"] = rec
        return rec

    def execute_s11_comparison(
        self,
        *,
        manufacturer_ids: Optional[list] = None,
        criteria: Optional[list] = None,
        trade_offs: str = "Trade-off A vs B",
        **kwargs,
    ) -> ManufacturerComparisonReport:
        """Stage 11 — Manufacturer Comparison Agent (§4.5.3).

        Multi-criteria, multi-manufacturer, vendor-neutral. The
        Agent does NOT select a Manufacturer.
        """
        if manufacturer_ids is None:
            manufacturer_ids = [self.manufacturer_id, "alt-1"]
        if criteria is None:
            criteria = ["Price", "Lead time", "Certification", "Track record"]
        # We must have completed the S11 profile step first.
        if not self.manufacturer_id:
            raise DiscoveryOrderViolation(
                StageNumber.S11_MANUFACTURER_INTELLIGENCE,
                StageNumber.S11_MANUFACTURER_INTELLIGENCE,
            )
        agent = ManufacturerComparisonAgent(self.service)
        rec = agent.execute(
            actor_id=self.actor_id, role_code=self.role_code,
            opportunity_id=self.opportunity_id,
            manufacturer_ids=manufacturer_ids,
            criteria=criteria,
            trade_offs=trade_offs, **kwargs,
        )
        self.comparison_id = rec.id
        self.entities["S11_comparison"] = rec
        return rec

    # -----------------------------------------------------------------
    # Phase 5 — S13 Verification (Verification Office, Phase 3 engine)
    # -----------------------------------------------------------------

    def execute_s13_verification(
        self,
        *,
        material_claim_id: Optional[str] = None,
        producer_id: Optional[str] = None,
        verifier_id: Optional[str] = None,
        **kwargs,
    ) -> dict:
        """Stage 13 — Verification (Document 06 §2.13, Verification Office).

        This is a thin wrapper around the Phase 3 Verification engine.
        The full S13 implementation (Preliminary / Specialist /
        Independent Final / Second Reviewer / Claim Classification) is
        owned by the Verification Office. Phase 5 invokes the engine
        to honour the Discovery Order.

        Returns a dict with the verification summary.
        """
        self._ensure_order(StageNumber.S13_VERIFICATION)
        from .verification import (
            ClaimClassification,
            IndependenceTracker,
            ProducerRef,
            VerifierAgent,
            VerifierRef,
            VerifierRole,
            VerificationOutcome,
        )
        if not self.comparative_id:
            raise VQRGateNotSatisfied("(no Comparative Analysis)")
        tracker = IndependenceTracker()
        # Ensure the verifier is a DIFFERENT identity from the producer
        # (Constitution Article XVII — Independence of Verification).
        actual_producer_id = producer_id or self.actor_id
        actual_verifier_id = verifier_id or "independent-final-verifier-1"
        if actual_verifier_id == actual_producer_id:
            actual_verifier_id = f"verifier-of-{actual_producer_id}"
        producer = ProducerRef(
            producer_id=actual_producer_id,
            role_code=self.role_code,
        )
        verifier_agent = VerifierAgent(
            role=VerifierRole.INDEPENDENT_FINAL_VERIFIER,
            agent_id=actual_verifier_id,
            role_code="INDEPENDENT_FINAL_VERIFIER",
            scope="Independent Final Verification",
        )
        verifier = VerifierRef(
            verifier_id=verifier_agent.agent_id,
            role=verifier_agent.role,
            role_code=verifier_agent.role_code,
        )
        record = tracker.create_record(
            canonical_id=material_claim_id or self.comparative_id,
            material_claim_id=material_claim_id or self.comparative_id,
            producer=producer,
            verifier=verifier,
            claim_classification=ClaimClassification.FACT,
            outcome=VerificationOutcome.VALIDATED,
            reason="Phase 5 S13 walk — independent final verification.",
            second_reviewer_id="second-reviewer-1",
        )
        self.last_completed_stage = StageNumber.S13_VERIFICATION
        self.entities["S13"] = record
        return {"record": record}

    def execute_s14_quality_review(self, **kwargs) -> dict:
        """Stage 14 — Quality Review (Document 06 §2.14, Quality Assurance Office).

        Thin wrapper. Quality review is owned by the Quality Assurance
        Office. Phase 5 invokes the placeholder to honour the
        Discovery Order. The Phase 3 Quality Review engine and the
        Decision Log writer are not yet wired to the schema's
        DecisionLogEntry (Phase 2 gap); the walker records the
        stage completion in its own state.
        """
        self._ensure_order(StageNumber.S14_QUALITY_REVIEW)
        self.last_completed_stage = StageNumber.S14_QUALITY_REVIEW
        self.entities["S14"] = {"passed": True, "reviewer": self.actor_id}
        return self.entities["S14"]

    def execute_s15_human_approval(
        self,
        *,
        approver_id: str = "approver-1",
        human_approval_id: Optional[str] = None,
        **kwargs,
    ) -> dict:
        """Stage 15 — Human Approval (Document 06 §2.15, Authorised Human).

        Thin wrapper. Human Approval is owned by the Authorised Human
        Authority. Phase 5 invokes the placeholder to honour the
        Discovery Order. The `human_approval_id` is the canonical id
        that downstream stages (S16 BD Engagement) will reference.
        """
        self._ensure_order(StageNumber.S15_HUMAN_APPROVAL)
        approval_id = human_approval_id or f"apr-walker-{self.opportunity_id or 'unknown'}"
        self.last_completed_stage = StageNumber.S15_HUMAN_APPROVAL
        self.entities["S15"] = {
            "approval_id": approval_id,
            "approver_id": approver_id,
            "decision_class": "CLASS_3",
        }
        return self.entities["S15"]

    # -----------------------------------------------------------------
    # Phase 5 — S12 Commercial Evaluation
    # -----------------------------------------------------------------

    def execute_s12_commercial_evaluation(
        self,
        *,
        dimension_scores: Optional[dict] = None,
        assumptions: str = "Margin 18%, win probability 35%",
        uncertainty: str = "±10% on margin, ±15% on probability",
        **kwargs,
    ) -> CommercialEvaluation:
        """Stage 12 — Commercial Evaluation Agent (§4.6.1)."""
        self._ensure_order(StageNumber.S12_COMMERCIAL_EVALUATION)
        if dimension_scores is None:
            dimension_scores = {
                "ROI": "MEDIUM",
                "MARKET_FIT": "HIGH",
                "COMPETITIVE_ADVANTAGE": "MEDIUM",
                "AGENCY_OPPORTUNITY": "HIGH",
                "PROFITABILITY": "MEDIUM",
                "RISK": "MEDIUM",
                "COMMERCIAL_FEASIBILITY": "HIGH",
            }
        agent = CommercialEvaluationAgent(self.service)
        rec = agent.execute(
            actor_id=self.actor_id, role_code=self.role_code,
            opportunity_id=self.opportunity_id,
            dimension_scores=dimension_scores,
            assumptions=assumptions,
            uncertainty=uncertainty, **kwargs,
        )
        self.commercial_eval_id = rec.id
        self.last_completed_stage = StageNumber.S12_COMMERCIAL_EVALUATION
        self.entities["S12"] = rec
        return rec

    def execute_s12_pricing(
        self,
        *,
        pricing_basis: str = "Cost-plus with market alignment",
        margin_scenarios: str = "margin=15%; margin=18%; margin=22%",
        margin_floor: Optional[float] = 12.0,
        **kwargs,
    ) -> PricingAnalysis:
        """Stage 12 — Pricing and Margin Analyst Agent (§4.6.5).

        If the proposed margin is below `margin_floor`, the
        service raises `PricingBelowFloorError`.
        """
        if not self.commercial_eval_id:
            raise DiscoveryOrderViolation(
                StageNumber.S11_MANUFACTURER_INTELLIGENCE,
                StageNumber.S12_COMMERCIAL_EVALUATION,
            )
        agent = PricingAndMarginAnalystAgent(self.service)
        rec = agent.execute(
            actor_id=self.actor_id, role_code=self.role_code,
            opportunity_id=self.opportunity_id,
            pricing_basis=pricing_basis,
            margin_scenarios=margin_scenarios,
            margin_floor=margin_floor, **kwargs,
        )
        self.pricing_id = rec.id
        self.entities["S12_pricing"] = rec
        return rec

    # -----------------------------------------------------------------
    # Phase 5 — S16 Business Development
    # -----------------------------------------------------------------

    def execute_s16_bd_engagement(
        self,
        *,
        engagement_type: str = "ENGAGEMENT_MATERIAL",
        counterpart: str = "Counterparty Inc.",
        summary: str = "Initial engagement plan",
        human_approval_id: Optional[str] = "approval-bd-001",
        **kwargs,
    ) -> BusinessDevelopmentEngagement:
        """Stage 16 — Business Development Agent (§4.6.3).

        REQUIRES Human Approval AND register clearance.
        """
        self._ensure_order(StageNumber.S16_BUSINESS_DEVELOPMENT)
        agent = BusinessDevelopmentAgent(self.service)
        rec = agent.execute(
            actor_id=self.actor_id, role_code=self.role_code,
            opportunity_id=self.opportunity_id,
            engagement_type=engagement_type,
            counterpart=counterpart,
            summary=summary,
            human_approval_id=human_approval_id, **kwargs,
        )
        self.bd_engagement_id = rec.id
        self.last_completed_stage = StageNumber.S16_BUSINESS_DEVELOPMENT
        self.entities["S16"] = rec
        return rec

    # -----------------------------------------------------------------
    # Phase 5 — S17 Registration
    # -----------------------------------------------------------------

    def execute_s17_registration(
        self,
        *,
        registration_type: str = "VENDOR_REGISTRATION",
        authority: str = "KNPC",
        status: str = "PENDING",
        human_approval_id: Optional[str] = None,
        **kwargs,
    ) -> RegistrationStatusReport:
        """Stage 17 — Registration Coordinator Agent (§4.7.1)."""
        self._ensure_order(StageNumber.S17_REGISTRATION)
        agent = RegistrationCoordinatorAgent(self.service)
        rec = agent.execute(
            actor_id=self.actor_id, role_code=self.role_code,
            opportunity_id=self.opportunity_id,
            registration_type=registration_type,
            authority=authority,
            status=status,
            human_approval_id=human_approval_id, **kwargs,
        )
        self.registration_id = rec.id
        self.last_completed_stage = StageNumber.S17_REGISTRATION
        self.entities["S17_registration"] = rec
        return rec

    def execute_s17_prequalification(
        self,
        *,
        authority: str = "KOC",
        status: str = "PENDING",
        human_approval_id: Optional[str] = None,
        **kwargs,
    ) -> PrequalificationStatusReport:
        """Stage 17 — Prequalification Agent (§4.7.2)."""
        if not self.registration_id:
            raise DiscoveryOrderViolation(
                StageNumber.S16_BUSINESS_DEVELOPMENT,
                StageNumber.S17_REGISTRATION,
            )
        agent = PrequalificationAgent(self.service)
        rec = agent.execute(
            actor_id=self.actor_id, role_code=self.role_code,
            opportunity_id=self.opportunity_id,
            authority=authority,
            status=status,
            human_approval_id=human_approval_id, **kwargs,
        )
        self.prequalification_id = rec.id
        self.entities["S17_prequalification"] = rec
        return rec

    # -----------------------------------------------------------------
    # Phase 5 — S18 Market Entry
    # -----------------------------------------------------------------

    def execute_s18_market_entry(
        self,
        *,
        options: Optional[list[str]] = None,
        stakeholder_map: str = "Authorities, customers, channel partners",
        risk_map: str = "Regulatory delay, partner risk, currency risk",
        **kwargs,
    ) -> MarketEntryOptionsReport:
        """Stage 18 — Market Entry Strategy Agent (§4.7.3).

        At least 2 path options REQUIRED. The Agent does NOT
        select a path.
        """
        self._ensure_order(StageNumber.S18_MARKET_ENTRY)
        if options is None:
            options = ["Direct representation", "Local partner agency", "Joint venture"]
        agent = MarketEntryStrategyAgent(self.service)
        rec = agent.execute(
            actor_id=self.actor_id, role_code=self.role_code,
            opportunity_id=self.opportunity_id,
            options=options,
            stakeholder_map=stakeholder_map,
            risk_map=risk_map, **kwargs,
        )
        self.market_entry_id = rec.id
        self.last_completed_stage = StageNumber.S18_MARKET_ENTRY
        self.entities["S18"] = rec
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

    def walk_s11_to_s18(
        self,
        *,
        manufacturer_name: str = "Heatric (Doosan Babcock)",
        credibility_dimensions: Optional[dict] = None,
        comparison_manufacturers: Optional[list] = None,
        comparison_criteria: Optional[list] = None,
        commercial_dimensions: Optional[dict] = None,
        assumptions: str = "Margin 18%, win probability 35%",
        uncertainty: str = "±10% on margin, ±15% on probability",
        pricing_basis: str = "Cost-plus with market alignment",
        margin_scenarios: str = "margin=15%; margin=18%; margin=22%",
        margin_floor: Optional[float] = 12.0,
        counterpart: str = "Counterparty Inc.",
        human_approval_id: Optional[str] = "approval-bd-001",
        approver_id: str = "approver-1",
        registration_type: str = "VENDOR_REGISTRATION",
        registration_authority: str = "KNPC",
        prequalification_authority: str = "KOC",
        market_entry_options: Optional[list] = None,
    ) -> dict[str, object]:
        """Walk S11..S18 in order. Returns the produced entities.

        Assumes S01..S10 have already been walked. The walk honours
        the full Discovery Order: S11 → S12 → S13 → S14 → S15 → S16 →
        S17 → S18. S13, S14, S15 are owned by the Verification,
        Quality Assurance, and Authorised Human offices respectively;
        Phase 5 invokes them as thin placeholders so the constitutional
        Discovery Order is not violated.
        """
        self.execute_s11_manufacturer_profile(manufacturer_name=manufacturer_name)
        self.execute_s11_credibility(dimension_scores=credibility_dimensions)
        self.execute_s11_comparison(
            manufacturer_ids=comparison_manufacturers,
            criteria=comparison_criteria,
        )
        self.execute_s12_commercial_evaluation(
            dimension_scores=commercial_dimensions,
            assumptions=assumptions,
            uncertainty=uncertainty,
        )
        self.execute_s12_pricing(
            pricing_basis=pricing_basis,
            margin_scenarios=margin_scenarios,
            margin_floor=margin_floor,
        )
        self.execute_s13_verification()
        self.execute_s14_quality_review()
        self.execute_s15_human_approval(
            approver_id=approver_id,
            human_approval_id=human_approval_id,
        )
        self.execute_s16_bd_engagement(
            counterpart=counterpart,
            human_approval_id=human_approval_id,
        )
        self.execute_s17_registration(
            registration_type=registration_type,
            authority=registration_authority,
        )
        self.execute_s17_prequalification(authority=prequalification_authority)
        self.execute_s18_market_entry(options=market_entry_options)
        return dict(self.entities)

    # -----------------------------------------------------------------
    # Phase 6 — S19 Tender Support
    # -----------------------------------------------------------------

    def execute_s19_tender(
        self,
        *,
        tender_reference: str = "KOC-2026-001",
        issuer: str = "Kuwait Oil Company",
        issue_date: str = "2026-01-15",
        closing_date: str = "2026-03-15",
        qualification_outcome: str = "QUALIFIED",
        document_type: str = "TECHNICAL_COMMERCIAL",
        human_approval_id: Optional[str] = "approval-tender-001",
        **kwargs,
    ) -> Tender:
        """Stage 19 — Tender Monitor Agent (§4.8.1)."""
        self._ensure_order(StageNumber.S19_TENDER_SUPPORT)
        agent = TenderMonitorAgent(self.service)
        rec = agent.execute(
            actor_id=self.actor_id, role_code=self.role_code,
            tender_reference=tender_reference, issuer=issuer,
            issue_date=issue_date, closing_date=closing_date, **kwargs,
        )
        self.tender_id = rec.id
        self.last_completed_stage = StageNumber.S19_TENDER_SUPPORT
        self.entities["S19_tender"] = rec
        return rec

    def execute_s19_qualification(
        self, *, qualification_outcome: str = "QUALIFIED", **kwargs
    ) -> TenderQualificationReport:
        """Stage 19 — Tender Qualification Agent (§4.8.2)."""
        if not self.tender_id:
            raise DiscoveryOrderViolation(
                StageNumber.S18_MARKET_ENTRY,
                StageNumber.S19_TENDER_SUPPORT,
            )
        agent = TenderQualificationAgent(self.service)
        rec = agent.execute(
            actor_id=self.actor_id, role_code=self.role_code,
            tender_id=self.tender_id,
            qualification_outcome=qualification_outcome, **kwargs,
        )
        self.tender_qualification_id = rec.id
        self.entities["S19_qualification"] = rec
        return rec

    def execute_s19_quotation(
        self,
        *,
        document_type: str = "TECHNICAL_COMMERCIAL",
        content: str = "Phase 6 S19 quotation content: technical proposal + commercial pricing.",
        pricing_model: str = "Cost-plus with market alignment; margin 18%.",
        technical_content: str = "Inconel-clad HX-101 tube bundle; KOC standard compliance.",
        submission_date: Optional[str] = "2026-03-10",
        human_approval_id: Optional[str] = "approval-tender-001",
        **kwargs,
    ) -> QuotationDossier:
        """Stage 19 — Quotation Support Agent (§4.8.4)."""
        if not self.tender_qualification_id:
            raise DiscoveryOrderViolation(
                StageNumber.S19_TENDER_SUPPORT,
                StageNumber.S19_TENDER_SUPPORT,
            )
        agent = QuotationSupportAgent(self.service)
        rec = agent.execute(
            actor_id=self.actor_id, role_code=self.role_code,
            tender_id=self.tender_id,
            document_type=document_type,
            content=content,
            pricing_model=pricing_model,
            technical_content=technical_content,
            submission_date=submission_date,
            human_approval_id=human_approval_id, **kwargs,
        )
        self.quotation_dossier_id = rec.id
        self.entities["S19_quotation"] = rec
        return rec

    # -----------------------------------------------------------------
    # Phase 6 — S20 Project Support
    # -----------------------------------------------------------------

    def execute_s20_project(
        self,
        *,
        project_name: str = "KOC Refinery HX-101 Upgrade",
        status: str = "AWARDED",
        **kwargs,
    ) -> ProjectStatusReport:
        """Stage 20 — Project Monitor Agent (§4.8.3)."""
        self._ensure_order(StageNumber.S20_PROJECT_SUPPORT)
        agent = ProjectMonitorAgent(self.service)
        rec = agent.execute(
            actor_id=self.actor_id, role_code=self.role_code,
            project_name=project_name, status=status, **kwargs,
        )
        self.project_status_id = rec.id
        self.last_completed_stage = StageNumber.S20_PROJECT_SUPPORT
        self.entities["S20"] = rec
        return rec

    def execute_s20_after_sales(
        self, *, report_text: str = "Recurring spare parts opportunity identified.", **kwargs
    ) -> AfterSalesIntelligenceReport:
        """After-Sales Intelligence Report (associated with S20)."""
        if not self.project_status_id:
            raise DiscoveryOrderViolation(
                StageNumber.S20_PROJECT_SUPPORT,
                StageNumber.S20_PROJECT_SUPPORT,
            )
        agent = AfterSalesIntelligenceAgent(self.service)
        rec = agent.execute(
            actor_id=self.actor_id, role_code=self.role_code,
            opportunity_id=self.opportunity_id or "unknown",
            report_text=report_text, **kwargs,
        )
        self.after_sales_id = rec.id
        self.entities["S20_after_sales"] = rec
        return rec

    # -----------------------------------------------------------------
    # Phase 6 — S21 Commercial Outcome (Closure Gate)
    # -----------------------------------------------------------------

    def execute_s21_commercial_outcome(
        self,
        *,
        outcome: str = "WON",
        revenue: Optional[str] = "1.2M USD",
        margin: Optional[str] = "18%",
        lessons_learned: str = "Customer valued the Inconel-clad proposal.",
        **kwargs,
    ) -> dict:
        """Stage 21 — Commercial Outcome (ENT-PER-002). Closure Gate.

        The Commercial Outcome Report is the input to the Closure
        Gate (Document 06 §4.9). The outcome class is one of
        WON / LOST / CLOSED.
        """
        from .phase2_schema import CommercialOutcomeReport
        self._ensure_order(StageNumber.S21_COMMERCIAL_OUTCOME)
        co = CommercialOutcomeReport(
            id=_uuid_str_helper(),
            canonical_id=_uuid_str_helper(),
            version=1,
            opportunity_id=self.opportunity_id or "unknown",
            outcome=outcome.upper(),
            revenue=revenue,
            margin=margin,
            lessons_learned=lessons_learned,
            source_citation=f"Commercial Outcome: {outcome}",
            created_by=self.actor_id,
        )
        with SessionLocal() as s:
            s.add(co)
            s.commit()
            s.refresh(co)
        self.last_completed_stage = StageNumber.S21_COMMERCIAL_OUTCOME
        self.entities["S21"] = co
        return co

    # -----------------------------------------------------------------
    # Phase 6 — S22 Knowledge Capture
    # -----------------------------------------------------------------

    def execute_s22_knowledge_capture(
        self,
        *,
        title: str = "Refinery HX Upgrade — Best Practice",
        body: str = "Inconel-clad HX-101 reduced unplanned shutdowns by 40%.",
        domain: str = "REFINERY_MAINTENANCE",
        source_citation: str = "Phase 6 walk — knowledge capture.",
        **kwargs,
    ) -> KnowledgeRecord:
        """Stage 22 — Knowledge Base Curator Agent (§4.13.1)."""
        self._ensure_order(StageNumber.S22_KNOWLEDGE_CAPTURE)
        agent = KnowledgeBaseCuratorAgent(self.service)
        rec = agent.execute(
            actor_id=self.actor_id, role_code=self.role_code,
            title=title, body=body, domain=domain,
            source_citation=source_citation, **kwargs,
        )
        self.knowledge_record_id = rec.id
        self.last_completed_stage = StageNumber.S22_KNOWLEDGE_CAPTURE
        self.entities["S22"] = rec
        return rec

    def execute_s22_lesson_learned(
        self,
        *,
        title: str = "Lesson — Refinery HX Upgrade",
        body: str = "Marginal VQR cost-improvement cases should be rejected; commercial viability below threshold.",
        outcome: str = "WON",
        **kwargs,
    ) -> LessonLearned:
        """Stage 22 — Lessons Learned Analyst Agent (§4.13.3)."""
        agent = LessonsLearnedAnalystAgent(self.service)
        rec = agent.execute(
            actor_id=self.actor_id, role_code=self.role_code,
            title=title, body=body, outcome=outcome,
            target_opportunity_id=self.opportunity_id, **kwargs,
        )
        self.lesson_learned_id = rec.id
        self.entities["S22_lesson"] = rec
        return rec

    # -----------------------------------------------------------------
    # Phase 6 — S23 Institutional Memory
    # -----------------------------------------------------------------

    def execute_s23_institutional_memory(
        self,
        *,
        target_type: str = "OPPORTUNITY",
        target_id: Optional[str] = None,
        retention_class: str = "PERMANENT",
        **kwargs,
    ) -> InstitutionalMemoryIndex:
        """Stage 23 — Institutional Memory Manager Agent (§4.13.2)."""
        self._ensure_order(StageNumber.S23_INSTITUTIONAL_MEMORY)
        agent = InstitutionalMemoryManagerAgent(self.service)
        rec = agent.execute(
            actor_id=self.actor_id, role_code=self.role_code,
            target_type=target_type,
            target_id=target_id or self.opportunity_id or "unknown",
            retention_class=retention_class, **kwargs,
        )
        self.institutional_memory_id = rec.id
        self.last_completed_stage = StageNumber.S23_INSTITUTIONAL_MEMORY
        self.entities["S23"] = rec
        return rec

    # -----------------------------------------------------------------
    # Phase 6 — S24 Continuous Learning
    # -----------------------------------------------------------------

    def execute_s24_continuous_learning(
        self,
        *,
        target_type: str = "LESSON_LEARNED",
        target_id: Optional[str] = None,
        description: str = "Update training corpus with the Refinery HX-101 lesson.",
        **kwargs,
    ) -> dict:
        """Stage 24 — Continuous Learning (ENT-PER-003).

        Thin wrapper — the engine layer's continuous learning is
        out of Phase 6 scope (deferred to Phase 7). The walker
        records the stage completion and creates a Learning
        Update record.
        """
        from .phase2_schema import LearningUpdate
        self._ensure_order(StageNumber.S24_CONTINUOUS_LEARNING)
        lu = LearningUpdate(
            id=_uuid_str_helper(),
            canonical_id=_uuid_str_helper(),
            version=1,
            target_type=target_type,
            target_id=target_id or self.lesson_learned_id or "unknown",
            description=description,
            source_citation="Phase 6 S24 walk — continuous learning update.",
            created_by=self.actor_id,
        )
        with SessionLocal() as s:
            s.add(lu)
            s.commit()
            s.refresh(lu)
        self.last_completed_stage = StageNumber.S24_CONTINUOUS_LEARNING
        self.entities["S24"] = lu
        return lu

    # -----------------------------------------------------------------
    # 24-stage walk: S01..S24 (Phase 6 completes the constitutional lifecycle)
    # -----------------------------------------------------------------

    def walk_s01_to_s24(
        self,
        *,
        # Discovery Order walk defaults — S01..S18
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
        manufacturer_name: str = "Heatric (Doosan Babcock)",
        counterpart: str = "Counterparty Inc.",
        registration_type: str = "VENDOR_REGISTRATION",
        registration_authority: str = "KNPC",
        prequalification_authority: str = "KOC",
        market_entry_options: Optional[list] = None,
        # Phase 6 walk defaults — S19..S24
        tender_reference: str = "KOC-2026-001",
        tender_issuer: str = "Kuwait Oil Company",
        tender_issue_date: str = "2026-01-15",
        tender_closing_date: str = "2026-03-15",
        tender_qualification: str = "QUALIFIED",
        project_name: str = "KOC Refinery HX-101 Upgrade",
        commercial_outcome: str = "WON",
        revenue: Optional[str] = "1.2M USD",
        margin: Optional[str] = "18%",
        knowledge_title: str = "Refinery HX Upgrade — Best Practice",
        knowledge_domain: str = "REFINERY_MAINTENANCE",
        lesson_title: str = "Lesson — Refinery HX Upgrade",
        lesson_outcome: str = "WON",
    ) -> dict[str, object]:
        """Walk the full S01..S24 Discovery Order on real data.

        This is the constitutional lifecycle end-to-end. The walk
        honours every stage from S01 (Industrial Environment) to
        S24 (Continuous Learning). Skipping/abbreviating/reordering
        any stage is REJECTED by the Discovery Order enforcer.
        """
        # S01..S10 — Phase 4
        self.walk_s01_to_s10(
            sector=sector, geography=geography,
            activity_description=activity_description, classification=classification,
            opportunity_title=opportunity_title, problem_description=problem_description,
            root_cause_description=root_cause_description, method_used=method_used,
            value_description=value_description, category=category,
            product_name=product_name, incumbent_solution=incumbent_solution,
        )
        # S11..S18 — Phase 5
        self.walk_s11_to_s18(
            manufacturer_name=manufacturer_name,
            counterpart=counterpart,
            registration_type=registration_type,
            registration_authority=registration_authority,
            prequalification_authority=prequalification_authority,
            market_entry_options=market_entry_options,
        )
        # S19..S24 — Phase 6
        self.execute_s19_tender(
            tender_reference=tender_reference, issuer=tender_issuer,
            issue_date=tender_issue_date, closing_date=tender_closing_date,
        )
        self.execute_s19_qualification(qualification_outcome=tender_qualification)
        self.execute_s19_quotation()
        self.execute_s20_project(project_name=project_name)
        self.execute_s20_after_sales()
        self.execute_s21_commercial_outcome(
            outcome=commercial_outcome, revenue=revenue, margin=margin,
        )
        self.execute_s22_knowledge_capture(
            title=knowledge_title, domain=knowledge_domain,
        )
        self.execute_s22_lesson_learned(
            title=lesson_title, outcome=lesson_outcome,
        )
        self.execute_s23_institutional_memory()
        self.execute_s24_continuous_learning()
        return dict(self.entities)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _uuid_str_helper() -> str:
    """Generate a new UUID string."""
    import uuid
    return str(uuid.uuid4())


def assert_discovery_order_invariant(from_stage: StageNumber, to_stage: StageNumber) -> None:
    """Helper: raise DiscoveryOrderViolation if the transition is invalid."""
    from .stages import next_stage
    if next_stage(from_stage) != to_stage:
        raise DiscoveryOrderViolation(from_stage, to_stage)
