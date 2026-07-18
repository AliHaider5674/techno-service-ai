"""SQLAlchemy ORM models for Phase 1 — Identity, Access, and Audit.

This module is the Data Layer. Per Document 04 (Software Architecture) and
Document 05 (Database & Information Model Design) — Phase 1 implements:

  Information Domain 1 — Constitutional Reference (audit access to governing docs)
  Information Domain 2 — Identity and Access  (User, Role, Session, AccessPolicy)
  Information Domain 3 — Audit               (AuditLog, immutable)

Article XX (Knowledge, Records, Institutional Memory) requirements applied:
  - provenance, version history, no silent erasure, auditability
  - the audit_log table is append-only (enforced by triggers in `db.apply_schema`)

Article XVII (Separation of Duties) is enforced in the Service Layer; here
we only persist the necessary fields (actor_user_id, actor_role_code) so
that the SoD check is auditable after the fact.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: Optional[datetime]) -> Optional[datetime]:
    """Return a datetime that is guaranteed to be UTC-aware.

    SQLite drops timezone information on read, so datetimes loaded from
    the database are naive. This helper attaches UTC tzinfo if missing.
    """
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Enums (declared early so models can use them)
# ---------------------------------------------------------------------------


class UserStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    ARCHIVED = "ARCHIVED"


class PersonaStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"


class SessionStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    INVALIDATED = "INVALIDATED"


class DecisionClass(int, enum.Enum):
    """Per Constitution Article XII paragraphs 3-6.

    CLASS_1 = Internal Intelligence
    CLASS_2 = Qualification & Recommendation
    CLASS_3 = External Action (requires Human Approval)
    CLASS_4 = Binding / Financial / Legal / Strategic (requires Human Approval)
    """

    CLASS_1 = 1
    CLASS_2 = 2
    CLASS_3 = 3
    CLASS_4 = 4


# ---------------------------------------------------------------------------
# User, Role, Persona, Session
# ---------------------------------------------------------------------------


class User(Base):
    __tablename__ = "user"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    username: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    email: Mapped[str] = mapped_column(String(254), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[UserStatus] = mapped_column(
        SAEnum(UserStatus, name="user_status"),
        nullable=False,
        default=UserStatus.ACTIVE,
    )
    # Recovery — challenge question + answer hash. The answer is salted and
    # hashed so it can be verified but not recovered in cleartext.
    recovery_question: Mapped[str] = mapped_column(String(255), nullable=False)
    recovery_answer_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    created_by: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("user.id"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_by: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("user.id"), nullable=True)
    # Version for the no-silent-amendment principle — every UPDATE bumps this.
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    roles: Mapped[list["UserRole"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="UserRole.user_id",
    )
    sessions: Mapped[list["UserSession"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    personas: Mapped[list["Persona"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="Persona.user_id",
    )


class Role(Base):
    __tablename__ = "role"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # sod_class is used by SoD enforcement. Roles with the same sod_class
    # cannot be held simultaneously by the same user (Article XVII).
    sod_class: Mapped[str] = mapped_column(String(64), nullable=False, default="DEFAULT")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    user_roles: Mapped[list["UserRole"]] = relationship(back_populates="role", cascade="all, delete-orphan")


class UserRole(Base):
    __tablename__ = "user_role"
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", "scope", name="uq_user_role_scope"),
        Index("ix_user_role_user", "user_id"),
        Index("ix_user_role_role", "role_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("user.id"), nullable=False)
    role_id: Mapped[str] = mapped_column(String(36), ForeignKey("role.id"), nullable=False)
    scope: Mapped[str] = mapped_column(String(64), nullable=False, default="GLOBAL")
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    assigned_by: Mapped[str] = mapped_column(String(36), ForeignKey("user.id"), nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_by: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("user.id"), nullable=True)
    revoke_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship(
        back_populates="roles", foreign_keys=[user_id]
    )
    role: Mapped["Role"] = relationship(back_populates="user_roles")


class Persona(Base):
    """A persona is a named role a user can 'switch into'.

    Per Article XIV (Human Authority and Approval Rules) a user may hold
    multiple roles; per UI/UX Section 2 (Persona Selection) the active
    persona determines the user's current authority context.
    """

    __tablename__ = "persona"
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="uq_persona_user_role"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("user.id"), nullable=False)
    role_id: Mapped[str] = mapped_column(String(36), ForeignKey("role.id"), nullable=False)
    label: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[PersonaStatus] = mapped_column(
        SAEnum(PersonaStatus, name="persona_status"),
        nullable=False,
        default=PersonaStatus.ACTIVE,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("user.id"), nullable=False)

    user: Mapped["User"] = relationship(
        back_populates="personas", foreign_keys=[user_id]
    )
    role: Mapped["Role"] = relationship()


class UserSession(Base):
    __tablename__ = "user_session"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("user.id"), nullable=False)
    # We store a SHA-256 of the JWT, not the JWT itself. The HttpOnly cookie
    # carries the JWT; on each request we hash it and look up the session.
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    persona_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("persona.id"), nullable=True)
    ip: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[SessionStatus] = mapped_column(
        SAEnum(SessionStatus, name="session_status"),
        nullable=False,
        default=SessionStatus.ACTIVE,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    invalidated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    invalidated_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    user: Mapped["User"] = relationship(back_populates="sessions")


# ---------------------------------------------------------------------------
# Access Policy + SoD
# ---------------------------------------------------------------------------


class AccessPolicy(Base):
    __tablename__ = "access_policy"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    decision_class: Mapped[DecisionClass] = mapped_column(
        SAEnum(DecisionClass, name="decision_class"), nullable=False, default=DecisionClass.CLASS_1
    )
    required_approver_role_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    sod_exclusion_role_codes: Mapped[str] = mapped_column(
        Text, nullable=False, default=""
    )  # comma-separated role codes; empty = no exclusion
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class AccessPolicyRole(Base):
    """The roles that a given AccessPolicy grants authority to."""

    __tablename__ = "access_policy_role"
    __table_args__ = (
        UniqueConstraint("policy_id", "role_id", name="uq_policy_role"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    policy_id: Mapped[str] = mapped_column(String(36), ForeignKey("access_policy.id"), nullable=False)
    role_id: Mapped[str] = mapped_column(String(36), ForeignKey("role.id"), nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    added_by: Mapped[str] = mapped_column(String(36), ForeignKey("user.id"), nullable=False)


# ---------------------------------------------------------------------------
# Audit Log — append-only, hash-chained (Article XX)
# ---------------------------------------------------------------------------


class AuditLog(Base):
    """Append-only audit trail.

    Article XX paragraph 6: "No material record may be silently deleted or
    overwritten. Corrections shall be recorded as corrections." This table
    is enforced append-only by SQLite triggers installed in `db.apply_schema`.

    Every entry is hash-chained: `entry_hash = SHA-256(prev_hash || canonical_json(payload))`.
    The chain head is the latest entry's entry_hash. A scan over the chain
    detects any tampering with historical entries (AC-AUD-002 immutability).
    """

    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    actor_username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    actor_role_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    actor_session_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    target_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    target_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False, default="SUCCESS")
    ip: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")

    # Hash chain for tamper evidence (AC-AUD-002).
    prev_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    entry_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    # Retention class — per Constitution Article XX. Default = PERMANENT.
    # A retention class cannot be downgraded silently; the field itself is
    # append-only (the trigger blocks UPDATE).
    retention_class: Mapped[str] = mapped_column(String(32), nullable=False, default="PERMANENT")


Index("ix_audit_event_type", AuditLog.event_type)
Index("ix_audit_actor_user", AuditLog.actor_user_id)
Index("ix_audit_target", AuditLog.target_type, AuditLog.target_id)
Index("ix_audit_occurred_at", AuditLog.occurred_at)


# ---------------------------------------------------------------------------
# Migration — records every applied migration (Phase 2)
# ---------------------------------------------------------------------------
#
# The `migration` table is OPERATIONAL (one of the 9 tables exempt from
# the constitutional no-silent-amendment triggers) so that `_record_migration`
# can do an UPSERT after a rollback-and-re-apply cycle. It is included in
# `Base.metadata` so that `reset_schema` drops and recreates it cleanly.


class Migration(Base):
    """A record of one applied (or attempted) schema migration.

    Forward-only, versioned, reproducible, auditable per Phase 2 requirements
    (Constitution Article XX + Document 05 §3). The version is unique. A
    migration can be in status `APPLIED`, `ROLLED_BACK`, or `FAILED`. The
    `checksum` is a SHA-256 of (version | name | body_fingerprint) so that
    drift is detectable.
    """

    __tablename__ = "migration"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    version: Mapped[str] = mapped_column(String(16), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    applied_by: Mapped[str] = mapped_column(String(64), nullable=False, default="system")
    environment: Mapped[str] = mapped_column(String(32), nullable=False, default="development")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="APPLIED")
    checksum: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
