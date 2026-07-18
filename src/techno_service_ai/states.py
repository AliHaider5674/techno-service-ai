"""Orchestration State Machine — Document 06 Section 8.

Defines the 10 Orchestration States and the allowed / forbidden
transitions between them. This is a pure-logic module with NO database
or HTTP coupling. The state machine is consulted by the Workflow
Engine, the Recovery Orchestrator, and the Audit Service.

Constitutional source:
  - Constitution Articles XVIII, XIX, XX
  - Document 06 §8 (Orchestration State Model)
  - STATE-G-001..004 (State Transition Guarantees)
  - AC-P3-003 (Orchestration State Machine enforces allowed/forbidden transitions)
"""
from __future__ import annotations

from enum import Enum
from typing import FrozenSet, Mapping


class OrchestrationState(str, Enum):
    """The 10 Orchestration States of Document 06 §8.1.

    The order of declaration is the canonical taxonomy order; it has no
    semantic meaning for transitions.
    """

    IDLE = "IDLE"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    SUSPENDED = "SUSPENDED"
    REWORK = "REWORK"
    ESCALATED = "ESCALATED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CLOSED = "CLOSED"
    ARCHIVED = "ARCHIVED"


# ---------------------------------------------------------------------------
# Allowed transitions (Document 06 §8.1, per state)
# ---------------------------------------------------------------------------

ALLOWED_TRANSITIONS: Mapping[OrchestrationState, FrozenSet[OrchestrationState]] = {
    OrchestrationState.IDLE: frozenset({
        OrchestrationState.RUNNING,
        OrchestrationState.ARCHIVED,
    }),
    OrchestrationState.RUNNING: frozenset({
        OrchestrationState.WAITING,
        OrchestrationState.SUSPENDED,
        OrchestrationState.REWORK,
        OrchestrationState.ESCALATED,
        OrchestrationState.APPROVED,
        OrchestrationState.REJECTED,
        OrchestrationState.CLOSED,
    }),
    OrchestrationState.WAITING: frozenset({
        OrchestrationState.RUNNING,
        OrchestrationState.ESCALATED,
        OrchestrationState.REJECTED,
    }),
    OrchestrationState.SUSPENDED: frozenset({
        OrchestrationState.RUNNING,
        OrchestrationState.ESCALATED,
        OrchestrationState.CLOSED,
    }),
    OrchestrationState.REWORK: frozenset({
        OrchestrationState.RUNNING,
        OrchestrationState.ESCALATED,
    }),
    OrchestrationState.ESCALATED: frozenset({
        OrchestrationState.RUNNING,
        OrchestrationState.APPROVED,
        OrchestrationState.REJECTED,
        OrchestrationState.CLOSED,
    }),
    OrchestrationState.APPROVED: frozenset({
        OrchestrationState.RUNNING,
        OrchestrationState.CLOSED,
        OrchestrationState.SUSPENDED,
        # Note: REVOKED is not in the Document 06 §8.1 list, but the
        # authority matrix allows revocation; we encode it as
        # APPROVED -> RUNNING (workflow re-runs under new conditions).
    }),
    OrchestrationState.REJECTED: frozenset({
        OrchestrationState.CLOSED,
        OrchestrationState.REWORK,
        OrchestrationState.ESCALATED,
    }),
    OrchestrationState.CLOSED: frozenset({
        OrchestrationState.ARCHIVED,
    }),
    OrchestrationState.ARCHIVED: frozenset(),  # Only reactivation by Major Amendment
}


# ---------------------------------------------------------------------------
# State transition guarantees (Document 06 §8.2)
# ---------------------------------------------------------------------------

class TransitionError(Exception):
    """A forbidden state transition was attempted.

    Per STATE-G-002, forbidden transitions are PREVENTED (not warned).
    Every transition is logged per STATE-G-001.
    """

    def __init__(self, from_state: OrchestrationState, to_state: OrchestrationState) -> None:
        self.from_state = from_state
        self.to_state = to_state
        super().__init__(
            f"Forbidden state transition: {from_state.value} -> {to_state.value}. "
            f"Per Document 06 §8.2 STATE-G-002, forbidden transitions are prevented."
        )


class StateMachine:
    """A pure-logic state machine for the 10 Orchestration States.

    The state machine:
      - Exposes `can_transition(from, to)` for inspection.
      - Exposes `transition(from, to)` which raises TransitionError on
        a forbidden transition.
      - Maintains the in-memory current state of a single workflow
        instance (one state machine per workflow instance).
      - Records every transition in `history` (in-memory) for audit.
    """

    def __init__(self, initial: OrchestrationState = OrchestrationState.IDLE) -> None:
        self._state: OrchestrationState = initial
        self.history: list[tuple[OrchestrationState, OrchestrationState]] = []

    @property
    def state(self) -> OrchestrationState:
        return self._state

    def can_transition(self, to: OrchestrationState) -> bool:
        return to in ALLOWED_TRANSITIONS[self._state]

    def allowed(self) -> FrozenSet[OrchestrationState]:
        return ALLOWED_TRANSITIONS[self._state]

    def transition(self, to: OrchestrationState) -> OrchestrationState:
        """Transition to `to` state. Raises TransitionError on forbidden."""
        if to == self._state:
            return self._state
        if to not in ALLOWED_TRANSITIONS[self._state]:
            raise TransitionError(self._state, to)
        from_state = self._state
        self._state = to
        self.history.append((from_state, to))
        return self._state

    def reset(self, to: OrchestrationState = OrchestrationState.IDLE) -> None:
        """Hard reset (for tests). Does not log a transition."""
        self._state = to
        self.history = []
