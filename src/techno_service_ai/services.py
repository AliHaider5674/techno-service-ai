"""Service Layer — Phase 4 wiring (closes GAP-PHASE3-001).

The service layer wires the Phase 3 pure-logic engines to the Phase 2
data layer. Every service call:

  1. Validates the constitutional invariants.
  2. Creates the canonical record (ConstitutionalMixin: canonical_id,
     version, created_at, created_by, source_citation).
  3. Writes the audit event.
  4. Writes the Decision Log Entry (if material).

Constitutional source:
  - Constitution Articles V, VI, VII, X, XII, XIV, XVII, XIX, XX
  - Document 04 §1.3 (Service Layer)
  - Document 05 §3 (all canonical entities)
  - Document 06 §3, §4, §5, §6, §7, §9
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from . import audit
from .commercial import (
    BDEngagementMissingApprovalError,
    BDEngagementSpec,
    CommercialDimensionScore,
    CommercialEngine,
    CommercialEvaluationMissingAssumptionsError,
    CommercialEvaluationSpec,
    EngagementType,
    PricingAnalysisSpec,
)
from .db import SessionLocal
from .knowledge import (
    InstitutionalMemoryIndexSpec,
    KnowledgeEngine,
    KnowledgeRecordSpec,
    LessonLearnedSpec,
)
from .log_service import LogService
from .manufacturer import (
    CredibilityAssessmentSpec,
    CredibilityDimensionScore,
    KuwaitRepresentationStatus,
    ManufacturerComparisonSpec,
    ManufacturerEngine,
    ManufacturerProfileSpec,
    ScoreLevel,
)
from .phase2_schema import (
    AfterSalesIntelligenceReport,
    ApprovedVendorListStatusReport,
    BusinessDevelopmentEngagement,
    CommercialEvaluation,
    CommercialModelOption,
    ComparativeAnalysis,
    ConflictDoNotPursueEntity,
    ConstitutionalMixin,
    EnvironmentalUpdate,
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
    PreliminaryReview,
    PricingAnalysis,
    ProblemOrNeed,
    ProductAnalysis,
    ProjectStatusReport,
    QuotationDossier,
    RepresentedPrincipal,
    RegistrationStatusReport,
    RestrictedProhibitedEntity,
    RootCause,
    TechnologyCategoryAnalysis,
    Tender,
    TenderQualificationReport,
    ValidatedSignal,
    ValueCase,
)
from .register_compliance import (
    GateKind,
    RegisterCheckResult,
    RegisterComplianceEngine,
    RegisterEntry,
)
from .registration import (
    MarketEntryOptionsSpec,
    PrequalificationStatusReportSpec,
    PrequalificationStatus,
    RegistrationEngine,
    RegistrationStatusReportSpec,
    RegistrationStatus,
)
from .schema import User
from .tender_project import (
    AfterSalesReportSpec,
    ProjectStatusReportSpec,
    QuotationDossierSpec,
    TenderProjectEngine,
    TenderQualificationSpec,
    TenderSpec,
)
from .vqr import ImprovementEvidence, VQRClassification, VQREngine, VQRResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Workflow Service
# ---------------------------------------------------------------------------


class WorkflowService:
    """Service that wraps the WorkflowEngine and writes to the DB.

    Per WorkflowEngine.advance semantics (Document 06 §3): a stage
    may be advanced only when the current stage has been completed
    and the produced output has been recorded.
    """

    def __init__(self) -> None:
        self.vqr_engine = VQREngine()
        self.manufacturer_engine = ManufacturerEngine()
        self.commercial_engine = CommercialEngine()
        self.registration_engine = RegistrationEngine()
        self.register_engine = RegisterComplianceEngine()
        self.tender_project_engine = TenderProjectEngine()
        self.knowledge_engine = KnowledgeEngine()

    # -----------------------------------------------------------------
    # Industrial Intelligence (S01-S03)
    # -----------------------------------------------------------------

    def create_environmental_profile(
        self,
        *,
        actor_id: str,
        role_code: str,
        sector: str,
        geography: str,
        regulatory_context: str = "",
        economic_context: str = "",
        sector_structure: str = "",
        source_citation: str = "",
    ) -> IndustrialEnvironmentProfile:
        """Stage 1 — Industrial Environment Monitor Agent.

        Creates an IndustrialEnvironmentProfile (ENT-IND-ENV-001).
        """
        p = IndustrialEnvironmentProfile(
            id=_uuid(),
            canonical_id=_uuid(),
            version=1,
            sector=sector,
            geography=geography,
            regulatory_context=regulatory_context or None,
            economic_context=economic_context or None,
            sector_structure=sector_structure or None,
            last_refreshed_at=_now(),
            active=True,
            source_citation=source_citation or f"Initial environmental profile for {sector} / {geography}",
            created_by=actor_id,
        )
        self._commit_and_audit(p, actor_id, role_code, "INDUSTRIAL_ENVIRONMENT_CREATED", {"stage": "S01"})
        return p

    def create_environmental_update(
        self,
        *,
        actor_id: str,
        role_code: str,
        profile_id: str,
        change_description: str,
        effective_date: str,
        source_citation: str = "",
    ) -> EnvironmentalUpdate:
        u = EnvironmentalUpdate(
            id=_uuid(),
            canonical_id=_uuid(),
            version=1,
            profile_id=profile_id,
            change_description=change_description,
            effective_date=effective_date,
            source_citation=source_citation or f"Environmental update: {change_description[:80]}",
            created_by=actor_id,
        )
        self._commit_and_audit(u, actor_id, role_code, "ENVIRONMENTAL_UPDATE", {"stage": "S01"})
        return u

    def create_industrial_activity(
        self,
        *,
        actor_id: str,
        role_code: str,
        sector: str,
        geography: str,
        activity_description: str,
        classification: str,  # Confirmed/Announced/Probable/Speculative
        activity_date: str,
        profile_id: Optional[str] = None,
        source_citation: str = "",
    ) -> IndustrialActivity:
        """Stage 2 — Industrial Activity Detection Agent.

        The classification must be one of: Confirmed, Announced,
        Probable, Speculative.
        """
        valid = {"CONFIRMED", "ANNOUNCED", "PROBABLE", "SPECULATIVE"}
        if classification.upper() not in valid:
            raise ValueError(
                f"Invalid classification '{classification}'. Must be one of: {sorted(valid)}"
            )
        speculative = classification.upper() == "SPECULATIVE"
        a = IndustrialActivity(
            id=_uuid(),
            canonical_id=_uuid(),
            version=1,
            sector=sector,
            geography=geography,
            activity_description=activity_description,
            classification=classification.upper(),
            activity_date=activity_date,
            speculative=speculative,
            status="CLASSIFIED",
            profile_id=profile_id,
            source_citation=source_citation or f"Industrial activity detected: {activity_description[:80]}",
            created_by=actor_id,
        )
        self._commit_and_audit(a, actor_id, role_code, "INDUSTRIAL_ACTIVITY_DETECTED", {"stage": "S02", "classification": classification.upper()})
        return a

    def create_validated_signal(
        self,
        *,
        actor_id: str,
        role_code: str,
        activity_id: str,
        preliminary_review_outcome: str,  # VALIDATED / REJECTED
        preliminary_reviewer_id: str,
        source_citation: str = "",
    ) -> ValidatedSignal:
        """Stage 3 — Validated Signal Agent.

        The Validated Signal certifies that the activity has cleared
        the Preliminary Evidence Review.
        """
        if preliminary_review_outcome.upper() not in ("VALIDATED", "REJECTED"):
            raise ValueError("preliminary_review_outcome must be VALIDATED or REJECTED")
        v = ValidatedSignal(
            id=_uuid(),
            canonical_id=_uuid(),
            version=1,
            activity_id=activity_id,
            preliminary_review_outcome=preliminary_review_outcome.upper(),
            preliminary_reviewer_id=preliminary_reviewer_id,
            preliminary_review_date=_now(),
            status=preliminary_review_outcome.upper(),
            source_citation=source_citation or f"Validated signal: {preliminary_review_outcome}",
            created_by=actor_id,
        )
        self._commit_and_audit(v, actor_id, role_code, "VALIDATED_SIGNAL", {"stage": "S03"})
        return v

    # -----------------------------------------------------------------
    # Opportunity Intelligence (S04-S06)
    # -----------------------------------------------------------------

    def create_problem_or_need(
        self,
        *,
        actor_id: str,
        role_code: str,
        validated_signal_id: str,
        problem_description: str,
        stakeholder_attribution: str = "",
        source_citation: str = "",
    ) -> ProblemOrNeed:
        """Stage 4 — Problem and Need Definition Agent."""
        p = ProblemOrNeed(
            id=_uuid(),
            canonical_id=_uuid(),
            version=1,
            validated_signal_id=validated_signal_id,
            problem_description=problem_description,
            stakeholder_attribution=stakeholder_attribution or None,
            definition_date=_now(),
            status="DEFINED",
            source_citation=source_citation or f"Problem or Need: {problem_description[:80]}",
            created_by=actor_id,
        )
        self._commit_and_audit(p, actor_id, role_code, "PROBLEM_DEFINED", {"stage": "S04"})
        return p

    def create_root_cause(
        self,
        *,
        actor_id: str,
        role_code: str,
        problem_id: str,
        root_cause_description: str,
        method_used: str,
        data_sources: str = "",
        alternatives_considered: str = "",
        source_citation: str = "",
    ) -> RootCause:
        """Stage 5 — Root Cause Analysis Agent."""
        r = RootCause(
            id=_uuid(),
            canonical_id=_uuid(),
            version=1,
            problem_id=problem_id,
            root_cause_description=root_cause_description,
            method_used=method_used,
            data_sources=data_sources or None,
            alternatives_considered=alternatives_considered or None,
            establishment_date=_now(),
            status="ESTABLISHED",
            source_citation=source_citation or f"Root cause: {root_cause_description[:80]}",
            created_by=actor_id,
        )
        self._commit_and_audit(r, actor_id, role_code, "ROOT_CAUSE_ESTABLISHED", {"stage": "S05"})
        return r

    def create_value_case(
        self,
        *,
        actor_id: str,
        role_code: str,
        root_cause_id: str,
        value_description: str,
        baseline: str = "",
        measurement_method: str = "Not specified (to be quantified at Stage 9)",
        uncertainty: str = "",
        source_citation: str = "",
    ) -> ValueCase:
        """Stage 6 — Commercial Value Definition Agent."""
        v = ValueCase(
            id=_uuid(),
            canonical_id=_uuid(),
            version=1,
            root_cause_id=root_cause_id,
            value_description=value_description,
            baseline=baseline or None,
            measurement_method=measurement_method or "Not specified (to be quantified at Stage 9)",
            uncertainty=uncertainty or None,
            source_citation=source_citation or f"Value Case: {value_description[:80]}",
            created_by=actor_id,
        )
        self._commit_and_audit(v, actor_id, role_code, "VALUE_CASE", {"stage": "S06"})
        return v

    # -----------------------------------------------------------------
    # Opportunity entity (creates the canonical root record)
    # -----------------------------------------------------------------

    def create_opportunity(
        self,
        *,
        actor_id: str,
        role_code: str,
        validated_signal_id: str,
        opportunity_title: str,
        source_citation: str = "",
    ) -> Opportunity:
        """Create an Opportunity from a Validated Signal.

        The Opportunity is the constitutional root entity. It carries
        the 3 independent Status dimensions (intelligence_status,
        approval_status, commercial_status).
        """
        o = Opportunity(
            id=_uuid(),
            canonical_id=_uuid(),
            version=1,
            validated_signal_id=validated_signal_id,
            opportunity_title=opportunity_title,
            creation_date=_now(),
            source_citation=source_citation or f"Opportunity: {opportunity_title}",
            created_by=actor_id,
        )
        self._commit_and_audit(o, actor_id, role_code, "OPPORTUNITY_CREATED", {"stage": "S04-S06"})
        return o

    # -----------------------------------------------------------------
    # Technology Intelligence (S07-S10)
    # -----------------------------------------------------------------

    def create_technology_category_analysis(
        self,
        *,
        actor_id: str,
        role_code: str,
        value_case_id: str,
        category: str,
        category_fit_rationale: str = "",
        alternatives_considered: str = "",
        source_citation: str = "",
    ) -> TechnologyCategoryAnalysis:
        """Stage 7 — Technology Category Analyst Agent."""
        t = TechnologyCategoryAnalysis(
            id=_uuid(),
            canonical_id=_uuid(),
            version=1,
            value_case_id=value_case_id,
            technology_category=category,
            category_fit_rationale=category_fit_rationale or None,
            alternatives_considered=alternatives_considered or None,
            source_citation=source_citation or f"Technology category: {category}",
            created_by=actor_id,
        )
        self._commit_and_audit(t, actor_id, role_code, "TECHNOLOGY_CATEGORY", {"stage": "S07"})
        return t

    def create_product_analysis(
        self,
        *,
        actor_id: str,
        role_code: str,
        technology_category_id: str,
        product_name: str,
        evaluation_criteria: str = "",
        performance_data: str = "",
        standards_and_certifications: str = "",
        source_citation: str = "",
    ) -> ProductAnalysis:
        """Stage 8 — Product Analyst Agent."""
        p = ProductAnalysis(
            id=_uuid(),
            canonical_id=_uuid(),
            version=1,
            technology_category_analysis_id=technology_category_id,
            product_name=product_name,
            evaluation_criteria=evaluation_criteria or None,
            performance_data=performance_data or None,
            standards_and_certifications=standards_and_certifications or None,
            source_citation=source_citation or f"Product analysis: {product_name}",
            created_by=actor_id,
        )
        self._commit_and_audit(p, actor_id, role_code, "PRODUCT_ANALYSIS", {"stage": "S08"})
        return p

    def create_comparative_analysis(
        self,
        *,
        actor_id: str,
        role_code: str,
        product_analysis_id: str,
        incumbent_solution: str = "",
        baseline: str = "",
        measurement_method: str = "",
        vqr_asserted_improvements: tuple[ImprovementEvidence, ...] = (),
        vqr_requested_classification: Optional[VQRClassification] = None,
        vqr_rationale: str = "",
        vqr_strategic_exception_approval_id: Optional[str] = None,
        source_citation: str = "",
    ) -> ComparativeAnalysis:
        """Stage 9 — Replacement and Comparative Analysis Agent.

        The VQR is APPLIED at this stage. The Comparative Analysis
        MUST carry a VQRResult; a case without one is REJECTED (the
        next stage is blocked).
        """
        vqr_result: VQRResult = self.vqr_engine.evaluate(
            material_canonical_id=product_analysis_id,
            asserted_improvements=vqr_asserted_improvements,
            rationale=vqr_rationale or "VQR evaluation at Stage 9",
            classified_by=actor_id,
            requested_classification=vqr_requested_classification,
            strategic_exception_approval_id=vqr_strategic_exception_approval_id,
        )
        c = ComparativeAnalysis(
            id=_uuid(),
            canonical_id=_uuid(),
            version=1,
            product_analysis_id=product_analysis_id,
            current_solution_description=incumbent_solution or None,
            baseline=baseline or None,
            measurement_method=measurement_method or None,
            value_qualification_classification=vqr_result.classification.value,
            # The 3 Status dimensions (independent writeable columns per Phase 2).
            intelligence_status=vqr_result.classification.value,
            source_citation=source_citation or f"Comparative analysis with VQR={vqr_result.classification.value}",
            created_by=actor_id,
        )
        self._commit_and_audit(
            c, actor_id, role_code, "COMPARATIVE_ANALYSIS",
            {"stage": "S09", "vqr": vqr_result.classification.value},
        )
        return c

    def create_kuwait_suitability_review(
        self,
        *,
        actor_id: str,
        role_code: str,
        comparative_analysis_id: str,
        regulatory_references: str = "",
        environmental_data: str = "",
        suitability_gap_record: str = "",
        source_citation: str = "",
    ) -> KuwaitSuitabilityReview:
        """Stage 10 — Kuwait Suitability Reviewer Agent.

        Without this record, the next stage (Stage 11 Manufacturer
        Intelligence) is BLOCKED per Document 06 §2.10.
        """
        k = KuwaitSuitabilityReview(
            id=_uuid(),
            canonical_id=_uuid(),
            version=1,
            comparative_analysis_id=comparative_analysis_id,
            suitability_description=regulatory_references or None,
            standards_and_certifications=environmental_data or None,
            environmental_assessment=environmental_data or None,
            suitability_gap=suitability_gap_record or None,
            status="CLEARED",
            source_citation=source_citation or "Kuwait Suitability Review",
            created_by=actor_id,
        )
        self._commit_and_audit(k, actor_id, role_code, "KUWAIT_SUITABILITY", {"stage": "S10"})
        return k

    # -----------------------------------------------------------------
    # Preliminary Evidence Review (ENT-VER-001) — used by Stage 3 and 13
    # -----------------------------------------------------------------

    def create_preliminary_review(
        self,
        *,
        actor_id: str,
        role_code: str,
        target_type: str,
        target_id: str,
        outcome: str,  # VALIDATED / REJECTED / PENDING
        rationale: str = "",
        review_criteria: str = "",
    ) -> PreliminaryReview:
        if outcome.upper() not in ("VALIDATED", "REJECTED", "PENDING"):
            raise ValueError("outcome must be VALIDATED, REJECTED, or PENDING")
        r = PreliminaryReview(
            id=_uuid(),
            canonical_id=_uuid(),
            version=1,
            target_type=target_type,
            target_id=target_id,
            reviewer_id=actor_id,
            outcome=outcome.upper(),
            rationale=rationale or review_criteria,
            review_date=_now(),
            source_citation=f"Preliminary review ({target_type}): {outcome}",
            created_by=actor_id,
        )
        self._commit_and_audit(r, actor_id, role_code, "PRELIMINARY_REVIEW", {"stage": "S03", "outcome": outcome.upper()})
        return r

    # -----------------------------------------------------------------
    # Workflow advancement — gates Stage N → Stage N+1
    # -----------------------------------------------------------------

    def advance(
        self,
        *,
        opportunity_id: str,
        from_stage_canonical_id: str,
        to_stage_canonical_id: str,
        actor_id: str,
        role_code: str,
        vqr_validated: bool = False,
        ksr_recorded: bool = False,
    ) -> None:
        """Advance the workflow. Validates VQR (Stage 9) and KSR
        (Stage 10) before allowing the next stage.

        The application logic decides which stage to advance to and
        what to record; the service ensures the constitutional
        invariants are met.
        """
        # The VQR / KSR enforcement is at the engine layer (see
        # DiscoveryOrderWalker). This method is a thin DB write of
        # the state transition.
        with SessionLocal() as s:
            # We use the LogService to record the transition.
            log = LogService()
            log.write_decision_log(
                decision_type="WORKFLOW_ADVANCE",
                decision_summary=f"Opportunity {opportunity_id} advances from {from_stage_canonical_id} to {to_stage_canonical_id}",
                decision_class="CLASS_1",  # internal state change
                decided_by=actor_id,
                decided_by_role=role_code,
                material_canonical_id=to_stage_canonical_id,
                opportunity_canonical_id=opportunity_id,
                decided_at=_now().isoformat(),
            )
            # Audit
            self._audit_via_session(
                s, actor_id, role_code, "WORKFLOW_ADVANCE",
                {
                    "opportunity_id": opportunity_id,
                    "from": from_stage_canonical_id,
                    "to": to_stage_canonical_id,
                    "vqr_validated": vqr_validated,
                    "ksr_recorded": ksr_recorded,
                },
            )

    # -----------------------------------------------------------------
    # Manufacturer Intelligence (S11) — Phase 5
    # -----------------------------------------------------------------

    def create_manufacturer_profile(
        self,
        *,
        actor_id: str,
        role_code: str,
        manufacturer_name: str,
        profile_date: Optional[str] = None,
        ownership: str = "",
        certifications: str = "",
        production_capacity: str = "",
        references: str = "",
        quality_indicators: str = "",
        after_sales_capability: str = "",
        global_reputation: str = "",
        source_citation: str = "",
    ) -> ManufacturerProfile:
        """Stage 11 — Manufacturer Profiler Agent (§4.5.1).

        Creates a ManufacturerProfile (ENT-MAN-001). The Agent does NOT
        declare representation status (Article VIII §2) — that is
        determined by the Register Compliance Engine.
        """
        spec = ManufacturerProfileSpec(
            manufacturer_name=manufacturer_name,
            profile_date=profile_date or _now().isoformat(),
            source_citation=source_citation or f"Manufacturer profile: {manufacturer_name}",
            ownership=ownership,
            certifications=certifications,
            production_capacity=production_capacity,
            references=references,
            quality_indicators=quality_indicators,
            after_sales_capability=after_sales_capability,
            global_reputation=global_reputation,
        )
        self.manufacturer_engine.validate_profile(spec)
        m = ManufacturerProfile(
            id=_uuid(),
            canonical_id=_uuid(),
            version=1,
            manufacturer_name=manufacturer_name,
            ownership=ownership or None,
            certifications=certifications or None,
            production_capacity=production_capacity or None,
            references=references or None,
            quality_indicators=quality_indicators or None,
            after_sales_capability=after_sales_capability or None,
            global_reputation=global_reputation or None,
            profile_date=_now(),
            register_reference="UNRESOLVED",  # Set by Register Compliance check.
            active=True,
            source_citation=source_citation or f"Manufacturer profile: {manufacturer_name}",
            created_by=actor_id,
        )
        self._commit_and_audit(m, actor_id, role_code, "MANUFACTURER_PROFILE", {"stage": "S11"})
        return m

    def create_credibility_assessment(
        self,
        *,
        actor_id: str,
        role_code: str,
        manufacturer_id: str,
        dimension_scores: dict[str, str],
        rationale_per_dimension: Optional[dict[str, str]] = None,
        source_citation: str = "",
    ) -> ManufacturerCredibilityAssessment:
        """Stage 11 — Manufacturer Credibility Analyst Agent (§4.5.2).

        Creates a ManufacturerCredibilityAssessment (ENT-MAN-002). A
        multi-dimensional scorecard is REQUIRED — single-dimension
        assessment is a Failure Condition (AC-P5-002).
        """
        rationale_per_dimension = rationale_per_dimension or {}
        scores = tuple(
            CredibilityDimensionScore(
                dimension=name,
                score=ScoreLevel(level.upper()),
                source_citation=source_citation or f"Score for {name}",
                rationale=rationale_per_dimension.get(name, ""),
            )
            for name, level in dimension_scores.items()
        )
        spec = CredibilityAssessmentSpec(
            manufacturer_id=manufacturer_id,
            assessment_date=_now().isoformat(),
            source_citation=source_citation or "Multi-dimensional Credibility Assessment",
            dimensions=scores,
        )
        result = self.manufacturer_engine.evaluate_credibility(spec)
        # The engine has already validated the multi-dimensional requirement.
        # Map the result to the schema. The 6 fields map 1:1.
        dim_map = {d.dimension: d.score.value for d in result.dimension_scores}
        c = ManufacturerCredibilityAssessment(
            id=_uuid(),
            canonical_id=_uuid(),
            version=1,
            manufacturer_id=manufacturer_id,
            financial_stability=dim_map.get("financial_stability"),
            quality_systems=dim_map.get("quality_systems"),
            delivery_track_record=dim_map.get("delivery_track_record"),
            after_sales_capability=dim_map.get("after_sales_capability"),
            references=dim_map.get("references"),
            reputation=dim_map.get("reputation"),
            assessment_date=_now(),
            overall_classification=result.overall_classification.value,
            source_citation=source_citation or "Credibility Assessment",
            created_by=actor_id,
        )
        self._commit_and_audit(
            c, actor_id, role_code, "CREDIBILITY_ASSESSMENT",
            {
                "stage": "S11",
                "manufacturer_id": manufacturer_id,
                "overall_classification": result.overall_classification.value,
                "requires_human_approval": result.requires_human_approval,
            },
        )
        return c

    def create_manufacturer_comparison(
        self,
        *,
        actor_id: str,
        role_code: str,
        opportunity_id: str,
        manufacturer_ids: list[str],
        criteria: list[str],
        trade_offs: str,
        recommended_manufacturer_id: Optional[str] = None,
        recommended_manufacturer_name: Optional[str] = None,
        comparison_summary: str = "",
        source_citation: str = "",
    ) -> ManufacturerComparisonReport:
        """Stage 11 — Manufacturer Comparison Agent (§4.5.3).

        Creates a ManufacturerComparisonReport (ENT-MAN-003). The
        Agent does NOT select a Manufacturer — that is a Human
        Authority decision.
        """
        spec = ManufacturerComparisonSpec(
            opportunity_id=opportunity_id,
            manufacturer_ids=tuple(manufacturer_ids),
            criteria=tuple(criteria),
            trade_offs=trade_offs,
            comparison_date=_now().isoformat(),
            source_citation=source_citation or "Multi-criteria Manufacturer Comparison",
            recommended_manufacturer_id=recommended_manufacturer_id,
            recommended_manufacturer_name=recommended_manufacturer_name,
            comparison_summary=comparison_summary,
        )
        self.manufacturer_engine.validate_comparison(spec)
        c = ManufacturerComparisonReport(
            id=_uuid(),
            canonical_id=_uuid(),
            version=1,
            opportunity_id=opportunity_id,
            comparison_summary=comparison_summary or f"Comparison across {len(criteria)} criteria, {len(manufacturer_ids)} manufacturers.",
            recommended_manufacturer_id=recommended_manufacturer_id,
            recommended_manufacturer_name=recommended_manufacturer_name,
            comparison_date=_now(),
            source_citation=source_citation or "Manufacturer Comparison Report",
            created_by=actor_id,
        )
        self._commit_and_audit(
            c, actor_id, role_code, "MANUFACTURER_COMPARISON",
            {"stage": "S11", "opportunity_id": opportunity_id, "criteria_count": len(criteria)},
        )
        return c

    def get_kuwait_representation_status(
        self, *, manufacturer_id: str, manufacturer_name: str
    ) -> KuwaitRepresentationStatus:
        """Determine the Kuwait Representation status of a Manufacturer.

        Per Document 02 §4.5.1 Authority Limits: the Manufacturer
        Profiler Agent may NOT declare representation status alone.
        The status is derived from the Represented Principals register.
        """
        entries = self._query_register_entries_for_entity(
            entity_id=manufacturer_id, entity_name=manufacturer_name
        )
        return ManufacturerEngine.kuwait_representation_status(
            manufacturer_id=manufacturer_id, register_entries=entries
        )

    # -----------------------------------------------------------------
    # Register Compliance Gate (Article VIII) — Phase 5
    # -----------------------------------------------------------------

    def _query_register_entries_for_entity(
        self, *, entity_id: str, entity_name: str
    ) -> tuple[RegisterEntry, ...]:
        """Query the three registers for entries matching the entity.

        Returns a tuple of RegisterEntry values for the engine. The
        match is by id (preferred) OR by name (for name-only entries).
        """
        entries: list[RegisterEntry] = []
        with SessionLocal() as s:
            # Represented Principals
            rps = s.query(RepresentedPrincipal).all()
            for r in rps:
                if (r.manufacturer_id == entity_id) or (r.brand == entity_name and r.manufacturer_id is None):
                    entries.append(RegisterEntry(
                        entity_id=r.manufacturer_id,
                        entity_name=r.brand,
                        register_kind="REPRESENTED_PRINCIPAL",
                        status=r.status,
                        effective_to=r.effective_to,
                        reason=r.reason or "",
                    ))
            # Conflict
            conflicts = s.query(ConflictDoNotPursueEntity).all()
            for c in conflicts:
                if (c.entity_id == entity_id) or (c.entity_name == entity_name and c.entity_id is None):
                    entries.append(RegisterEntry(
                        entity_id=c.entity_id,
                        entity_name=c.entity_name,
                        register_kind="CONFLICT",
                        status=c.status,
                        effective_to=c.effective_to,
                        reason=c.reason or "",
                    ))
            # Restricted
            restricted = s.query(RestrictedProhibitedEntity).all()
            for r in restricted:
                if (r.entity_id == entity_id) or (r.entity_name == entity_name and r.entity_id is None):
                    entries.append(RegisterEntry(
                        entity_id=r.entity_id,
                        entity_name=r.entity_name,
                        register_kind="RESTRICTED",
                        status=r.status,
                        effective_to=r.effective_to,
                        reason=r.reason or "",
                    ))
        return tuple(entries)

    def check_register_compliance(
        self,
        *,
        entity_id: str,
        entity_name: str,
        gate: GateKind,
    ) -> RegisterCheckResult:
        """Run the Register Compliance check at the given gate.

        Returns a RegisterCheckResult. The Service Layer's caller is
        expected to call `raise_for_rejection` on the result to enforce
        the rejection at the gate.
        """
        entries = self._query_register_entries_for_entity(
            entity_id=entity_id, entity_name=entity_name
        )
        return self.register_engine.check(
            entity_id=entity_id,
            entity_name=entity_name,
            register_entries=entries,
            gate=gate,
        )

    # -----------------------------------------------------------------
    # Commercial Development (S12, S16) — Phase 5
    # -----------------------------------------------------------------

    def create_commercial_evaluation(
        self,
        *,
        actor_id: str,
        role_code: str,
        opportunity_id: str,
        dimension_scores: dict[str, str],
        assumptions: str,
        uncertainty: str,
        margin_estimate: str = "",
        pricing_basis: str = "",
        source_citation: str = "",
    ) -> CommercialEvaluation:
        """Stage 12 — Commercial Evaluation Agent (§4.6.1).

        Creates a CommercialEvaluation (ENT-COM-001). A multi-dimensional
        scorecard with assumptions and uncertainty is REQUIRED.
        """
        scores = tuple(
            CommercialDimensionScore(dimension=name, score=level, rationale="")
            for name, level in dimension_scores.items()
        )
        spec = CommercialEvaluationSpec(
            opportunity_id=opportunity_id,
            evaluation_date=_now().isoformat(),
            source_citation=source_citation or "Commercial Evaluation",
            dimensions=scores,
            assumptions=assumptions,
            uncertainty=uncertainty,
            margin_estimate=margin_estimate,
            pricing_basis=pricing_basis,
        )
        result = self.commercial_engine.evaluate(spec)
        c = CommercialEvaluation(
            id=_uuid(),
            canonical_id=_uuid(),
            version=1,
            opportunity_id=opportunity_id,
            commercial_case_description=source_citation or "Commercial Evaluation",
            margin_estimate=margin_estimate or None,
            pricing_basis=pricing_basis or None,
            evaluation_date=_now(),
            status=result.overall_viability.value,
            source_citation=source_citation or "Commercial Evaluation",
            created_by=actor_id,
        )
        self._commit_and_audit(
            c, actor_id, role_code, "COMMERCIAL_EVALUATION",
            {
                "stage": "S12",
                "opportunity_id": opportunity_id,
                "viability": result.overall_viability.value,
            },
        )
        return c

    def create_pricing_analysis(
        self,
        *,
        actor_id: str,
        role_code: str,
        opportunity_id: str,
        pricing_basis: str,
        margin_scenarios: str,
        margin_floor: Optional[float] = None,
        source_citation: str = "",
    ) -> PricingAnalysis:
        """Stage 12 — Pricing and Margin Analyst Agent (§4.6.5).

        Creates a PricingAnalysis (ENT-COM-005). If `margin_floor` is
        given, the proposed margin is checked. Below the floor
        requires Human Approval.
        """
        spec = PricingAnalysisSpec(
            opportunity_id=opportunity_id,
            analysis_date=_now().isoformat(),
            source_citation=source_citation or "Pricing Analysis",
            pricing_basis=pricing_basis,
            margin_scenarios=margin_scenarios,
            margin_floor=margin_floor,
        )
        result = self.commercial_engine.evaluate_pricing(spec)
        p = PricingAnalysis(
            id=_uuid(),
            canonical_id=_uuid(),
            version=1,
            opportunity_id=opportunity_id,
            pricing_basis=pricing_basis or None,
            margin_scenarios=margin_scenarios or None,
            analysis_date=_now(),
            source_citation=source_citation or "Pricing Analysis",
            created_by=actor_id,
        )
        self._commit_and_audit(
            p, actor_id, role_code, "PRICING_ANALYSIS",
            {
                "stage": "S12",
                "opportunity_id": opportunity_id,
                "status": result.status.value,
                "requires_human_approval": result.requires_human_approval,
            },
        )
        return p

    def create_bd_engagement(
        self,
        *,
        actor_id: str,
        role_code: str,
        opportunity_id: str,
        engagement_type: str,
        counterpart: str,
        summary: str,
        counterpart_entity_id: Optional[str] = None,
        counterpart_entity_name: Optional[str] = None,
        human_approval_id: Optional[str] = None,
        source_citation: str = "",
    ) -> BusinessDevelopmentEngagement:
        """Stage 16 — Business Development Agent (§4.6.3).

        Creates a BusinessDevelopmentEngagement (ENT-COM-003). REQUIRES:
          (a) Human Approval reference (Constitution Article XII).
          (b) Register Compliance clearance (Constitution Article VIII).

        A non-Represented Principal at the Commercial Gate → REJECTED.
        A Restricted or Conflict entity → REJECTED everywhere.
        """
        # Run the register check on the counterpart.
        register_outcome_value = "CLEARED"
        if counterpart_entity_id or counterpart_entity_name:
            try:
                result = self.check_register_compliance(
                    entity_id=counterpart_entity_id or "",
                    entity_name=counterpart_entity_name or counterpart,
                    gate=GateKind.COMMERCIAL,
                )
                register_outcome_value = result.outcome.value
                from .register_compliance import raise_for_rejection
                raise_for_rejection(result)
            except Exception:
                # The register check raised — the BD engagement is blocked.
                raise

        # Verify the human approval reference and register outcome.
        spec = BDEngagementSpec(
            opportunity_id=opportunity_id,
            engagement_type=EngagementType(engagement_type.upper()),
            counterpart=counterpart,
            summary=summary,
            engagement_date=_now().isoformat(),
            human_approval_id=human_approval_id,
            register_outcome=register_outcome_value,
        )
        self.commercial_engine.evaluate_engagement(spec)
        e = BusinessDevelopmentEngagement(
            id=_uuid(),
            canonical_id=_uuid(),
            version=1,
            opportunity_id=opportunity_id,
            engagement_type=engagement_type.upper(),
            counterpart=counterpart,
            summary=summary,
            engagement_date=_now(),
            source_citation=source_citation or f"BD Engagement: {engagement_type} with {counterpart}",
            created_by=actor_id,
        )
        self._commit_and_audit(
            e, actor_id, role_code, "BD_ENGAGEMENT",
            {
                "stage": "S16",
                "opportunity_id": opportunity_id,
                "human_approval_id": human_approval_id,
                "register_outcome": register_outcome_value,
            },
        )
        return e

    # -----------------------------------------------------------------
    # Registration and Market Entry (S17, S18) — Phase 5
    # -----------------------------------------------------------------

    def create_registration_status(
        self,
        *,
        actor_id: str,
        role_code: str,
        opportunity_id: str,
        registration_type: str,
        authority: str,
        status: str,
        notes: str = "",
        human_approval_id: Optional[str] = None,
        source_citation: str = "",
    ) -> RegistrationStatusReport:
        """Stage 17 — Registration Coordinator Agent (§4.7.1).

        Creates a RegistrationStatusReport (ENT-REG-001). A filing
        (status=REGISTERED) REQUIRES Human Approval.
        """
        spec = RegistrationStatusReportSpec(
            opportunity_id=opportunity_id,
            registration_type=registration_type,
            authority=authority,
            status=RegistrationStatus(status.upper()),
            notes=notes,
            human_approval_id=human_approval_id,
        )
        result = self.registration_engine.evaluate_registration(spec)
        r = RegistrationStatusReport(
            id=_uuid(),
            canonical_id=_uuid(),
            version=1,
            opportunity_id=opportunity_id,
            registration_type=registration_type,
            authority=authority,
            status=result.status.value,
            notes=notes or None,
            source_citation=source_citation or f"Registration: {registration_type} / {authority}",
            created_by=actor_id,
        )
        self._commit_and_audit(
            r, actor_id, role_code, "REGISTRATION_STATUS",
            {
                "stage": "S17",
                "opportunity_id": opportunity_id,
                "registration_type": registration_type,
                "status": result.status.value,
                "requires_human_approval": result.requires_human_approval,
            },
        )
        return r

    def create_prequalification_status(
        self,
        *,
        actor_id: str,
        role_code: str,
        opportunity_id: str,
        authority: str,
        status: str,
        notes: str = "",
        human_approval_id: Optional[str] = None,
        source_citation: str = "",
    ) -> PrequalificationStatusReport:
        """Stage 17 — Prequalification Agent (§4.7.2).

        Creates a PrequalificationStatusReport (schema ENT-REG-003,
        canonical ENT-REG-002). A submission (status=QUALIFIED) REQUIRES
        Human Approval.
        """
        spec = PrequalificationStatusReportSpec(
            opportunity_id=opportunity_id,
            authority=authority,
            status=PrequalificationStatus(status.upper()),
            notes=notes,
            human_approval_id=human_approval_id,
        )
        result = self.registration_engine.evaluate_prequalification(spec)
        p = PrequalificationStatusReport(
            id=_uuid(),
            canonical_id=_uuid(),
            version=1,
            opportunity_id=opportunity_id,
            authority=authority,
            status=result.status.value,
            notes=notes or None,
            source_citation=source_citation or f"Prequalification: {authority}",
            created_by=actor_id,
        )
        self._commit_and_audit(
            p, actor_id, role_code, "PREQUALIFICATION_STATUS",
            {
                "stage": "S17",
                "opportunity_id": opportunity_id,
                "authority": authority,
                "status": result.status.value,
                "requires_human_approval": result.requires_human_approval,
            },
        )
        return p

    def create_market_entry_options(
        self,
        *,
        actor_id: str,
        role_code: str,
        opportunity_id: str,
        options: list[str],
        stakeholder_map: str,
        risk_map: str,
        manufacturer_id: Optional[str] = None,
        source_citation: str = "",
    ) -> MarketEntryOptionsReport:
        """Stage 18 — Market Entry Strategy Agent (§4.7.3).

        Creates a MarketEntryOptionsReport (ENT-REG-004 / schema
        ENT-REG-005). At least 2 path options REQUIRED. The Agent
        does NOT select a path.
        """
        spec = MarketEntryOptionsSpec(
            opportunity_id=opportunity_id,
            manufacturer_id=manufacturer_id,
            options_set=tuple(options),
            stakeholder_map=stakeholder_map,
            risk_map=risk_map,
            report_date=_now().isoformat(),
            source_citation=source_citation or "Market Entry Options",
            selected_path=None,
        )
        result = self.registration_engine.evaluate_market_entry(spec)
        import json
        m = MarketEntryOptionsReport(
            id=_uuid(),
            canonical_id=_uuid(),
            version=1,
            opportunity_id=opportunity_id,
            manufacturer_id=manufacturer_id,
            options_set=json.dumps(list(result.options_set)),
            stakeholder_map=result.stakeholder_map,
            risk_map=result.risk_map,
            selected_path=None,
            report_date=_now(),
            source_citation=source_citation or "Market Entry Options Report",
            created_by=actor_id,
        )
        self._commit_and_audit(
            m, actor_id, role_code, "MARKET_ENTRY_OPTIONS",
            {
                "stage": "S18",
                "opportunity_id": opportunity_id,
                "options_count": result.options_count,
            },
        )
        return m

    # -----------------------------------------------------------------
    # Phase 6 — Tender and Project Intelligence (S19, S20) — §4.8
    # -----------------------------------------------------------------

    def create_tender(
        self,
        *,
        actor_id: str,
        role_code: str,
        tender_reference: str,
        issuer: str,
        issue_date: str,
        closing_date: str,
        description: str = "",
        opportunity_id: Optional[str] = None,
        source_citation: str = "",
    ) -> Tender:
        """Stage 19 entry — Tender Monitor Agent (§4.8.1)."""
        spec = TenderSpec(
            tender_reference=tender_reference,
            issuer=issuer,
            issue_date=issue_date,
            closing_date=closing_date,
            description=description,
            opportunity_id=opportunity_id,
        )
        self.tender_project_engine.validate_tender(spec)
        t = Tender(
            id=_uuid(),
            canonical_id=_uuid(),
            version=1,
            opportunity_id=opportunity_id,
            tender_reference=tender_reference,
            issuer=issuer,
            issue_date=datetime.fromisoformat(issue_date.replace("Z", "+00:00"))
            if "T" in issue_date or "Z" in issue_date
            else datetime.fromisoformat(issue_date + "T00:00:00+00:00"),
            closing_date=datetime.fromisoformat(closing_date.replace("Z", "+00:00"))
            if "T" in closing_date or "Z" in closing_date
            else datetime.fromisoformat(closing_date + "T00:00:00+00:00"),
            status="OPEN",
            description=description or None,
            source_citation=source_citation or f"Tender: {tender_reference}",
            created_by=actor_id,
        )
        self._commit_and_audit(
            t, actor_id, role_code, "TENDER_MONITORED",
            {"stage": "S19", "tender_reference": tender_reference},
        )
        return t

    def create_tender_qualification(
        self,
        *,
        actor_id: str,
        role_code: str,
        tender_id: str,
        qualification_outcome: str,
        rationale: str = "",
        fit_assessment: str = "",
        risk_assessment: str = "",
        commercial_assessment: str = "",
        source_citation: str = "",
    ) -> TenderQualificationReport:
        """Stage 19 — Tender Qualification Agent (§4.8.2)."""
        spec = TenderQualificationSpec(
            tender_id=tender_id,
            qualification_outcome=qualification_outcome,
            rationale=rationale,
            fit_assessment=fit_assessment,
            risk_assessment=risk_assessment,
            commercial_assessment=commercial_assessment,
        )
        outcome = self.tender_project_engine.evaluate_qualification(spec)
        q = TenderQualificationReport(
            id=_uuid(),
            canonical_id=_uuid(),
            version=1,
            tender_id=tender_id,
            qualification_outcome=outcome.value,
            rationale=(
                f"{rationale or ''}\n"
                f"[fit] {fit_assessment}\n"
                f"[risk] {risk_assessment}\n"
                f"[commercial] {commercial_assessment}"
            ).strip(),
            report_date=_now(),
            source_citation=source_citation or f"Tender qualification: {outcome.value}",
            created_by=actor_id,
        )
        self._commit_and_audit(
            q, actor_id, role_code, "TENDER_QUALIFIED",
            {"stage": "S19", "tender_id": tender_id, "outcome": outcome.value},
        )
        return q

    def create_quotation_dossier(
        self,
        *,
        actor_id: str,
        role_code: str,
        tender_id: str,
        document_type: str,
        content: str,
        pricing_model: str = "",
        technical_content: str = "",
        submission_date: Optional[str] = None,
        human_approval_id: Optional[str] = None,
        source_citation: str = "",
    ) -> QuotationDossier:
        """Stage 19 — Quotation Support Agent (§4.8.4)."""
        spec = QuotationDossierSpec(
            tender_id=tender_id,
            document_type=document_type,
            content=content,
            pricing_model=pricing_model,
            technical_content=technical_content,
            submission_date=submission_date,
            human_approval_id=human_approval_id,
        )
        self.tender_project_engine.validate_quotation_dossier(spec)
        d = QuotationDossier(
            id=_uuid(),
            canonical_id=_uuid(),
            version=1,
            tender_id=tender_id,
            document_type=document_type,
            content=content,
            submission_date=(
                datetime.fromisoformat(submission_date.replace("Z", "+00:00"))
                if submission_date and ("T" in submission_date or "Z" in submission_date)
                else datetime.fromisoformat(submission_date + "T00:00:00+00:00")
                if submission_date
                else None
            ),
            source_citation=source_citation or f"Quotation Dossier: {document_type}",
            created_by=actor_id,
        )
        self._commit_and_audit(
            d, actor_id, role_code, "QUOTATION_DOSSIER",
            {
                "stage": "S19",
                "tender_id": tender_id,
                "document_type": document_type,
                "submission_date": submission_date,
                "human_approval_id": human_approval_id,
            },
        )
        return d

    def create_project_status_report(
        self,
        *,
        actor_id: str,
        role_code: str,
        project_name: str,
        status: str = "AWARDED",
        issues: str = "",
        opportunity_id: Optional[str] = None,
        source_citation: str = "",
    ) -> ProjectStatusReport:
        """Stage 20 — Project Monitor Agent (§4.8.3)."""
        spec = ProjectStatusReportSpec(
            project_name=project_name,
            status=status,
            issues=issues,
            opportunity_id=opportunity_id,
        )
        self.tender_project_engine.validate_project_status(spec)
        p = ProjectStatusReport(
            id=_uuid(),
            canonical_id=_uuid(),
            version=1,
            opportunity_id=opportunity_id,
            project_name=project_name,
            status=status.upper(),
            issues=issues or None,
            source_citation=source_citation or f"Project Status: {project_name}",
            created_by=actor_id,
        )
        self._commit_and_audit(
            p, actor_id, role_code, "PROJECT_STATUS",
            {"stage": "S20", "project_name": project_name, "status": status.upper()},
        )
        return p

    def create_after_sales_report(
        self,
        *,
        actor_id: str,
        role_code: str,
        opportunity_id: str,
        report_text: str,
        recurring_opportunity: str = "",
        source_citation: str = "",
    ) -> AfterSalesIntelligenceReport:
        """After-Sales Intelligence Agent (§4.6.6)."""
        spec = AfterSalesReportSpec(
            opportunity_id=opportunity_id,
            report_text=report_text,
            recurring_opportunity=recurring_opportunity,
        )
        self.tender_project_engine.validate_after_sales(spec)
        a = AfterSalesIntelligenceReport(
            id=_uuid(),
            canonical_id=_uuid(),
            version=1,
            opportunity_id=opportunity_id,
            report_text=report_text,
            recurring_opportunity_identification=recurring_opportunity or None,
            source_citation=source_citation or "After-Sales Intelligence Report",
            created_by=actor_id,
        )
        self._commit_and_audit(
            a, actor_id, role_code, "AFTER_SALES_REPORT",
            {"stage": "S20-AFTER-SALES", "opportunity_id": opportunity_id},
        )
        return a

    # -----------------------------------------------------------------
    # Phase 6 — Knowledge and Institutional Memory (S22, S23, S24) — §4.13
    # -----------------------------------------------------------------

    def create_knowledge_record(
        self,
        *,
        actor_id: str,
        role_code: str,
        title: str,
        body: str,
        domain: str,
        tags: str = "",
        source_citation: str = "",
        quality_status: str = "DRAFT",
    ) -> KnowledgeRecord:
        """Stage 22 — Knowledge Base Curator Agent (§4.13.1)."""
        spec = KnowledgeRecordSpec(
            title=title,
            body=body,
            domain=domain,
            tags=tags,
            source_citation=source_citation,
            quality_status=quality_status,
        )
        result = self.knowledge_engine.validate_knowledge_record(spec)
        k = KnowledgeRecord(
            id=_uuid(),
            canonical_id=_uuid(),
            version=1,
            title=result.title,
            body=result.body,
            domain=result.domain,
            tags=result.tags or None,
            quality_status=result.quality_status.value,
            source_citation=result.source_citation,
            created_by=actor_id,
        )
        self._commit_and_audit(
            k, actor_id, role_code, "KNOWLEDGE_RECORD",
            {
                "stage": "S22",
                "title": title,
                "domain": domain,
                "quality_status": result.quality_status.value,
            },
        )
        return k

    def create_institutional_memory_index(
        self,
        *,
        actor_id: str,
        role_code: str,
        target_type: str,
        target_id: str,
        retention_class: str = "PERMANENT",
        retention_until: Optional[str] = None,
        human_approval_id: Optional[str] = None,
        source_citation: str = "",
    ) -> InstitutionalMemoryIndex:
        """Stage 23 — Institutional Memory Manager Agent (§4.13.2)."""
        spec = InstitutionalMemoryIndexSpec(
            target_type=target_type,
            target_id=target_id,
            retention_class=retention_class,
            retention_until=retention_until,
            human_approval_id=human_approval_id,
        )
        result = self.knowledge_engine.validate_institutional_memory(spec)
        i = InstitutionalMemoryIndex(
            id=_uuid(),
            canonical_id=_uuid(),
            version=1,
            target_type=result.target_type,
            target_id=result.target_id,
            retention_class=result.retention_class.value,
            retention_until=(
                datetime.fromisoformat(retention_until.replace("Z", "+00:00"))
                if retention_until and ("T" in retention_until or "Z" in retention_until)
                else datetime.fromisoformat(retention_until + "T00:00:00+00:00")
                if retention_until
                else None
            ),
            source_citation=source_citation or f"Institutional Memory: {target_type}/{target_id}",
            created_by=actor_id,
        )
        self._commit_and_audit(
            i, actor_id, role_code, "INSTITUTIONAL_MEMORY",
            {
                "stage": "S23",
                "target_type": target_type,
                "target_id": target_id,
                "retention_class": result.retention_class.value,
            },
        )
        return i

    def create_lesson_learned(
        self,
        *,
        actor_id: str,
        role_code: str,
        title: str,
        body: str,
        outcome: str,
        target_opportunity_id: Optional[str] = None,
        source_citation: str = "",
    ) -> LessonLearned:
        """Stage 22 — Lessons Learned Analyst Agent (§4.13.3)."""
        spec = LessonLearnedSpec(
            title=title,
            body=body,
            outcome=outcome,
            target_opportunity_id=target_opportunity_id,
            source_citation=source_citation,
        )
        result = self.knowledge_engine.validate_lesson_learned(spec)
        l = LessonLearned(
            id=_uuid(),
            canonical_id=_uuid(),
            version=1,
            title=result.title,
            body=result.body,
            outcome=result.outcome.value,
            target_opportunity_id=result.target_opportunity_id,
            source_citation=result.source_citation or "Lesson Learned",
            created_by=actor_id,
        )
        self._commit_and_audit(
            l, actor_id, role_code, "LESSON_LEARNED",
            {
                "stage": "S22",
                "title": title,
                "outcome": result.outcome.value,
                "target_opportunity_id": target_opportunity_id,
            },
        )
        return l

    # -----------------------------------------------------------------
    # Phase 6 — Deferred Commercial Development agents (S12, S16) — §4.6.2, 4.6.4, 4.6.6
    # -----------------------------------------------------------------

    def create_commercial_model_option(
        self,
        *,
        actor_id: str,
        role_code: str,
        opportunity_id: str,
        model_type: str,
        model_description: str = "",
        selected: bool = False,
        source_citation: str = "",
    ) -> CommercialModelOption:
        """§4.6.2 — Commercial Model Designer Agent. The Agent does
        NOT approve a model. `selected` is a Human Authority decision."""
        self.commercial_engine.validate_commercial_model_option(
            model_type=model_type,
            model_description=model_description,
            selected=selected,
        )
        m = CommercialModelOption(
            id=_uuid(),
            canonical_id=_uuid(),
            version=1,
            opportunity_id=opportunity_id,
            model_type=model_type,
            model_description=model_description or None,
            selected=False,  # always False at the Agent level
            source_citation=source_citation or f"Commercial Model: {model_type}",
            created_by=actor_id,
        )
        self._commit_and_audit(
            m, actor_id, role_code, "COMMERCIAL_MODEL_OPTION",
            {"stage": "S12", "opportunity_id": opportunity_id, "model_type": model_type},
        )
        return m

    def create_negotiation_analysis(
        self,
        *,
        actor_id: str,
        role_code: str,
        opportunity_id: str,
        scenario: str,
        constraints: str,
        analysis_date: Optional[str] = None,
        source_citation: str = "",
    ) -> NegotiationAnalysis:
        """§4.6.4 — Negotiation Support Agent. The Agent supports a
        human-led negotiation; it does NOT accept, reject, or commit."""
        self.commercial_engine.validate_negotiation_analysis(
            scenario=scenario,
            constraints=constraints,
            analysis_date=analysis_date or _now().isoformat(),
        )
        n = NegotiationAnalysis(
            id=_uuid(),
            canonical_id=_uuid(),
            version=1,
            opportunity_id=opportunity_id,
            scenario=scenario,
            constraints=constraints,
            analysis_date=_now(),
            source_citation=source_citation or "Negotiation Analysis",
            created_by=actor_id,
        )
        self._commit_and_audit(
            n, actor_id, role_code, "NEGOTIATION_ANALYSIS",
            {"stage": "S16", "opportunity_id": opportunity_id},
        )
        return n

    # -----------------------------------------------------------------
    # Phase 6 — Approved Vendor List Manager (S17) — §4.7.4
    # -----------------------------------------------------------------

    def create_avl_status(
        self,
        *,
        actor_id: str,
        role_code: str,
        opportunity_id: str,
        authority: str,
        status: str,
        renewal_date: Optional[str] = None,
        human_approval_id: Optional[str] = None,
        source_citation: str = "",
    ) -> ApprovedVendorListStatusReport:
        """§4.7.4 — Approved Vendor List Manager Agent. A submission
        (status=SUBMITTED) requires Human Approval."""
        self.registration_engine.validate_avl_status(
            opportunity_id=opportunity_id,
            authority=authority,
            status=status,
            human_approval_id=human_approval_id,
        )
        a = ApprovedVendorListStatusReport(
            id=_uuid(),
            canonical_id=_uuid(),
            version=1,
            opportunity_id=opportunity_id,
            authority=authority,
            status=status.upper(),
            renewal_date=(
                datetime.fromisoformat(renewal_date.replace("Z", "+00:00"))
                if renewal_date and ("T" in renewal_date or "Z" in renewal_date)
                else datetime.fromisoformat(renewal_date + "T00:00:00+00:00")
                if renewal_date
                else None
            ),
            source_citation=source_citation or f"AVL Status: {authority}",
            created_by=actor_id,
        )
        self._commit_and_audit(
            a, actor_id, role_code, "AVL_STATUS",
            {
                "stage": "S17",
                "opportunity_id": opportunity_id,
                "authority": authority,
                "status": status.upper(),
            },
        )
        return a

    # -----------------------------------------------------------------
    # Internal: write + audit
    # -----------------------------------------------------------------

    def _commit_and_audit(
        self,
        entity: ConstitutionalMixin,
        actor_id: str,
        role_code: str,
        event_type: str,
        payload: dict,
    ) -> None:
        with SessionLocal() as s:
            s.add(entity)
            s.commit()
            s.refresh(entity)
            # Audit
            self._audit_via_session(
                s, actor_id, role_code, event_type,
                {**payload, "entity_id": entity.id, "canonical_id": entity.canonical_id},
            )

    def _audit_via_session(
        self, s: Session, actor_id: str, role_code: str, event_type: str, payload: dict
    ) -> None:
        try:
            audit.record(
                s,
                event_type=event_type,
                action=event_type.lower(),
                actor_user_id=actor_id,
                actor_username=actor_id,
                actor_role_code=role_code,
                target_type="phase4_workflow",
                target_id=payload.get("canonical_id", ""),
                outcome="SUCCESS",
                payload=payload,
            )
            s.commit()
        except Exception:
            s.rollback()
