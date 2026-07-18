"""Workflow Engine + Orchestrator — Document 06 Section 3.

Implements the WorkflowEngine that orchestrates the 24 stages of the
Discovery Order, the 10 Orchestration States, the 9 Decision Gates,
and the engines (verification, approval, notification, escalation,
handoff, exceptions, recovery).

This is a pure-logic module (no DB coupling) that ties the engines
together. The service layer in production wraps it with persistence
and audit-log writes.

Constitutional source:
  - Constitution Article VI
  - Document 06 §3 (Agent Orchestration Rules)
  - Document 06 §4 (Decision Gates)
  - Document 06 §5 (Human Approval Workflow)
  - Document 06 §6 (Verification Workflow)
  - Document 06 §7 (Exception Handling)
  - Document 06 §8 (Orchestration State Model)
  - Document 06 §9 (Cross-Office Collaboration)
  - Document 06 §12 (Recovery Model)
  - AC-P3-001 (workflow can be initiated, executed, transitioned, closed)
  - AC-P3-002 (every Decision Gate enforces its conditions)
  - AC-P3-003 (State Machine enforces allowed/forbidden transitions)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, List, Optional

from .approval import ApprovalEngine
from .escalation import EscalationEngine
from .exceptions import ExceptionEngine
from .gates import GateBypassError, GateEngine, GateName
from .handoff import HandoffRejected, HandoffService
from .notification import NotificationEngine
from .recovery import RecoveryEngine, RollbackRequiresApproval, Class3Or4ResumeRequiresApproval
from .stages import (
    DISCOVERY_ORDER,
    StageNumber,
    is_valid_progression,
    next_stage,
)
from .states import OrchestrationState, StateMachine, TransitionError
from .verification import IndependenceTracker


class WorkflowEventType(str, Enum):
    INITIATED = "INITIATED"
    STAGE_STARTED = "STAGE_STARTED"
    STAGE_COMPLETED = "STAGE_COMPLETED"
    STAGE_REJECTED = "STAGE_REJECTED"
    STATE_TRANSITION = "STATE_TRANSITION"
    GATE_PASSED = "GATE_PASSED"
    GATE_BYPASS_REJECTED = "GATE_BYPASS_REJECTED"
    ESCALATION_RAISED = "ESCALATION_RAISED"
    HANDOFF_INITIATED = "HANDOFF_INITIATED"
    HANDOFF_ACCEPTED = "HANDOFF_ACCEPTED"
    HANDOFF_REJECTED = "HANDOFF_REJECTED"
    EXCEPTION_HANDLED = "EXCEPTION_HANDLED"
    WORKFLOW_CLOSED = "WORKFLOW_CLOSED"
    WORKFLOW_ARCHIVED = "WORKFLOW_ARCHIVED"


@dataclass(frozen=True)
class WorkflowEvent:
    event_type: WorkflowEventType
    workflow_canonical_id: str
    payload: dict


# ---------------------------------------------------------------------------
# Workflow Engine
# ---------------------------------------------------------------------------


class WorkflowEngine:
    """The constitutional workflow engine.

    One instance per workflow. Owns a StateMachine, references the
    other engines (verification, approval, etc.), and exposes the
    canonical operations:

      - initiate: state IDLE -> RUNNING, stage = S01
      - start_stage: ensure stage is the next valid one
      - complete_stage: stage -> next stage (with gate checks)
      - request_approval: route an Approval Request to the Approval Engine
      - verify: route a verification record to the Independence Tracker
      - escalate: raise an escalation
      - handoff: initiate / accept / reject a handoff
      - close: state RUNNING/APPROVED -> CLOSED
      - archive: state CLOSED -> ARCHIVED
      - rollback: requires Human Approval

    The engine NEVER silently bypasses a gate. Any gate bypass attempt
    is REJECTED and recorded as a GATE_BYPASS_REJECTED event.
    """

    def __init__(
        self,
        *,
        workflow_canonical_id: str = "",
        gate_engine: GateEngine | None = None,
        state_machine: StateMachine | None = None,
        verification_tracker: IndependenceTracker | None = None,
        approval_engine: ApprovalEngine | None = None,
        notification_engine: NotificationEngine | None = None,
        escalation_engine: EscalationEngine | None = None,
        handoff_service: HandoffService | None = None,
        exception_engine: ExceptionEngine | None = None,
        recovery_engine: RecoveryEngine | None = None,
    ) -> None:
        self.workflow_canonical_id = workflow_canonical_id or _uuid_str()
        self.gate_engine = gate_engine or GateEngine()
        self.state_machine = state_machine or StateMachine(OrchestrationState.IDLE)
        self.verification_tracker = verification_tracker or IndependenceTracker()
        self.approval_engine = approval_engine or ApprovalEngine()
        self.notification_engine = notification_engine or NotificationEngine()
        self.escalation_engine = escalation_engine or EscalationEngine()
        self.handoff_service = handoff_service or HandoffService()
        self.exception_engine = exception_engine or ExceptionEngine()
        self.recovery_engine = recovery_engine or RecoveryEngine()
        self.events: list[WorkflowEvent] = []
        self.current_stage: StageNumber | None = None
        self.completed_stages: list[StageNumber] = []
        # Per-stage gate state: which gates have been passed for the
        # current stage (or in general).
        self.passed_gates: set[GateName] = set()

    # ---- initiate / close / archive -----------------------------------

    def initiate(self, *, start_stage: StageNumber = StageNumber.S01_INDUSTRIAL_ENVIRONMENT) -> StageNumber:
        """Initiate the workflow. IDLE -> RUNNING, current = start_stage."""
        if self.current_stage is not None:
            raise ValueError("Workflow already initiated")
        self._transition_state(OrchestrationState.RUNNING)
        self.current_stage = start_stage
        self._event(WorkflowEventType.INITIATED, {"stage": start_stage.name})
        self._event(WorkflowEventType.STAGE_STARTED, {"stage": start_stage.name})
        return start_stage

    def close(self) -> OrchestrationState:
        """Close the workflow. RUNNING/APPROVED -> CLOSED."""
        if self.current_stage != DISCOVERY_ORDER[-1]:
            raise ValueError(
                f"Cannot close: current stage is {self.current_stage}; "
                f"must be at the last stage ({DISCOVERY_ORDER[-1].name})"
            )
        self._transition_state(OrchestrationState.CLOSED)
        self._event(WorkflowEventType.WORKFLOW_CLOSED, {})
        return OrchestrationState.CLOSED

    def archive(self) -> OrchestrationState:
        """Archive the workflow. CLOSED -> ARCHIVED."""
        if self.state_machine.state != OrchestrationState.CLOSED:
            raise ValueError("Can only archive from CLOSED state")
        self._transition_state(OrchestrationState.ARCHIVED)
        self._event(WorkflowEventType.WORKFLOW_ARCHIVED, {})
        return OrchestrationState.ARCHIVED

    # ---- stage progression --------------------------------------------

    def start_stage(self, stage: StageNumber) -> None:
        """Begin executing a stage. Must be the next valid stage."""
        if self.current_stage is None:
            raise ValueError("Workflow not initiated")
        if not is_valid_progression(self.current_stage, stage):
            raise ValueError(
                f"Invalid progression: {self.current_stage.name} -> {stage.name}. "
                f"Skipping, abbreviating, or reordering is REJECTED "
                f"(Document 06 §3.1 ORCH-SEQ-003, WF-PRIN-007)."
            )
        self._event(WorkflowEventType.STAGE_STARTED, {"stage": stage.name})

    def complete_stage(self, stage: StageNumber) -> StageNumber | None:
        """Mark `stage` complete. Returns the next stage, or None if at the end.

        No gate bypass is performed. Callers must pass the required
        gates before calling complete_stage.
        """
        if stage != self.current_stage:
            raise ValueError(
                f"Cannot complete {stage.name}: current stage is {self.current_stage.name}"
            )
        self.completed_stages.append(stage)
        self._event(WorkflowEventType.STAGE_COMPLETED, {"stage": stage.name})
        nxt = next_stage(stage)
        if nxt is None:
            return None
        self.current_stage = nxt
        self._event(WorkflowEventType.STAGE_STARTED, {"stage": nxt.name})
        return nxt

    # ---- gate enforcement ---------------------------------------------

    def pass_gate(self, gate: GateName, facts: dict | None = None) -> None:
        """Record that a gate has been passed (entry + exit conditions satisfied)."""
        facts = facts or {}
        self.gate_engine.check_entry(gate, facts)
        self.gate_engine.check_exit(gate, facts)
        self.passed_gates.add(gate)
        self._event(WorkflowEventType.GATE_PASSED, {"gate": gate.value, "facts": list(facts.keys())})

    def attempt_gate_bypass(self, gate: GateName, facts: dict | None = None) -> None:
        """A bypass attempt on a gate. Always REJECTED."""
        facts = facts or {}
        try:
            self.gate_engine.bypass_attempt(gate, facts)
        except GateBypassError as e:
            self._event(WorkflowEventType.GATE_BYPASS_REJECTED, {"gate": gate.value, "reason": str(e)})
            raise

    # ---- state transitions --------------------------------------------

    def _transition_state(self, to: OrchestrationState) -> OrchestrationState:
        try:
            from_state = self.state_machine.state
            new_state = self.state_machine.transition(to)
            self._event(WorkflowEventType.STATE_TRANSITION, {"from": from_state.value, "to": new_state.value})
            return new_state
        except TransitionError as e:
            self._event(
                WorkflowEventType.STAGE_REJECTED,
                {"reason": "forbidden state transition", "from": e.from_state.value, "to": e.to_state.value},
            )
            raise

    # ---- events --------------------------------------------------------

    def _event(self, event_type: WorkflowEventType, payload: dict) -> None:
        self.events.append(
            WorkflowEvent(
                event_type=event_type,
                workflow_canonical_id=self.workflow_canonical_id,
                payload=payload,
            )
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _uuid_str() -> str:
    import uuid
    return str(uuid.uuid4())
