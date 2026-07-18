"""Escalation Engine — Document 06 §3.7.

Implements the Escalation Engine with the 6 channels of Interaction
Matrix Section 7:

  - Normal
  - Constitutional
  - Commercial
  - Verification
  - Human
  - Emergency

Every escalation records: trigger, route, recipient, response window,
outcome (ORCH-ESC-003). Unacknowledged escalations are escalated
further (ORCH-ESC-004, ORCH-WAIT-003).

This is a pure-logic module.

Constitutional source:
  - Constitution Article XII, Article XVIII
  - Document 06 §3.7 (ORCH-ESC-001..004)
  - Interaction Matrix Section 7
  - REQ-FN-EXE-003
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional


class EscalationChannel(str, Enum):
    """The 6 escalation channels of Interaction Matrix Section 7."""

    NORMAL = "NORMAL"
    CONSTITUTIONAL = "CONSTITUTIONAL"
    COMMERCIAL = "COMMERCIAL"
    VERIFICATION = "VERIFICATION"
    HUMAN = "HUMAN"
    EMERGENCY = "EMERGENCY"


# Channel priority order: lower number = higher priority.
# Emergency overrides Normal (ORCH-ESC-004) but never overrides the
# Constitution (Constitution Article XVIII).
CHANNEL_PRIORITY_RANK: dict[EscalationChannel, int] = {
    EscalationChannel.EMERGENCY: 0,
    EscalationChannel.CONSTITUTIONAL: 1,
    EscalationChannel.HUMAN: 2,
    EscalationChannel.VERIFICATION: 3,
    EscalationChannel.COMMERCIAL: 4,
    EscalationChannel.NORMAL: 5,
}


# Channels in escalation order (when unacknowledged, escalate to the
# NEXT channel in this list, which has higher priority). The list is
# the "promotion" order.
PROMOTION_ORDER: tuple[EscalationChannel, ...] = (
    EscalationChannel.NORMAL,
    EscalationChannel.COMMERCIAL,
    EscalationChannel.VERIFICATION,
    EscalationChannel.HUMAN,
    EscalationChannel.CONSTITUTIONAL,
    EscalationChannel.EMERGENCY,
)


class EscalationStatus(str, Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"
    EXPIRED = "EXPIRED"


@dataclass
class Escalation:
    canonical_id: str
    channel: EscalationChannel
    trigger: str
    route: str
    recipient: str
    response_window: timedelta
    raised_at: str
    acknowledged_at: str | None = None
    resolved_at: str | None = None
    outcome: str = ""
    status: EscalationStatus = EscalationStatus.OPEN
    # Promotion chain: the chain of escalated-from canonical_ids,
    # if this escalation is the result of an unacknowledged prior one.
    promoted_from: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class EscalationError(Exception):
    """Generic escalation error."""


# ---------------------------------------------------------------------------
# Escalation Engine
# ---------------------------------------------------------------------------


class EscalationEngine:
    """Pure-logic escalation engine.

    Methods:
      - raise_escalation: create an escalation
      - acknowledge: mark as acknowledged
      - resolve: mark as resolved
      - check_unacknowledged_and_promote: scan the queue; any OPEN
        escalations past their response window are PROMOTED to the
        next channel in the constitutional priority order.
    """

    def __init__(self) -> None:
        self.escalations: dict[str, Escalation] = {}
        self.audit: list[dict] = []

    def raise_escalation(
        self,
        *,
        channel: EscalationChannel,
        trigger: str,
        route: str,
        recipient: str,
        response_window: timedelta,
        raised_at: str = "",
        promoted_from: list[str] | None = None,
        canonical_id: str = "",
    ) -> Escalation:
        """Create an escalation."""
        e = Escalation(
            canonical_id=canonical_id or _uuid_str(),
            channel=channel,
            trigger=trigger,
            route=route,
            recipient=recipient,
            response_window=response_window,
            raised_at=raised_at or _now_iso(),
            promoted_from=list(promoted_from) if promoted_from else [],
        )
        self.escalations[e.canonical_id] = e
        self.audit.append(
            {
                "event": "RAISED",
                "id": e.canonical_id,
                "channel": channel.value,
                "trigger": trigger,
                "recipient": recipient,
            }
        )
        return e

    def acknowledge(self, canonical_id: str, acknowledged_at: str = "") -> Escalation:
        e = self._get(canonical_id)
        e.acknowledged_at = acknowledged_at or _now_iso()
        e.status = EscalationStatus.ACKNOWLEDGED
        self.audit.append({"event": "ACKNOWLEDGED", "id": canonical_id})
        return e

    def resolve(self, canonical_id: str, outcome: str, resolved_at: str = "") -> Escalation:
        e = self._get(canonical_id)
        e.resolved_at = resolved_at or _now_iso()
        e.outcome = outcome
        e.status = EscalationStatus.RESOLVED
        self.audit.append({"event": "RESOLVED", "id": canonical_id, "outcome": outcome})
        return e

    def open_escalations(self) -> list[Escalation]:
        return [e for e in self.escalations.values() if e.status == EscalationStatus.OPEN]

    def promote_unacknowledged(
        self,
        *,
        now: datetime | None = None,
        trigger: str = "Unacknowledged escalation: response window exceeded",
    ) -> list[Escalation]:
        """Promote OPEN escalations past their response window.

        Per ORCH-ESC-004 and ORCH-WAIT-003, unacknowledged escalations
        are escalated to a higher authority (the next channel in the
        constitutional priority order).

        Returns the new escalations created.
        """
        now = now or datetime.now(timezone.utc)
        new: list[Escalation] = []
        for e in self.open_escalations():
            raised = datetime.fromisoformat(e.raised_at)
            if raised + e.response_window <= now:
                next_channel = _next_channel_in_priority(e.channel)
                if next_channel is None:
                    # Already at the top; mark EXPIRED
                    e.status = EscalationStatus.EXPIRED
                    self.audit.append({"event": "EXPIRED", "id": e.canonical_id, "reason": "top of priority order; no further promotion"})
                    continue
                promoted = self.raise_escalation(
                    channel=next_channel,
                    trigger=trigger,
                    route=e.route,
                    recipient=_higher_authority(e.recipient),
                    response_window=_shorter_window(e.response_window),
                    promoted_from=e.promoted_from + [e.canonical_id],
                )
                new.append(promoted)
        return new


def _next_channel_in_priority(c: EscalationChannel) -> EscalationChannel | None:
    """Return the next channel with HIGHER priority (lower rank number)."""
    rank = CHANNEL_PRIORITY_RANK[c]
    for nc in PROMOTION_ORDER:
        if CHANNEL_PRIORITY_RANK[nc] < rank:
            return nc
    return None  # already at the top


def _higher_authority(recipient: str) -> str:
    """Return a placeholder for a higher authority than the current recipient.

    In production this would consult the Authority Matrix; for pure
    logic tests, we append '+1' to the recipient string.
    """
    return f"{recipient}+1"


def _shorter_window(window: timedelta) -> timedelta:
    """Half the window for the next promotion (urgency increases)."""
    return max(timedelta(minutes=1), window / 2)


def _uuid_str() -> str:
    import uuid
    return str(uuid.uuid4())


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
