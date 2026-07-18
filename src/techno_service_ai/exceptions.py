"""Exception Handling — Document 06 Section 7.

Implements the 9 exception scenarios:

  7.1 Missing Evidence (EXC-EV-001..003)
  7.2 Duplicate Opportunities (EXC-DUP-001..002)
  7.3 Conflicting Sources (EXC-CON-001..002)
  7.4 Register Conflicts (EXC-REG-001..002)
  7.5 Commercial Conflicts (EXC-COM-001..002)
  7.6 Constitutional Incidents (EXC-INC-001..003)
  7.7 Agent Failure (EXC-AGT-001..003)
  7.8 Human Unavailable (EXC-HUM-001..003)
  7.9 External Dependency Unavailable (EXC-EXT-001..003)

This is a pure-logic module. The Recovery Model (Section 12) lives in
its own module `recovery.py`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping


class ExceptionScenario(str, Enum):
    """The 9 exception scenarios of Document 06 §7."""

    MISSING_EVIDENCE = "MISSING_EVIDENCE"                  # §7.1
    DUPLICATE_OPPORTUNITY = "DUPLICATE_OPPORTUNITY"        # §7.2
    CONFLICTING_SOURCES = "CONFLICTING_SOURCES"            # §7.3
    REGISTER_CONFLICT = "REGISTER_CONFLICT"                # §7.4
    COMMERCIAL_CONFLICT = "COMMERCIAL_CONFLICT"            # §7.5
    CONSTITUTIONAL_INCIDENT = "CONSTITUTIONAL_INCIDENT"    # §7.6
    AGENT_FAILURE = "AGENT_FAILURE"                        # §7.7
    HUMAN_UNAVAILABLE = "HUMAN_UNAVAILABLE"                # §7.8
    EXTERNAL_DEPENDENCY_UNAVAILABLE = "EXTERNAL_DEPENDENCY_UNAVAILABLE"  # §7.9


# Outcomes (the constitutional outcomes of each exception)
@dataclass(frozen=True)
class ExceptionSpec:
    scenario: ExceptionScenario
    trigger: str
    action: str
    record_requirement: str
    escalation_target: str | None = None


EXCEPTION_SPECS: Mapping[ExceptionScenario, ExceptionSpec] = {
    ExceptionScenario.MISSING_EVIDENCE: ExceptionSpec(
        scenario=ExceptionScenario.MISSING_EVIDENCE,
        trigger="A material claim is presented without Evidence.",
        action=(
            "The material claim is NOT presented as verified. The claim is "
            "held pending the Evidence. If the Evidence cannot be obtained "
            "within a defined window, classify as Unverified Value Hypothesis, "
            "On Hold, or Rejected per the Value Qualification Rule."
        ),
        record_requirement="Log the missing Evidence and the hold.",
        escalation_target="Originating Office",
    ),
    ExceptionScenario.DUPLICATE_OPPORTUNITY: ExceptionSpec(
        scenario=ExceptionScenario.DUPLICATE_OPPORTUNITY,
        trigger="A new Opportunity is a duplicate of an existing one.",
        action="Merge the new Opportunity with the existing Opportunity; do not re-report.",
        record_requirement="Record the merge in the Decision Log.",
    ),
    ExceptionScenario.CONFLICTING_SOURCES: ExceptionSpec(
        scenario=ExceptionScenario.CONFLICTING_SOURCES,
        trigger="Sources conflict on a material matter.",
        action=(
            "Resolve using the higher-authority source, or report the "
            "conflict and present the range of estimates."
        ),
        record_requirement="Record the conflict in the Verification Record and the Claim Classification Record.",
        escalation_target="Originating Office + Verification Office",
    ),
    ExceptionScenario.REGISTER_CONFLICT: ExceptionSpec(
        scenario=ExceptionScenario.REGISTER_CONFLICT,
        trigger="A counterparty or activity matches an entry in a Constitutional Register.",
        action=(
            "Identify the conflict at the gate. Close the Opportunity. "
            "Escalate to the Risk and Compliance Office."
        ),
        record_requirement="Log the conflict and the closure in the Decision Log.",
        escalation_target="Risk and Compliance Office",
    ),
    ExceptionScenario.COMMERCIAL_CONFLICT: ExceptionSpec(
        scenario=ExceptionScenario.COMMERCIAL_CONFLICT,
        trigger="A commercial conflict is identified at the Commercial Gate.",
        action="Escalate to the Authorised Executive. Log the conflict.",
        record_requirement="Log in the Decision Log.",
        escalation_target="Authorised Executive",
    ),
    ExceptionScenario.CONSTITUTIONAL_INCIDENT: ExceptionSpec(
        scenario=ExceptionScenario.CONSTITUTIONAL_INCIDENT,
        trigger="A constitutional incident is identified.",
        action=(
            "Log, escalate, investigate, and remediate. Trigger a "
            "Remediation Plan. Record as ENT-RIS-003 ConstitutionalIncident."
        ),
        record_requirement="Record as ConstitutionalIncident (ENT-RIS-003).",
        escalation_target="Constitutional Owner + Risk and Compliance Office",
    ),
    ExceptionScenario.AGENT_FAILURE: ExceptionSpec(
        scenario=ExceptionScenario.AGENT_FAILURE,
        trigger="An Agent fails to complete its Charter work.",
        action=(
            "Trigger the Continuity and Substitution governance. Assign a "
            "substitute under a temporary mandate. Preserve Verification "
            "Independence. Log as a Constitutional Incident if material."
        ),
        record_requirement="Log the failure and the substitute.",
        escalation_target="Continuity and Substitution governance",
    ),
    ExceptionScenario.HUMAN_UNAVAILABLE: ExceptionSpec(
        scenario=ExceptionScenario.HUMAN_UNAVAILABLE,
        trigger="The Required Approver Role is unavailable.",
        action=(
            "Enter a Waiting state. The Human Escalation Coordination Agent "
            "issues a reminder. If the unavailability persists, escalate "
            "to a higher authority. Emergency Approvals are governed by "
            "Authority Matrix Section 9."
        ),
        record_requirement="Log the unavailability and the escalation.",
        escalation_target="Higher authority / Emergency Approval",
    ),
    ExceptionScenario.EXTERNAL_DEPENDENCY_UNAVAILABLE: ExceptionSpec(
        scenario=ExceptionScenario.EXTERNAL_DEPENDENCY_UNAVAILABLE,
        trigger="An external dependency is unavailable.",
        action=(
            "Log the failure. Enter a Waiting state. Notify the Continuity "
            "Service and the Security Operations Agent if material. "
            "Escalate to the Continuity and Recovery Agent."
        ),
        record_requirement="Log the failure and the waiting state.",
        escalation_target="Continuity and Recovery Agent",
    ),
}


def all_scenarios() -> list[ExceptionScenario]:
    """Return the 9 exception scenarios in document order."""
    return list(ExceptionScenario)


# ---------------------------------------------------------------------------
# Exception Engine
# ---------------------------------------------------------------------------


class ExceptionEngine:
    """Pure-logic exception engine.

    Each scenario is processed by `handle(...)`, which returns an
    ExceptionRecord. The record is appended to the audit log.
    """

    def __init__(self) -> None:
        self.records: list[dict] = []

    def handle(
        self,
        scenario: ExceptionScenario,
        *,
        material_canonical_id: str,
        reason: str,
        triggered_by: str,
    ) -> dict:
        spec = EXCEPTION_SPECS[scenario]
        rec = {
            "scenario": scenario.value,
            "spec": spec,
            "material_canonical_id": material_canonical_id,
            "reason": reason,
            "triggered_by": triggered_by,
            "escalation_target": spec.escalation_target,
        }
        self.records.append(rec)
        return rec
