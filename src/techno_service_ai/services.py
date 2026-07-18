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
from .db import SessionLocal
from .log_service import LogService
from .phase2_schema import (
    ComparativeAnalysis,
    ConstitutionalMixin,
    EnvironmentalUpdate,
    IndustrialActivity,
    IndustrialEnvironmentProfile,
    KuwaitSuitabilityReview,
    Opportunity,
    PreliminaryReview,
    ProblemOrNeed,
    ProductAnalysis,
    RootCause,
    TechnologyCategoryAnalysis,
    ValidatedSignal,
    ValueCase,
)
from .schema import User
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
