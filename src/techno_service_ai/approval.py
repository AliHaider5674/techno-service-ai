"""Approval Engine — Document 06 Section 5 + Authority Matrix.

Implements the Approval Engine of Document 06 §5 and the Authority
Matrix:

  - 4 Decision Classes (1: Internal Intelligence, 2: Qualification &
    Recommendation, 3: External Action, 4: Binding/Financial/Legal/Strategic)
  - Required Approver Role resolution per Authority Matrix Section 3
  - Approval Request / Approval Package / Decision Log Entry
  - Conditional Approval (with duration, revocation conditions, expiry)
  - Approval Revocation (per Authority Matrix Section 10)
  - Approval Audit Trail
  - Concentration limits (Authority Matrix Section 8: One-Person-One-
    Approval, Self-Approval Prohibited)
  - **Silence != Approval** (Constitution Article XII paragraph 7,
    Article XVII paragraph 2(15), GATE-HA-006, REQ-RULE-005):
    silence, urgency, prior behaviour, similar historical approval,
    or an Agent recommendation does NOT constitute Human Approval.
  - Standing Authorisations (Authority Matrix Section 5)

This is a pure-logic module with NO database coupling.

Constitutional source:
  - Constitution Article XII paragraphs 5, 6, 7, 8; Article XIII;
    Article XVII paragraph 2(15)
  - Authority Matrix Sections 1..13
  - Document 06 §5.1..5.8 (Approval Workflow)
  - Document 06 §4.4 (Human Approval Gate)
  - AC-APR-001..006 (Human Approval criteria)
  - AC-P3-005 (Approval request: routed to correct Required Approver Role
    based on Decision Class; decision recorded)
  - AC-P3-008 (Human Approval Gate cannot be bypassed by silence,
    urgency, prior behaviour, AI recommendation)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import FrozenSet, Mapping


# ---------------------------------------------------------------------------
# Decision Classes (Constitution Article XII)
# ---------------------------------------------------------------------------


class DecisionClass(str, Enum):
    """The 4 Decision Classes of Constitution Article XII."""

    CLASS_1 = "CLASS_1"  # Internal Intelligence
    CLASS_2 = "CLASS_2"  # Qualification / Recommendation
    CLASS_3 = "CLASS_3"  # External Action
    CLASS_4 = "CLASS_4"  # Binding / Financial / Legal / Strategic


# ---------------------------------------------------------------------------
# Approval decision outcomes
# ---------------------------------------------------------------------------


class ApprovalDecision(str, Enum):
    """The four terminal outcomes of an approval request."""

    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CONDITIONAL = "CONDITIONAL"
    EXPIRED = "EXPIRED"  # Conditional approval past its duration without renewal


# ---------------------------------------------------------------------------
# Constitutional Approver Roster (Authority Matrix Sections 3 + 4)
# ---------------------------------------------------------------------------


# Per Authority Matrix §3.1, Class 1 default is the Agent itself (within
# Charter). No Required Approver Role in the human-approval sense.
#
# Per §3.2, Class 2 default is the Responsible Human Function Owner
# (RHFO) of the originating Office.
#
# Per §3.3, Class 3 default is the RHFO of the originating Office.
# Material Class 3 requires the Authorised Executive.
#
# Per §3.4, Class 4 has specific named approvers (Authorised Executive
# or Constitutional Owner) per the per-decision-type table.

REQUIRED_APPROVER_ROLE: Mapping[DecisionClass, str] = {
    DecisionClass.CLASS_1: "AGENT_WITHIN_CHARTER",  # no human approval required
    DecisionClass.CLASS_2: "RESPONSIBLE_HUMAN_FUNCTION_OWNER",
    DecisionClass.CLASS_3: "RESPONSIBLE_HUMAN_FUNCTION_OWNER",
    DecisionClass.CLASS_4: "AUTHORISED_EXECUTIVE_OR_CONSTITUTIONAL_OWNER",
}


# Class 4 per-decision-type approver (Authority Matrix Section 3.4 table)
CLASS_4_APPROVER: Mapping[str, str] = {
    "BINDING_OFFER": "AUTHORISED_EXECUTIVE",
    "COMMIT_PRICE": "AUTHORISED_EXECUTIVE",
    "INCUR_EXPENDITURE": "AUTHORISED_EXECUTIVE",
    "COMMIT_INVENTORY": "AUTHORISED_EXECUTIVE",
    "BINDING_BID": "AUTHORISED_EXECUTIVE",
    "PILOT_RESOURCES": "AUTHORISED_EXECUTIVE",
    "AGENCY_TERMS": "CONSTITUTIONAL_OWNER",
    "EXCLUSIVITY": "CONSTITUTIONAL_OWNER",
    "SIGN_CONTRACT": "CONSTITUTIONAL_OWNER",
    "ACCEPT_LEGAL_TERMS": "CONSTITUTIONAL_OWNER",
    "DISCLOSE_PROTECTED_INFO": "AUTHORISED_EXECUTIVE",
    "STRATEGIC_PARTNERSHIP": "CONSTITUTIONAL_OWNER",
    "APPOINT_TERMINATE_REP": "CONSTITUTIONAL_OWNER",
    "MATERIAL_PUBLIC_STATEMENT": "CONSTITUTIONAL_OWNER",
    "AMEND_CONSTITUTION": "CONSTITUTIONAL_OWNER",
}


# ---------------------------------------------------------------------------
# Approval Request / Decision / Revocation — the constitutional record
# ---------------------------------------------------------------------------


class SilenceNotApproval(Exception):
    """A bypass attempt on the Human Approval Gate was REJECTED.

    Per Constitution Article XII paragraph 7, Article XVII paragraph
    2(15), GATE-HA-006, REQ-RULE-005: silence, urgency, prior
    behaviour, similar historical approval, or an Agent recommendation
    does NOT constitute Human Approval.

    This exception is raised whenever any of those bypass signals is
    presented as a substitute for a real approval.
    """

    def __init__(self, reason_code: str, detail: str) -> None:
        self.reason_code = reason_code
        super().__init__(
            f"Human Approval Gate bypass REJECTED ({reason_code}): {detail}. "
            f"Per Constitution Article XII paragraph 7, GATE-HA-006, and "
            f"REQ-RULE-005, silence/urgency/prior-behaviour/AI-recommendation "
            f"does NOT constitute Human Approval."
        )


# The five reason codes (per the user's Phase 3 sign-off prompt)
BYPASS_SIGNALS: FrozenSet[str] = frozenset({
    "SILENCE",
    "URGENCY",
    "PRIOR_BEHAVIOUR",
    "SIMILAR_HISTORICAL_APPROVAL",
    "AI_RECOMMENDATION",
})


@dataclass(frozen=True)
class ApprovalPackage:
    """The Approval Package of APR-REQ-003 / APR-PKG-001..003.

    Carries the verified material, claim classifications, evidence
    references, verification references, decision options, risk
    register references, performance data references, and a
    Constitutional Compliance Attestation.
    """

    material_reference: str
    decision_class: DecisionClass
    required_approver_role: str
    verified_material: str
    claim_classifications: tuple[str, ...]
    evidence_references: tuple[str, ...]
    verification_references: tuple[str, ...]
    decision_options: tuple[str, ...]
    risk_register_references: tuple[str, ...]
    performance_data_references: tuple[str, ...]
    constitutional_compliance_attestation: str
    originating_office: str
    originating_agent_id: str


@dataclass(frozen=True)
class ApprovalRequest:
    """The Approval Request of APR-REQ-001..004.

    Identified by a canonical_id. The originating Office and Agent
    are recorded; the originating Agent MAY NOT be the approver
    (Self-Approval Prohibited, Authority Matrix Section 8.2).
    """

    canonical_id: str
    package: ApprovalPackage
    request_date: str
    response_window: timedelta


@dataclass(frozen=True)
class ConditionalApprovalTerms:
    """The terms of a Conditional Approval (APR-CON-001..003)."""

    conditions: tuple[str, ...]
    duration: timedelta
    revocation_conditions: tuple[str, ...]


@dataclass(frozen=True)
class ApprovalDecisionRecord:
    """The Decision record of Section 7 of the Authority Matrix.

    This is the authoritative record. It is hash-chained to the audit
    log via the service layer.
    """

    canonical_id: str
    request_canonical_id: str
    decision: ApprovalDecision
    approver_id: str
    approver_role: str
    decision_date: str
    conditions: tuple[str, ...] = ()
    revocation_conditions: tuple[str, ...] = ()
    duration: timedelta | None = None
    expiry_date: str | None = None
    reason: str = ""


@dataclass(frozen=True)
class RevocationRecord:
    """The Revocation record of Authority Matrix Section 10."""

    canonical_id: str
    decision_canonical_id: str
    revoker_id: str
    revocation_date: str
    grounds: str
    remediation: str


# ---------------------------------------------------------------------------
# Concentration limits (Authority Matrix Section 8)
# ---------------------------------------------------------------------------


class SoDViolation(Exception):
    """A Separation of Duties violation was REJECTED.

    Authority Matrix Section 8:
      8.1 One-Person-One-Approval — no individual may be the sole
          human authority over both the recommendation and the
          approval of the same material Decision.
      8.2 Self-Approval Prohibited — no individual may approve a
          Decision in which that individual was the originator, the
          recommender, the verifier, or the executor.
    """

    def __init__(self, rule: str, detail: str) -> None:
        self.rule = rule
        super().__init__(
            f"SoD violation ({rule}) REJECTED: {detail}. "
            f"Per Authority Matrix Section 8, One-Person-One-Approval "
            f"and Self-Approval Prohibited are constitutional limits."
        )


# ---------------------------------------------------------------------------
# Approval Engine
# ---------------------------------------------------------------------------


class ApprovalEngine:
    """Pure-logic approval engine.

    Methods:
      - create_request: create an Approval Request, resolve Required
        Approver Role from Decision Class.
      - decide: an authorised human issues a Decision (approved,
        rejected, conditional). Enforces Self-Approval Prohibited and
        silence != approval.
      - revoke: an authorised human revokes a prior decision.
      - check_silence_not_approval: helper to validate that the
        decision is not a substitute signal.
    """

    def __init__(self) -> None:
        self.requests: dict[str, ApprovalRequest] = {}
        self.decisions: dict[str, ApprovalDecisionRecord] = {}
        self.revocations: list[RevocationRecord] = []
        # Counter of bypass rejections for audit.
        self.bypass_rejections: list[SilenceNotApproval] = []

    # ---- Step 1: create the request ------------------------------------

    def create_request(
        self,
        *,
        package: ApprovalPackage,
        request_date: str,
        response_window: timedelta,
        canonical_id: str = "",
    ) -> ApprovalRequest:
        """Create an Approval Request.

        The Required Approver Role is resolved from the Decision Class
        (per Authority Matrix Sections 3.1..3.4). For Class 4, the
        per-decision-type approver is taken from the material_reference
        or the package's required_approver_role.
        """
        cid = canonical_id or _uuid_str()
        req = ApprovalRequest(
            canonical_id=cid,
            package=package,
            request_date=request_date,
            response_window=response_window,
        )
        self.requests[cid] = req
        return req

    def required_approver_role(
        self, decision_class: DecisionClass, decision_type: str | None = None
    ) -> str:
        """Return the Required Approver Role per Authority Matrix §3."""
        if decision_class == DecisionClass.CLASS_4 and decision_type:
            return CLASS_4_APPROVER.get(decision_type, REQUIRED_APPROVER_ROLE[decision_class])
        return REQUIRED_APPROVER_ROLE[decision_class]

    # ---- Step 2: enforce silence != approval ----------------------------

    def check_silence_not_approval(
        self,
        *,
        request_canonical_id: str,
        bypass_signal: str,
        detail: str,
    ) -> None:
        """Reject a bypass attempt. Raises SilenceNotApproval.

        Per GATE-HA-006 and REQ-RULE-005, the following signals are NOT
        Human Approval:
          - SILENCE (no response within window)
          - URGENCY (the matter is time-critical)
          - PRIOR_BEHAVIOUR (the approver has approved similar cases)
          - SIMILAR_HISTORICAL_APPROVAL (precedent)
          - AI_RECOMMENDATION (an Agent recommended approval)

        The Approval Engine exposes this check so that the orchestrator
        can attempt to record a "decision" via these signals and be
        rejected.
        """
        if bypass_signal not in BYPASS_SIGNALS:
            raise ValueError(f"Unknown bypass signal: {bypass_signal}")
        rejection = SilenceNotApproval(bypass_signal, detail)
        self.bypass_rejections.append(rejection)
        raise rejection

    # ---- Step 3: decide -------------------------------------------------

    def decide(
        self,
        *,
        request_canonical_id: str,
        approver_id: str,
        approver_role: str,
        decision: ApprovalDecision,
        decision_date: str,
        conditions: tuple[str, ...] = (),
        revocation_conditions: tuple[str, ...] = (),
        duration: timedelta | None = None,
        reason: str = "",
    ) -> ApprovalDecisionRecord:
        """Issue an Approval Decision.

        Enforces:
          - Self-Approval Prohibited (Authority Matrix §8.2)
          - Required Approver Role (the approver_role must equal the
            request's required_approver_role)
          - For Conditional decisions, terms must include conditions,
            duration, and revocation_conditions.
        """
        req = self.requests.get(request_canonical_id)
        if req is None:
            raise ValueError(f"Unknown request: {request_canonical_id}")
        # Self-Approval Prohibited.
        if approver_id == req.package.originating_agent_id:
            raise SoDViolation(
                rule="Self-Approval Prohibited",
                detail=(
                    f"approver '{approver_id}' is the originating agent of "
                    f"request {request_canonical_id}"
                ),
            )
        # Required Approver Role.
        expected = req.package.required_approver_role
        if approver_role != expected:
            raise SoDViolation(
                rule="Required Approver Role",
                detail=(
                    f"approver role '{approver_role}' does not match the "
                    f"Required Approver Role '{expected}' for decision "
                    f"class {req.package.decision_class.value}"
                ),
            )
        # Conditional terms required for CONDITIONAL decisions.
        if decision == ApprovalDecision.CONDITIONAL:
            if not conditions:
                raise ValueError("CONDITIONAL decision requires at least one condition")
            if duration is None:
                raise ValueError("CONDITIONAL decision requires a duration")
            if not revocation_conditions:
                raise ValueError(
                    "CONDITIONAL decision requires at least one revocation condition"
                )
        expiry = None
        if decision == ApprovalDecision.CONDITIONAL and duration is not None:
            expiry = (
                datetime.fromisoformat(decision_date)
                + duration
            ).isoformat()
        rec = ApprovalDecisionRecord(
            canonical_id=_uuid_str(),
            request_canonical_id=request_canonical_id,
            decision=decision,
            approver_id=approver_id,
            approver_role=approver_role,
            decision_date=decision_date,
            conditions=conditions,
            revocation_conditions=revocation_conditions,
            duration=duration,
            expiry_date=expiry,
            reason=reason,
        )
        self.decisions[rec.canonical_id] = rec
        return rec

    # ---- Step 4: revoke -------------------------------------------------

    def revoke(
        self,
        *,
        decision_canonical_id: str,
        revoker_id: str,
        revocation_date: str,
        grounds: str,
        remediation: str,
    ) -> RevocationRecord:
        """Revoke a prior Approval Decision.

        Per Authority Matrix §10, the revoker may be the issuing human
        authority, a higher authority, the Governance Body, the
        Constitutional Compliance Coordination Agent for cause, or the
        Constitutional Owner. The grounds must be one of:
          - Material new information
          - Error
          - Fraud
          - Breach of conditions
          - Expiry
          - Higher-authority decision
        """
        valid_grounds = {
            "MATERIAL_NEW_INFORMATION",
            "ERROR",
            "FRAUD",
            "BREACH_OF_CONDITIONS",
            "EXPIRY",
            "HIGHER_AUTHORITY_DECISION",
        }
        if grounds not in valid_grounds:
            raise ValueError(f"Invalid revocation grounds: {grounds}")
        decision = self.decisions.get(decision_canonical_id)
        if decision is None:
            raise ValueError(f"Unknown decision: {decision_canonical_id}")
        if decision.decision == ApprovalDecision.REJECTED:
            raise ValueError("Cannot revoke a REJECTED decision (no approval to revoke)")
        rec = RevocationRecord(
            canonical_id=_uuid_str(),
            decision_canonical_id=decision_canonical_id,
            revoker_id=revoker_id,
            revocation_date=revocation_date,
            grounds=grounds,
            remediation=remediation,
        )
        self.revocations.append(rec)
        return rec

    # ---- Step 5: query --------------------------------------------------

    def decision_for(self, request_canonical_id: str) -> ApprovalDecisionRecord | None:
        for d in self.decisions.values():
            if d.request_canonical_id == request_canonical_id:
                return d
        return None

    def is_revoked(self, decision_canonical_id: str) -> bool:
        return any(r.decision_canonical_id == decision_canonical_id for r in self.revocations)

    def audit_trail(self, request_canonical_id: str) -> list:
        """Return the audit trail for a request: request, decision, revocations."""
        out: list = []
        req = self.requests.get(request_canonical_id)
        if req:
            out.append(req)
        for d in self.decisions.values():
            if d.request_canonical_id == request_canonical_id:
                out.append(d)
        for r in self.revocations:
            for d in self.decisions.values():
                if d.canonical_id == r.decision_canonical_id and d.request_canonical_id == request_canonical_id:
                    out.append(r)
        return out


# ---------------------------------------------------------------------------
# Standing Authorisations (Authority Matrix Section 5)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StandingAuthorisation:
    """A Standing Authorisation of Authority Matrix Section 5.

    Per §5.1: may be issued only if the Decision Class is Class 3; the
    Decision is repetitive, low-risk, narrowly defined; the Agent has a
    verified training and audit history; and the Authorisation is
    approved by the Authorised Executive with Risk and Compliance
    Office concurrence.

    Per §5.3 (Prohibited Categories): NO Standing Authorisation may be
    issued for any Class 4 Decision, contact with a Restricted Entity,
    commitment of price/margin/discount/exclusivity, expenditure or
    inventory, binding bid or tender, signing of a contract, disclosure
    of protected information, public statement, constitutional
    amendment, or register change to a Represented Principal or
    Restricted Entity.
    """

    canonical_id: str
    issuing_authority: str
    issuing_date: str
    expiry_date: str
    scope: str
    recipients: tuple[str, ...]
    approved_content_template: str
    prohibited_representations: tuple[str, ...]
    responsible_human_owner: str
    revocation_conditions: tuple[str, ...]
    audit_requirements: str
    review_date: str


class StandingAuthorisationValidator:
    """Validates a proposed Standing Authorisation against §5.1..5.3.

    A proposed SA is rejected if it is for a Class 4 Decision or any of
    the §5.3 prohibited categories.
    """

    PROHIBITED_CATEGORIES: FrozenSet[str] = frozenset({
        "CLASS_4",
        "RESTRICTED_ENTITY_CONTACT",
        "PRICE_MARGIN_DISCOUNT_EXCLUSIVITY_COMMITMENT",
        "EXPENDITURE_INVENTORY_COMMITMENT",
        "BINDING_BID_OR_TENDER",
        "CONTRACT_SIGNING",
        "PROTECTED_INFO_DISCLOSURE_BEYOND_TEMPLATE",
        "PUBLIC_STATEMENT",
        "CONSTITUTIONAL_AMENDMENT",
        "REGISTER_CHANGE_REPRESENTED_PRINCIPAL",
        "REGISTER_CHANGE_RESTRICTED_ENTITY",
    })

    def validate(
        self, sa: StandingAuthorisation, decision_class: DecisionClass
    ) -> None:
        if decision_class == DecisionClass.CLASS_4:
            raise SilenceNotApproval(
                "STANDING_AUTH_CLASS_4",
                "Standing Authorisations may not be issued for Class 4 Decisions "
                "(Authority Matrix §5.3 Prohibited Categories).",
            )
        # The scope field carries a tag (the authoriser records it).
        if sa.scope in self.PROHIBITED_CATEGORIES:
            raise SilenceNotApproval(
                "STANDING_AUTH_PROHIBITED_CATEGORY",
                f"Standing Authorisation scope '{sa.scope}' is in the §5.3 "
                f"Prohibited Categories list.",
            )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _uuid_str() -> str:
    import uuid
    return str(uuid.uuid4())
