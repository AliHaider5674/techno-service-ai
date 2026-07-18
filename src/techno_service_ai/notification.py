"""Notification Engine — Document 06 Section 9 + UI/UX §10.

Implements the Notification Engine:

  - 6 Categories: Alerts, Approvals, Escalations, Reminders, Workflow
    Changes, AI Notifications.
  - 5 Channels: in-app, push, email, SMS (Class 3 and Class 4 only),
    voice (Emergency only).
  - Priority order: Class 4 > Class 3 > Class 2 > Class 1 > Operational
    > Informational. (Constitution Articles XII, XIII, XIV; Authority
    Matrix; REQ-FN-NOT-002, REQ-APR-002)
  - Audit: every issuance, delivery, acknowledgement, dismissal,
    suppression is recorded.
  - Suppression of Class 3/4 notifications is FORBIDDEN (Constitution
    Article XVII paragraph 7, REQ-FN-NOT-006, REQ-RULE-005).

This is a pure-logic module with NO database coupling.

Constitutional source:
  - Constitution Article XVII
  - Document 06 §9
  - UI/UX §10 (NOT-001..NOT-005)
  - AC-P3-006 (Notification: created, delivered, acknowledged)
  - REQ-FN-NOT-001..009
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import FrozenSet, Mapping


# ---------------------------------------------------------------------------
# Categories (6) and Channels (5) — Document 06 §9
# ---------------------------------------------------------------------------


class NotificationCategory(str, Enum):
    """The 6 notification categories."""

    ALERT = "ALERT"
    APPROVAL = "APPROVAL"
    ESCALATION = "ESCALATION"
    REMINDER = "REMINDER"
    WORKFLOW_CHANGE = "WORKFLOW_CHANGE"
    AI_NOTIFICATION = "AI_NOTIFICATION"


class NotificationChannel(str, Enum):
    """The 5 notification channels."""

    IN_APP = "IN_APP"
    PUSH = "PUSH"
    EMAIL = "EMAIL"
    SMS = "SMS"           # Class 3 and Class 4 only
    VOICE = "VOICE"       # Emergency only


class NotificationPriority(str, Enum):
    """The constitutional priority order.

    Lower number = higher priority. The order in the enum is the
    canonical sort order.
    """

    CLASS_4 = "CLASS_4"                  # 0 (highest)
    CLASS_3 = "CLASS_3"                  # 1
    CLASS_2 = "CLASS_2"                  # 2
    CLASS_1 = "CLASS_1"                  # 3
    OPERATIONAL = "OPERATIONAL"          # 4
    INFORMATIONAL = "INFORMATIONAL"      # 5 (lowest)


# Priority order: a list of (priority, rank) — the sort key for the
# priority order is the rank.
PRIORITY_RANK: Mapping[NotificationPriority, int] = {
    NotificationPriority.CLASS_4: 0,
    NotificationPriority.CLASS_3: 1,
    NotificationPriority.CLASS_2: 2,
    NotificationPriority.CLASS_1: 3,
    NotificationPriority.OPERATIONAL: 4,
    NotificationPriority.INFORMATIONAL: 5,
}


# Channel eligibility:
#   - SMS is reserved for Class 3 and Class 4
#   - VOICE is reserved for Emergency
# Per UI/UX §10 NOT-* and Document 06 §9.
SMS_ELIGIBLE_PRIORITIES: FrozenSet[NotificationPriority] = frozenset({
    NotificationPriority.CLASS_3,
    NotificationPriority.CLASS_4,
})

# VOICE is reserved for Emergency — encoded as a special category
# (Emergency == ESCALATION with channel=VOICE is the only allowed
# combination).
VOICE_RESERVED_FOR: FrozenSet[str] = frozenset({"EMERGENCY"})


# ---------------------------------------------------------------------------
# Notification record
# ---------------------------------------------------------------------------


class NotificationStatus(str, Enum):
    ISSUED = "ISSUED"
    DELIVERED = "DELIVERED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    DISMISSED = "DISMISSED"
    SUPPRESSED = "SUPPRESSED"  # only for non-Class-3/4


@dataclass(frozen=True)
class Notification:
    canonical_id: str
    recipient_id: str
    category: NotificationCategory
    priority: NotificationPriority
    channel: NotificationChannel
    subject: str
    body: str
    issued_at: str
    delivered_at: str | None = None
    acknowledged_at: str | None = None
    dismissed_at: str | None = None
    status: NotificationStatus = NotificationStatus.ISSUED


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class SuppressionForbidden(Exception):
    """A suppression of a Class 3 or Class 4 notification was REJECTED.

    Per Constitution Article XVII paragraph 7, REQ-FN-NOT-006,
    REQ-RULE-005: suppression of Class 3/4 notifications is FORBIDDEN.
    """

    def __init__(self, priority: NotificationPriority) -> None:
        self.priority = priority
        super().__init__(
            f"Suppression of {priority.value} notification is FORBIDDEN. "
            f"Per Constitution Article XVII paragraph 7, REQ-FN-NOT-006, "
            f"and REQ-RULE-005, Class 3 and Class 4 notifications cannot "
            f"be suppressed."
        )


class ChannelIneligible(Exception):
    """A channel is not eligible for the given priority."""

    def __init__(self, channel: NotificationChannel, priority: NotificationPriority) -> None:
        self.channel = channel
        self.priority = priority
        super().__init__(
            f"Channel {channel.value} is not eligible for priority {priority.value}. "
            f"SMS is reserved for Class 3 / Class 4. Voice is reserved for Emergency."
        )


# ---------------------------------------------------------------------------
# Notification Engine
# ---------------------------------------------------------------------------


class NotificationEngine:
    """Pure-logic notification engine.

    Methods:
      - issue: create and validate a notification
      - deliver: mark a notification as delivered
      - acknowledge: mark a notification as acknowledged
      - dismiss: mark a notification as dismissed
      - suppress: REJECTED for Class 3/4
      - priority_queue: sort a list of notifications by priority order
    """

    def __init__(self) -> None:
        self.notifications: dict[str, Notification] = {}
        self.audit: list[dict] = []
        self.suppression_attempts: list[SuppressionForbidden] = []

    # ---- issue --------------------------------------------------------

    def issue(
        self,
        *,
        recipient_id: str,
        category: NotificationCategory,
        priority: NotificationPriority,
        channel: NotificationChannel,
        subject: str,
        body: str,
        issued_at: str = "",
        canonical_id: str = "",
    ) -> Notification:
        """Create a Notification. Validates channel eligibility."""
        self._validate_channel(channel, priority, category)
        n = Notification(
            canonical_id=canonical_id or _uuid_str(),
            recipient_id=recipient_id,
            category=category,
            priority=priority,
            channel=channel,
            subject=subject,
            body=body,
            issued_at=issued_at or _now_iso(),
            status=NotificationStatus.ISSUED,
        )
        self.notifications[n.canonical_id] = n
        self.audit.append({"event": "ISSUED", "id": n.canonical_id, "category": category.value, "priority": priority.value, "channel": channel.value})
        return n

    def _validate_channel(
        self, channel: NotificationChannel, priority: NotificationPriority, category: NotificationCategory
    ) -> None:
        if channel == NotificationChannel.SMS and priority not in SMS_ELIGIBLE_PRIORITIES:
            raise ChannelIneligible(channel, priority)
        if channel == NotificationChannel.VOICE and category.value != "EMERGENCY":
            raise ChannelIneligible(channel, priority)

    # ---- deliver / acknowledge / dismiss / suppress --------------------

    def deliver(self, canonical_id: str, delivered_at: str = "") -> Notification:
        n = self._get(canonical_id)
        n2 = _replace(n, status=NotificationStatus.DELIVERED, delivered_at=delivered_at or _now_iso())
        self.notifications[canonical_id] = n2
        self.audit.append({"event": "DELIVERED", "id": canonical_id})
        return n2

    def acknowledge(self, canonical_id: str, acknowledged_at: str = "") -> Notification:
        n = self._get(canonical_id)
        n2 = _replace(n, status=NotificationStatus.ACKNOWLEDGED, acknowledged_at=acknowledged_at or _now_iso())
        self.notifications[canonical_id] = n2
        self.audit.append({"event": "ACKNOWLEDGED", "id": canonical_id})
        return n2

    def dismiss(self, canonical_id: str, dismissed_at: str = "") -> Notification:
        n = self._get(canonical_id)
        n2 = _replace(n, status=NotificationStatus.DISMISSED, dismissed_at=dismissed_at or _now_iso())
        self.notifications[canonical_id] = n2
        self.audit.append({"event": "DISMISSED", "id": canonical_id})
        return n2

    def suppress(self, canonical_id: str, reason: str) -> Notification:
        """Suppress a notification. REJECTED for Class 3 / Class 4."""
        n = self._get(canonical_id)
        if n.priority in (NotificationPriority.CLASS_3, NotificationPriority.CLASS_4):
            err = SuppressionForbidden(n.priority)
            self.suppression_attempts.append(err)
            raise err
        n2 = _replace(n, status=NotificationStatus.SUPPRESSED)
        self.notifications[canonical_id] = n2
        self.audit.append({"event": "SUPPRESSED", "id": canonical_id, "reason": reason})
        return n2

    # ---- priority queue -----------------------------------------------

    def priority_queue(self, recipient_id: str | None = None) -> list[Notification]:
        """Return the priority-ordered queue, optionally filtered by recipient."""
        items = list(self.notifications.values())
        if recipient_id is not None:
            items = [n for n in items if n.recipient_id == recipient_id]
        # Constitutional priority: Class 4 (rank 0) > Class 3 > Class 2 >
        # Class 1 > Operational > Informational.
        return sorted(items, key=lambda n: (PRIORITY_RANK[n.priority], n.issued_at))

    # ---- helpers -------------------------------------------------------

    def _get(self, canonical_id: str) -> Notification:
        n = self.notifications.get(canonical_id)
        if n is None:
            raise ValueError(f"Unknown notification: {canonical_id}")
        return n

    def by_recipient(self, recipient_id: str) -> list[Notification]:
        return [n for n in self.notifications.values() if n.recipient_id == recipient_id]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _uuid_str() -> str:
    import uuid
    return str(uuid.uuid4())


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _replace(n: Notification, **kwargs) -> Notification:
    """Return a new Notification with the given fields replaced.

    dataclasses.replace is the standard way, but kept explicit to avoid
    an extra import.
    """
    from dataclasses import replace
    return replace(n, **kwargs)
