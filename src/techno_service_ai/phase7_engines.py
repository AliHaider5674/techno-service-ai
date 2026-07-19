"""Phase 7 Engines — Reporting, Notification, Risk, Performance.

Combined engine module for Phase 7. The 7 Offices activated in
Phase 7 are mostly coordination / monitoring / reporting. The
core engine logic is concentrated in:

  - ReportingEngine — Constitutional Compliance Attestation, Claim
    Classification, Verification references, source citations,
    freshness date.
  - NotificationEngine — 6 categories × 5 channels, priority order,
    suppression rules (Class 3/4 is FORBIDDEN to suppress).
  - RiskComplianceEngine — Risk register, Compliance monitoring,
    Register Steward, Constitutional Incident investigation.
  - PerformanceEngine — KPIs, trends, bottlenecks, SLA, office
    workload.

The remaining offices (Security/Data Governance, Relationship
Management, Executive AI) are pure coordination — their logic is
delegated to the engines above plus the existing Phase 3-6
infrastructure.

Constitutional source:
  - Document 02 §4.11, §4.12, §4.14, §4.15, §4.16, §4.17
  - Document 06 §9 (Notification), §4.9 (Closure), §3.7 (Escalation)
  - Constitution Article XII (Human Approval)
  - Constitution Article XX (Audit completeness)
  - Constitution Article XXV (Security / Data Governance)
  - Constitution Article XXVIII (Document Hierarchy)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple


# ===========================================================================
# Reporting Engine (§4.15)
# ===========================================================================


class ReportType(str, Enum):
    EXECUTIVE = "EXECUTIVE"
    OPERATIONAL = "OPERATIONAL"
    COMPLIANCE = "COMPLIANCE"
    COMMERCIAL = "COMMERCIAL"
    BOARD = "BOARD"


class ReportFreshnessClass(str, Enum):
    """The freshness class of a Report.

    Per Document 02 §4.15.1 the freshness date is REQUIRED on every
    Report.
    """

    REAL_TIME = "REAL_TIME"
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    ANNUAL = "ANNUAL"
    AD_HOC = "AD_HOC"


class ClaimClassification(str, Enum):
    """The Claim Classification of every report claim.

    Per Document 02 §4.15.5 and Constitution Article XXIII, every
    report claim is classified as one of these."""

    FACT = "FACT"
    INFERENCE = "INFERENCE"
    PROJECTION = "PROJECTION"
    RECOMMENDATION = "RECOMMENDATION"
    UNVERIFIED = "UNVERIFIED"


class ComplianceAttestationOutcome(str, Enum):
    """The outcome of a Constitutional Compliance Attestation.

    Per Document 02 §4.15.2 and AC-P7-006, every Report carries a
    Constitutional Compliance Attestation. The attestation may be
    COMPLIANT, COMPLIANT_WITH_QUALIFICATIONS, NON_COMPLIANT, or
    PENDING_REVIEW.
    """

    COMPLIANT = "COMPLIANT"
    COMPLIANT_WITH_QUALIFICATIONS = "COMPLIANT_WITH_QUALIFICATIONS"
    NON_COMPLIANT = "NON_COMPLIANT"
    PENDING_REVIEW = "PENDING_REVIEW"


@dataclass(frozen=True)
class ReportClaim:
    """A single claim within a Report.

    Per AC-P7-006 every Report must carry a Claim Classification,
    Verification references where material, and source citations.
    """

    claim_text: str
    classification: ClaimClassification
    source_citation: str
    verification_reference: Optional[str] = None  # Required for MATERIAL claims


@dataclass(frozen=True)
class ReportSpec:
    """The input spec for a Report."""

    report_type: ReportType
    title: str
    body: str
    freshness_date: str
    freshness_class: ReportFreshnessClass = ReportFreshnessClass.AD_HOC
    claims: Tuple[ReportClaim, ...] = ()


@dataclass(frozen=True)
class ComplianceAttestation:
    """The Constitutional Compliance Attestation on a Report.

    Per AC-P7-006 — every Report must carry one of these.
    """

    outcome: ComplianceAttestationOutcome
    attestation_text: str
    attestor_id: str
    attestor_role: str
    attested_at: str


@dataclass(frozen=True)
class ReportResult:
    """The result of a Report validation + attestation."""

    report_type: ReportType
    title: str
    body: str
    freshness_date: str
    freshness_class: ReportFreshnessClass
    claims: Tuple[ReportClaim, ...]
    attestation: ComplianceAttestation
    material_claims_count: int
    unverified_claims_count: int


class ReportingEngineError(Exception):
    """Base for reporting engine errors."""


class ReportMissingFreshnessError(ReportingEngineError):
    """A Report without a freshness_date is REJECTED."""

    def __init__(self) -> None:
        super().__init__(
            f"Report REJECTED: missing freshness_date. Per Document 02 "
            f"§4.15.1, every Report must carry a freshness date."
        )


class ReportMissingClaimSourceError(ReportingEngineError):
    """A Report claim without a source citation is REJECTED."""

    def __init__(self) -> None:
        super().__init__(
            f"Report REJECTED: at least one claim is missing the source "
            f"citation. Per Document 02 §4.15.1 and Constitution Article "
            f"X, every claim must be sourced."
        )


class MaterialClaimWithoutVerificationError(ReportingEngineError):
    """A MATERIAL claim (FACT / INFERENCE / PROJECTION) without a
    Verification reference is REJECTED."""

    def __init__(self) -> None:
        super().__init__(
            f"Report REJECTED: a MATERIAL claim (FACT / INFERENCE / "
            f"PROJECTION) is missing a Verification reference. Per "
            f"Document 02 §4.15.2 and Constitution Article XVII, every "
            f"material claim must carry a Verification reference."
        )


MATERIAL_CLAIM_CATEGORIES = frozenset(
    {ClaimClassification.FACT, ClaimClassification.INFERENCE, ClaimClassification.PROJECTION}
)


class ReportingEngine:
    """The Reporting Engine — Document 02 §4.15."""

    def validate_report(self, spec: ReportSpec) -> ReportResult:
        """Validate a Report spec.

        Enforces:
          - freshness_date is set.
          - Every claim has a source citation.
          - Every MATERIAL claim has a Verification reference.
          - The unverified_claims_count is reported.
        """
        if not spec.freshness_date or not spec.freshness_date.strip():
            raise ReportMissingFreshnessError()
        if not spec.claims:
            raise ReportMissingClaimSourceError()

        # Per-claim validation
        for claim in spec.claims:
            if not claim.source_citation or not claim.source_citation.strip():
                raise ReportMissingClaimSourceError()
            if (
                claim.classification in MATERIAL_CLAIM_CATEGORIES
                and (
                    not claim.verification_reference
                    or not claim.verification_reference.strip()
                )
            ):
                raise MaterialClaimWithoutVerificationError()

        material_count = sum(
            1 for c in spec.claims if c.classification in MATERIAL_CLAIM_CATEGORIES
        )
        unverified_count = sum(
            1 for c in spec.claims if c.classification == ClaimClassification.UNVERIFIED
        )

        # Build the attestation. The default is COMPLIANT; the
        # caller (service layer) may override to NON_COMPLIANT if
        # an incident is found.
        attestation = ComplianceAttestation(
            outcome=ComplianceAttestationOutcome.COMPLIANT,
            attestation_text=(
                f"Report carries {len(spec.claims)} claims ({material_count} "
                f"material, {unverified_count} unverified). All material "
                f"claims carry Verification references; all claims carry "
                f"source citations. Constitutional compliance verified."
            ),
            attestor_id="system",
            attestor_role="CONSTITUTIONAL_COMPLIANCE_COORDINATOR",
            attested_at=spec.freshness_date,
        )

        return ReportResult(
            report_type=spec.report_type,
            title=spec.title,
            body=spec.body,
            freshness_date=spec.freshness_date,
            freshness_class=spec.freshness_class,
            claims=spec.claims,
            attestation=attestation,
            material_claims_count=material_count,
            unverified_claims_count=unverified_count,
        )

    def non_compliant_attestation(
        self, spec: ReportSpec, attestor_id: str, attestor_role: str, reason: str
    ) -> ComplianceAttestation:
        """Build a NON_COMPLIANT attestation. Used when a Compliance
        Incident is found after the report was issued."""
        return ComplianceAttestation(
            outcome=ComplianceAttestationOutcome.NON_COMPLIANT,
            attestation_text=f"NON_COMPLIANT: {reason}",
            attestor_id=attestor_id,
            attestor_role=attestor_role,
            attested_at=spec.freshness_date,
        )


# ===========================================================================
# Notification Engine (§4.16)
# ===========================================================================


class NotificationCategory(str, Enum):
    """The 6 Notification categories per Document 02 §4.16.1."""

    ALERTS = "ALERTS"
    APPROVALS = "APPROVALS"
    ESCALATIONS = "ESCALATIONS"
    REMINDERS = "REMINDERS"
    WORKFLOW_CHANGES = "WORKFLOW_CHANGES"
    AI_NOTIFICATIONS = "AI_NOTIFICATIONS"


class NotificationChannel(str, Enum):
    """The 5 Notification channels per Document 02 §4.16.1."""

    IN_APP = "IN_APP"
    PUSH = "PUSH"
    EMAIL = "EMAIL"
    SMS = "SMS"
    VOICE = "VOICE"


class NotificationPriority(str, Enum):
    """The priority order per Document 02 §4.16.1.

    Class 4 → Class 3 → Class 2 → Class 1 → Operational → Informational.
    """

    CLASS_4 = 4
    CLASS_3 = 3
    CLASS_2 = 2
    CLASS_1 = 1
    OPERATIONAL = 0
    INFORMATIONAL = -1


PRIORITY_ORDER = [
    NotificationPriority.CLASS_4,
    NotificationPriority.CLASS_3,
    NotificationPriority.CLASS_2,
    NotificationPriority.CLASS_1,
    NotificationPriority.OPERATIONAL,
    NotificationPriority.INFORMATIONAL,
]


@dataclass(frozen=True)
class NotificationSpec:
    """A Notification spec."""

    category: NotificationCategory
    priority: NotificationPriority
    subject: str
    body: str
    target_user_id: str
    channels: Tuple[NotificationChannel, ...] = (NotificationChannel.IN_APP,)
    suppressed: bool = False  # Class 3/4 cannot be suppressed


@dataclass(frozen=True)
class NotificationResult:
    """The result of a Notification routing."""

    category: NotificationCategory
    priority: NotificationPriority
    subject: str
    body: str
    target_user_id: str
    channels: Tuple[NotificationChannel, ...]
    delivered: bool
    suppression_violation: bool  # True if a Class 3/4 was suppressed


class NotificationEngineError(Exception):
    """Base for notification engine errors."""


class SuppressionForbiddenError(NotificationEngineError):
    """Suppression of a Class 3 or Class 4 notification is REJECTED.

    Per Document 02 §4.16.3 (Alert Fatigue Controller) and AC-P7-003,
    suppression of Class 3 or Class 4 notifications is FORBIDDEN.
    """

    def __init__(self, priority: NotificationPriority) -> None:
        self.priority = priority
        super().__init__(
            f"Notification suppression REJECTED: {priority.name} notifications "
            f"cannot be suppressed. Per Document 02 §4.16.3 and AC-P7-003, "
            f"suppression of Class 3 or Class 4 notifications is FORBIDDEN. "
            f"Constitution Article XII requires Human Approval for Class 3/4 "
            f"actions; suppressing the notification is a silent override."
        )


class SmsReservedForClass3Or4Error(NotificationEngineError):
    """SMS channel is reserved for Class 3 / Class 4 notifications."""

    def __init__(self) -> None:
        super().__init__(
            f"Notification channel REJECTED: SMS is reserved for Class 3 / "
            f"Class 4 notifications. Per Document 02 §4.16.1 and AC-P3-006, "
            f"the SMS channel is reserved for Class 3 / Class 4 only."
        )


class VoiceReservedForEmergencyError(NotificationEngineError):
    """Voice channel is reserved for Emergency notifications."""

    def __init__(self) -> None:
        super().__init__(
            f"Notification channel REJECTED: Voice is reserved for "
            f"Emergency notifications. Per Document 02 §4.16.1, the Voice "
            f"channel is reserved for Emergency (Constitutional Incident) only."
        )


# SMS and Voice channel restrictions per Document 02 §4.16.1.
SMS_ALLOWED_PRIORITIES = frozenset(
    {NotificationPriority.CLASS_3, NotificationPriority.CLASS_4}
)
VOICE_ALLOWED_PRIORITIES = frozenset({NotificationPriority.CLASS_4})


class NotificationEngine:
    """The Notification Engine — Document 02 §4.16."""

    def route(self, spec: NotificationSpec) -> NotificationResult:
        """Route a Notification.

        Enforces:
          - SMS is reserved for Class 3 / Class 4.
          - Voice is reserved for Class 4 (Emergency).
          - Suppression of Class 3 / Class 4 is REJECTED.
        """
        # Channel eligibility
        for ch in spec.channels:
            if ch == NotificationChannel.SMS and spec.priority not in SMS_ALLOWED_PRIORITIES:
                raise SmsReservedForClass3Or4Error()
            if ch == NotificationChannel.VOICE and spec.priority not in VOICE_ALLOWED_PRIORITIES:
                raise VoiceReservedForEmergencyError()

        # Suppression check
        suppression_violation = False
        if spec.suppressed and spec.priority in (
            NotificationPriority.CLASS_3,
            NotificationPriority.CLASS_4,
        ):
            raise SuppressionForbiddenError(spec.priority)

        # Routing result
        return NotificationResult(
            category=spec.category,
            priority=spec.priority,
            subject=spec.subject,
            body=spec.body,
            target_user_id=spec.target_user_id,
            channels=spec.channels,
            delivered=True,
            suppression_violation=suppression_violation,
        )

    def priority_order(self) -> List[NotificationPriority]:
        """Return the canonical priority order."""
        return list(PRIORITY_ORDER)


# ===========================================================================
# Risk and Compliance Engine (§4.11)
# ===========================================================================


class RiskSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RiskStatus(str, Enum):
    IDENTIFIED = "IDENTIFIED"
    ASSESSED = "ASSESSED"
    MITIGATING = "MITIGATING"
    CLOSED = "CLOSED"
    ESCALATED = "ESCALATED"


class ComplianceStatus(str, Enum):
    COMPLIANT = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    AT_RISK = "AT_RISK"
    REMEDIATION_IN_PROGRESS = "REMEDIATION_IN_PROGRESS"


class ConstitutionalIncidentSeverity(str, Enum):
    """The severity of a Constitutional Incident per Article XXIII."""

    MINOR = "MINOR"
    MAJOR = "MAJOR"
    CRITICAL = "CRITICAL"


class ConstitutionalIncidentStatus(str, Enum):
    REPORTED = "REPORTED"
    UNDER_INVESTIGATION = "UNDER_INVESTIGATION"
    REMEDIATED = "REMEDIATED"
    ESCALATED_TO_HUMAN = "ESCALATED_TO_HUMAN"


@dataclass(frozen=True)
class RiskEntrySpec:
    """A Risk entry."""

    title: str
    description: str
    severity: RiskSeverity
    owner_office: str
    source_citation: str = ""


@dataclass(frozen=True)
class RiskEntryResult:
    """The result of a Risk entry validation."""

    title: str
    description: str
    severity: RiskSeverity
    status: RiskStatus
    owner_office: str
    source_citation: str
    requires_human_approval: bool


@dataclass(frozen=True)
class ConstitutionalIncidentSpec:
    """A Constitutional Incident."""

    title: str
    description: str
    severity: ConstitutionalIncidentSeverity
    affected_clause: str
    reporter_id: str
    source_citation: str = ""


@dataclass(frozen=True)
class ConstitutionalIncidentResult:
    """The result of a Constitutional Incident investigation."""

    title: str
    description: str
    severity: ConstitutionalIncidentSeverity
    affected_clause: str
    status: ConstitutionalIncidentStatus
    escalated_to_human: bool
    remediation_actions: Tuple[str, ...] = ()


class RiskComplianceEngineError(Exception):
    """Base for risk/compliance engine errors."""


class ConstitutionalIncidentWithoutReporterError(RiskComplianceEngineError):
    """A Constitutional Incident must have a reporter (the
    reporter identity is the chain-of-custody anchor)."""

    def __init__(self) -> None:
        super().__init__(
            f"Constitutional Incident REJECTED: missing reporter_id. "
            f"Per Constitution Article XX paragraph 7, every constitutional "
            f"incident must have a chain-of-custody anchor (the reporter)."
        )


class RiskEngine:
    """The Risk Engine — Document 02 §4.11.1."""

    def validate_risk(self, spec: RiskEntrySpec) -> RiskEntryResult:
        """Validate a Risk entry."""
        if not spec.title or not spec.title.strip():
            raise ValueError("title is required")
        if not spec.description or not spec.description.strip():
            raise ValueError("description is required")
        if not spec.owner_office or not spec.owner_office.strip():
            raise ValueError("owner_office is required")
        return RiskEntryResult(
            title=spec.title,
            description=spec.description,
            severity=spec.severity,
            status=RiskStatus.IDENTIFIED,
            owner_office=spec.owner_office,
            source_citation=spec.source_citation or f"Risk: {spec.title}",
            requires_human_approval=(
                spec.severity in (RiskSeverity.HIGH, RiskSeverity.CRITICAL)
            ),
        )


class ComplianceEngine:
    """The Compliance Engine — Document 02 §4.11.2."""

    def evaluate_compliance(
        self, *, office: str, status: ComplianceStatus, evidence: str
    ) -> ComplianceStatus:
        """Evaluate compliance for an Office."""
        if not office or not office.strip():
            raise ValueError("office is required")
        if not evidence or not evidence.strip():
            raise ValueError("evidence is required")
        return status


class ConstitutionalIncidentEngine:
    """The Constitutional Incident Engine — Document 02 §4.11.3."""

    CRITICAL_CLAUSES = frozenset(
        {"Article VIII", "Article XII", "Article XVII", "Article XX", "Article XXVIII"}
    )

    def investigate(
        self, spec: ConstitutionalIncidentSpec
    ) -> ConstitutionalIncidentResult:
        """Investigate a Constitutional Incident.

        Per Constitution Article XXIII, every Constitutional
        Incident must be recorded, escalated, and remediated. The
        reporter_id is the chain-of-custody anchor.
        """
        if not spec.reporter_id or not spec.reporter_id.strip():
            raise ConstitutionalIncidentWithoutReporterError()
        if not spec.title or not spec.title.strip():
            raise ValueError("title is required")
        if not spec.description or not spec.description.strip():
            raise ValueError("description is required")
        if not spec.affected_clause or not spec.affected_clause.strip():
            raise ValueError("affected_clause is required")

        # Critical clauses are escalated to human immediately.
        escalated = spec.severity == ConstitutionalIncidentSeverity.CRITICAL or (
            spec.affected_clause in self.CRITICAL_CLAUSES
        )
        status = (
            ConstitutionalIncidentStatus.ESCALATED_TO_HUMAN
            if escalated
            else ConstitutionalIncidentStatus.UNDER_INVESTIGATION
        )

        # Remediation actions: at minimum, record the incident
        # in the Decision Log. Critical incidents also require
        # Human Approval for any system change.
        actions = [
            "Record incident in Decision Log",
            f"Notify {spec.reporter_id} and the Constitutional Compliance Coordinator",
        ]
        if escalated:
            actions.append("Escalate to Human Approval (Class 4)")
        if spec.severity == ConstitutionalIncidentSeverity.CRITICAL:
            actions.append("Suspend the affected operation pending remediation")

        return ConstitutionalIncidentResult(
            title=spec.title,
            description=spec.description,
            severity=spec.severity,
            affected_clause=spec.affected_clause,
            status=status,
            escalated_to_human=escalated,
            remediation_actions=tuple(actions),
        )


# ===========================================================================
# Performance Engine (§4.17)
# ===========================================================================


class PerformanceMetricDirection(str, Enum):
    HIGHER_IS_BETTER = "HIGHER_IS_BETTER"
    LOWER_IS_BETTER = "LOWER_IS_BETTER"
    TARGET = "TARGET"


@dataclass(frozen=True)
class PerformanceMetricSpec:
    """A Performance Metric."""

    metric_name: str
    metric_value: float
    target: Optional[float] = None
    direction: PerformanceMetricDirection = PerformanceMetricDirection.HIGHER_IS_BETTER
    period_start: str = ""
    period_end: str = ""


@dataclass(frozen=True)
class PerformanceMetricResult:
    """The result of a Performance Metric evaluation."""

    metric_name: str
    metric_value: float
    target: Optional[float]
    status: str  # ON_TRACK / AT_RISK / OFF_TRACK
    delta: Optional[float]


class PerformanceEngine:
    """The Performance Engine — Document 02 §4.17.1."""

    def evaluate_metric(
        self, spec: PerformanceMetricSpec
    ) -> PerformanceMetricResult:
        """Evaluate a Performance Metric against its target.

        Returns the metric status: ON_TRACK if within 5% of target,
        AT_RISK if within 10%, OFF_TRACK otherwise.
        """
        if spec.target is None:
            return PerformanceMetricResult(
                metric_name=spec.metric_name,
                metric_value=spec.metric_value,
                target=None,
                status="UNMEASURED",
                delta=None,
            )

        delta = spec.metric_value - spec.target
        if spec.direction == PerformanceMetricDirection.HIGHER_IS_BETTER:
            ratio = spec.metric_value / spec.target if spec.target != 0 else 1.0
        elif spec.direction == PerformanceMetricDirection.LOWER_IS_BETTER:
            ratio = spec.target / spec.metric_value if spec.metric_value != 0 else 1.0
        else:  # TARGET
            ratio = 1.0 - abs(delta) / abs(spec.target) if spec.target != 0 else 1.0

        if ratio >= 0.95:
            status = "ON_TRACK"
        elif ratio >= 0.90:
            status = "AT_RISK"
        else:
            status = "OFF_TRACK"

        return PerformanceMetricResult(
            metric_name=spec.metric_name,
            metric_value=spec.metric_value,
            target=spec.target,
            status=status,
            delta=delta,
        )

    def detect_bottleneck(
        self, *, stage_name: str, avg_cycle_hours: float, threshold_hours: float
    ) -> bool:
        """Detect a workflow bottleneck.

        A stage is a bottleneck if its average cycle time exceeds
        the threshold. Returns True if a bottleneck is detected.
        """
        return avg_cycle_hours > threshold_hours

    def check_sla(
        self, *, sla_name: str, target_hours: float, actual_hours: float
    ) -> bool:
        """Check an SLA. Returns True if the SLA is met."""
        return actual_hours <= target_hours
