"""Phase 7 Tests — Every Office Alive.

Covers AC-P7-001..006 + AC-AUD-001..005 + 6 categories × 5 channels
notification + Class 3/4 suppression rejected + agent roster.

Also verifies the S24 Continuous Learning engine (closes
GAP-PHASE6-001) and the Performance and Learning Office activation
(closes GAP-PHASE6-002).
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

_TMP = Path(tempfile.mkdtemp(prefix="tsai-phase7-"))
os.environ.setdefault("TSAI_DATABASE_URL", f"sqlite:///{(_TMP / 'test.db').as_posix()}")
os.environ.setdefault("TSAI_JWT_SECRET", "test-secret-key-for-pytest-only")
os.environ.setdefault("TSAI_DEFAULT_ADMIN_PASSWORD", "ChangeMe!2026")

from techno_service_ai import bootstrap  # noqa: E402
from techno_service_ai.agents import (  # noqa: E402
    AccessControlAgent,
    BoardReportAgent,
    BottleneckDetectorAgent,
    ChiefOrchestrationAgent,
    CommercialOutcomesAnalystAgent,
    CommercialReportAgent,
    ComplianceMonitorAgent,
    ComplianceReportAgent,
    ConstitutionalComplianceCoordinationAgent,
    ConstitutionalCoordinationAgent,
    ConstitutionalDecisionSupportAgent,
    ConstitutionalDiscoveryCoordinationAgent,
    ConstitutionalIncidentInvestigatorAgent,
    ConstitutionalLearningAgent,
    ContinuityAndRecoveryAgent,
    CustomerRelationshipAgent,
    DataGovernanceAgent,
    EscalationCoordinatorAgent,
    HumanEscalationCoordinationAgent,
    InstitutionalMemoryManagerAgent,
    LearningCoordinationAgent,
    ManufacturerRelationshipAgent,
    NotificationComposerAgent,
    OperationalReportAgent,
    PartnerRelationshipAgent,
    PerformanceMeasurementAgent,
    RegisterStewardAgent,
    ReportAuthorAgent,
    RiskAnalystAgent,
    SecurityOperationsAgent,
    SLAMonitorAgent,
    WorkflowMonitorAgent,
    assert_phase7_agents,
    thirty_one_agent_roster,
)
from techno_service_ai.continuous_learning import (  # noqa: E402
    ContinuousLearningEngine,
    ConstitutionalAmendmentWithoutApprovalError,
    IrreversibleUpdateRejectedError,
    LearningUpdateOutcome,
    LearningUpdateProposal,
    LearningUpdateScope,
)
from techno_service_ai.phase7_engines import (  # noqa: E402
    ClaimClassification as ReportClaimClassification,
    ComplianceEngine,
    ComplianceStatus,
    ConstitutionalIncidentEngine,
    ConstitutionalIncidentSeverity,
    ConstitutionalIncidentSpec,
    MaterialClaimWithoutVerificationError,
    NotificationCategory,
    NotificationChannel,
    NotificationEngine,
    NotificationPriority,
    NotificationSpec,
    PerformanceEngine,
    PerformanceMetricDirection,
    PerformanceMetricSpec,
    ReportClaim,
    ReportFreshnessClass,
    ReportingEngine,
    ReportMissingClaimSourceError,
    ReportMissingFreshnessError,
    ReportSpec,
    ReportType,
    RiskEngine,
    RiskEntrySpec,
    RiskSeverity,
    SmsReservedForClass3Or4Error,
    SuppressionForbiddenError,
    VoiceReservedForEmergencyError,
)


# ---------------------------------------------------------------------------
# Agent roster (target 31 across 7 Offices)
# ---------------------------------------------------------------------------


def test_phase7_agent_roster_31_agents() -> None:
    """Phase 7 activates 31 Principal Agents across 7 Offices."""
    assert assert_phase7_agents() == 31
    roster = thirty_one_agent_roster()
    assert len(roster) == 31


def test_phase7_offices_distribution() -> None:
    """The 31 agents are spread across 7 distinct Offices."""
    roster = thirty_one_agent_roster()
    offices = {a.office for a in roster}
    assert len(offices) == 7
    # Each office has the expected number of agents.
    counts: dict = {}
    for a in roster:
        counts[a.office] = counts.get(a.office, 0) + 1
    assert counts["Performance and Learning Office"] == 4
    assert counts["Reporting and Decision Support Office"] == 5
    assert counts["Notification and Monitoring Office"] == 6
    assert counts["Risk and Compliance Office"] == 4
    assert counts["Security and Data Governance Office"] == 4
    assert counts["Relationship Management Office"] == 3
    assert counts["Executive AI Office"] == 5


# ---------------------------------------------------------------------------
# S24 Continuous Learning engine (closes GAP-PHASE6-001)
# ---------------------------------------------------------------------------


def test_continuous_learning_engine_approves_safe_proposal() -> None:
    """A safe Learning Update proposal is APPROVED."""
    eng = ContinuousLearningEngine()
    proposal = LearningUpdateProposal(
        target_type="PARAMETER", target_id="p-1",
        description="Lower confidence threshold from 0.7 to 0.65",
        scope="SYSTEM_TUNING", reversible=True,
    )
    result = eng.review(proposal)
    assert result.outcome == LearningUpdateOutcome.APPROVED


def test_continuous_learning_engine_rejects_irreversible() -> None:
    """An irreversible Learning Update is REJECTED."""
    eng = ContinuousLearningEngine()
    proposal = LearningUpdateProposal(
        target_type="PARAMETER", target_id="p-1",
        description="Drop audit log table", scope="SYSTEM_TUNING",
        reversible=False,
    )
    result = eng.review(proposal)
    assert result.outcome == LearningUpdateOutcome.REJECTED_IRREVERSIBLE


def test_continuous_learning_engine_rejects_constitutional_impact() -> None:
    """A Learning Update that affects an invariable constitutional
    clause is REJECTED (Constitution Article XXVIII)."""
    eng = ContinuousLearningEngine()
    proposal = LearningUpdateProposal(
        target_type="POLICY", target_id="p-1",
        description="Weaken Article XII Human Approval gate",
        scope="POLICY_REFINEMENT", reversible=True,
        affected_clauses=("Article XII",),
    )
    result = eng.review(proposal)
    assert result.outcome == LearningUpdateOutcome.REJECTED_CONSTITUTIONAL_IMPACT


def test_continuous_learning_engine_rejects_constitutional_amendment_without_approval() -> None:
    """A CONSTITUTIONAL_AMENDMENT without Human Approval is REJECTED."""
    eng = ContinuousLearningEngine()
    proposal = LearningUpdateProposal(
        target_type="CONSTITUTION", target_id="clause-1",
        description="Amend Article VIII", scope="CONSTITUTIONAL_AMENDMENT",
        reversible=True, human_approval_id=None,
    )
    result = eng.review(proposal)
    assert result.outcome == LearningUpdateOutcome.REJECTED_MISSING_APPROVAL


def test_continuous_learning_engine_approves_constitutional_amendment_with_approval() -> None:
    """A CONSTITUTIONAL_AMENDMENT WITH Human Approval is APPROVED."""
    eng = ContinuousLearningEngine()
    proposal = LearningUpdateProposal(
        target_type="CONSTITUTION", target_id="clause-1",
        description="Amend Article VIII", scope="CONSTITUTIONAL_AMENDMENT",
        reversible=True, human_approval_id="approval-1",
    )
    result = eng.review(proposal)
    assert result.outcome == LearningUpdateOutcome.APPROVED
    assert result.requires_human_approval


def test_continuous_learning_engine_rejects_invalid_scope() -> None:
    """A Learning Update with an invalid scope is REJECTED."""
    eng = ContinuousLearningEngine()
    proposal = LearningUpdateProposal(
        target_type="PARAMETER", target_id="p-1",
        description="Invalid scope", scope="BOGUS_SCOPE",
        reversible=True,
    )
    result = eng.review(proposal)
    assert result.outcome == LearningUpdateOutcome.REJECTED_INVALID_SCOPE


# ---------------------------------------------------------------------------
# Reporting engine (Constitutional Compliance Attestation)
# ---------------------------------------------------------------------------


def test_reporting_engine_requires_freshness_date() -> None:
    """A Report without a freshness_date is REJECTED (AC-P7-006)."""
    eng = ReportingEngine()
    with pytest.raises(ReportMissingFreshnessError):
        eng.validate_report(ReportSpec(
            report_type=ReportType.EXECUTIVE,
            title="Executive Report",
            body="…",
            freshness_date="",
            claims=(ReportClaim(
                claim_text="claim", classification=ReportClaimClassification.FACT,
                source_citation="x", verification_reference="v-1",
            ),),
        ))


def test_reporting_engine_requires_claim_source() -> None:
    """A Report claim without source citation is REJECTED (Article X)."""
    eng = ReportingEngine()
    with pytest.raises(ReportMissingClaimSourceError):
        eng.validate_report(ReportSpec(
            report_type=ReportType.EXECUTIVE,
            title="x", body="…",
            freshness_date="2026-01-01",
            claims=(ReportClaim(
                claim_text="claim", classification=ReportClaimClassification.FACT,
                source_citation="", verification_reference="v-1",
            ),),
        ))


def test_reporting_engine_requires_verification_for_material_claim() -> None:
    """A material claim (FACT / INFERENCE / PROJECTION) without a
    Verification reference is REJECTED (Constitution Article XVII)."""
    eng = ReportingEngine()
    with pytest.raises(MaterialClaimWithoutVerificationError):
        eng.validate_report(ReportSpec(
            report_type=ReportType.BOARD,
            title="Board Report", body="…",
            freshness_date="2026-01-01",
            claims=(ReportClaim(
                claim_text="claim", classification=ReportClaimClassification.FACT,
                source_citation="x", verification_reference=None,
            ),),
        ))


def test_reporting_engine_valid_report_with_attestation() -> None:
    """A valid Report carries a Constitutional Compliance Attestation."""
    eng = ReportingEngine()
    result = eng.validate_report(ReportSpec(
        report_type=ReportType.COMPLIANCE,
        title="Compliance Report", body="…",
        freshness_date="2026-01-01",
        freshness_class=ReportFreshnessClass.QUARTERLY,
        claims=(
            ReportClaim(
                claim_text="Material claim", classification=ReportClaimClassification.FACT,
                source_citation="Phase 7 test", verification_reference="v-1",
            ),
            ReportClaim(
                claim_text="Recommendation", classification=ReportClaimClassification.RECOMMENDATION,
                source_citation="Phase 7 test",
            ),
        ),
    ))
    assert result.material_claims_count == 1
    assert result.unverified_claims_count == 0
    assert result.attestation.outcome.value == "COMPLIANT"


# ---------------------------------------------------------------------------
# Notification engine (6 categories × 5 channels, suppression)
# ---------------------------------------------------------------------------


def test_notification_engine_priority_order() -> None:
    """The 6 priorities follow Class 4 → Class 3 → Class 2 → Class 1 →
    Operational → Informational."""
    eng = NotificationEngine()
    order = eng.priority_order()
    assert order == [
        NotificationPriority.CLASS_4,
        NotificationPriority.CLASS_3,
        NotificationPriority.CLASS_2,
        NotificationPriority.CLASS_1,
        NotificationPriority.OPERATIONAL,
        NotificationPriority.INFORMATIONAL,
    ]


def test_notification_engine_routes_class_4_via_voice() -> None:
    """A Class 4 (Emergency) notification can be routed via Voice."""
    eng = NotificationEngine()
    spec = NotificationSpec(
        category=NotificationCategory.ESCALATIONS,
        priority=NotificationPriority.CLASS_4,
        subject="Constitutional Incident", body="…",
        target_user_id="u-1",
        channels=(NotificationChannel.IN_APP, NotificationChannel.VOICE),
    )
    result = eng.route(spec)
    assert result.delivered


def test_notification_engine_rejects_voice_for_class_3() -> None:
    """Voice is reserved for Class 4 (Emergency) — REJECTED for Class 3."""
    eng = NotificationEngine()
    spec = NotificationSpec(
        category=NotificationCategory.APPROVALS,
        priority=NotificationPriority.CLASS_3,
        subject="Approval needed", body="…",
        target_user_id="u-1",
        channels=(NotificationChannel.VOICE,),
    )
    with pytest.raises(VoiceReservedForEmergencyError):
        eng.route(spec)


def test_notification_engine_rejects_sms_for_class_1() -> None:
    """SMS is reserved for Class 3 / Class 4 — REJECTED for Class 1."""
    eng = NotificationEngine()
    spec = NotificationSpec(
        category=NotificationCategory.REMINDERS,
        priority=NotificationPriority.CLASS_1,
        subject="Reminder", body="…",
        target_user_id="u-1",
        channels=(NotificationChannel.SMS,),
    )
    with pytest.raises(SmsReservedForClass3Or4Error):
        eng.route(spec)


def test_notification_engine_allows_sms_for_class_3() -> None:
    """SMS is allowed for Class 3."""
    eng = NotificationEngine()
    spec = NotificationSpec(
        category=NotificationCategory.APPROVALS,
        priority=NotificationPriority.CLASS_3,
        subject="Approval needed", body="…",
        target_user_id="u-1",
        channels=(NotificationChannel.SMS,),
    )
    result = eng.route(spec)
    assert result.delivered


def test_notification_engine_rejects_suppression_of_class_3() -> None:
    """Suppression of a Class 3 notification is FORBIDDEN (AC-P7-003)."""
    eng = NotificationEngine()
    spec = NotificationSpec(
        category=NotificationCategory.APPROVALS,
        priority=NotificationPriority.CLASS_3,
        subject="Approval needed", body="…",
        target_user_id="u-1",
        suppressed=True,
    )
    with pytest.raises(SuppressionForbiddenError):
        eng.route(spec)


def test_notification_engine_rejects_suppression_of_class_4() -> None:
    """Suppression of a Class 4 notification is FORBIDDEN (AC-P7-003)."""
    eng = NotificationEngine()
    spec = NotificationSpec(
        category=NotificationCategory.ESCALATIONS,
        priority=NotificationPriority.CLASS_4,
        subject="Constitutional Incident", body="…",
        target_user_id="u-1",
        suppressed=True,
    )
    with pytest.raises(SuppressionForbiddenError):
        eng.route(spec)


def test_notification_engine_allows_suppression_of_operational() -> None:
    """Suppression of Operational notifications is allowed."""
    eng = NotificationEngine()
    spec = NotificationSpec(
        category=NotificationCategory.REMINDERS,
        priority=NotificationPriority.OPERATIONAL,
        subject="Reminder", body="…",
        target_user_id="u-1",
        suppressed=True,
    )
    result = eng.route(spec)
    assert result.delivered
    assert not result.suppression_violation


# ---------------------------------------------------------------------------
# Risk and Compliance engine
# ---------------------------------------------------------------------------


def test_risk_engine_high_severity_requires_human_approval() -> None:
    """A HIGH-severity risk requires Human Approval (AC-P7-004)."""
    eng = RiskEngine()
    spec = RiskEntrySpec(
        title="Critical supplier failure", description="…",
        severity=RiskSeverity.HIGH, owner_office="Risk and Compliance Office",
    )
    result = eng.validate_risk(spec)
    assert result.requires_human_approval


def test_risk_engine_low_severity_no_approval() -> None:
    """A LOW-severity risk does NOT require Human Approval."""
    eng = RiskEngine()
    spec = RiskEntrySpec(
        title="Minor", description="…",
        severity=RiskSeverity.LOW, owner_office="Risk and Compliance Office",
    )
    result = eng.validate_risk(spec)
    assert not result.requires_human_approval


def test_constitutional_incident_engine_escalates_critical() -> None:
    """A CRITICAL Constitutional Incident is escalated to Human (Class 4)."""
    eng = ConstitutionalIncidentEngine()
    spec = ConstitutionalIncidentSpec(
        title="Article XII bypassed", description="…",
        severity=ConstitutionalIncidentSeverity.CRITICAL,
        affected_clause="Article XII", reporter_id="u-1",
    )
    result = eng.investigate(spec)
    assert result.escalated_to_human
    assert result.status.value == "ESCALATED_TO_HUMAN"


def test_constitutional_incident_engine_requires_reporter() -> None:
    """A Constitutional Incident without a reporter is REJECTED
    (Constitution Article XX paragraph 7)."""
    eng = ConstitutionalIncidentEngine()
    with pytest.raises(Exception):
        eng.investigate(ConstitutionalIncidentSpec(
            title="x", description="x",
            severity=ConstitutionalIncidentSeverity.MAJOR,
            affected_clause="Article VI", reporter_id="",
        ))


# ---------------------------------------------------------------------------
# Performance engine
# ---------------------------------------------------------------------------


def test_performance_engine_evaluates_metric_on_track() -> None:
    """A metric within 5% of target is ON_TRACK."""
    eng = PerformanceEngine()
    spec = PerformanceMetricSpec(
        metric_name="win_rate", metric_value=0.97, target=1.0,
        direction=PerformanceMetricDirection.HIGHER_IS_BETTER,
    )
    result = eng.evaluate_metric(spec)
    assert result.status == "ON_TRACK"


def test_performance_engine_detects_bottleneck() -> None:
    """The Performance engine detects a bottleneck."""
    eng = PerformanceEngine()
    assert eng.detect_bottleneck(stage_name="S09", avg_cycle_hours=72.0, threshold_hours=48.0)
    assert not eng.detect_bottleneck(stage_name="S09", avg_cycle_hours=24.0, threshold_hours=48.0)


def test_performance_engine_checks_sla() -> None:
    """The Performance engine checks SLAs."""
    eng = PerformanceEngine()
    assert eng.check_sla(sla_name="approval_24h", target_hours=24.0, actual_hours=18.0)
    assert not eng.check_sla(sla_name="approval_24h", target_hours=24.0, actual_hours=30.0)


# ---------------------------------------------------------------------------
# Compliance engine
# ---------------------------------------------------------------------------


def test_compliance_engine_evaluates_status() -> None:
    """The Compliance engine evaluates compliance status."""
    eng = ComplianceEngine()
    status = eng.evaluate_compliance(
        office="Risk and Compliance Office",
        status=ComplianceStatus.COMPLIANT,
        evidence="Phase 7 test",
    )
    assert status == ComplianceStatus.COMPLIANT


# ---------------------------------------------------------------------------
# Constitutional Amendment without approval (typed exception)
# ---------------------------------------------------------------------------


def test_constitutional_amendment_error_typed() -> None:
    """The CONSTITUTIONAL_AMENDMENT without approval raises a typed error."""
    err = ConstitutionalAmendmentWithoutApprovalError()
    assert "Article XXVIII" in str(err)


def test_irreversible_update_error_typed() -> None:
    """The irreversible update error is a typed error."""
    err = IrreversibleUpdateRejectedError()
    assert "REVERSIBLE" in str(err)
