"""Audit Service — record, query, export, retention.

Per Constitution Article XX (Knowledge, Records, Institutional Memory) and
the AC-AUD-001..005 acceptance criteria, the audit service is the source
of truth for who did what, when, from where, and with what outcome.

AC-AUD-002 (immutable) is enforced at the database layer by triggers in
`db.apply_schema` — this service cannot circumvent them.
"""
from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import chain_head, hash_chain, session_scope
from .schema import AuditLog


# ---------------------------------------------------------------------------
# Canonical payload serialisation
# ---------------------------------------------------------------------------


def _canonical_payload(d: dict[str, Any]) -> str:
    """Return a deterministic JSON string for hashing.

    `sort_keys=True` + `separators=(",", ":")` + `ensure_ascii=False`
    guarantees the same logical payload always produces the same bytes.
    """
    return json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


# ---------------------------------------------------------------------------
# Event types (a phase-1 subset; full taxonomy in Document 06 Section 10)
# ---------------------------------------------------------------------------


class EventType:
    # Identity
    SIGN_IN = "IDENTITY.SIGN_IN"
    SIGN_IN_FAILED = "IDENTITY.SIGN_IN_FAILED"
    SIGN_OUT = "IDENTITY.SIGN_OUT"
    RECOVERY_INITIATED = "IDENTITY.RECOVERY_INITIATED"
    RECOVERY_COMPLETED = "IDENTITY.RECOVERY_COMPLETED"
    PASSWORD_CHANGED = "IDENTITY.PASSWORD_CHANGED"
    # Persona
    PERSONA_SELECTED = "PERSONA.SELECTED"
    # Access / Role
    USER_CREATED = "ACCESS.USER_CREATED"
    USER_UPDATED = "ACCESS.USER_UPDATED"
    USER_SUSPENDED = "ACCESS.USER_SUSPENDED"
    USER_ARCHIVED = "ACCESS.USER_ARCHIVED"
    ROLE_CREATED = "ACCESS.ROLE_CREATED"
    ROLE_UPDATED = "ACCESS.ROLE_UPDATED"
    ROLE_ASSIGNED = "ACCESS.ROLE_ASSIGNED"
    ROLE_REVOKED = "ACCESS.ROLE_REVOKED"
    POLICY_CREATED = "ACCESS.POLICY_CREATED"
    POLICY_UPDATED = "ACCESS.POLICY_UPDATED"
    # Security
    ACCESS_DENIED = "SECURITY.ACCESS_DENIED"
    AUDIT_EXPORT = "SECURITY.AUDIT_EXPORT"


@dataclass(frozen=True)
class AuditEvent:
    event_type: str
    action: str
    actor_user_id: Optional[str]
    actor_username: Optional[str]
    actor_role_code: Optional[str]
    actor_session_id: Optional[str]
    target_type: Optional[str]
    target_id: Optional[str]
    outcome: str
    ip: Optional[str]
    user_agent: Optional[str]
    payload: dict[str, Any]


# ---------------------------------------------------------------------------
# Recording
# ---------------------------------------------------------------------------


def record(
    session: Session,
    *,
    event_type: str,
    action: str,
    actor_user_id: Optional[str] = None,
    actor_username: Optional[str] = None,
    actor_role_code: Optional[str] = None,
    actor_session_id: Optional[str] = None,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    outcome: str = "SUCCESS",
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
    payload: Optional[dict[str, Any]] = None,
) -> AuditLog:
    """Append a new audit log entry. Append-only — UPDATE/DELETE will fail.

    The entry is hash-chained: entry_hash = SHA-256(prev_hash || canonical_json).
    The `sequence` value is computed as max(sequence) + 1 within the same
    session. SQLite does not support AUTOINCREMENT on a non-PK column, so
    we compute it explicitly. The UNIQUE constraint on `sequence` still
    detects concurrent inserts; the application is single-writer for now.
    """
    from sqlalchemy import func, select
    payload = payload or {}
    # SQLite drops timezone info on round-trip; to keep the hash chain stable,
    # we always store and re-read as a naive UTC datetime.
    occurred_at = datetime.now(timezone.utc).replace(tzinfo=None)

    # Compute next sequence value.
    current_max = session.execute(select(func.max(AuditLog.sequence))).scalar()
    next_seq = 1 if current_max is None else int(current_max) + 1

    prev = chain_head(session)
    canonical = _canonical_payload(
        {
            "occurred_at": occurred_at.isoformat(),
            "event_type": event_type,
            "action": action,
            "actor_user_id": actor_user_id,
            "actor_username": actor_username,
            "actor_role_code": actor_role_code,
            "actor_session_id": actor_session_id,
            "target_type": target_type,
            "target_id": target_id,
            "outcome": outcome,
            "ip": ip,
            "user_agent": user_agent,
            "payload": payload,
        }
    )
    entry_hash = hash_chain(prev, canonical)

    entry = AuditLog(
        sequence=next_seq,
        occurred_at=occurred_at,
        event_type=event_type,
        action=action,
        actor_user_id=actor_user_id,
        actor_username=actor_username,
        actor_role_code=actor_role_code,
        actor_session_id=actor_session_id,
        target_type=target_type,
        target_id=target_id,
        outcome=outcome,
        ip=ip,
        user_agent=user_agent,
        payload_json=json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str),
        prev_hash=prev,
        entry_hash=entry_hash,
        retention_class="PERMANENT",
    )
    session.add(entry)
    session.flush()
    return entry


# ---------------------------------------------------------------------------
# Querying
# ---------------------------------------------------------------------------


def query(
    session: Session,
    *,
    event_type: Optional[str] = None,
    actor_user_id: Optional[str] = None,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    limit: int = 1000,
    offset: int = 0,
) -> list[AuditLog]:
    """Return audit entries matching the filters, newest first.

    AC-AUD-004 (queryable) is satisfied by this function.
    """
    stmt = select(AuditLog).order_by(AuditLog.sequence.desc())
    if event_type:
        stmt = stmt.where(AuditLog.event_type == event_type)
    if actor_user_id:
        stmt = stmt.where(AuditLog.actor_user_id == actor_user_id)
    if target_type:
        stmt = stmt.where(AuditLog.target_type == target_type)
    if target_id:
        stmt = stmt.where(AuditLog.target_id == target_id)
    if since:
        stmt = stmt.where(AuditLog.occurred_at >= since)
    if until:
        stmt = stmt.where(AuditLog.occurred_at < until)
    stmt = stmt.limit(limit).offset(offset)
    return list(session.execute(stmt).scalars())


def count(session: Session, **filters: Any) -> int:
    """Count audit entries matching the filters."""
    from sqlalchemy import func

    stmt = select(func.count()).select_from(AuditLog)
    if filters.get("event_type"):
        stmt = stmt.where(AuditLog.event_type == filters["event_type"])
    if filters.get("actor_user_id"):
        stmt = stmt.where(AuditLog.actor_user_id == filters["actor_user_id"])
    if filters.get("target_type"):
        stmt = stmt.where(AuditLog.target_type == filters["target_type"])
    if filters.get("target_id"):
        stmt = stmt.where(AuditLog.target_id == filters["target_id"])
    return int(session.execute(stmt).scalar_one())


# ---------------------------------------------------------------------------
# Export (AC-AUD-003)
# ---------------------------------------------------------------------------


def export_csv(entries: Iterable[AuditLog]) -> str:
    """Return a CSV export of the given entries.

    AC-AUD-003 requires that the export matches the database content. We
    include every column so that the export is a complete, lossless copy.
    """
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(
        [
            "sequence",
            "occurred_at",
            "event_type",
            "action",
            "actor_user_id",
            "actor_username",
            "actor_role_code",
            "actor_session_id",
            "target_type",
            "target_id",
            "outcome",
            "ip",
            "user_agent",
            "payload_json",
            "prev_hash",
            "entry_hash",
            "retention_class",
        ]
    )
    for e in entries:
        writer.writerow(
            [
                e.sequence,
                e.occurred_at.isoformat() if e.occurred_at else "",
                e.event_type,
                e.action,
                e.actor_user_id or "",
                e.actor_username or "",
                e.actor_role_code or "",
                e.actor_session_id or "",
                e.target_type or "",
                e.target_id or "",
                e.outcome,
                e.ip or "",
                e.user_agent or "",
                e.payload_json,
                e.prev_hash,
                e.entry_hash,
                e.retention_class,
            ]
        )
    return buf.getvalue()


def export_json(entries: Iterable[AuditLog]) -> str:
    """Return a JSON export (array of objects) of the given entries."""
    return json.dumps(
        [
            {
                "sequence": e.sequence,
                "occurred_at": e.occurred_at.isoformat() if e.occurred_at else None,
                "event_type": e.event_type,
                "action": e.action,
                "actor_user_id": e.actor_user_id,
                "actor_username": e.actor_username,
                "actor_role_code": e.actor_role_code,
                "actor_session_id": e.actor_session_id,
                "target_type": e.target_type,
                "target_id": e.target_id,
                "outcome": e.outcome,
                "ip": e.ip,
                "user_agent": e.user_agent,
                "payload": json.loads(e.payload_json or "{}"),
                "prev_hash": e.prev_hash,
                "entry_hash": e.entry_hash,
                "retention_class": e.retention_class,
            }
            for e in entries
        ],
        indent=2,
        default=str,
    )


# ---------------------------------------------------------------------------
# Chain verification (used by tests and by the Audit Log screen)
# ---------------------------------------------------------------------------


def verify_chain(session: Session) -> tuple[bool, Optional[int]]:
    """Walk the audit chain and verify every entry_hash.

    Returns (ok, first_bad_sequence). If `ok` is False, the entry with
    `first_bad_sequence` is the first whose stored entry_hash does not
    match a recomputation.
    """
    rows = session.execute(select(AuditLog).order_by(AuditLog.sequence.asc())).scalars().all()
    prev = ""
    for r in rows:
        canonical = _canonical_payload(
            {
                "occurred_at": r.occurred_at.isoformat() if r.occurred_at else "",
                "event_type": r.event_type,
                "action": r.action,
                "actor_user_id": r.actor_user_id,
                "actor_username": r.actor_username,
                "actor_role_code": r.actor_role_code,
                "actor_session_id": r.actor_session_id,
                "target_type": r.target_type,
                "target_id": r.target_id,
                "outcome": r.outcome,
                "ip": r.ip,
                "user_agent": r.user_agent,
                "payload": json.loads(r.payload_json or "{}"),
            }
        )
        expected = hash_chain(prev, canonical)
        if expected != r.entry_hash or prev != r.prev_hash:
            return False, r.sequence
        prev = r.entry_hash
    return True, None
