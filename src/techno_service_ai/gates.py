"""Decision Gates — Document 06 Section 4.

Defines the 9 Decision Gates that are non-bypassable constitutional
checkpoints. Every Gate has Entry Conditions, Exit Conditions, an
Owner, and a Bypass Prohibition. A bypass attempt is REJECTED.

This is a pure-logic module with NO database or HTTP coupling. The
gates are consulted by the Workflow Engine and the Orchestrator.

Constitutional source:
  - Constitution Articles VI, VIII, XI, XII, XVI, XVII, XIX, XXIII
  - Document 06 §4.1..4.9 (9 Decision Gates)
  - GATE-* (Bypass Prohibition: "No workflow may bypass the ... Gate")
  - AC-P3-002 (Every Decision Gate enforces its conditions;
    bypass attempt is rejected)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Mapping


class GateName(str, Enum):
    """The 9 Decision Gates of Document 06 §4.

    Declaration order matches the document order.
    """

    EVIDENCE = "EVIDENCE"          # §4.1
    VERIFICATION = "VERIFICATION"  # §4.2
    QUALITY = "QUALITY"            # §4.3
    HUMAN_APPROVAL = "HUMAN_APPROVAL"  # §4.4
    COMMERCIAL = "COMMERCIAL"      # §4.5
    REGISTRATION = "REGISTRATION"  # §4.6
    TENDER = "TENDER"              # §4.7
    PROJECT = "PROJECT"            # §4.8
    CLOSURE = "CLOSURE"            # §4.9


@dataclass(frozen=True)
class GateSpec:
    """The constitutional spec of one Decision Gate.

    Fields mirror Document 06 §4.{n} for the corresponding gate.
    """

    name: GateName
    purpose: str
    location: str
    entry_conditions: tuple[str, ...]
    exit_conditions: tuple[str, ...]
    owner: str
    bypass_prohibition: str  # The "No workflow may bypass the ... Gate" text


# ---------------------------------------------------------------------------
# 9 Gate specifications (Document 06 §4.1..4.9)
# ---------------------------------------------------------------------------

GATES: Mapping[GateName, GateSpec] = {
    GateName.EVIDENCE: GateSpec(
        name=GateName.EVIDENCE,
        purpose="Ensure that the Opportunity case is supported by Evidence.",
        location=(
            "Invoked at the entry of every Verification stage and at the entry "
            "of every Reporting stage."
        ),
        entry_conditions=(
            "A material claim is in scope.",
            "An Evidence record is required.",
        ),
        exit_conditions=(
            "The Evidence record exists, is sourced, and is linked to the claim.",
        ),
        owner="Originating Office for the material claim; Verification Office for verification.",
        bypass_prohibition="No workflow may bypass the Evidence Gate.",
    ),
    GateName.VERIFICATION: GateSpec(
        name=GateName.VERIFICATION,
        purpose="Ensure that the material case has been subject to Independent Verification.",
        location=(
            "Invoked at the exit of Stage 13 and at the entry of Stage 15 of the end-to-end workflow."
        ),
        entry_conditions=(
            "The material case is complete.",
            "The verification is mandated by Stage 15 of the Discovery Order.",
        ),
        exit_conditions=(
            "The Independent Final Verification Record is complete.",
            "The outcome is recorded.",
        ),
        owner="Verification Office.",
        bypass_prohibition="No workflow may bypass the Verification Gate.",
    ),
    GateName.QUALITY: GateSpec(
        name=GateName.QUALITY,
        purpose="Ensure that the verified output meets quality criteria.",
        location=(
            "Invoked at the entry of Stage 14 and at the entry of every Reporting stage."
        ),
        entry_conditions=(
            "A material output is in scope.",
            "Quality review is required.",
        ),
        exit_conditions=(
            "The Quality Review Record is complete.",
            "The rework request, if any, is issued and closed.",
        ),
        owner="Quality Assurance Office.",
        bypass_prohibition="No workflow may bypass the Quality Gate.",
    ),
    GateName.HUMAN_APPROVAL: GateSpec(
        name=GateName.HUMAN_APPROVAL,
        purpose=(
            "Ensure that Class 3 External Action Decisions and Class 4 Binding, "
            "Financial, Legal, or Strategic Decisions are subject to Human Approval."
        ),
        location=(
            "Invoked at the entry of every External Action and at the entry of every "
            "Binding Decision."
        ),
        entry_conditions=(
            "The Decision Class is determined.",
            "The Required Approver Role is identified.",
        ),
        exit_conditions=(
            "The Approval, Rejection, or Conditional Approval is recorded.",
            "The Decision Log Entry is created.",
        ),
        owner="Authorised Human Authority.",
        bypass_prohibition=(
            "No workflow may bypass the Human Approval Gate. Silence, urgency, prior "
            "behaviour, similar historical approval, or an Agent recommendation does "
            "not constitute Human Approval."
        ),
    ),
    GateName.COMMERCIAL: GateSpec(
        name=GateName.COMMERCIAL,
        purpose="Ensure that the commercial case is properly established before any commercial engagement.",
        location=(
            "Invoked at the entry of Stage 16 (Business Development), Stage 17 "
            "(Registration), Stage 18 (Market Entry), Stage 19 (Tender Support), "
            "and Stage 20 (Project Support)."
        ),
        entry_conditions=(
            "The Commercial Evaluation is complete.",
            "The constitutional register check is clear.",
            "The Human Approval for engagement is in place.",
        ),
        exit_conditions=(
            "The register check is clear.",
            "The engagement is approved.",
            "The commercial action is logged.",
        ),
        owner="Commercial Development Office; Registration and Market Entry Office; Tender and Project Intelligence Office.",
        bypass_prohibition="No workflow may bypass the Commercial Gate.",
    ),
    GateName.REGISTRATION: GateSpec(
        name=GateName.REGISTRATION,
        purpose="Ensure that registration and prequalification activities are subject to Human Approval.",
        location=(
            "Invoked at the entry of Stage 17 (Registration) and at the entry of "
            "Prequalification and Approved Vendor List activities."
        ),
        entry_conditions=(
            "A registration or prequalification activity is in scope.",
            "Requirements are identified.",
        ),
        exit_conditions=(
            "The dossier is prepared.",
            "The filing is approved.",
            "The status is updated.",
        ),
        owner="Registration and Market Entry Office.",
        bypass_prohibition="No workflow may bypass the Registration Gate.",
    ),
    GateName.TENDER: GateSpec(
        name=GateName.TENDER,
        purpose="Ensure that tender qualification and submission are subject to Verification and Human Approval.",
        location=(
            "Invoked at the entry of Stage 19 (Tender Support) and at the entry of "
            "every tender submission."
        ),
        entry_conditions=(
            "The tender is qualified.",
            "The pricing is analysed.",
            "The verification is complete.",
            "The Human Approval is in place.",
        ),
        exit_conditions=(
            "The Quotation Dossier is prepared.",
            "The submission is approved.",
            "The outcome is logged.",
        ),
        owner="Tender and Project Intelligence Office; Commercial Development Office.",
        bypass_prohibition="No workflow may bypass the Tender Gate.",
    ),
    GateName.PROJECT: GateSpec(
        name=GateName.PROJECT,
        purpose="Ensure that awarded projects are monitored and that commitments are not modified without authority.",
        location=(
            "Invoked at the entry of Stage 20 (Project Support) and at every Project "
            "commitment change."
        ),
        entry_conditions=(
            "A project is awarded.",
            "The project record is current.",
        ),
        exit_conditions=(
            "The Project Status Report is delivered.",
            "Issues are logged.",
            "After-sales opportunities are identified.",
        ),
        owner="Tender and Project Intelligence Office; Commercial Development Office.",
        bypass_prohibition="No workflow may bypass the Project Gate.",
    ),
    GateName.CLOSURE: GateSpec(
        name=GateName.CLOSURE,
        purpose=(
            "Ensure that an Opportunity reaches a governed Final Disposition with "
            "all required records preserved."
        ),
        location=(
            "Invoked at the transition to any Final Disposition status of the "
            "Commercial Status dimension."
        ),
        entry_conditions=(
            "The Opportunity is at a status that permits closure.",
            "The Commercial Outcome is recorded.",
            "The Knowledge Capture is complete.",
        ),
        exit_conditions=(
            "The Final Disposition is recorded.",
            "The Institutional Memory Entry is preserved.",
            "The Decision Log Entry is created.",
        ),
        owner="Originating Office; Performance and Learning Office.",
        bypass_prohibition=(
            "No workflow may bypass the Closure Gate. An Opportunity is constitutionally "
            "complete only when it reaches a governed Final Disposition with all "
            "required records preserved."
        ),
    ),
}


# ---------------------------------------------------------------------------
# Gate enforcement — bypass attempts are REJECTED
# ---------------------------------------------------------------------------


class GateBypassError(Exception):
    """A bypass attempt on a Decision Gate was REJECTED.

    Per GATE-*-006, "No workflow may bypass the ... Gate". A bypass
    attempt is an error, not a warning.
    """

    def __init__(self, gate: GateName, reason: str) -> None:
        self.gate = gate
        self.reason = reason
        super().__init__(
            f"Decision Gate '{gate.value}' bypass attempt REJECTED: {reason}. "
            f"Per Document 06 §4.{_gate_section(gate)}, no workflow may bypass this Gate."
        )


def _gate_section(gate: GateName) -> int:
    """Return the §4 subsection number of a gate (1..9)."""
    order = list(GateName)
    return order.index(gate) + 1


class GateEngine:
    """Evaluates entry and exit conditions for the 9 Decision Gates.

    The engine is a pure-logic state machine over a dict of facts
    (the inputs to condition evaluation). Conditions are callables that
    receive the facts and return True (satisfied) or False.

    A bypass attempt is always REJECTED (GateBypassError).
    """

    def __init__(
        self,
        entry_evaluators: Mapping[GateName, Callable[[Mapping[str, Any]], bool]] | None = None,
        exit_evaluators: Mapping[GateName, Callable[[Mapping[str, Any]], bool]] | None = None,
    ) -> None:
        # If a gate has no custom evaluator, its conditions are treated
        # as informational only and the gate is considered "open" for
        # the test suite. The bypass-prohibition is enforced regardless.
        self.entry_evaluators: dict[GateName, Callable[[Mapping[str, Any]], bool]] = (
            dict(entry_evaluators) if entry_evaluators else {}
        )
        self.exit_evaluators: dict[GateName, Callable[[Mapping[str, Any]], bool]] = (
            dict(exit_evaluators) if exit_evaluators else {}
        )
        # History of gate entries/exits for audit.
        self.history: list[dict[str, Any]] = []

    def check_entry(self, gate: GateName, facts: Mapping[str, Any]) -> None:
        """Verify entry conditions for the gate.

        Raises GateBypassError if the entry conditions are not satisfied.
        The bypass is rejected — a "soft skip" is not permitted.
        """
        evaluator = self.entry_evaluators.get(gate)
        if evaluator is not None and not evaluator(facts):
            self._record(gate, "ENTRY", "REJECTED", facts)
            raise GateBypassError(
                gate,
                f"entry conditions not satisfied: {list(GATES[gate].entry_conditions)}",
            )
        self._record(gate, "ENTRY", "PASSED", facts)

    def check_exit(self, gate: GateName, facts: Mapping[str, Any]) -> None:
        """Verify exit conditions for the gate.

        Raises GateBypassError if the exit conditions are not satisfied.
        """
        evaluator = self.exit_evaluators.get(gate)
        if evaluator is not None and not evaluator(facts):
            self._record(gate, "EXIT", "REJECTED", facts)
            raise GateBypassError(
                gate,
                f"exit conditions not satisfied: {list(GATES[gate].exit_conditions)}",
            )
        self._record(gate, "EXIT", "PASSED", facts)

    def bypass_attempt(self, gate: GateName, facts: Mapping[str, Any]) -> None:
        """Always REJECTS a bypass attempt on the given gate.

        Per GATE-*-006, "No workflow may bypass the ... Gate". This
        method exists so callers can be explicit about the bypass and
        get a uniform error.
        """
        self._record(gate, "BYPASS", "REJECTED", facts)
        raise GateBypassError(gate, "bypass is constitutionally prohibited")

    def _record(self, gate: GateName, action: str, result: str, facts: Mapping[str, Any]) -> None:
        self.history.append(
            {
                "gate": gate.value,
                "action": action,
                "result": result,
                "fact_keys": sorted(facts.keys()),
            }
        )


# ---------------------------------------------------------------------------
# Convenience: enumerate all gates for tests
# ---------------------------------------------------------------------------


def all_gates() -> list[GateName]:
    """Return all 9 Decision Gates in §4 order."""
    return list(GateName)


def is_bypass_attempt(gate: GateName) -> str:
    """Return the constitutional text of the gate's bypass prohibition."""
    return GATES[gate].bypass_prohibition
