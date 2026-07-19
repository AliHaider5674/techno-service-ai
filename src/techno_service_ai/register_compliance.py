"""Register Compliance Engine — Constitution Article VIII.

Implements the Register Compliance Gate. This gate is invoked at the
entry of every commercial action (Commercial Gate, Registration Gate,
Tender Gate, Project Gate) — i.e. at the entry of Stages 16, 17, 18,
19, 20 of the Discovery Order. Per Document 06 §4.5 GATE-CO-002 exit
conditions: "The register check is clear."

Three constitutional rules are enforced:

  1. RESTRICTED — a Restricted/Prohibited Entity is REJECTED everywhere.
     (Constitution Article VIII §4, Document 06 §4.5 GATE-CO-002.)
  2. CONFLICT — a Conflict / Do-Not-Pursue Entity is REJECTED everywhere.
     (Constitution Article VIII §3.)
  3. NON_REPRESENTED_PRINCIPAL — a non-Represented Principal is
     REJECTED at the Commercial Gate (Stages 16-20). (Constitution
     Article VIII §2; Document 02 §4.5.1 — Manufacturer Profiler
     "may not declare representation status alone".)

The engine is PURE LOGIC. It does not touch the database. The
Service Layer wires the engine to the three register tables
(Constitution Article VIII §1 — independent tables per DB-PRIN-013).

Constitutional source:
  - Constitution Article VIII (the three Registers)
  - Document 02 §4.5, 4.6, 4.7 (Manufacturer, Commercial, Registration)
  - Document 06 §4.5 GATE-CO-002 (Commercial Gate exit conditions)
  - Document 06 §4.6 GATE-RG-002 (Registration Gate)
  - DB-PRIN-013 — Independence of the three Registers
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Iterable, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class RegisterCheckOutcome(str, Enum):
    """The outcome of a Register Compliance check."""

    CLEARED = "CLEARED"
    REJECTED_RESTRICTED = "REJECTED_RESTRICTED"
    REJECTED_CONFLICT = "REJECTED_CONFLICT"
    REJECTED_NOT_REPRESENTED = "REJECTED_NOT_REPRESENTED"


class GateKind(str, Enum):
    """The kind of gate at which the register check is invoked."""

    COMMERCIAL = "COMMERCIAL"          # Stages 16, 17, 18, 19, 20
    REGISTRATION = "REGISTRATION"      # Stage 17, Prequalification, AVL
    TENDER = "TENDER"                  # Stage 19
    PROJECT = "PROJECT"                # Stage 20


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class RegisterComplianceError(Exception):
    """Base for register compliance rejections."""


class RestrictedEntityError(RegisterComplianceError):
    """A Restricted / Prohibited Entity was used anywhere — REJECTED.

    Per Constitution Article VIII §4: a Restricted/Prohibited entity
    shall not be the subject of any commercial action. This is the
    strongest of the three register rejections — it applies at EVERY
    gate, not just the Commercial Gate.
    """

    def __init__(self, entity_id: str, entity_name: str) -> None:
        self.entity_id = entity_id
        self.entity_name = entity_name
        super().__init__(
            f"Restricted/Prohibited Entity REJECTED: '{entity_name}' (id={entity_id}). "
            f"Per Constitution Article VIII §4 and Document 06 §4.5 GATE-CO-002, "
            f"a Restricted entity shall not be the subject of any commercial action. "
            f"Engagement is constitutionally PROHIBITED."
        )


class ConflictEntityError(RegisterComplianceError):
    """A Conflict / Do-Not-Pursue Entity was used — REJECTED.

    Per Constitution Article VIII §3: a Conflict / Do-Not-Pursue
    entity shall not be the subject of commercial action. This is
    also a hard rejection — it applies at every gate.
    """

    def __init__(self, entity_id: str, entity_name: str) -> None:
        self.entity_id = entity_id
        self.entity_name = entity_name
        super().__init__(
            f"Conflict/Do-Not-Pursue Entity REJECTED: '{entity_name}' (id={entity_id}). "
            f"Per Constitution Article VIII §3, a Conflict entity shall not be the "
            f"subject of any commercial action. Engagement is constitutionally PROHIBITED."
        )


class NotRepresentedPrincipalError(RegisterComplianceError):
    """A non-Represented Principal was presented at the Commercial Gate — REJECTED.

    Per Constitution Article VIII §2: only a Represented Principal may
    be the subject of commercial action. A non-Represented Principal
    is REJECTED at the Commercial Gate (Stages 16-20). At other
    gates (Evidence, Verification, Quality, Human Approval,
    Closure) the rule does not apply — a non-Represented Principal
    may still be subject of intelligence and verification work.
    """

    def __init__(self, entity_id: str, entity_name: str) -> None:
        self.entity_id = entity_id
        self.entity_name = entity_name
        super().__init__(
            f"Non-Represented Principal REJECTED at Commercial Gate: '{entity_name}' "
            f"(id={entity_id}). Per Constitution Article VIII §2, only a Represented "
            f"Principal may be the subject of commercial action. A non-Represented "
            f"Principal may be subject of intelligence and verification but NOT of "
            f"Business Development (S16), Registration (S17), Market Entry (S18), "
            f"Tender (S19), or Project (S20)."
        )


# ---------------------------------------------------------------------------
# Inputs (the engine is pure logic; the Service Layer supplies these)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RegisterEntry:
    """A snapshot of a register entry (or absence of one).

    The engine does not query the database; the Service Layer translates
    register rows into RegisterEntry values. This keeps the engine pure
    and testable.
    """

    entity_id: Optional[str]  # The entity's id (None = entry by name only)
    entity_name: str
    register_kind: str  # 'REPRESENTED_PRINCIPAL', 'CONFLICT', 'RESTRICTED'
    status: str  # 'ACTIVE' / 'SUPERSEDED' / 'REJECTED'
    effective_to: Optional[str]  # None = open-ended
    reason: str = ""


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RegisterCheckResult:
    """The result of a Register Compliance check.

    `outcome` is the verdict. `rejection_reason` is the human-readable
    explanation when outcome is REJECTED_*. `checked_at_gate` records
    which gate the check was run at (Commercial / Registration / Tender
    / Project). `evaluated_at` is the timestamp.
    """

    outcome: RegisterCheckOutcome
    entity_id: str
    entity_name: str
    checked_at_gate: GateKind
    evaluated_at: str
    rejection_reason: str = ""
    is_cleared: bool = field(default=False)

    def __post_init__(self) -> None:
        # The cleared flag is derived from outcome.
        if self.outcome == RegisterCheckOutcome.CLEARED and not self.is_cleared:
            object.__setattr__(self, "is_cleared", True)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class RegisterComplianceEngine:
    """The Register Compliance Engine — Constitution Article VIII.

    The engine takes:

      - The entity (id + name) being presented.
      - The list of register entries that match the entity (across the
        three registers: Represented Principals, Conflict, Restricted).
      - The gate at which the check is being run (Commercial, Registration,
        Tender, Project).

    It returns a RegisterCheckResult. The Service Layer raises the
    appropriate typed exception when the outcome is REJECTED_*.

    The engine is a pure function of its inputs. It is idempotent and
    does NOT mutate the registers.
    """

    def check(
        self,
        *,
        entity_id: str,
        entity_name: str,
        register_entries: Iterable[RegisterEntry],
        gate: GateKind,
        now: Optional[str] = None,
    ) -> RegisterCheckResult:
        """Run the register check.

        The check is composed of three sub-checks, in order:

          1. RESTRICTED — if any active entry in the Restricted register
             matches this entity, REJECTED_RESTRICTED. This rule is
             universal — it applies at every gate.

          2. CONFLICT — if any active entry in the Conflict register
             matches this entity, REJECTED_CONFLICT. This rule is also
             universal — it applies at every gate.

          3. NON_REPRESENTED — if the entity has no ACTIVE entry in
             the Represented Principals register AND the gate is a
             commercial gate (COMMERCIAL, REGISTRATION, TENDER, PROJECT),
             REJECTED_NOT_REPRESENTED. At other gates, the rule does
             not apply.
        """
        evaluated_at = now or datetime.now(timezone.utc).isoformat()
        entries = list(register_entries)

        # 1. RESTRICTED
        for e in entries:
            if (
                e.register_kind == "RESTRICTED"
                and e.status == "ACTIVE"
                and self._matches(e, entity_id, entity_name)
                and self._is_currently_effective(e, evaluated_at)
            ):
                return RegisterCheckResult(
                    outcome=RegisterCheckOutcome.REJECTED_RESTRICTED,
                    entity_id=entity_id,
                    entity_name=entity_name,
                    checked_at_gate=gate,
                    evaluated_at=evaluated_at,
                    rejection_reason=(
                        f"Entity is on the Restricted/Prohibited register "
                        f"(reason: {e.reason or 'unspecified'})."
                    ),
                )

        # 2. CONFLICT
        for e in entries:
            if (
                e.register_kind == "CONFLICT"
                and e.status == "ACTIVE"
                and self._matches(e, entity_id, entity_name)
                and self._is_currently_effective(e, evaluated_at)
            ):
                return RegisterCheckResult(
                    outcome=RegisterCheckOutcome.REJECTED_CONFLICT,
                    entity_id=entity_id,
                    entity_name=entity_name,
                    checked_at_gate=gate,
                    evaluated_at=evaluated_at,
                    rejection_reason=(
                        f"Entity is on the Conflict/Do-Not-Pursue register "
                        f"(reason: {e.reason or 'unspecified'})."
                    ),
                )

        # 3. NON_REPRESENTED_PRINCIPAL (only at commercial gates)
        if gate in (GateKind.COMMERCIAL, GateKind.REGISTRATION, GateKind.TENDER, GateKind.PROJECT):
            has_active_representation = any(
                e.register_kind == "REPRESENTED_PRINCIPAL"
                and e.status == "ACTIVE"
                and self._matches(e, entity_id, entity_name)
                and self._is_currently_effective(e, evaluated_at)
                for e in entries
            )
            if not has_active_representation:
                return RegisterCheckResult(
                    outcome=RegisterCheckOutcome.REJECTED_NOT_REPRESENTED,
                    entity_id=entity_id,
                    entity_name=entity_name,
                    checked_at_gate=gate,
                    evaluated_at=evaluated_at,
                    rejection_reason=(
                        "Entity is not on the Represented Principals register. "
                        "Per Article VIII §2, only a Represented Principal may be the subject "
                        "of commercial action."
                    ),
                )

        return RegisterCheckResult(
            outcome=RegisterCheckOutcome.CLEARED,
            entity_id=entity_id,
            entity_name=entity_name,
            checked_at_gate=gate,
            evaluated_at=evaluated_at,
        )

    # -----------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------

    @staticmethod
    def _matches(entry: RegisterEntry, entity_id: str, entity_name: str) -> bool:
        """An entry matches if either the id matches or the name matches.

        The Service Layer may pass register entries with entity_id=None
        (name-only entries). In that case, we match by name only.
        """
        if entry.entity_id is not None and entry.entity_id != "":
            return entry.entity_id == entity_id
        return entry.entity_name == entity_name

    @staticmethod
    def _is_currently_effective(entry: RegisterEntry, evaluated_at: str) -> bool:
        """Return True if the entry is effective at `evaluated_at`."""
        # We treat the effective_to as an ISO date string (YYYY-MM-DD) or
        # None for open-ended. If effective_to is set, the entry expires
        # at end-of-day on that date.
        to = entry.effective_to
        if to is None or to == "":
            return True
        # Compare prefix (YYYY-MM-DD) — evaluated_at is ISO with time.
        return evaluated_at[:10] <= to[:10]


# ---------------------------------------------------------------------------
# Convenience: raise the right exception for a result
# ---------------------------------------------------------------------------


def raise_for_rejection(result: RegisterCheckResult) -> None:
    """Raise the typed exception for a REJECTED_* result.

    No-op when the result is CLEARED.
    """
    if result.outcome == RegisterCheckOutcome.CLEARED:
        return
    if result.outcome == RegisterCheckOutcome.REJECTED_RESTRICTED:
        raise RestrictedEntityError(result.entity_id, result.entity_name)
    if result.outcome == RegisterCheckOutcome.REJECTED_CONFLICT:
        raise ConflictEntityError(result.entity_id, result.entity_name)
    if result.outcome == RegisterCheckOutcome.REJECTED_NOT_REPRESENTED:
        raise NotRepresentedPrincipalError(result.entity_id, result.entity_name)
    raise RegisterComplianceError(f"Unknown outcome: {result.outcome}")
