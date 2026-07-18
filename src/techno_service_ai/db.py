"""Database engine, session, and schema bootstrap.

Per Article XXVIII (Document Hierarchy) and Document 04 (Software
Architecture), the database engine is an implementer choice. The choice
(here: SQLite via SQLAlchemy) is recorded as ASS-PHASE1-001 in
`docs/DECISION_AND_ASSUMPTION_REGISTER.md`.

The schema is created by `apply_schema`, which:
  1. Creates all ORM tables.
  2. Installs SQLite triggers that REJECT UPDATE and DELETE on `audit_log`
     (AC-AUD-002 immutability).
  3. Creates the audit hash-chain seed.
"""
from __future__ import annotations

import hashlib
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .config import SETTINGS
from .schema import Base

# Single shared engine. SQLite needs check_same_thread=False for FastAPI.
_engine: Engine = create_engine(
    SETTINGS.database_url,
    echo=False,
    future=True,
    connect_args={"check_same_thread": False} if SETTINGS.database_url.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(
    bind=_engine,
    autoflush=False,
    autocommit=False,
    future=True,
    # Keep attributes loaded after commit. The handler typically needs to
    # read .id / simple columns on objects returned from `with session_scope():`
    # after the block exits. Expire-on-commit (the default) would force a
    # lazy reload on a closed session, which raises DetachedInstanceError.
    expire_on_commit=False,
)


# Enable FK constraints on SQLite (off by default).
if SETTINGS.database_url.startswith("sqlite"):
    @event.listens_for(_engine, "connect")
    def _enable_sqlite_fk(dbapi_connection, connection_record):  # noqa: ARG001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()


# ---------------------------------------------------------------------------
# Schema bootstrap
# ---------------------------------------------------------------------------

# Triggers are created after the ORM tables. They REJECT UPDATE and DELETE on
# the audit_log table, satisfying AC-AUD-002 (immutable).
_AUDIT_IMMUTABILITY_TRIGGERS = [
    """
    CREATE TRIGGER IF NOT EXISTS audit_log_no_update
    BEFORE UPDATE ON audit_log
    BEGIN
        SELECT RAISE(ABORT, 'audit_log is append-only: UPDATE is forbidden (Constitution Article XX)');
    END;
    """,
    """
    CREATE TRIGGER IF NOT EXISTS audit_log_no_delete
    BEFORE DELETE ON audit_log
    BEGIN
        SELECT RAISE(ABORT, 'audit_log is append-only: DELETE is forbidden (Constitution Article XX)');
    END;
    """,
]


def apply_schema(engine: Engine | None = None) -> None:
    """Create all tables and install audit-immutability triggers.

    Idempotent. Safe to call at startup and in tests.
    """
    eng = engine or _engine
    Base.metadata.create_all(eng)
    if eng.dialect.name == "sqlite":
        with eng.begin() as conn:
            for stmt in _AUDIT_IMMUTABILITY_TRIGGERS:
                conn.execute(text(stmt))


def reset_schema(engine: Engine | None = None) -> None:
    """Drop and recreate everything.

    The audit_log table is append-only (UPDATE/DELETE forbidden by trigger).
    To produce a clean test fixture, we DROP all tables and recreate them
    along with the triggers. Production code MUST NOT call this function.
    """
    eng = engine or _engine
    Base.metadata.drop_all(eng)
    apply_schema(eng)


def get_engine() -> Engine:
    return _engine


@contextmanager
def session_scope() -> Iterator[Session]:
    """Yield a SQLAlchemy session, committing on success and rolling back on error.

    Use as: with session_scope() as s: ...
    """
    s = SessionLocal()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def hash_chain(prev_hash: str, payload_canonical: str) -> str:
    """Return the SHA-256 hash of (prev_hash || payload_canonical) as hex.

    `payload_canonical` MUST be a deterministic serialisation of the entry
    (sorted JSON, no whitespace). See `audit._canonical_payload`.
    """
    h = hashlib.sha256()
    h.update(prev_hash.encode("utf-8"))
    h.update(b"|")
    h.update(payload_canonical.encode("utf-8"))
    return h.hexdigest()


def chain_head(session: Session) -> str:
    """Return the entry_hash of the most recent audit log row, or '' if empty."""
    row = session.execute(
        text("SELECT entry_hash FROM audit_log ORDER BY sequence DESC LIMIT 1")
    ).first()
    if row is None:
        return ""
    return row[0]
