"""Phase 3 acceptance tests.

Covers:
  - AC-P3-001..008 — Workflow, Verification, Approval, Notification,
                     Orchestration, Independence, Human Approval Gate.
  - AC-VER-001..005 — Verification independence criteria.
  - AC-APR-001..006 — Human Approval criteria.
  - The 3 specific bypass tests:
    - Discovery Order cannot be skipped / abbreviated / reordered.
    - Human Approval Gate cannot be bypassed by silence / urgency /
      prior behaviour / AI recommendation.
    - Producer != Verifier is enforced.

Source: Document 06 (Workflow and AI Orchestration Design v1.0);
Authority Matrix v1.0; Charter Manual v1.0.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from techno_service_ai.approval import (
    ApprovalDecision,
    ApprovalEngine,
    ApprovalPackage,
    DecisionClass,
    SilenceNotApproval,
    SoDViolation,
    StandingAuthorisation,
    StandingAuthorisationValidator,
    REQUIRED_APPROVER_ROLE,
)
from techno_service_ai.escalation import (
    EscalationChannel,
    EscalationEngine,
)
from techno_service_ai.exceptions import ExceptionEngine, ExceptionScenario, all_scenarios
from techno_service_ai.gates import (
    GATES,
    GateBypassError,
    GateEngine,
    GateName,
    all_gates,
    is_bypass_attempt,
)
from techno_service_ai.handoff import (
    HandoffRejected,
    HandoffService,
)
from techno_service_ai.notification import (
    NotificationCategory,
    NotificationChannel,
    NotificationEngine,
    NotificationPriority,
    PRIORITY_RANK,
    SuppressionForbidden,
)
from techno_service_ai.orchestration import WorkflowEngine, WorkflowEventType
from techno_service_ai.recovery import (
    Class3Or4ResumeRequiresApproval,
    RecoveryEngine,
    RollbackRequiresApproval,
)
from techno_service_ai.stages import (
    DISCOVERY_ORDER,
    StageNumber,
    assert_total_stages,
    is_valid_progression,
    next_stage,
)
from techno_service_ai.states import (
    ALLOWED_TRANSITIONS,
    OrchestrationState,
    StateMachine,
    TransitionError,
)
from techno_service_ai.verification import (
    ClaimClassification,
    IndependenceTracker,
    IndependenceViolation,
    ProducerRef,
    VerifierAgent,
    VerifierRef,
    VerifierRole,
    VerificationOutcome,
    five_agent_roster,
)


# ---------------------------------------------------------------------------
# AC-P3-001 — A workflow can be initiated, executed, transitioned, closed
# ---------------------------------------------------------------------------


def test_ac_p3_001_workflow_initiated_executed_transitioned_closed() -> None:
    """The WorkflowEngine supports the full lifecycle: initiate ->
    execute stages -> close -> archive."""
    eng = WorkflowEngine()
    assert eng.state_machine.state == OrchestrationState.IDLE
    # Initiate.
    eng.initiate()
    assert eng.state_machine.state == OrchestrationState.RUNNING
    assert eng.current_stage == StageNumber.S01_INDUSTRIAL_ENVIRONMENT
    # Complete S01 (already started by initiate).
    nxt = eng.complete_stage(eng.current_stage)
    # Complete the remaining 23 stages in order.
    for _ in range(23):
        assert nxt is not None
        nxt = eng.complete_stage(nxt)
    # After the last stage, complete_stage returns None.
    assert nxt is None
    # Close.
    eng.close()
    assert eng.state_machine.state == OrchestrationState.CLOSED
    # Archive.
    eng.archive()
    assert eng.state_machine.state == OrchestrationState.ARCHIVED
    # Events recorded.
    initiated = [e for e in eng.events if e.event_type == WorkflowEventType.INITIATED]
    completed = [e for e in eng.events if e.event_type == WorkflowEventType.STAGE_COMPLETED]
    assert len(initiated) == 1
    assert len(completed) == 24
    closed = [e for e in eng.events if e.event_type == WorkflowEventType.WORKFLOW_CLOSED]
    archived = [e for e in eng.events if e.event_type == WorkflowEventType.WORKFLOW_ARCHIVED]
    assert len(closed) == 1
    assert len(archived) == 1


# ---------------------------------------------------------------------------
# AC-P3-002 — Every Decision Gate enforces its conditions
# ---------------------------------------------------------------------------


def test_ac_p3_002_nine_gates_registered() -> None:
    """All 9 Decision Gates are registered with their constitutional spec."""
    gates = all_gates()
    assert len(gates) == 9
    # Every gate has a spec with the four mandatory fields.
    for g in gates:
        spec = GATES[g]
        assert spec.purpose
        assert spec.location
        assert spec.entry_conditions
        assert spec.exit_conditions
        assert spec.owner
        # Bypass prohibition mentions the gate.
        assert "No workflow may bypass" in spec.bypass_prohibition


@pytest.mark.parametrize("gate", all_gates())
def test_ac_p3_002_every_gate_bypass_rejected(gate: GateName) -> None:
    """A bypass attempt on any of the 9 gates is REJECTED."""
    ge = GateEngine()
    with pytest.raises(GateBypassError) as exc_info:
        ge.bypass_attempt(gate, {})
    assert exc_info.value.gate == gate
    # The gate's bypass_prohibition spec must contain the canonical
    # "No workflow may bypass" text (per Document 06 §4.X for each gate).
    assert "No workflow may bypass" in is_bypass_attempt(gate)


# ---------------------------------------------------------------------------
# AC-P3-003 — Orchestration State Machine enforces allowed/forbidden
# ---------------------------------------------------------------------------


def test_ac_p3_003_ten_states_implemented() -> None:
    """All 10 Orchestration States are implemented (Document 06 §8.1)."""
    assert len(OrchestrationState) == 10
    expected = {
        "IDLE", "RUNNING", "WAITING", "SUSPENDED", "REWORK",
        "ESCALATED", "APPROVED", "REJECTED", "CLOSED", "ARCHIVED",
    }
    assert {s.value for s in OrchestrationState} == expected


def test_ac_p3_003_forbidden_transition_rejected() -> None:
    """A forbidden transition is prevented, not warned."""
    sm = StateMachine(OrchestrationState.IDLE)
    sm.transition(OrchestrationState.RUNNING)
    # RUNNING -> IDLE is forbidden per §8.1.
    with pytest.raises(TransitionError):
        sm.transition(OrchestrationState.IDLE)
    # RUNNING -> ARCHIVED is forbidden per §8.1.
    with pytest.raises(TransitionError):
        sm.transition(OrchestrationState.ARCHIVED)
    # CLOSED can only go to ARCHIVED.
    sm2 = StateMachine(OrchestrationState.RUNNING)
    sm2.transition(OrchestrationState.CLOSED)
    with pytest.raises(TransitionError):
        sm2.transition(OrchestrationState.RUNNING)


def test_ac_p3_003_every_transition_recorded() -> None:
    """Every transition is recorded in the history (STATE-G-001)."""
    sm = StateMachine(OrchestrationState.IDLE)
    sm.transition(OrchestrationState.RUNNING)
    sm.transition(OrchestrationState.WAITING)
    sm.transition(OrchestrationState.RUNNING)
    assert len(sm.history) == 3
    assert sm.history[0] == (OrchestrationState.IDLE, OrchestrationState.RUNNING)


def test_ac_p3_003_allowed_transitions_match_doc() -> None:
    """The allowed transitions match Document 06 §8.1."""
    # IDLE: {RUNNING, ARCHIVED}
    assert ALLOWED_TRANSITIONS[OrchestrationState.IDLE] == frozenset({
        OrchestrationState.RUNNING, OrchestrationState.ARCHIVED,
    })
    # CLOSED: {ARCHIVED} only
    assert ALLOWED_TRANSITIONS[OrchestrationState.CLOSED] == frozenset({
        OrchestrationState.ARCHIVED,
    })
    # ARCHIVED: {} (reactivation only by Major Amendment)
    assert ALLOWED_TRANSITIONS[OrchestrationState.ARCHIVED] == frozenset()


# ---------------------------------------------------------------------------
# AC-P3-004 + AC-VER-002 — Producer != Verifier is REJECTED
# ---------------------------------------------------------------------------


def test_ac_p3_004_producer_not_equal_to_verifier_rejected() -> None:
    """When producer_id == verifier_id, the verification is REJECTED."""
    tracker = IndependenceTracker()
    producer = ProducerRef(producer_id="agent-X", role_code="ANALYST")
    verifier = VerifierRef(verifier_id="agent-X", role=VerifierRole.PRELIMINARY_EVIDENCE_REVIEWER, role_code="VERIFIER")
    with pytest.raises(IndependenceViolation):
        tracker.create_record(
            canonical_id="v1", material_claim_id="claim-1", producer=producer, verifier=verifier,
            claim_classification=ClaimClassification.FACT, outcome=VerificationOutcome.VALIDATED,
            reason="attempting to self-verify", source_citations=("src1",),
            second_reviewer_id=None, created_at="2026-01-01",
        )
    # The violation is recorded on the tracker.
    assert len(tracker.rejections) == 1


def test_ac_p3_004_independent_producer_verifier_accepted() -> None:
    """When producer_id != verifier_id, the verification is ACCEPTED."""
    tracker = IndependenceTracker()
    producer = ProducerRef(producer_id="analyst-1", role_code="ANALYST")
    verifier = VerifierRef(verifier_id="verifier-1", role=VerifierRole.PRELIMINARY_EVIDENCE_REVIEWER, role_code="VERIFIER")
    rec = tracker.create_record(
        canonical_id="v1", material_claim_id="claim-1", producer=producer, verifier=verifier,
        claim_classification=ClaimClassification.FACT, outcome=VerificationOutcome.VALIDATED,
        reason="source verified", source_citations=("src1",), second_reviewer_id=None, created_at="2026-01-01",
    )
    assert tracker.is_independent(rec) is True
    assert rec.independence_checked is True


# ---------------------------------------------------------------------------
# AC-VER-001..005 — Verification independence criteria
# ---------------------------------------------------------------------------


def test_ac_ver_001_five_verifier_roles_implemented() -> None:
    """All 5 Verifier Roles are implemented (Document 06 §6)."""
    assert len(VerifierRole) == 5
    assert VerifierRole.PRELIMINARY_EVIDENCE_REVIEWER in VerifierRole
    assert VerifierRole.SPECIALIST_VERIFIER in VerifierRole
    assert VerifierRole.INDEPENDENT_FINAL_VERIFIER in VerifierRole
    assert VerifierRole.SECOND_REVIEWER in VerifierRole
    assert VerifierRole.CLAIM_CLASSIFIER in VerifierRole
    # The 5-agent roster has one of each.
    roster = five_agent_roster()
    assert len(roster) == 5
    assert {a.role for a in roster} == set(VerifierRole)


def test_ac_ver_002_producer_verifier_separation() -> None:
    """VER-IND-001..003: producer and verifier are separately identifiable."""
    # The Independence Tracker enforces this.
    tracker = IndependenceTracker()
    producer = ProducerRef(producer_id="P1", role_code="ANALYST")
    verifier = VerifierRef(verifier_id="V1", role=VerifierRole.INDEPENDENT_FINAL_VERIFIER, role_code="VERIFIER")
    rec = tracker.create_record(
        canonical_id="v1", material_claim_id="c1", producer=producer, verifier=verifier,
        claim_classification=ClaimClassification.FACT, outcome=VerificationOutcome.VALIDATED,
        reason="r", source_citations=("s1",), second_reviewer_id="V2", created_at="2026-01-01",
    )
    assert rec.producer.producer_id != rec.verifier.verifier_id
    assert tracker.is_independent(rec)


def test_ac_ver_003_second_reviewer_required_for_independent_final() -> None:
    """VER-IFV-003: an Independent Final Verifier on a material claim
    requires a Second Reviewer."""
    tracker = IndependenceTracker()
    producer = ProducerRef(producer_id="analyst-1", role_code="ANALYST")
    verifier = VerifierRef(verifier_id="ifv-1", role=VerifierRole.INDEPENDENT_FINAL_VERIFIER, role_code="VERIFIER")
    with pytest.raises(IndependenceViolation):
        tracker.create_record(
            canonical_id="v1", material_claim_id="c1", producer=producer, verifier=verifier,
            claim_classification=ClaimClassification.FACT, outcome=VerificationOutcome.VALIDATED,
            reason="r", source_citations=("s1",), second_reviewer_id=None,
            created_at="2026-01-01",
        )


def test_ac_ver_004_claim_classification_enum() -> None:
    """The 5 Claim Classifications of Constitution Article XXIII are implemented."""
    assert len(ClaimClassification) == 5
    assert ClaimClassification.FACT in ClaimClassification
    assert ClaimClassification.INFERENCE in ClaimClassification
    assert ClaimClassification.PROJECTION in ClaimClassification
    assert ClaimClassification.RECOMMENDATION in ClaimClassification
    assert ClaimClassification.UNVERIFIED in ClaimClassification


def test_ac_ver_005_verification_outcomes_recorded() -> None:
    """The 4 outcomes (VALIDATED, QUALIFIED, REJECTED, PENDING) are recorded."""
    assert VerificationOutcome.VALIDATED in VerificationOutcome
    assert VerificationOutcome.QUALIFIED in VerificationOutcome
    assert VerificationOutcome.REJECTED in VerificationOutcome
    assert VerificationOutcome.PENDING in VerificationOutcome


# ---------------------------------------------------------------------------
# AC-P3-005 + AC-APR-001..006 — Approval Engine
# ---------------------------------------------------------------------------


def _make_class4_package(originating_agent_id: str = "agent-1", decision_type: str = "BINDING_BID") -> ApprovalPackage:
    """Build a Class 4 ApprovalPackage with the resolved Required Approver Role.

    The generic CLASS_4 role is "AUTHORISED_EXECUTIVE_OR_CONSTITUTIONAL_OWNER";
    for a per-decision-type test we resolve the actual approver from
    the Authority Matrix Section 3.4 table.
    """
    # The resolved per-decision-type approver for a BINDING_BID is AUTHORISED_EXECUTIVE.
    required_approver = "AUTHORISED_EXECUTIVE" if decision_type == "BINDING_BID" else "CONSTITUTIONAL_OWNER"
    return ApprovalPackage(
        material_reference=decision_type,
        decision_class=DecisionClass.CLASS_4,
        required_approver_role=required_approver,
        verified_material="Material v1",
        claim_classifications=("FACT",),
        evidence_references=("ev1",),
        verification_references=("v1",),
        decision_options=("APPROVE", "REJECT"),
        risk_register_references=(),
        performance_data_references=(),
        constitutional_compliance_attestation="attested",
        originating_office="Tender",
        originating_agent_id=originating_agent_id,
    )


def test_ac_p3_005_approval_routed_to_required_approver() -> None:
    """An approval request is routed to the Required Approver Role."""
    eng = ApprovalEngine()
    pkg = _make_class4_package(originating_agent_id="agent-1")
    req = eng.create_request(
        package=pkg, request_date="2026-01-01", response_window=timedelta(days=7)
    )
    # The required approver role is resolved from the decision class.
    role = eng.required_approver_role(DecisionClass.CLASS_4, "BINDING_BID")
    assert role == "AUTHORISED_EXECUTIVE"
    # The package carries the resolved role.
    assert req.package.required_approver_role == "AUTHORISED_EXECUTIVE"
    # The wrong role is REJECTED.
    with pytest.raises(SoDViolation) as exc:
        eng.decide(
            request_canonical_id=req.canonical_id, approver_id="rhfo-1",
            approver_role="RESPONSIBLE_HUMAN_FUNCTION_OWNER",
            decision=ApprovalDecision.APPROVED, decision_date="2026-01-08",
        )
    assert exc.value.rule == "Required Approver Role"
    # The right role is ACCEPTED.
    dec = eng.decide(
        request_canonical_id=req.canonical_id, approver_id="exec-1",
        approver_role="AUTHORISED_EXECUTIVE",
        decision=ApprovalDecision.APPROVED, decision_date="2026-01-08", reason="ok"
    )
    assert dec.decision == ApprovalDecision.APPROVED
    assert dec.approver_id == "exec-1"


def test_ac_apr_001_silence_is_not_approval() -> None:
    """AC-P3-008: silence, urgency, prior behaviour, AI recommendation
    are NOT approval. All four are REJECTED."""
    eng = ApprovalEngine()
    pkg = _make_class4_package()
    req = eng.create_request(package=pkg, request_date="2026-01-01", response_window=timedelta(days=7))
    for signal, detail in [
        ("SILENCE", "approver did not respond within the 7-day window"),
        ("URGENCY", "the customer needs an answer today"),
        ("PRIOR_BEHAVIOUR", "the same approver approved a similar tender last month"),
        ("SIMILAR_HISTORICAL_APPROVAL", "tender T-2025-08 was approved on similar terms"),
        ("AI_RECOMMENDATION", "the Commercial Agent recommends approval"),
    ]:
        with pytest.raises(SilenceNotApproval) as exc:
            eng.check_silence_not_approval(
                request_canonical_id=req.canonical_id,
                bypass_signal=signal, detail=detail,
            )
        assert exc.value.reason_code == signal
    # All 5 rejections are recorded.
    assert len(eng.bypass_rejections) == 5


def test_ac_apr_002_self_approval_prohibited() -> None:
    """Authority Matrix §8.2: Self-Approval Prohibited."""
    eng = ApprovalEngine()
    pkg = _make_class4_package(originating_agent_id="agent-1")
    req = eng.create_request(package=pkg, request_date="2026-01-01", response_window=timedelta(days=7))
    with pytest.raises(SoDViolation) as exc:
        eng.decide(
            request_canonical_id=req.canonical_id, approver_id="agent-1",
            approver_role="AUTHORISED_EXECUTIVE",
            decision=ApprovalDecision.APPROVED, decision_date="2026-01-08",
        )
    assert exc.value.rule == "Self-Approval Prohibited"


def test_ac_apr_003_conditional_approval_requires_terms() -> None:
    """A CONDITIONAL decision requires conditions, duration, and revocation conditions."""
    eng = ApprovalEngine()
    pkg = _make_class4_package()
    req = eng.create_request(package=pkg, request_date="2026-01-01", response_window=timedelta(days=7))
    # No conditions -> rejected.
    with pytest.raises(ValueError):
        eng.decide(
            request_canonical_id=req.canonical_id, approver_id="exec-1",
            approver_role="AUTHORISED_EXECUTIVE",
            decision=ApprovalDecision.CONDITIONAL, decision_date="2026-01-08",
        )
    # No duration -> rejected.
    with pytest.raises(ValueError):
        eng.decide(
            request_canonical_id=req.canonical_id, approver_id="exec-1",
            approver_role="AUTHORISED_EXECUTIVE",
            decision=ApprovalDecision.CONDITIONAL, decision_date="2026-01-08",
            conditions=("price within budget",), revocation_conditions=("price changes",),
        )
    # No revocation conditions -> rejected.
    with pytest.raises(ValueError):
        eng.decide(
            request_canonical_id=req.canonical_id, approver_id="exec-1",
            approver_role="AUTHORISED_EXECUTIVE",
            decision=ApprovalDecision.CONDITIONAL, decision_date="2026-01-08",
            conditions=("price within budget",), duration=timedelta(days=30),
        )
    # All present -> accepted with expiry.
    dec = eng.decide(
        request_canonical_id=req.canonical_id, approver_id="exec-1",
        approver_role="AUTHORISED_EXECUTIVE",
        decision=ApprovalDecision.CONDITIONAL, decision_date="2026-01-08",
        conditions=("price within budget",), revocation_conditions=("price changes",),
        duration=timedelta(days=30), reason="conditional",
    )
    assert dec.expiry_date is not None
    assert dec.decision == ApprovalDecision.CONDITIONAL


def test_ac_apr_004_approval_revocation() -> None:
    """A prior Approval Decision can be revoked per Authority Matrix §10."""
    eng = ApprovalEngine()
    pkg = _make_class4_package()
    req = eng.create_request(package=pkg, request_date="2026-01-01", response_window=timedelta(days=7))
    dec = eng.decide(
        request_canonical_id=req.canonical_id, approver_id="exec-1",
        approver_role="AUTHORISED_EXECUTIVE",
        decision=ApprovalDecision.APPROVED, decision_date="2026-01-08", reason="ok"
    )
    # Invalid grounds -> rejected.
    with pytest.raises(ValueError):
        eng.revoke(
            decision_canonical_id=dec.canonical_id, revoker_id="exec-1",
            revocation_date="2026-02-01", grounds="BECAUSE_I_SAID_SO",
            remediation="re-evaluate",
        )
    # Valid grounds -> revoked.
    rv = eng.revoke(
        decision_canonical_id=dec.canonical_id, revoker_id="exec-1",
        revocation_date="2026-02-01", grounds="BREACH_OF_CONDITIONS",
        remediation="re-issue at lower price",
    )
    assert rv.grounds == "BREACH_OF_CONDITIONS"
    assert eng.is_revoked(dec.canonical_id) is True


def test_ac_apr_005_decision_audit_trail() -> None:
    """Every Approval Request, Decision, and Revocation is in the audit trail."""
    eng = ApprovalEngine()
    pkg = _make_class4_package()
    req = eng.create_request(package=pkg, request_date="2026-01-01", response_window=timedelta(days=7))
    dec = eng.decide(
        request_canonical_id=req.canonical_id, approver_id="exec-1",
        approver_role="AUTHORISED_EXECUTIVE",
        decision=ApprovalDecision.APPROVED, decision_date="2026-01-08", reason="ok"
    )
    eng.revoke(
        decision_canonical_id=dec.canonical_id, revoker_id="exec-1",
        revocation_date="2026-02-01", grounds="ERROR", remediation="re-evaluate"
    )
    trail = eng.audit_trail(req.canonical_id)
    # 1 request + 1 decision + 1 revocation = 3 events.
    assert len(trail) == 3


def test_ac_apr_006_four_decision_classes() -> None:
    """The 4 Decision Classes of Constitution Article XII are implemented."""
    assert len(DecisionClass) == 4
    assert REQUIRED_APPROVER_ROLE[DecisionClass.CLASS_1] == "AGENT_WITHIN_CHARTER"
    assert REQUIRED_APPROVER_ROLE[DecisionClass.CLASS_2] == "RESPONSIBLE_HUMAN_FUNCTION_OWNER"
    assert REQUIRED_APPROVER_ROLE[DecisionClass.CLASS_3] == "RESPONSIBLE_HUMAN_FUNCTION_OWNER"
    assert REQUIRED_APPROVER_ROLE[DecisionClass.CLASS_4] == "AUTHORISED_EXECUTIVE_OR_CONSTITUTIONAL_OWNER"


def test_ac_apr_standing_authorisation_prohibited_categories() -> None:
    """Authority Matrix §5.3: Standing Authorisations may not be issued
    for Class 4 or any of the prohibited categories."""
    eng = ApprovalEngine()
    validator = StandingAuthorisationValidator()
    # Class 4 SA is rejected.
    sa = StandingAuthorisation(
        canonical_id="sa-1", issuing_authority="exec-1", issuing_date="2026-01-01",
        expiry_date="2027-01-01", scope="CLASS_4", recipients=("vendor-1",),
        approved_content_template="x", prohibited_representations=(),
        responsible_human_owner="exec-1", revocation_conditions=(),
        audit_requirements="annual", review_date="2026-12-01",
    )
    with pytest.raises(SilenceNotApproval):
        validator.validate(sa, DecisionClass.CLASS_4)
    # Prohibited category scope is rejected even at Class 3.
    sa2 = StandingAuthorisation(
        canonical_id="sa-2", issuing_authority="exec-1", issuing_date="2026-01-01",
        expiry_date="2027-01-01", scope="BINDING_BID_OR_TENDER", recipients=("vendor-1",),
        approved_content_template="x", prohibited_representations=(),
        responsible_human_owner="exec-1", revocation_conditions=(),
        audit_requirements="annual", review_date="2026-12-01",
    )
    with pytest.raises(SilenceNotApproval):
        validator.validate(sa2, DecisionClass.CLASS_3)


# ---------------------------------------------------------------------------
# AC-P3-006 — Notification: created, delivered, acknowledged
# ---------------------------------------------------------------------------


def test_ac_p3_006_notification_create_deliver_acknowledge() -> None:
    """A notification is created, delivered, and acknowledged."""
    ne = NotificationEngine()
    n = ne.issue(
        recipient_id="u1", category=NotificationCategory.APPROVAL,
        priority=NotificationPriority.CLASS_2, channel=NotificationChannel.EMAIL,
        subject="Approval needed", body="Please review", issued_at="2026-01-01"
    )
    assert n.status.value == "ISSUED"
    ne.deliver(n.canonical_id, delivered_at="2026-01-01T01:00:00")
    n2 = ne.notifications[n.canonical_id]
    assert n2.status.value == "DELIVERED"
    ne.acknowledge(n.canonical_id, acknowledged_at="2026-01-02T00:00:00")
    n3 = ne.notifications[n.canonical_id]
    assert n3.status.value == "ACKNOWLEDGED"


def test_ac_p3_006_six_categories_five_channels_priority_order() -> None:
    """6 categories, 5 channels, priority order per Constitution."""
    assert len(NotificationCategory) == 6
    assert len(NotificationChannel) == 5
    assert len(NotificationPriority) == 6
    # The constitutional priority order: Class 4 > Class 3 > Class 2 >
    # Class 1 > Operational > Informational.
    expected = [
        NotificationPriority.CLASS_4, NotificationPriority.CLASS_3,
        NotificationPriority.CLASS_2, NotificationPriority.CLASS_1,
        NotificationPriority.OPERATIONAL, NotificationPriority.INFORMATIONAL,
    ]
    for a, b in zip(expected, expected[1:]):
        assert PRIORITY_RANK[a] < PRIORITY_RANK[b]


def test_ac_p3_006_suppression_of_class_3_or_4_forbidden() -> None:
    """Suppression of Class 3 / Class 4 notifications is FORBIDDEN."""
    ne = NotificationEngine()
    n3 = ne.issue(
        recipient_id="u1", category=NotificationCategory.ESCALATION,
        priority=NotificationPriority.CLASS_3, channel=NotificationChannel.PUSH,
        subject="x", body="y", issued_at="2026-01-01"
    )
    n4 = ne.issue(
        recipient_id="u1", category=NotificationCategory.ESCALATION,
        priority=NotificationPriority.CLASS_4, channel=NotificationChannel.PUSH,
        subject="x", body="y", issued_at="2026-01-01"
    )
    with pytest.raises(SuppressionForbidden):
        ne.suppress(n3.canonical_id, reason="noise")
    with pytest.raises(SuppressionForbidden):
        ne.suppress(n4.canonical_id, reason="noise")
    # Class 1 / Informational CAN be suppressed.
    n1 = ne.issue(
        recipient_id="u1", category=NotificationCategory.REMINDER,
        priority=NotificationPriority.INFORMATIONAL, channel=NotificationChannel.EMAIL,
        subject="x", body="y", issued_at="2026-01-01"
    )
    ne.suppress(n1.canonical_id, reason="reminder redundant")
    assert ne.notifications[n1.canonical_id].status.value == "SUPPRESSED"


def test_ac_p3_006_sms_reserved_for_class_3_4() -> None:
    """SMS is reserved for Class 3 and Class 4 (UI/UX §10)."""
    from techno_service_ai.notification import ChannelIneligible
    ne = NotificationEngine()
    with pytest.raises(ChannelIneligible):
        ne.issue(
            recipient_id="u1", category=NotificationCategory.REMINDER,
            priority=NotificationPriority.CLASS_1, channel=NotificationChannel.SMS,
            subject="x", body="y", issued_at="2026-01-01"
        )
    # Class 3 SMS is OK.
    ne.issue(
        recipient_id="u1", category=NotificationCategory.ESCALATION,
        priority=NotificationPriority.CLASS_3, channel=NotificationChannel.SMS,
        subject="x", body="y", issued_at="2026-01-01"
    )


# ---------------------------------------------------------------------------
# AC-P3-007 — Independence of Verification preserved (already covered)
# ---------------------------------------------------------------------------


def test_ac_p3_007_independence_preserved_throughout_workflow() -> None:
    """Independence is preserved on every verification record in a workflow."""
    eng = WorkflowEngine()
    eng.initiate()
    producer = ProducerRef(producer_id="analyst-1", role_code="ANALYST")
    verifier = VerifierRef(verifier_id="ifv-1", role=VerifierRole.INDEPENDENT_FINAL_VERIFIER, role_code="VERIFIER")
    rec = eng.verification_tracker.create_record(
        canonical_id="v1", material_claim_id="c1", producer=producer, verifier=verifier,
        claim_classification=ClaimClassification.FACT, outcome=VerificationOutcome.VALIDATED,
        reason="verified", source_citations=("s1",), second_reviewer_id="sr-1", created_at="2026-01-01"
    )
    assert eng.verification_tracker.is_independent(rec)


# ---------------------------------------------------------------------------
# Discovery Order cannot be skipped / abbreviated / reordered
# ---------------------------------------------------------------------------


def test_discovery_order_cannot_be_skipped() -> None:
    """WF-PRIN-007 / ORCH-SEQ-003: a stage cannot be skipped."""
    eng = WorkflowEngine()
    eng.initiate()
    # Try to start Stage 5 from Stage 1.
    with pytest.raises(ValueError) as exc:
        eng.start_stage(StageNumber.S05_ROOT_CAUSE)
    assert "Invalid progression" in str(exc.value)
    assert "REJECTED" in str(exc.value)


def test_discovery_order_cannot_be_reordered() -> None:
    """ORCH-SEQ-002: a stage cannot be reordered (the sequence is fixed)."""
    eng = WorkflowEngine()
    eng.initiate()
    # Current is S01. Trying to start S02 from S01 is valid (forward).
    # But trying to start S01 again (the same stage) is invalid.
    with pytest.raises(ValueError):
        eng.start_stage(StageNumber.S01_INDUSTRIAL_ENVIRONMENT)
    # Advance to S02.
    eng.complete_stage(eng.current_stage)
    assert eng.current_stage == StageNumber.S02_INDUSTRIAL_ACTIVITY_DETECTION
    # Trying to go BACK to S01 is rejected.
    with pytest.raises(ValueError):
        eng.start_stage(StageNumber.S01_INDUSTRIAL_ENVIRONMENT)
    # Trying to skip to S05 is rejected.
    with pytest.raises(ValueError):
        eng.start_stage(StageNumber.S05_ROOT_CAUSE)


def test_discovery_order_cannot_be_abbreviated() -> None:
    """ORCH-SEQ-003: the only valid forward transition is current -> next."""
    # Walk the entire order to confirm there is no shortcut.
    seen: list[StageNumber] = []
    eng = WorkflowEngine()
    eng.initiate()
    seen.append(eng.current_stage)
    for _ in range(23):
        nxt = eng.complete_stage(eng.current_stage)
        if nxt is None:
            break
        seen.append(nxt)
    assert seen == list(DISCOVERY_ORDER)
    assert assert_total_stages() == 24


# ---------------------------------------------------------------------------
# Human Approval Gate cannot be bypassed by any signal
# ---------------------------------------------------------------------------


def test_human_approval_gate_bypass_by_silence_rejected() -> None:
    eng = ApprovalEngine()
    pkg = _make_class4_package()
    req = eng.create_request(package=pkg, request_date="2026-01-01", response_window=timedelta(days=7))
    with pytest.raises(SilenceNotApproval) as exc:
        eng.check_silence_not_approval(
            request_canonical_id=req.canonical_id,
            bypass_signal="SILENCE", detail="no response within 7 days"
        )
    assert exc.value.reason_code == "SILENCE"


def test_human_approval_gate_bypass_by_urgency_rejected() -> None:
    eng = ApprovalEngine()
    pkg = _make_class4_package()
    req = eng.create_request(package=pkg, request_date="2026-01-01", response_window=timedelta(days=7))
    with pytest.raises(SilenceNotApproval) as exc:
        eng.check_silence_not_approval(
            request_canonical_id=req.canonical_id,
            bypass_signal="URGENCY", detail="customer needs it today"
        )
    assert exc.value.reason_code == "URGENCY"


def test_human_approval_gate_bypass_by_prior_behaviour_rejected() -> None:
    eng = ApprovalEngine()
    pkg = _make_class4_package()
    req = eng.create_request(package=pkg, request_date="2026-01-01", response_window=timedelta(days=7))
    with pytest.raises(SilenceNotApproval) as exc:
        eng.check_silence_not_approval(
            request_canonical_id=req.canonical_id,
            bypass_signal="PRIOR_BEHAVIOUR", detail="same approver said yes last month"
        )
    assert exc.value.reason_code == "PRIOR_BEHAVIOUR"


def test_human_approval_gate_bypass_by_ai_recommendation_rejected() -> None:
    eng = ApprovalEngine()
    pkg = _make_class4_package()
    req = eng.create_request(package=pkg, request_date="2026-01-01", response_window=timedelta(days=7))
    with pytest.raises(SilenceNotApproval) as exc:
        eng.check_silence_not_approval(
            request_canonical_id=req.canonical_id,
            bypass_signal="AI_RECOMMENDATION",
            detail="the Commercial Agent recommends approval"
        )
    assert exc.value.reason_code == "AI_RECOMMENDATION"


def test_human_approval_gate_direct_bypass_rejected() -> None:
    """The Gate Engine rejects a direct bypass attempt on the Human Approval Gate."""
    ge = GateEngine()
    with pytest.raises(GateBypassError) as exc:
        ge.bypass_attempt(GateName.HUMAN_APPROVAL, {"fake_approval": True})
    assert exc.value.gate == GateName.HUMAN_APPROVAL
    assert "Silence, urgency, prior behaviour" in is_bypass_attempt(GateName.HUMAN_APPROVAL)


# ---------------------------------------------------------------------------
# Producer != Verifier enforced
# ---------------------------------------------------------------------------


def test_producer_equals_verifier_rejected_with_each_role() -> None:
    """For every one of the 5 verifier roles, producer == verifier is REJECTED."""
    tracker = IndependenceTracker()
    producer = ProducerRef(producer_id="self", role_code="ANALYST")
    for role in VerifierRole:
        verifier = VerifierRef(verifier_id="self", role=role, role_code="VERIFIER")
        kwargs = dict(
            canonical_id=f"v-{role.value}", material_claim_id="c1",
            producer=producer, verifier=verifier,
            claim_classification=ClaimClassification.FACT,
            outcome=VerificationOutcome.VALIDATED, reason="r",
            source_citations=("s1",), created_at="2026-01-01",
        )
        if role == VerifierRole.INDEPENDENT_FINAL_VERIFIER:
            kwargs["second_reviewer_id"] = "sr-1"
        with pytest.raises(IndependenceViolation):
            tracker.create_record(**kwargs)
    # All 5 rejections recorded.
    assert len(tracker.rejections) == 5


# ---------------------------------------------------------------------------
# Escalation Engine — 6 channels, unacknowledged promotion
# ---------------------------------------------------------------------------


def test_escalation_six_channels() -> None:
    """The 6 Escalation Channels of Interaction Matrix Section 7 are implemented."""
    assert len(EscalationChannel) == 6
    assert EscalationChannel.NORMAL in EscalationChannel
    assert EscalationChannel.CONSTITUTIONAL in EscalationChannel
    assert EscalationChannel.COMMERCIAL in EscalationChannel
    assert EscalationChannel.VERIFICATION in EscalationChannel
    assert EscalationChannel.HUMAN in EscalationChannel
    assert EscalationChannel.EMERGENCY in EscalationChannel


def test_escalation_unacknowledged_promotes() -> None:
    """An unacknowledged escalation is PROMOTED to a higher-priority channel."""
    ee = EscalationEngine()
    esc = ee.raise_escalation(
        channel=EscalationChannel.NORMAL, trigger="approver unavailable",
        route="via inbox", recipient="rhfo-1",
        response_window=timedelta(seconds=0),  # immediately expired
        raised_at="2026-01-01T00:00:00+00:00",
    )
    now = datetime(2026, 1, 1, 0, 1, 0, tzinfo=timezone.utc)
    promoted = ee.promote_unacknowledged(now=now)
    assert len(promoted) == 1
    assert promoted[0].channel == EscalationChannel.COMMERCIAL
    assert promoted[0].promoted_from == [esc.canonical_id]


# ---------------------------------------------------------------------------
# Handoff Service — initiation, acceptance, audit
# ---------------------------------------------------------------------------


def test_handoff_initiation_acceptance_audit() -> None:
    """A handoff is initiated, accepted with valid criteria, and audited."""
    hs = HandoffService()
    h = hs.initiate(
        material_canonical_id="m1", relinquishing_office="Industrial",
        receiving_office="Opportunity", initiated_by="agent-1",
        acceptance_criteria=("material_present", "verified"),
    )
    assert h.status.value == "INITIATED"
    accepted = hs.accept(
        handoff_canonical_id=h.canonical_id, accepted_by="agent-2",
        facts={"material_present": True, "verified": True}
    )
    assert accepted.status.value == "ACCEPTED"
    # Audit log has INITIATED + ACCEPTED.
    audit = hs.audit_log(h.canonical_id)
    assert [a["event"] for a in audit] == ["INITIATED", "ACCEPTED"]


def test_handoff_rejected_when_criteria_missing() -> None:
    """A handoff that fails acceptance is REJECTED."""
    hs = HandoffService()
    h = hs.initiate(
        material_canonical_id="m1", relinquishing_office="Industrial",
        receiving_office="Opportunity", initiated_by="agent-1",
        acceptance_criteria=("material_present", "verified"),
    )
    with pytest.raises(HandoffRejected):
        hs.accept(
            handoff_canonical_id=h.canonical_id, accepted_by="agent-2",
            facts={"material_present": True}  # 'verified' missing
        )
    # Handoff is now in REJECTED state.
    assert hs.handoffs[h.canonical_id].status.value == "REJECTED"


# ---------------------------------------------------------------------------
# Exception Engine — 9 scenarios
# ---------------------------------------------------------------------------


def test_exception_engine_nine_scenarios() -> None:
    """All 9 Exception Scenarios of Document 06 §7 are registered."""
    scenarios = all_scenarios()
    assert len(scenarios) == 9
    # Every scenario has a spec with action and record requirement.
    from techno_service_ai.exceptions import EXCEPTION_SPECS
    for s in scenarios:
        spec = EXCEPTION_SPECS[s]
        assert spec.action
        assert spec.record_requirement
    # The engine handles a scenario.
    ee = ExceptionEngine()
    rec = ee.handle(
        ExceptionScenario.MISSING_EVIDENCE, material_canonical_id="m1",
        reason="test", triggered_by="agent-1"
    )
    assert rec["scenario"] == "MISSING_EVIDENCE"


# ---------------------------------------------------------------------------
# Recovery Engine — interrupted, restart, resume, rollback
# ---------------------------------------------------------------------------


def test_recovery_rollback_requires_approval() -> None:
    """REC-ROLL-001: a rollback requires documented Human Approval."""
    re = RecoveryEngine()
    with pytest.raises(RollbackRequiresApproval):
        re.rollback(
            workflow_canonical_id="wf-1", rollback_to_stage="S05",
            description="undo", continuity_plan_reference="CP-1",
            responsible_authority="exec-1", preserved_state="stage 5",
        )


def test_recovery_resume_class_3_or_4_requires_approval() -> None:
    """REC-RESUME-003: a resume that affects Class 3/4 requires Human Approval."""
    re = RecoveryEngine()
    with pytest.raises(Class3Or4ResumeRequiresApproval):
        re.resume(
            workflow_canonical_id="wf-1", restart_at_stage="S05",
            description="resume", continuity_plan_reference="CP-1",
            responsible_authority="exec-1", preserved_state="stage 5",
            affects_class_3_or_4=True, decision_class="CLASS_4",
            human_approval_recorded=False,
        )


def test_recovery_rollback_with_approval_accepted() -> None:
    """A rollback with Human Approval is accepted and recorded."""
    re = RecoveryEngine()
    r = re.rollback(
        workflow_canonical_id="wf-1", rollback_to_stage="S05",
        description="undo", continuity_plan_reference="CP-1",
        responsible_authority="exec-1", preserved_state="stage 5",
        human_approval_recorded=True,
    )
    assert r.rollback_to_stage == "S05"


# ---------------------------------------------------------------------------
# AC-P3-008 — Human Approval Gate cannot be bypassed (consolidated)
# ---------------------------------------------------------------------------


def test_ac_p3_008_human_approval_gate_not_bypassable() -> None:
    """The Human Approval Gate cannot be bypassed by ANY means:
    silence, urgency, prior behaviour, similar historical approval,
    AI recommendation, or a direct bypass."""
    # Direct gate bypass.
    ge = GateEngine()
    with pytest.raises(GateBypassError):
        ge.bypass_attempt(GateName.HUMAN_APPROVAL, {})
    # 5 substitute signals via the Approval Engine.
    eng = ApprovalEngine()
    pkg = _make_class4_package()
    req = eng.create_request(package=pkg, request_date="2026-01-01", response_window=timedelta(days=7))
    for signal in ["SILENCE", "URGENCY", "PRIOR_BEHAVIOUR", "SIMILAR_HISTORICAL_APPROVAL", "AI_RECOMMENDATION"]:
        with pytest.raises(SilenceNotApproval):
            eng.check_silence_not_approval(
                request_canonical_id=req.canonical_id, bypass_signal=signal, detail="x"
            )
    # All 5 recorded on the engine.
    assert len(eng.bypass_rejections) == 5
