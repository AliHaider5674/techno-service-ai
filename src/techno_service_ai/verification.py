"""Verification Engine — Document 06 Section 6.

Implements the 5 Verifier Agents and the Independence Tracker.

  1. Preliminary Evidence Reviewer Agent (VER-PRE-001..003) — at every
     layer where a material claim is produced.
  2. Specialist Verifier Agent (VER-SPE-001..003) — domain-specific.
  3. Independent Final Verifier Agent (VER-IFV-001..004) — at Stage 15
     of the Discovery Order, before any executive recommendation,
     external engagement, board report, commercial pursuit, or public
     claim.
  4. Second Reviewer Agent (VER-IFV-003) — supports the Independent
     Final Verifier on material claims.
  5. Claim Classifier Agent (Constitution Article XXIII) — classifies
     each material claim.

Independence (VER-IND-001..003): the producer and the verifier SHALL be
separately identifiable on every material record. A discovering or
researching function may not be the sole verifier of its own claim.
Producer == Verifier is REJECTED.

This is a pure-logic module with NO database coupling. The
service-layer wiring (loading actors, writing to the audit log) lives
in the verification service.

Constitutional source:
  - Constitution Article VI paragraph 5, Article XVII paragraph 2(1)
  - Document 06 §6.1..6.7 (Verification Workflow)
  - AC-VER-001..005 (Verification independence criteria)
  - AC-P3-004 (Producer != Verifier)
  - AC-P3-007 (Independence of Verification preserved)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import FrozenSet, Mapping


class VerifierRole(str, Enum):
    """The 5 Verifier Agent roles of Document 06 §6."""

    PRELIMINARY_EVIDENCE_REVIEWER = "PRELIMINARY_EVIDENCE_REVIEWER"
    SPECIALIST_VERIFIER = "SPECIALIST_VERIFIER"
    INDEPENDENT_FINAL_VERIFIER = "INDEPENDENT_FINAL_VERIFIER"
    SECOND_REVIEWER = "SECOND_REVIEWER"
    CLAIM_CLASSIFIER = "CLAIM_CLASSIFIER"


ALL_VERIFIER_ROLES: tuple[VerifierRole, ...] = tuple(VerifierRole)


class VerificationOutcome(str, Enum):
    """The outcome of a verification record.

    Mirrors the DB-PRIN-015 requirements: the outcome must be explicit
    and recorded.
    """

    VALIDATED = "VALIDATED"
    QUALIFIED = "QUALIFIED"  # validated with conditions
    REJECTED = "REJECTED"
    PENDING = "PENDING"  # only valid transiently, not a final state


class ClaimClassification(str, Enum):
    """The 5 Claim Classifications of Constitution Article XXIII.

    Declaration order is the canonical taxonomy order.
    """

    FACT = "FACT"                    # verifiable by independent source
    INFERENCE = "INFERENCE"          # logically derived from facts
    PROJECTION = "PROJECTION"        # forward-looking statement
    RECOMMENDATION = "RECOMMENDATION"  # agent recommendation
    UNVERIFIED = "UNVERIFIED"        # no source available


# A material claim is any claim that will be reported, shared, or used
# to drive a downstream decision.
MATERIAL_CLAIM_CATEGORIES: FrozenSet[ClaimClassification] = frozenset({
    ClaimClassification.FACT,
    ClaimClassification.INFERENCE,
    ClaimClassification.PROJECTION,
})


# ---------------------------------------------------------------------------
# Producer-Verifier Independence
# ---------------------------------------------------------------------------


class IndependenceViolation(Exception):
    """A producer == verifier scenario was REJECTED.

    Per VER-IND-002: "A discovering or researching function may not be
    the sole verifier of its own material claim."

    The error message is part of the constitutional record.
    """

    def __init__(self, producer_id: str, verifier_id: str, role: VerifierRole) -> None:
        self.producer_id = producer_id
        self.verifier_id = verifier_id
        self.role = role
        super().__init__(
            f"Independence violation: producer '{producer_id}' == verifier "
            f"'{verifier_id}' for role {role.value}. "
            f"Per Document 06 §6.7 VER-IND-002, a discovering or researching "
            f"function may not be the sole verifier of its own material claim. "
            f"Per Article XVII paragraph 2(1), Independence of Verification is "
            f"a constitutional requirement."
        )


# Same ROLE-CLASS may also violate independence if the role is the
# producer of the same claim. We model the independence check as
# "producer_id != verifier_id" (the strict test). Callers can also
# enforce broader role-based exclusions (e.g. an Analyst role may not
# verify its own claim even if the IDs differ — the Application
# Policy may add this layer).


@dataclass(frozen=True)
class ProducerRef:
    """The producer of a material claim.

    The producer is the function that discovered, researched, or
    authored the claim. The producer's identity is recorded on every
    material record (VER-IND-001).
    """

    producer_id: str
    role_code: str  # SoD class code from Phase 1 (ADMIN, ANALYST, ...)


@dataclass(frozen=True)
class VerifierRef:
    """The verifier of a material claim.

    The verifier is the function that independently reviews the
    producer's claim. The verifier's identity is recorded on every
    material record (VER-IND-001).
    """

    verifier_id: str
    role: VerifierRole
    role_code: str  # SoD class code from Phase 1


@dataclass(frozen=True)
class VerificationRecord:
    """A verification record (Document 06 §6.1..6.5).

    The record is the authoritative evidence of independent review.
    """

    canonical_id: str
    material_claim_id: str
    producer: ProducerRef
    verifier: VerifierRef
    claim_classification: ClaimClassification
    outcome: VerificationOutcome
    reason: str
    source_citations: tuple[str, ...]
    second_reviewer_id: str | None  # required for material claims (VER-IFV-003)
    created_at: str
    independence_checked: bool = True  # always True on a valid record


# ---------------------------------------------------------------------------
# Independence Tracker
# ---------------------------------------------------------------------------


class IndependenceTracker:
    """Tracks the independence of every verification record.

    The tracker enforces (VER-IND-001..003) at the time of verification
    creation. It is the single source of truth for the
    "producer and verifier are clearly distinct" property of every
    material record.

    A material claim is rejected if producer == verifier, even if the
    roles are different. Identity equality is the strictest test and
    matches the constitutional text. A weaker "role class" test
    can be added by the application.
    """

    def __init__(self) -> None:
        self.records: list[VerificationRecord] = []
        self.rejections: list[IndependenceViolation] = []

    def create_record(
        self,
        *,
        canonical_id: str,
        material_claim_id: str,
        producer: ProducerRef,
        verifier: VerifierRef,
        claim_classification: ClaimClassification,
        outcome: VerificationOutcome,
        reason: str,
        source_citations: tuple[str, ...] = (),
        second_reviewer_id: str | None = None,
        created_at: str = "",
    ) -> VerificationRecord:
        """Create a verification record. Enforces independence."""
        self._assert_independent(producer, verifier)
        if (
            claim_classification in MATERIAL_CLAIM_CATEGORIES
            and verifier.role == VerifierRole.INDEPENDENT_FINAL_VERIFIER
            and not second_reviewer_id
        ):
            raise IndependenceViolation(
                producer_id=producer.producer_id,
                verifier_id=verifier.verifier_id,
                role=verifier.role,
            ).with_note(
                "Material claim with Independent Final Verifier requires a "
                "Second Reviewer (VER-IFV-003)."
            )
        rec = VerificationRecord(
            canonical_id=canonical_id,
            material_claim_id=material_claim_id,
            producer=producer,
            verifier=verifier,
            claim_classification=claim_classification,
            outcome=outcome,
            reason=reason,
            source_citations=source_citations,
            second_reviewer_id=second_reviewer_id,
            created_at=created_at,
            independence_checked=True,
        )
        self.records.append(rec)
        return rec

    def _assert_independent(self, producer: ProducerRef, verifier: VerifierRef) -> None:
        if producer.producer_id == verifier.verifier_id:
            violation = IndependenceViolation(
                producer_id=producer.producer_id,
                verifier_id=verifier.verifier_id,
                role=verifier.role,
            )
            self.rejections.append(violation)
            raise violation

    def is_independent(self, record: VerificationRecord) -> bool:
        """Re-check independence on an existing record (audit)."""
        return record.producer.producer_id != record.verifier.verifier_id

    def by_claim(self, material_claim_id: str) -> list[VerificationRecord]:
        return [r for r in self.records if r.material_claim_id == material_claim_id]

    def by_verifier(self, verifier_id: str) -> list[VerificationRecord]:
        return [r for r in self.records if r.verifier.verifier_id == verifier_id]

    def by_producer(self, producer_id: str) -> list[VerificationRecord]:
        return [r for r in self.records if r.producer.producer_id == producer_id]

    def all_records(self) -> list[VerificationRecord]:
        return list(self.records)


# ---------------------------------------------------------------------------
# Verifier Agent API
# ---------------------------------------------------------------------------


@dataclass
class VerifierAgent:
    """One Verifier Agent per role (Document 06 §6.1..6.5)."""

    role: VerifierRole
    agent_id: str
    role_code: str
    # The agent's scope (e.g. "Industrial", "Technology", "Independent Final").
    scope: str = ""

    def verify(
        self,
        tracker: IndependenceTracker,
        *,
        material_claim_id: str,
        producer: ProducerRef,
        claim_classification: ClaimClassification,
        outcome: VerificationOutcome,
        reason: str,
        source_citations: tuple[str, ...] = (),
        second_reviewer_id: str | None = None,
        canonical_id: str = "",
        created_at: str = "",
    ) -> VerificationRecord:
        """Submit a verification record on behalf of this agent.

        The tracker enforces producer != verifier. If the agent
        attempts to verify a claim that the agent itself produced,
        IndependenceViolation is raised.
        """
        verifier = VerifierRef(
            verifier_id=self.agent_id,
            role=self.role,
            role_code=self.role_code,
        )
        return tracker.create_record(
            canonical_id=canonical_id or _uuid_str(),
            material_claim_id=material_claim_id,
            producer=producer,
            verifier=verifier,
            claim_classification=claim_classification,
            outcome=outcome,
            reason=reason,
            source_citations=source_citations,
            second_reviewer_id=second_reviewer_id,
            created_at=created_at,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _uuid_str() -> str:
    import uuid

    return str(uuid.uuid4())


# Patch the IndependenceViolation class to add a with_note helper.
def _with_note(self: IndependenceViolation, note: str) -> IndependenceViolation:  # type: ignore[no-redef]
    """Return a new violation with an appended constitutional note."""
    msg = f"{str(self)} Note: {note}"
    new = IndependenceViolation(self.producer_id, self.verifier_id, self.role)
    new.args = (msg,)
    return new


IndependenceViolation.with_note = _with_note  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Convenience: which roles may serve as the "Independent Final Verifier"
# ---------------------------------------------------------------------------


# A claim must be verified by an Independent Final Verifier when:
#   - it is a material claim
#   - it precedes a Class 3 External Action Decision
#   - it precedes a Class 4 Binding Decision
#   - it is a Board Report
#   - it is a public claim
INDEPENDENT_FINAL_REQUIRED_FOR = frozenset({
    "EXECUTIVE_RECOMMENDATION",
    "EXTERNAL_ENGAGEMENT",
    "BOARD_REPORT",
    "COMMERCIAL_PURSUIT",
    "PUBLIC_CLAIM",
    "TENDER_SUBMISSION",
})


# ---------------------------------------------------------------------------
# Five-agent roster factory
# ---------------------------------------------------------------------------


def five_agent_roster(role_code: str = "VERIFIER") -> list[VerifierAgent]:
    """Return one VerifierAgent for each of the 5 verifier roles.

    Each agent has a unique id (so producer != verifier is enforced
    by default for any producer with a different id).
    """
    return [
        VerifierAgent(
            role=VerifierRole.PRELIMINARY_EVIDENCE_REVIEWER,
            agent_id=f"verifier-preliminary-{role_code.lower()}",
            role_code=role_code,
            scope="PRELIMINARY",
        ),
        VerifierAgent(
            role=VerifierRole.SPECIALIST_VERIFIER,
            agent_id=f"verifier-specialist-{role_code.lower()}",
            role_code=role_code,
            scope="SPECIALIST",
        ),
        VerifierAgent(
            role=VerifierRole.INDEPENDENT_FINAL_VERIFIER,
            agent_id=f"verifier-independent-final-{role_code.lower()}",
            role_code=role_code,
            scope="INDEPENDENT_FINAL",
        ),
        VerifierAgent(
            role=VerifierRole.SECOND_REVIEWER,
            agent_id=f"verifier-second-reviewer-{role_code.lower()}",
            role_code=role_code,
            scope="SECOND_REVIEWER",
        ),
        VerifierAgent(
            role=VerifierRole.CLAIM_CLASSIFIER,
            agent_id=f"verifier-claim-classifier-{role_code.lower()}",
            role_code=role_code,
            scope="CLAIM_CLASSIFICATION",
        ),
    ]
