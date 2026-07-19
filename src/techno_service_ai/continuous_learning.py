"""S24 Continuous Learning Engine — Document 02 §4.17, Phase 7.

Closes GAP-PHASE6-001.

Implements the pure-logic engine for the S24 (Continuous Learning)
stage. The engine is the consumer of `LearningUpdate` records:
each proposal is reviewed for constitutional impact before it is
applied.

Constitutional rules enforced by the engine:

  1. **Constitutional Impact Review** — every Learning Update
     proposal must be reviewed against the Constitution. A
     proposal that would amend, suspend, override, or weaken any
     constitutional clause is REJECTED.

  2. **Authority to amend** — the engine does NOT have authority
     to amend the Constitution. Only the Constitutional Owner
     (Class 4) can amend the Constitution. A proposal marked
     `constitutional_amendment=True` REQUIRES a Human Approval
     reference; without one, it is REJECTED.

  3. **Scope classification** — every Learning Update is
     classified as one of: SYSTEM_TUNING, POLICY_REFINEMENT,
     KNOWLEDGE_UPDATE, CONSTITUTIONAL_AMENDMENT. The first three
     may be auto-approved by the engine; the fourth REQUIRES
     Human Approval.

  4. **Rollback safety** — every Learning Update records whether
     it is REVERSIBLE. An irreversible update is REJECTED.

Constitutional source:
  - Constitution Article XXVIII (Document Hierarchy)
  - Document 02 §4.17 (Performance and Learning Office)
  - Document 06 §2.24 (Stage 24 — Continuous Learning)
  - Document 05 §3.19 (ENT-PER-003 LearningUpdate)
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class LearningUpdateScope(str, Enum):
    """The scope of a Learning Update proposal.

    Per Document 02 §4.17.3 (Learning Coordination Agent), the
    engine classifies every proposal before reviewing it.
    """

    SYSTEM_TUNING = "SYSTEM_TUNING"
    POLICY_REFINEMENT = "POLICY_REFINEMENT"
    KNOWLEDGE_UPDATE = "KNOWLEDGE_UPDATE"
    CONSTITUTIONAL_AMENDMENT = "CONSTITUTIONAL_AMENDMENT"


class LearningUpdateOutcome(str, Enum):
    """The outcome of a Continuous Learning review."""

    APPROVED = "APPROVED"
    REJECTED_CONSTITUTIONAL_IMPACT = "REJECTED_CONSTITUTIONAL_IMPACT"
    REJECTED_IRREVERSIBLE = "REJECTED_IRREVERSIBLE"
    REJECTED_MISSING_APPROVAL = "REJECTED_MISSING_APPROVAL"
    REJECTED_INVALID_SCOPE = "REJECTED_INVALID_SCOPE"


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class ContinuousLearningEngineError(Exception):
    """Base for S24 engine errors."""


class ConstitutionalAmendmentWithoutApprovalError(ContinuousLearningEngineError):
    """A CONSTITUTIONAL_AMENDMENT Learning Update is REJECTED without
    a Human Approval reference. The engine does NOT have authority
    to amend the Constitution (Constitution Article XXVIII)."""

    def __init__(self) -> None:
        super().__init__(
            f"Learning Update REJECTED: CONSTITUTIONAL_AMENDMENT without "
            f"Human Approval. Per Constitution Article XXVIII and Document 02 "
            f"§4.17.3, only the Constitutional Owner (Class 4) can amend the "
            f"Constitution. The Learning Coordination Agent does NOT have "
            f"authority to amend, suspend, override, or weaken any constitutional clause."
        )


class IrreversibleUpdateRejectedError(ContinuousLearningEngineError):
    """An irreversible Learning Update is REJECTED.

    Per Document 02 §4.17.3, every Learning Update must be
    REVERSIBLE. An irreversible update is REJECTED at the engine
    level (no human override)."""

    def __init__(self) -> None:
        super().__init__(
            f"Learning Update REJECTED: irreversible change. Per Document 02 "
            f"§4.17.3, every Learning Update must be REVERSIBLE. An "
            f"irreversible update is REJECTED."
        )


class ConstitutionalImpactError(ContinuousLearningEngineError):
    """A Learning Update has a constitutional impact that is
    REJECTED. The proposal would amend, suspend, override, or
    weaken a constitutional clause."""

    def __init__(self, clause: str) -> None:
        self.clause = clause
        super().__init__(
            f"Learning Update REJECTED: constitutional impact on clause "
            f"'{clause}'. Per Document 02 §4.17.3 Constitutional Impact "
            f"Review, a proposal that would amend, suspend, override, or "
            f"weaken a constitutional clause is REJECTED."
        )


# ---------------------------------------------------------------------------
# Inputs / Outputs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LearningUpdateProposal:
    """The input spec for a Continuous Learning proposal.

    The S24 engine reviews the proposal against the Constitution
    and returns a LearningUpdateResult.
    """

    target_type: str
    target_id: str
    description: str
    scope: str = "SYSTEM_TUNING"  # One of LearningUpdateScope
    reversible: bool = True
    human_approval_id: Optional[str] = None
    affected_clauses: Tuple[str, ...] = ()


@dataclass(frozen=True)
class LearningUpdateResult:
    """The result of a Continuous Learning review."""

    target_type: str
    target_id: str
    description: str
    scope: LearningUpdateScope
    reversible: bool
    outcome: LearningUpdateOutcome
    rationale: str
    requires_human_approval: bool


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


# The list of constitutional clauses the engine treats as
# inviolable. Any Learning Update whose affected_clauses includes
# one of these is REJECTED at the engine level.
INVARIABLE_CONSTITUTIONAL_CLAUSES: Tuple[str, ...] = (
    "Article I",
    "Article II",
    "Article III",
    "Article IV",
    "Article V",
    "Article VI",
    "Article VII",
    "Article VIII",
    "Article XII",
    "Article XVII",
    "Article XX",
    "Article XXVIII",
)


class ContinuousLearningEngine:
    """The S24 (Continuous Learning) pure-logic engine.

    Closes GAP-PHASE6-001. The engine reviews every LearningUpdate
    proposal for constitutional impact. The engine does NOT have
    authority to amend the Constitution; that authority is
    reserved to the Constitutional Owner.
    """

    def review(self, proposal: LearningUpdateProposal) -> LearningUpdateResult:
        """Review a Learning Update proposal.

        The review is a 4-step process:

          1. **Scope validation.** The scope must be one of the
             four LearningUpdateScope values. An invalid scope is
             REJECTED.
          2. **Reversibility check.** A proposal marked
             `reversible=False` is REJECTED.
          3. **Constitutional Impact Review.** If any affected
             clause is in the invariable list, the proposal is
             REJECTED.
          4. **Human Approval gate.** A CONSTITUTIONAL_AMENDMENT
             proposal REQUIRES a Human Approval reference. Without
             it, the proposal is REJECTED.

        Returns a LearningUpdateResult.
        """
        # 1. Scope validation
        try:
            scope = LearningUpdateScope(proposal.scope.upper())
        except ValueError as e:
            return LearningUpdateResult(
                target_type=proposal.target_type,
                target_id=proposal.target_id,
                description=proposal.description,
                scope=LearningUpdateScope.SYSTEM_TUNING,
                reversible=proposal.reversible,
                outcome=LearningUpdateOutcome.REJECTED_INVALID_SCOPE,
                rationale=f"Invalid scope: {e}",
                requires_human_approval=False,
            )

        # 2. Reversibility check
        if not proposal.reversible:
            return LearningUpdateResult(
                target_type=proposal.target_type,
                target_id=proposal.target_id,
                description=proposal.description,
                scope=scope,
                reversible=False,
                outcome=LearningUpdateOutcome.REJECTED_IRREVERSIBLE,
                rationale="Irreversible Learning Update is REJECTED.",
                requires_human_approval=False,
            )

        # 3. Constitutional Impact Review
        for clause in proposal.affected_clauses:
            if clause in INVARIABLE_CONSTITUTIONAL_CLAUSES:
                return LearningUpdateResult(
                    target_type=proposal.target_type,
                    target_id=proposal.target_id,
                    description=proposal.description,
                    scope=scope,
                    reversible=proposal.reversible,
                    outcome=LearningUpdateOutcome.REJECTED_CONSTITUTIONAL_IMPACT,
                    rationale=f"Affects invariable clause {clause}.",
                    requires_human_approval=True,
                )

        # 4. Human Approval gate for CONSTITUTIONAL_AMENDMENT
        if scope == LearningUpdateScope.CONSTITUTIONAL_AMENDMENT:
            if not proposal.human_approval_id or not proposal.human_approval_id.strip():
                return LearningUpdateResult(
                    target_type=proposal.target_type,
                    target_id=proposal.target_id,
                    description=proposal.description,
                    scope=scope,
                    reversible=proposal.reversible,
                    outcome=LearningUpdateOutcome.REJECTED_MISSING_APPROVAL,
                    rationale="CONSTITUTIONAL_AMENDMENT requires Human Approval.",
                    requires_human_approval=True,
                )

        # All checks passed — APPROVED
        rationale = f"Approved: scope={scope.value}, reversible=True"
        if proposal.affected_clauses:
            rationale += f", affected_clauses={list(proposal.affected_clauses)}"
        return LearningUpdateResult(
            target_type=proposal.target_type,
            target_id=proposal.target_id,
            description=proposal.description,
            scope=scope,
            reversible=proposal.reversible,
            outcome=LearningUpdateOutcome.APPROVED,
            rationale=rationale,
            requires_human_approval=(
                scope == LearningUpdateScope.CONSTITUTIONAL_AMENDMENT
            ),
        )

    def is_constitutional_amendment(self, proposal: LearningUpdateProposal) -> bool:
        """Return True if the proposal is a CONSTITUTIONAL_AMENDMENT."""
        try:
            return LearningUpdateScope(proposal.scope.upper()) == LearningUpdateScope.CONSTITUTIONAL_AMENDMENT
        except ValueError:
            return False
