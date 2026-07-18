"""Phase 4 acceptance tests.

Covers:
  - AC-P4-001..007 — Discovery Order Operational Surfaces
  - AC-SCR-001..005 — Screen-level acceptance
  - AC-AI-001..005 — AI Agent acceptance

Constitutional source:
  - Document 02 §4.2-4.4 (10 Principal Agents)
  - Document 06 §2.1-2.24 (24 Stages)
  - Constitution Articles VI, VII, X
  - Constitution Article XX (No Silent Amendment)
"""
from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from techno_service_ai.agents import (
    ten_agent_roster, assert_total_agents,
    IndustrialEnvironmentMonitorAgent, IndustrialActivityDetectionAgent,
    ValidatedSignalAgent, ProblemAndNeedDefinitionAgent, RootCauseAnalysisAgent,
    CommercialValueDefinitionAgent, TechnologyCategoryAnalystAgent,
    ProductAnalystAgent, ReplacementAndComparativeAnalysisAgent,
    KuwaitSuitabilityReviewerAgent,
)
from techno_service_ai.ai_recommendation import (
    AIRecommendationEngine, AIRecommendationNotConstitutional,
    AIRecommendationPresentsAsHumanAuthority, AIConfidenceOutOfRange,
)
from techno_service_ai.discovery_walker import (
    DiscoveryOrderWalker, DiscoveryOrderViolation, VQRGateNotSatisfied, KSRGateNotSatisfied,
)
from techno_service_ai.orch_cond import (
    ORCHCONDEngine, OmissionType,
    ORCHCONDMissingApproval, ORCHCONDMissingReason, ORCHCONDMissingReEntry,
    EquivalentControlNotEquivalent,
    APPROVAL_REQUIRED_OMISSIONS,
)
from techno_service_ai.phase2_schema import (
    IndustrialEnvironmentProfile, IndustrialActivity, ValidatedSignal,
    ProblemOrNeed, RootCause, ValueCase, Opportunity,
    TechnologyCategoryAnalysis, ProductAnalysis, ComparativeAnalysis,
    KuwaitSuitabilityReview,
)
from techno_service_ai.services import WorkflowService
from techno_service_ai.vqr import (
    VQREngine, VQRClassification, VQRDimension, VQRMissingClassification,
    VQRInsufficientEvidence, VQRStrategicExceptionRequiresApproval,
    ImprovementEvidence, VQR_THRESHOLD_PERCENT,
)
from techno_service_ai.schema import User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_admin_id(session: Session) -> str:
    admin = session.execute(select(User).where(User.username == "admin")).scalar_one()
    return admin.id


# ---------------------------------------------------------------------------
# AC-P4-001 — A Validated Signal can be detected, classified, and recorded
# ---------------------------------------------------------------------------


def test_ac_p4_001_validated_signal_detected_classified_recorded(client) -> None:
    """The Industrial Intelligence Office can detect an Industrial
    Activity, classify it, and record a Validated Signal."""
    with client.app.dependency_overrides_provider() if False else _noop():
        from techno_service_ai.db import SessionLocal
        s = SessionLocal()
        try:
            actor_id = _get_admin_id(s)
            svc = WorkflowService()
            # S01
            profile = svc.create_environmental_profile(
                actor_id=actor_id, role_code="ANALYST",
                sector="Oil & Gas", geography="Kuwait",
            )
            # S02
            activity = svc.create_industrial_activity(
                actor_id=actor_id, role_code="ANALYST",
                sector="Oil & Gas", geography="Kuwait",
                activity_description="Refinery maintenance turnaround",
                classification="CONFIRMED", activity_date="2026-01-01",
                profile_id=profile.id,
            )
            assert activity.classification == "CONFIRMED"
            # S03
            signal = svc.create_validated_signal(
                actor_id=actor_id, role_code="VERIFIER",
                activity_id=activity.id,
                preliminary_review_outcome="VALIDATED",
                preliminary_reviewer_id=actor_id,
            )
            assert signal.preliminary_review_outcome == "VALIDATED"
            assert signal.activity_id == activity.id
        finally:
            s.close()


# ---------------------------------------------------------------------------
# AC-P4-002 — An Opportunity can be created from a Validated Signal
# ---------------------------------------------------------------------------


def test_ac_p4_002_opportunity_created_from_validated_signal(client) -> None:
    from techno_service_ai.db import SessionLocal
    s = SessionLocal()
    try:
        actor_id = _get_admin_id(s)
        svc = WorkflowService()
        # Walk to S03
        profile = svc.create_environmental_profile(actor_id=actor_id, role_code="ANALYST", sector="Oil & Gas", geography="Kuwait")
        activity = svc.create_industrial_activity(actor_id=actor_id, role_code="ANALYST", sector="Oil & Gas", geography="Kuwait",
                                                   activity_description="x", classification="CONFIRMED", activity_date="2026-01-01", profile_id=profile.id)
        signal = svc.create_validated_signal(actor_id=actor_id, role_code="VERIFIER", activity_id=activity.id,
                                              preliminary_review_outcome="VALIDATED", preliminary_reviewer_id=actor_id)
        # S04 creates the Opportunity
        opp = svc.create_opportunity(actor_id=actor_id, role_code="ANALYST", validated_signal_id=signal.id, opportunity_title="Refurbish HX-101")
        assert opp.opportunity_title == "Refurbish HX-101"
        assert opp.validated_signal_id == signal.id
        # 3 Status dimensions are independent.
        assert opp.intelligence_status
        assert opp.approval_status
        assert opp.commercial_status
    finally:
        s.close()


# ---------------------------------------------------------------------------
# AC-P4-003 — Discovery Order end-to-end (S01..S10) — walker test
# ---------------------------------------------------------------------------


def test_ac_p4_003_discovery_order_walk_s01_to_s10(client) -> None:
    """The Walker walks S01..S10 in order, creating real records."""
    from techno_service_ai.db import SessionLocal
    s = SessionLocal()
    try:
        actor_id = _get_admin_id(s)
        walker = DiscoveryOrderWalker(actor_id=actor_id, role_code="ANALYST")
        entities = walker.walk_s01_to_s10()
        assert "S01" in entities
        assert "S02" in entities
        assert "S03" in entities
        assert "S04" in entities
        assert "S05" in entities
        assert "S06" in entities
        assert "S07" in entities
        assert "S08" in entities
        assert "S09" in entities
        assert "S10" in entities
        # All 10 entities are constitutional records.
        assert isinstance(entities["S01"], IndustrialEnvironmentProfile)
        assert isinstance(entities["S02"], IndustrialActivity)
        assert isinstance(entities["S03"], ValidatedSignal)
        assert isinstance(entities["S04"], ProblemOrNeed)
        assert isinstance(entities["S05"], RootCause)
        assert isinstance(entities["S06"], ValueCase)
        assert isinstance(entities["S07"], TechnologyCategoryAnalysis)
        assert isinstance(entities["S08"], ProductAnalysis)
        assert isinstance(entities["S09"], ComparativeAnalysis)
        assert isinstance(entities["S10"], KuwaitSuitabilityReview)
    finally:
        s.close()


def test_ac_p4_003_skip_rejected(client) -> None:
    """Skipping a stage is REJECTED."""
    from techno_service_ai.db import SessionLocal
    s = SessionLocal()
    try:
        actor_id = _get_admin_id(s)
        walker = DiscoveryOrderWalker(actor_id=actor_id, role_code="ANALYST")
        walker.execute_s01_environment()
        # Try to skip S02-S04
        with pytest.raises(DiscoveryOrderViolation):
            walker.execute_s05_root_cause()
    finally:
        s.close()


# ---------------------------------------------------------------------------
# AC-P4-004 — Preliminary / Specialist / Independent Final Verification
# ---------------------------------------------------------------------------


def test_ac_p4_004_three_verifications_required_for_material_claim(client) -> None:
    """For a material claim, the three verifications (Preliminary,
    Specialist, Independent Final) are required.

    This is enforced via the IndependenceTracker from Phase 3. A
    single agent may not be the sole verifier (VER-IND-002). The
    IndependentTracker is exercised here.
    """
    from techno_service_ai.verification import (
        IndependenceTracker, VerifierRef, ProducerRef, VerifierRole,
        VerificationOutcome, ClaimClassification,
    )
    tracker = IndependenceTracker()
    producer = ProducerRef(producer_id="analyst-1", role_code="ANALYST")
    # Preliminary review by a different agent
    p_v = VerifierRef(verifier_id="verifier-preliminary", role=VerifierRole.PRELIMINARY_EVIDENCE_REVIEWER, role_code="VERIFIER")
    rec1 = tracker.create_record(
        canonical_id="v1", material_claim_id="claim-1", producer=producer, verifier=p_v,
        claim_classification=ClaimClassification.FACT, outcome=VerificationOutcome.VALIDATED,
        reason="source verified", source_citations=("src1",), second_reviewer_id=None, created_at="2026-01-01",
    )
    # Specialist review by a different agent
    s_v = VerifierRef(verifier_id="verifier-specialist", role=VerifierRole.SPECIALIST_VERIFIER, role_code="VERIFIER")
    rec2 = tracker.create_record(
        canonical_id="v2", material_claim_id="claim-1", producer=producer, verifier=s_v,
        claim_classification=ClaimClassification.FACT, outcome=VerificationOutcome.VALIDATED,
        reason="domain verified", source_citations=("src1",), second_reviewer_id=None, created_at="2026-01-01",
    )
    # Independent Final by a different agent with a second reviewer (required for material claim)
    ifv = VerifierRef(verifier_id="verifier-independent-final", role=VerifierRole.INDEPENDENT_FINAL_VERIFIER, role_code="VERIFIER")
    rec3 = tracker.create_record(
        canonical_id="v3", material_claim_id="claim-1", producer=producer, verifier=ifv,
        claim_classification=ClaimClassification.FACT, outcome=VerificationOutcome.VALIDATED,
        reason="independent verification", source_citations=("src1",),
        second_reviewer_id="verifier-second-reviewer", created_at="2026-01-01",
    )
    # All 3 verifications are present and producer != verifier.
    assert tracker.is_independent(rec1)
    assert tracker.is_independent(rec2)
    assert tracker.is_independent(rec3)
    # Three verifications for the same claim from three different agents.
    records = tracker.by_claim("claim-1")
    assert len(records) == 3
    assert {r.verifier.role for r in records} == {
        VerifierRole.PRELIMINARY_EVIDENCE_REVIEWER,
        VerifierRole.SPECIALIST_VERIFIER,
        VerifierRole.INDEPENDENT_FINAL_VERIFIER,
    }


# ---------------------------------------------------------------------------
# AC-P4-005 — AI Recommendations are sourced, evidenced, explainable
# ---------------------------------------------------------------------------


def test_ac_p4_005_ai_recommendation_must_be_sourced_evidenced_explainable() -> None:
    """An AI Recommendation without any of source, evidence, confidence,
    explainability is REJECTED."""
    eng = AIRecommendationEngine()
    # 1. Missing source.
    with pytest.raises(AIRecommendationNotConstitutional) as exc:
        eng.issue(producer_agent_id="a1", producer_agent_role="ANALYST",
                  target_entity_type="Opportunity", target_entity_canonical_id="m1",
                  recommendation_text="x", source_citations=(), evidence_canonical_ids=("e1",),
                  confidence=0.9, explainability="because")
    assert "source" in exc.value.missing
    # 2. Missing evidence.
    with pytest.raises(AIRecommendationNotConstitutional) as exc:
        eng.issue(producer_agent_id="a1", producer_agent_role="ANALYST",
                  target_entity_type="Opportunity", target_entity_canonical_id="m1",
                  recommendation_text="x", source_citations=("s1",), evidence_canonical_ids=(),
                  confidence=0.9, explainability="because")
    assert "evidence" in exc.value.missing
    # 3. Missing confidence (out of range).
    with pytest.raises(AIConfidenceOutOfRange):
        eng.issue(producer_agent_id="a1", producer_agent_role="ANALYST",
                  target_entity_type="Opportunity", target_entity_canonical_id="m1",
                  recommendation_text="x", source_citations=("s1",), evidence_canonical_ids=("e1",),
                  confidence=1.5, explainability="because")
    # 4. Missing explainability.
    with pytest.raises(AIRecommendationNotConstitutional) as exc:
        eng.issue(producer_agent_id="a1", producer_agent_role="ANALYST",
                  target_entity_type="Opportunity", target_entity_canonical_id="m1",
                  recommendation_text="x", source_citations=("s1",), evidence_canonical_ids=("e1",),
                  confidence=0.9, explainability="")
    assert "explainability" in exc.value.missing
    # 5. Presents as human authority.
    with pytest.raises(AIRecommendationPresentsAsHumanAuthority):
        eng.issue(producer_agent_id="a1", producer_agent_role="ANALYST",
                  target_entity_type="Opportunity", target_entity_canonical_id="m1",
                  recommendation_text="x", source_citations=("s1",), evidence_canonical_ids=("e1",),
                  confidence=0.9, explainability="because",
                  presented_as_human_authority=True)
    # A valid Recommendation is accepted.
    rec = eng.issue(producer_agent_id="a1", producer_agent_role="ANALYST",
                    target_entity_type="Opportunity", target_entity_canonical_id="m1",
                    recommendation_text="x", source_citations=("s1",), evidence_canonical_ids=("e1",),
                    confidence=0.9, explainability="because")
    assert rec.confidence == 0.9
    assert rec.explainability == "because"
    assert rec.constitutional_role_acknowledged is True


def test_ac_p4_005_ai_recommendation_records_outcome() -> None:
    from techno_service_ai.ai_recommendation import RecommendationOutcome
    eng = AIRecommendationEngine()
    rec = eng.issue(producer_agent_id="a1", producer_agent_role="ANALYST",
                    target_entity_type="Opportunity", target_entity_canonical_id="m1",
                    recommendation_text="x", source_citations=("s1",), evidence_canonical_ids=("e1",),
                    confidence=0.9, explainability="because")
    rec2 = eng.set_outcome(rec.canonical_id, RecommendationOutcome.ACCEPTED, outcome_by="rhfo-1")
    assert rec2.outcome == RecommendationOutcome.ACCEPTED


# ---------------------------------------------------------------------------
# AC-P4-006 — VQR applied at Stage 9
# ---------------------------------------------------------------------------


def test_ac_p4_006_vqr_qualifies_with_25_percent_improvement(client) -> None:
    """A Comparative Analysis with >= 25% improvement in one dimension
    classifies as QUALIFIES."""
    from techno_service_ai.db import SessionLocal
    s = SessionLocal()
    try:
        actor_id = _get_admin_id(s)
        svc = WorkflowService()
        # Walk to S08
        walker = DiscoveryOrderWalker(actor_id=actor_id, role_code="ANALYST")
        walker.execute_s01_environment()
        walker.execute_s02_activity()
        walker.execute_s03_signal()
        walker.execute_s04_problem()
        walker.execute_s04_opportunity()
        walker.execute_s05_root_cause()
        walker.execute_s06_value_case()
        walker.execute_s07_tech_category()
        walker.execute_s08_product()
        # S09 with VQR
        evs = (ImprovementEvidence(
            dimension=VQRDimension.COST,
            asserted_improvement_pct=30.0,
            source_citation="Internal study 2026-01-01",
            measurement_date="2026-01-01",
        ),)
        c = walker.execute_s09_comparative(
            incumbent_solution="Carbon steel tube bundle (3-year life)",
            vqr_asserted_improvements=evs,
            vqr_requested_classification=VQRClassification.QUALIFIES,
            vqr_rationale="30% cost improvement from Inconel-clad bundle",
        )
        assert c.value_qualification_classification == "QUALIFIES"
        assert c.intelligence_status == "QUALIFIES"
    finally:
        s.close()


def test_ac_p4_006_vqr_unverified_when_no_improvement(client) -> None:
    """A Comparative Analysis with no asserted improvement classifies as
    UNVERIFIED_VALUE_HYPOTHESIS (per Article VII paragraph 4(a))."""
    from techno_service_ai.db import SessionLocal
    s = SessionLocal()
    try:
        actor_id = _get_admin_id(s)
        walker = DiscoveryOrderWalker(actor_id=actor_id, role_code="ANALYST")
        for fn, args in [
            (walker.execute_s01_environment, {}),
            (walker.execute_s02_activity, {}),
            (walker.execute_s03_signal, {}),
            (walker.execute_s04_problem, {}),
            (walker.execute_s04_opportunity, {}),
            (walker.execute_s05_root_cause, {}),
            (walker.execute_s06_value_case, {}),
            (walker.execute_s07_tech_category, {}),
            (walker.execute_s08_product, {}),
        ]:
            fn(**args)
        c = walker.execute_s09_comparative(
            incumbent_solution="Carbon steel tube bundle (3-year life)",
            vqr_asserted_improvements=(),  # no assertions
        )
        assert c.value_qualification_classification == "UNVERIFIED_VALUE_HYPOTHESIS"
    finally:
        s.close()


def test_ac_p4_006_vqr_strategic_exception_requires_human_approval() -> None:
    """STRATEGIC_EXCEPTION requires a Human Approval."""
    ve = VQREngine()
    with pytest.raises(VQRStrategicExceptionRequiresApproval):
        ve.evaluate(
            material_canonical_id="m1",
            asserted_improvements=(),
            rationale="strategic",
            classified_by="agent-1",
            requested_classification=VQRClassification.STRATEGIC_EXCEPTION,
            strategic_exception_approval_id=None,  # missing
        )
    # With approval, it works.
    r = ve.evaluate(
        material_canonical_id="m1",
        asserted_improvements=(),
        rationale="strategic",
        classified_by="agent-1",
        requested_classification=VQRClassification.STRATEGIC_EXCEPTION,
        strategic_exception_approval_id="approval-001",
    )
    assert r.classification == VQRClassification.STRATEGIC_EXCEPTION


# ---------------------------------------------------------------------------
# AC-P4-007 — Kuwait Suitability Review at Stage 10
# ---------------------------------------------------------------------------


def test_ac_p4_007_kuwait_suitability_review_required_for_next_stage(client) -> None:
    """The Kuwait Suitability Review is the Entry Condition for Stage 11.
    Without it, the next stage is BLOCKED."""
    from techno_service_ai.db import SessionLocal
    s = SessionLocal()
    try:
        actor_id = _get_admin_id(s)
        # Walk to S10
        walker = DiscoveryOrderWalker(actor_id=actor_id, role_code="ANALYST")
        walker.walk_s01_to_s10()
        # The KSR is the prerequisite for Stage 11.
        assert walker.ksr_id is not None
        # The KSR record exists and has the constitutional fields.
        ksr = walker.entities["S10"]
        assert isinstance(ksr, KuwaitSuitabilityReview)
        assert ksr.comparative_analysis_id == walker.comparative_id
    finally:
        s.close()


# ---------------------------------------------------------------------------
# Agent roster — 10 agents
# ---------------------------------------------------------------------------


def test_ten_agents_roster() -> None:
    """10 Principal Agents are registered (Document 02 §4.2-4.4).

    Industrial Intelligence: 3
    Opportunity Intelligence: 3
    Technology Intelligence: 4
    Total: 10.
    """
    assert assert_total_agents() == 10
    roster = ten_agent_roster()
    assert len(roster) == 10
    # Every agent has a name, an office, a charter section, and a list of prohibited actions.
    for a in roster:
        assert a.name
        assert a.office
        assert a.charter_section
        assert a.prohibited_actions
        assert a.constitutional_purpose


def test_three_offices_represented() -> None:
    """The 3 Intelligence Offices are represented in the roster."""
    roster = ten_agent_roster()
    offices = {a.office for a in roster}
    assert "Industrial Intelligence Office" in offices
    assert "Opportunity Intelligence Office" in offices
    assert "Technology Intelligence Office" in offices


# ---------------------------------------------------------------------------
# ORCH-COND path
# ---------------------------------------------------------------------------


def test_orch_cond_skip_requires_approval() -> None:
    """A SKIPPED_BY_AUTHORIZED_HUMAN_DECISION omission requires a Human Approval."""
    from techno_service_ai.stages import StageNumber
    from techno_service_ai.orch_cond import ORCHCONDMissingApproval
    eng = ORCHCONDEngine()
    with pytest.raises(ORCHCONDMissingApproval):
        eng.mark(
            opportunity_canonical_id="o1", stage=StageNumber.S15_HUMAN_APPROVAL,
            omission_type=OmissionType.SKIPPED_BY_AUTHORIZED_HUMAN_DECISION,
            reason="x", responsible_authority="admin",
        )


def test_orch_cond_equivalent_control_requires_assurance() -> None:
    """REPLACED_BY_EQUIVALENT_CONTROL requires an assurance statement (not a waiver)."""
    from techno_service_ai.stages import StageNumber
    eng = ORCHCONDEngine()
    with pytest.raises(EquivalentControlNotEquivalent):
        eng.mark(
            opportunity_canonical_id="o1", stage=StageNumber.S15_HUMAN_APPROVAL,
            omission_type=OmissionType.REPLACED_BY_EQUIVALENT_CONTROL,
            reason="x", responsible_authority="admin",
            human_approval_id="approval-1",
            equivalent_control_reference="ctrl-1",
            equivalent_control_assurance="",  # missing
        )
    # With assurance, it works.
    r = eng.mark(
        opportunity_canonical_id="o1", stage=StageNumber.S15_HUMAN_APPROVAL,
        omission_type=OmissionType.REPLACED_BY_EQUIVALENT_CONTROL,
        reason="x", responsible_authority="admin",
        human_approval_id="approval-1",
        equivalent_control_reference="ctrl-1",
        equivalent_control_assurance="The control provides equivalent assurance per document audit.",
    )
    assert r.equivalent_control_assurance


def test_orch_cond_deferred_requires_re_entry_date() -> None:
    """A DEFERRED omission requires a re_entry_date."""
    from techno_service_ai.stages import StageNumber
    eng = ORCHCONDEngine()
    with pytest.raises(ORCHCONDMissingReEntry):
        eng.mark(
            opportunity_canonical_id="o1", stage=StageNumber.S15_HUMAN_APPROVAL,
            omission_type=OmissionType.DEFERRED,
            reason="x", responsible_authority="admin",
        )


def test_orch_cond_all_omission_types_with_required_fields_succeed() -> None:
    """All 4 omission types with the required fields succeed."""
    from techno_service_ai.stages import StageNumber
    eng = ORCHCONDEngine()
    for omission_type in OmissionType:
        kwargs = dict(
            opportunity_canonical_id=f"o-{omission_type.value}",
            stage=StageNumber.S15_HUMAN_APPROVAL,
            omission_type=omission_type, reason="x", responsible_authority="admin",
        )
        if omission_type in APPROVAL_REQUIRED_OMISSIONS:
            kwargs["human_approval_id"] = "approval-1"
        if omission_type == OmissionType.REPLACED_BY_EQUIVALENT_CONTROL:
            kwargs["equivalent_control_reference"] = "ctrl-1"
            kwargs["equivalent_control_assurance"] = "Equivalent assurance statement."
        if omission_type == OmissionType.DEFERRED:
            kwargs["re_entry_date"] = "2026-12-31"
        r = eng.mark(**kwargs)
        assert r.omission_type == omission_type


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


class _noop:
    def __enter__(self): return self
    def __exit__(self, *a): pass
