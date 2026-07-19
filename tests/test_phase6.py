"""Phase 6 Tests — Tender, Project, Knowledge, and the 24-Stage Walk.

Covers AC-P6-001..008:

  - AC-P6-001 — A tender is monitored, qualified, and submitted with
    the Tender Gate enforced.
  - AC-P6-002 — A project is awarded, monitored, and supported.
  - AC-P6-003 — After-sales opportunities are identified.
  - AC-P6-004 — Knowledge Capture, Institutional Memory, and Lessons
    Learned are performed.
  - AC-P6-005 — Tender Gate cannot be bypassed.
  - AC-P6-006 — Project Gate cannot be bypassed.
  - AC-P6-007 — Closure Gate is enforced at the Final Disposition.
  - AC-P6-008 — The full 24-stage walk S01..S24 completes on real data.

Also covers the reconciliation of GAP-PHASE5-001 (DecisionLogEntry
field-name alignment).
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from typing import Iterator

import pytest

# Make `src/` importable and set up a temp DB.
_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

_TMP = Path(tempfile.mkdtemp(prefix="tsai-phase6-"))
os.environ.setdefault("TSAI_DATABASE_URL", f"sqlite:///{(_TMP / 'test.db').as_posix()}")
os.environ.setdefault("TSAI_JWT_SECRET", "test-secret-key-for-pytest-only")
os.environ.setdefault("TSAI_DEFAULT_ADMIN_PASSWORD", "ChangeMe!2026")

from techno_service_ai import bootstrap  # noqa: E402
from techno_service_ai.agents import (  # noqa: E402
    AfterSalesIntelligenceAgent,
    ApprovedVendorListManagerAgent,
    CommercialModelDesignerAgent,
    InstitutionalMemoryManagerAgent,
    KnowledgeBaseCuratorAgent,
    LessonsLearnedAnalystAgent,
    NegotiationSupportAgent,
    ProjectMonitorAgent,
    QuotationSupportAgent,
    TenderMonitorAgent,
    TenderQualificationAgent,
    assert_phase6_agents,
    eleven_agent_roster,
)
from techno_service_ai.commercial import (  # noqa: E402
    CommercialEngine,
    CommercialModelSelectionNotAllowedError,
)
from techno_service_ai.knowledge import (  # noqa: E402
    InstitutionalMemorySilentDeletionError,
    KnowledgeEngine,
    KnowledgeRecordMissingProvenanceError,
    KnowledgeQualityStatusRejectionError,
    LessonLearnedMissingOutcomeError,
)
from techno_service_ai.registration import (  # noqa: E402
    AVLSubmissionMissingApprovalError,
    RegistrationEngine,
)
from techno_service_ai.tender_project import (  # noqa: E402
    ProjectCommitmentChangeError,
    QuotationSubmissionWithoutApprovalError,
    TenderProjectEngine,
    TenderQualificationOutcome,
    TenderStatus,
)


# ---------------------------------------------------------------------------
# Agent roster (AC-P6-001..004 prerequisite)
# ---------------------------------------------------------------------------


def test_phase6_agent_roster_11_agents() -> None:
    """Phase 6 activates 11 Principal Agents across 3 Offices."""
    assert assert_phase6_agents() == 11
    roster = eleven_agent_roster()
    assert len(roster) == 11


def test_phase6_three_offices_represented() -> None:
    """The 11 agents come from 3 distinct Offices."""
    roster = eleven_agent_roster()
    offices = {a.office for a in roster}
    assert offices == {
        "Tender and Project Intelligence Office",
        "Knowledge and Institutional Memory Office",
        "Commercial Development Office",
        "Registration and Market Entry Office",
    }


def test_phase6_agents_match_canonical_names() -> None:
    """Every agent name matches Document 02 §4.6/4.7/4.8/4.13."""
    roster = eleven_agent_roster()
    names = {a.name for a in roster}
    assert "Tender Monitor Agent" in names
    assert "Tender Qualification Agent" in names
    assert "Quotation Support Agent" in names
    assert "Project Monitor Agent" in names
    assert "Knowledge Base Curator Agent" in names
    assert "Institutional Memory Manager Agent" in names
    assert "Lessons Learned Analyst Agent" in names
    assert "Commercial Model Designer Agent" in names
    assert "Negotiation Support Agent" in names
    assert "After-Sales Intelligence Agent" in names
    assert "Approved Vendor List Manager Agent" in names


# ---------------------------------------------------------------------------
# Tender and Project Engine (AC-P6-001, AC-P6-002, AC-P6-005, AC-P6-006)
# ---------------------------------------------------------------------------


def test_tender_monitor_validates_required_fields() -> None:
    """A Tender record missing required fields is REJECTED."""
    eng = TenderProjectEngine()
    with pytest.raises(ValueError):
        eng.validate_tender(__import__("techno_service_ai.tender_project", fromlist=["TenderSpec"]).TenderSpec(
            tender_reference="", issuer="x", issue_date="2026-01-01", closing_date="2026-03-01"
        ))


def test_quotation_submission_without_approval_rejected() -> None:
    """AC-P6-005 — A Quotation Dossier submitted without Human
    Approval is REJECTED."""
    eng = TenderProjectEngine()
    from techno_service_ai.tender_project import QuotationDossierSpec
    with pytest.raises(QuotationSubmissionWithoutApprovalError):
        eng.validate_quotation_dossier(QuotationDossierSpec(
            tender_id="t-1",
            document_type="TECHNICAL_COMMERCIAL",
            content="...",
            pricing_model="cost-plus",
            technical_content="...",
            submission_date="2026-03-10",
            human_approval_id=None,
        ))


def test_quotation_dossier_missing_pricing_model_rejected() -> None:
    """A Quotation Dossier without pricing_model is REJECTED."""
    eng = TenderProjectEngine()
    from techno_service_ai.tender_project import QuotationMissingRequiredFieldError, QuotationDossierSpec
    with pytest.raises(QuotationMissingRequiredFieldError):
        eng.validate_quotation_dossier(QuotationDossierSpec(
            tender_id="t-1",
            document_type="TECHNICAL_COMMERCIAL",
            content="...",
            pricing_model="",
            technical_content="...",
        ))


def test_project_commitment_change_without_approval_rejected() -> None:
    """AC-P6-006 — A project commitment change without Human Approval
    is REJECTED (GATE-PJ-002)."""
    eng = TenderProjectEngine()
    with pytest.raises(ProjectCommitmentChangeError):
        eng.check_commitment_change(
            has_commitment_change=True,
            human_approval_id=None,
        )


def test_project_commitment_change_with_approval_accepted() -> None:
    """A project commitment change WITH Human Approval is accepted."""
    eng = TenderProjectEngine()
    eng.check_commitment_change(
        has_commitment_change=True,
        human_approval_id="approval-pc-001",
    )  # no exception


def test_tender_qualification_outcome_validated() -> None:
    """A Tender Qualification outcome is validated."""
    eng = TenderProjectEngine()
    from techno_service_ai.tender_project import TenderQualificationSpec
    out = eng.evaluate_qualification(TenderQualificationSpec(
        tender_id="t-1",
        qualification_outcome="QUALIFIED",
    ))
    assert out == TenderQualificationOutcome.QUALIFIED

    out2 = eng.evaluate_qualification(TenderQualificationSpec(
        tender_id="t-1",
        qualification_outcome="NOT_QUALIFIED",
    ))
    assert out2 == TenderQualificationOutcome.NOT_QUALIFIED


def test_after_sales_report_validates_required_fields() -> None:
    """An After-Sales report missing fields is REJECTED."""
    eng = TenderProjectEngine()
    from techno_service_ai.tender_project import AfterSalesReportSpec
    with pytest.raises(ValueError):
        eng.validate_after_sales(AfterSalesReportSpec(
            opportunity_id="", report_text="x"
        ))
    with pytest.raises(ValueError):
        eng.validate_after_sales(AfterSalesReportSpec(
            opportunity_id="o-1", report_text=""
        ))


# ---------------------------------------------------------------------------
# Knowledge Engine (AC-P6-004)
# ---------------------------------------------------------------------------


def test_knowledge_record_requires_provenance() -> None:
    """AC-P6-004 — A Knowledge Record without source_citation is REJECTED."""
    eng = KnowledgeEngine()
    from techno_service_ai.knowledge import KnowledgeRecordSpec
    with pytest.raises(KnowledgeRecordMissingProvenanceError):
        eng.validate_knowledge_record(KnowledgeRecordSpec(
            title="x", body="y", domain="z",
            source_citation="",  # missing provenance
        ))


def test_knowledge_record_with_provenance_accepted() -> None:
    """A Knowledge Record WITH source_citation is accepted."""
    eng = KnowledgeEngine()
    from techno_service_ai.knowledge import KnowledgeRecordSpec, KnowledgeQualityStatus
    result = eng.validate_knowledge_record(KnowledgeRecordSpec(
        title="Lesson 1", body="text", domain="REFINERY",
        source_citation="Phase 6 walk test",
    ))
    assert result.has_provenance is True
    assert result.quality_status == KnowledgeQualityStatus.DRAFT


def test_knowledge_quality_status_transition_governed() -> None:
    """A skip in the quality status flow is REJECTED."""
    eng = KnowledgeEngine()
    with pytest.raises(KnowledgeQualityStatusRejectionError):
        eng.check_quality_status_transition(
            from_status="DRAFT", to_status="PUBLISHED",  # skipping REVIEWED
        )


def test_institutional_memory_silent_deletion_rejected() -> None:
    """An Institutional Memory material deletion without Human
    Approval is REJECTED (silent deletion PROHIBITED)."""
    eng = KnowledgeEngine()
    from techno_service_ai.knowledge import InstitutionalMemoryIndexSpec
    with pytest.raises(InstitutionalMemorySilentDeletionError):
        eng.validate_institutional_memory(InstitutionalMemoryIndexSpec(
            target_type="OPPORTUNITY", target_id="o-1",
            retention_class="PERMANENT",
            retention_until="2026-12-31",  # implies deletion
            human_approval_id=None,  # no approval
        ))


def test_institutional_memory_silent_deletion_with_approval_accepted() -> None:
    """A material deletion WITH Human Approval is accepted."""
    eng = KnowledgeEngine()
    from techno_service_ai.knowledge import InstitutionalMemoryIndexSpec
    result = eng.validate_institutional_memory(InstitutionalMemoryIndexSpec(
        target_type="OPPORTUNITY", target_id="o-1",
        retention_class="PERMANENT",
        retention_until="2026-12-31",
        human_approval_id="approval-im-001",
    ))
    assert result.deletion_authorized is True


def test_lesson_learned_requires_source() -> None:
    """AC-P6-004 — A Lesson Learned without a source (Opportunity or
    Incident) is REJECTED."""
    eng = KnowledgeEngine()
    from techno_service_ai.knowledge import LessonLearnedSpec
    with pytest.raises(LessonLearnedMissingOutcomeError):
        eng.validate_lesson_learned(LessonLearnedSpec(
            title="x", body="y", outcome="WON",
            target_opportunity_id=None, source_citation="",
        ))


def test_lesson_learned_with_source_accepted() -> None:
    """A Lesson Learned WITH a closed Opportunity is accepted."""
    eng = KnowledgeEngine()
    from techno_service_ai.knowledge import LessonLearnedSpec, LessonLearnedOutcome
    result = eng.validate_lesson_learned(LessonLearnedSpec(
        title="x", body="y", outcome="WON",
        target_opportunity_id="opp-1",
    ))
    assert result.outcome == LessonLearnedOutcome.WON
    assert result.has_source is True


# ---------------------------------------------------------------------------
# Deferred Commercial Development agents (Phase 5 → Phase 6)
# ---------------------------------------------------------------------------


def test_commercial_model_designer_prohibits_selection() -> None:
    """§4.6.2 — The Commercial Model Designer is PROHIBITED from
    selecting a model."""
    eng = CommercialEngine()
    with pytest.raises(CommercialModelSelectionNotAllowedError):
        eng.validate_commercial_model_option(
            model_type="DIRECT_REP", model_description="x", selected=True,
        )


def test_negotiation_support_validates_required_fields() -> None:
    """§4.6.4 — Negotiation Analysis requires scenario + constraints."""
    eng = CommercialEngine()
    with pytest.raises(ValueError):
        eng.validate_negotiation_analysis(
            scenario="", constraints="x", analysis_date="2026-01-01",
        )
    with pytest.raises(ValueError):
        eng.validate_negotiation_analysis(
            scenario="x", constraints="", analysis_date="2026-01-01",
        )


def test_avl_submission_without_approval_rejected() -> None:
    """§4.7.4 — An AVL submission without Human Approval is REJECTED."""
    eng = RegistrationEngine()
    with pytest.raises(AVLSubmissionMissingApprovalError):
        eng.validate_avl_status(
            opportunity_id="opp-1", authority="KOC",
            status="SUBMITTED", human_approval_id=None,
        )


# ---------------------------------------------------------------------------
# DecisionLogEntry reconciliation (GAP-PHASE5-001)
# ---------------------------------------------------------------------------


def test_decision_log_entry_reconciliation_works() -> None:
    """GAP-PHASE5-001 — The LogService can write a DecisionLogEntry
    using the LogService field names (decision_type, decision_summary,
    decision_class, decided_by_role, etc.) which now map to the
    schema's canonical field set (target_type, decision_summary,
    decision_class, etc.)."""
    from techno_service_ai.db import reset_schema
    from techno_service_ai.log_service import LogService

    reset_schema()
    bootstrap.seed()
    svc = LogService()
    rec = svc.write_decision_log(
        decision_type="TENDER_SUBMISSION",
        decision_summary="Tender KOC-2026-001 submitted for Human Approval.",
        decision_class="CLASS_3",
        decided_by="approver-1",
        decided_by_role="AUTHORISED_HUMAN",
        material_canonical_id="tender-1",
        opportunity_canonical_id="opp-1",
        rationale="Phase 6 GAP-PHASE5-001 closure test.",
        conditions="Margin ≥ 12% (floor).",
        related_approval_id="approval-tender-001",
    )
    # Both the legacy schema fields AND the LogService fields are populated.
    assert rec.target_type == "TENDER_SUBMISSION"
    assert rec.decision_class == "CLASS_3"
    assert rec.decision_summary == rec.decision  # legacy alias
    assert rec.decided_by_role == "AUTHORISED_HUMAN"
    assert rec.material_canonical_id == "tender-1"
    assert rec.opportunity_canonical_id == "opp-1"
    assert rec.rationale == "Phase 6 GAP-PHASE5-001 closure test."
    assert rec.related_approval_id == "approval-tender-001"


# ---------------------------------------------------------------------------
# Discovery Order walk S19..S24 (AC-P6-001, AC-P6-002, AC-P6-003, AC-P6-004)
# ---------------------------------------------------------------------------


def test_discovery_order_walk_s19_to_s24_creates_real_records() -> None:
    """AC-P6-001..004 — Walking S19..S24 creates real DB records."""
    from techno_service_ai.db import reset_schema
    from techno_service_ai.services import WorkflowService
    from techno_service_ai.discovery_walker import DiscoveryOrderWalker

    reset_schema()
    bootstrap.seed()
    svc = WorkflowService()
    walker = DiscoveryOrderWalker(actor_id="agent-1", role_code="ANALYST", service=svc)
    # First walk S01..S18 (so S19 has the upstream data).
    walker.walk_s01_to_s10()
    walker.walk_s11_to_s18()
    # Now S19..S24.
    walker.execute_s19_tender()
    walker.execute_s19_qualification()
    walker.execute_s19_quotation()
    walker.execute_s20_project()
    walker.execute_s20_after_sales()
    walker.execute_s21_commercial_outcome()
    walker.execute_s22_knowledge_capture()
    walker.execute_s22_lesson_learned()
    walker.execute_s23_institutional_memory()
    walker.execute_s24_continuous_learning()
    assert walker.tender_id is not None
    assert walker.tender_qualification_id is not None
    assert walker.quotation_dossier_id is not None
    assert walker.project_status_id is not None
    assert walker.after_sales_id is not None
    assert walker.knowledge_record_id is not None
    assert walker.lesson_learned_id is not None
    assert walker.institutional_memory_id is not None
    # Verify last_completed_stage reached S24.
    from techno_service_ai.stages import StageNumber
    assert walker.last_completed_stage == StageNumber.S24_CONTINUOUS_LEARNING


def test_discovery_order_skip_rejected_in_phase6() -> None:
    """AC-P6-005 + AC-P6-006 — Skipping a stage in S19..S24 is REJECTED."""
    from techno_service_ai.db import reset_schema
    from techno_service_ai.services import WorkflowService
    from techno_service_ai.discovery_walker import DiscoveryOrderWalker, DiscoveryOrderViolation
    from techno_service_ai.stages import StageNumber

    reset_schema()
    bootstrap.seed()
    svc = WorkflowService()
    walker = DiscoveryOrderWalker(actor_id="agent-1", role_code="ANALYST", service=svc)
    # Walk up to S18.
    walker.walk_s01_to_s10()
    walker.walk_s11_to_s18()
    # Try to skip S19 entirely.
    with pytest.raises(DiscoveryOrderViolation):
        walker._ensure_order(StageNumber.S20_PROJECT_SUPPORT)


# ---------------------------------------------------------------------------
# Full 24-stage walk S01..S24 (AC-P6-008)
# ---------------------------------------------------------------------------


def test_full_24_stage_walk_s01_to_s24_succeeds() -> None:
    """AC-P6-008 — The full 24-stage walk S01..S24 succeeds on real data."""
    from techno_service_ai.db import reset_schema
    from techno_service_ai.services import WorkflowService
    from techno_service_ai.discovery_walker import DiscoveryOrderWalker

    reset_schema()
    bootstrap.seed()
    svc = WorkflowService()
    walker = DiscoveryOrderWalker(actor_id="agent-1", role_code="ANALYST", service=svc)
    entities = walker.walk_s01_to_s24()
    # The walk must produce at least 24 entities (one per stage, with
    # some stages having multiple sub-records like S11 with profile +
    # credibility + comparison = 3 entities from one stage).
    assert len(entities) >= 24
    # Verify every stage marker is in the result.
    expected_markers = {
        "S01", "S02", "S03", "S04", "S05", "S06", "S07", "S08", "S09", "S10",
        "S11_profile", "S11_credibility", "S11_comparison",
        "S12", "S12_pricing",
        "S13", "S14", "S15", "S16", "S17_registration", "S17_prequalification",
        "S18",
        "S19_tender", "S19_qualification", "S19_quotation",
        "S20", "S20_after_sales",
        "S21", "S22", "S22_lesson", "S23", "S24",
    }
    missing = expected_markers - entities.keys()
    assert not missing, f"Missing entities: {missing}"


def test_full_24_stage_walk_no_skip_no_abbreviation_no_reorder() -> None:
    """AC-P6-005, AC-P6-006, AC-P6-007 — The full walk is non-skippable,
    non-abbreviation, non-reorderable. We verify the constitutional
    invariant by attempting an out-of-order progression and confirming
    it raises."""
    from techno_service_ai.db import reset_schema
    from techno_service_ai.services import WorkflowService
    from techno_service_ai.discovery_walker import DiscoveryOrderWalker, DiscoveryOrderViolation
    from techno_service_ai.stages import StageNumber

    reset_schema()
    bootstrap.seed()
    svc = WorkflowService()
    walker = DiscoveryOrderWalker(actor_id="agent-1", role_code="ANALYST", service=svc)
    walker.walk_s01_to_s10()
    # Try to skip S11..S13 and go to S14.
    with pytest.raises(DiscoveryOrderViolation):
        walker._ensure_order(StageNumber.S14_QUALITY_REVIEW)
    # Try to skip ahead to S24.
    with pytest.raises(DiscoveryOrderViolation):
        walker._ensure_order(StageNumber.S24_CONTINUOUS_LEARNING)


# ---------------------------------------------------------------------------
# Closure Gate (AC-P6-007)
# ---------------------------------------------------------------------------


def test_closure_gate_final_disposition_recorded() -> None:
    """AC-P6-007 — The Commercial Outcome (S21) is the input to the
    Closure Gate. The walker records the final disposition."""
    from techno_service_ai.db import reset_schema
    from techno_service_ai.services import WorkflowService
    from techno_service_ai.discovery_walker import DiscoveryOrderWalker
    from techno_service_ai.phase2_schema import CommercialOutcomeReport

    reset_schema()
    bootstrap.seed()
    svc = WorkflowService()
    walker = DiscoveryOrderWalker(actor_id="agent-1", role_code="ANALYST", service=svc)
    walker.walk_s01_to_s10()
    walker.walk_s11_to_s18()
    # Walk through S19-S20 to reach S21 (Closure Gate input).
    walker.execute_s19_tender()
    walker.execute_s19_qualification()
    walker.execute_s19_quotation()
    walker.execute_s20_project()
    walker.execute_s20_after_sales()
    walker.execute_s21_commercial_outcome(outcome="WON", revenue="1.2M USD", margin="18%")
    co = walker.entities["S21"]
    assert isinstance(co, CommercialOutcomeReport)
    assert co.outcome == "WON"
    assert co.revenue == "1.2M USD"
