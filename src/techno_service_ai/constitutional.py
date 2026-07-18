"""Constitutional primitives shared by every canonical entity.

This module defines:

  - The three Status dimensions (Constitution Article XIX).
  - The ConstitutionalRecord mixin used by every canonical entity.
  - The base class for Constitutional Register entries (Article VIII).
  - The three Status enums and the Independence helpers.

Per Constitution Article XX paragraph 6 and DB-PRIN-018, every record
in a constitutional table is append-only. "Update" is implemented by
INSERTing a new versioned row (same `canonical_id`, new `version`).
Per Article XIX, the three Status dimensions are independent: each
Opportunity-shaped entity has its own columns for Intelligence, Approval,
and Commercial status; no trigger or view derives one from another.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    DateTime,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Three Status dimensions (Constitution Article XIX)
# ---------------------------------------------------------------------------
# Each status is a separate writeable column. The Independence rule
# (DB-PRIN-014) says: no status dimension shall be treated as a
# replacement for another. We enforce this at the data layer by storing
# each as an independent column on the relevant entities, with no
# triggers or computed columns that couple them.


class IntelligenceStatus(str, enum.Enum):
    """Constitution Article XIX §2."""

    SIGNAL_DETECTED = "SIGNAL_DETECTED"
    UNDER_INVESTIGATION = "UNDER_INVESTIGATION"
    PROBLEM_OR_NEED_CONFIRMED = "PROBLEM_OR_NEED_CONFIRMED"
    VALUE_HYPOTHESIS = "VALUE_HYPOTHESIS"
    VALUE_CASE_ESTABLISHED = "VALUE_CASE_ESTABLISHED"
    RESEARCH_ACTIVE = "RESEARCH_ACTIVE"
    VERIFICATION_PENDING = "VERIFICATION_PENDING"
    QUALIFIED = "QUALIFIED"
    CONDITIONALLY_QUALIFIED = "CONDITIONALLY_QUALIFIED"
    REJECTED = "REJECTED"
    ON_HOLD = "ON_HOLD"
    MONITORING = "MONITORING"


class ApprovalStatus(str, enum.Enum):
    """Constitution Article XIX §3."""

    NOT_SUBMITTED = "NOT_SUBMITTED"
    AWAITING_HUMAN_REVIEW = "AWAITING_HUMAN_REVIEW"
    APPROVED_FOR_FURTHER_ANALYSIS = "APPROVED_FOR_FURTHER_ANALYSIS"
    APPROVED_FOR_CONTACT = "APPROVED_FOR_CONTACT"
    APPROVED_WITH_CONDITIONS = "APPROVED_WITH_CONDITIONS"
    REJECTED_BY_HUMAN_AUTHORITY = "REJECTED_BY_HUMAN_AUTHORITY"
    APPROVAL_EXPIRED = "APPROVAL_EXPIRED"
    APPROVAL_WITHDRAWN = "APPROVAL_WITHDRAWN"


class CommercialStatus(str, enum.Enum):
    """Constitution Article XIX §4."""

    MANUFACTURER_IDENTIFICATION = "MANUFACTURER_IDENTIFICATION"
    MANUFACTURER_CONTACTED = "MANUFACTURER_CONTACTED"
    UNDER_DISCUSSION = "UNDER_DISCUSSION"
    COMMERCIAL_MODEL_REVIEW = "COMMERCIAL_MODEL_REVIEW"
    CUSTOMER_MAPPING = "CUSTOMER_MAPPING"
    CUSTOMER_ENGAGEMENT = "CUSTOMER_ENGAGEMENT"
    REGISTRATION = "REGISTRATION"
    PILOT_PREPARATION = "PILOT_PREPARATION"
    PILOT_ACTIVE = "PILOT_ACTIVE"
    TENDER_OR_QUOTATION = "TENDER_OR_QUOTATION"
    NEGOTIATION = "NEGOTIATION"
    AGREEMENT = "AGREEMENT"
    IMPLEMENTATION = "IMPLEMENTATION"
    AFTER_SALES = "AFTER_SALES"
    EXPANSION_OR_RENEWAL = "EXPANSION_OR_RENEWAL"
    WON = "WON"
    LOST = "LOST"
    CLOSED = "CLOSED"


# ---------------------------------------------------------------------------
# Constitutional Record mixin
# ---------------------------------------------------------------------------
# Every constitutional entity is versioned. The `id` is a per-row UUID
# (immutable). The `canonical_id` is stable across versions of the same
# logical entity. The `version` is monotonic within a canonical_id. The
# "current" record for a canonical_id is the row with the highest version.
#
# This mixin is paired with no-silent-amendment triggers (BEFORE UPDATE
# and BEFORE DELETE RAISE(ABORT)) installed by `db.apply_schema`.


class ConstitutionalMixin:
    """Mixin: every constitutional entity carries these fields."""

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    canonical_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    created_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    # The following fields are tracked but the table is append-only, so they
    # are recorded as fields on the NEW row (the OLD row is left intact).
    source_citation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # For traceability: which prior version this one supersedes.
    previous_version_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
