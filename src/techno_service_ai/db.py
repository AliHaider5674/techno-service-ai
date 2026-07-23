"""Database engine, session, and schema bootstrap.

Per Article XXVIII (Document Hierarchy) and Document 04 (Software
Architecture), the database engine is an implementer choice. The choice
(here: SQLite via SQLAlchemy) is recorded as ASS-PHASE1-001 in
`docs/DECISION_AND_ASSUMPTION_REGISTER.md`.

The schema is created by `apply_schema`, which:
  1. Creates all ORM tables (Phase 1 + Phase 2 entities).
  2. Installs SQLite triggers that REJECT UPDATE and DELETE on `audit_log`
     (AC-AUD-002 immutability).
  3. Installs SQLite triggers that REJECT UPDATE and DELETE on every
     constitutional table (AC-P2-005, AC-DL-004 — no silent amendment).
  4. Runs the migration framework (Phase 2 / IMPL-P2-023).
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

# Importing phase2_schema registers all 20 Information Domains of Phase 2
# with the SQLAlchemy Base, so that `Base.metadata.create_all` creates
# them. The constitutional trigger installation below then protects them.
from . import phase2_schema  # noqa: F401  (side-effect import)


def _resolve_db_url(url: str) -> str:
    """Ensure PostgreSQL URLs use the psycopg (v3) driver dialect.

    Render provides `postgresql://...` which SQLAlchemy maps to psycopg2
    by default. We use psycopg3, so rewrite to `postgresql+psycopg://`.
    """
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    return url


# Single shared engine. SQLite needs check_same_thread=False for FastAPI.
_engine: Engine = create_engine(
    _resolve_db_url(SETTINGS.database_url),
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


# PostgreSQL equivalents of the audit-immutability triggers.
# Uses RAISE EXCEPTION instead of RAISE(ABORT).
_AUDIT_IMMUTABILITY_TRIGGERS_PG = [
    """
    CREATE OR REPLACE FUNCTION audit_log_no_update_fn() RETURNS trigger AS $$
    BEGIN
        RAISE EXCEPTION 'audit_log is append-only: UPDATE is forbidden (Constitution Article XX)';
        RETURN NULL;
    END;
    $$ LANGUAGE plpgsql;
    """,
    """
    DROP TRIGGER IF EXISTS audit_log_no_update ON audit_log;
    CREATE TRIGGER audit_log_no_update
    BEFORE UPDATE ON audit_log
    FOR EACH ROW EXECUTE FUNCTION audit_log_no_update_fn();
    """,
    """
    CREATE OR REPLACE FUNCTION audit_log_no_delete_fn() RETURNS trigger AS $$
    BEGIN
        RAISE EXCEPTION 'audit_log is append-only: DELETE is forbidden (Constitution Article XX)';
        RETURN NULL;
    END;
    $$ LANGUAGE plpgsql;
    """,
    """
    DROP TRIGGER IF EXISTS audit_log_no_delete ON audit_log;
    CREATE TRIGGER audit_log_no_delete
    BEFORE DELETE ON audit_log
    FOR EACH ROW EXECUTE FUNCTION audit_log_no_delete_fn();
    """,
]


def apply_schema(engine: Engine | None = None) -> None:
    """Create all tables and install audit-immutability triggers.

    Idempotent. Safe to call at startup and in tests.
    """
    eng = engine or _engine
    # Ensure pgcrypto is available for PostgreSQL (needed by encryption.py).
    if eng.dialect.name == "postgresql":
        with eng.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
    Base.metadata.create_all(eng)
    if eng.dialect.name == "sqlite":
        with eng.begin() as conn:
            for stmt in _AUDIT_IMMUTABILITY_TRIGGERS:
                conn.execute(text(stmt))
        install_constitutional_triggers(eng)
    elif eng.dialect.name == "postgresql":
        with eng.begin() as conn:
            for stmt in _AUDIT_IMMUTABILITY_TRIGGERS_PG:
                conn.execute(text(stmt))
        install_constitutional_triggers(eng)


def install_constitutional_triggers(engine: Engine) -> None:
    """Install BEFORE UPDATE and BEFORE DELETE triggers on every table
    marked `__constitutional__ = True`.

    Per Constitution Article XX paragraph 6 / DB-PRIN-018:
    No material record may be silently deleted or overwritten.

    The triggers raise a database-specific error (RAISE(ABORT) on SQLite,
    RAISE EXCEPTION on PostgreSQL) with a table-specific message so the
    violation is auditable. Updates are implemented by inserting a new
    versioned row (same canonical_id, new version) — see `ConstitutionalMixin`
    and the Phase 2 docs.

    Supported dialects: SQLite, PostgreSQL.
    """
    # Tables that legitimately need to be updated: audit_log, migration,
    # and the Phase 1 operational tables (user, role, user_role, persona,
    # user_session, access_policy, access_policy_role). These are
    # *operational* records, not constitutional records.
    EXEMPT = {
        "audit_log",
        "migration",
        "user", "role", "user_role", "persona",
        "user_session", "access_policy", "access_policy_role",
    }
    constitutional_tables: set[str] = set()
    # Pull the class attribute from each mapped class.
    for mapper in Base.registry.mappers:
        cls = mapper.class_
        if getattr(cls, "__constitutional__", False):
            tbl = getattr(cls, "__tablename__", None)
            if tbl:
                constitutional_tables.add(tbl)
    # Also include any Table marked constitutional via Table.info (future-proofing).
    for t in Base.metadata.tables.values():
        if getattr(t, "info", {}).get("constitutional", False):
            constitutional_tables.add(t.name)
    # De-duplicate and exclude exempt tables.
    targets = sorted({t for t in constitutional_tables if t not in EXEMPT})

    dialect = engine.dialect.name

    if dialect == "sqlite":
        with engine.begin() as conn:
            for table in targets:
                # Idempotent: drop any prior triggers we may have installed.
                for trig in (f"{table}_no_update", f"{table}_no_delete"):
                    conn.execute(text(f"DROP TRIGGER IF EXISTS {trig}"))
                conn.execute(text(
                    f"""
                    CREATE TRIGGER {table}_no_update
                    BEFORE UPDATE ON {table}
                    BEGIN
                        SELECT RAISE(ABORT, '{table} is constitutional and append-only: UPDATE is forbidden (Constitution Article XX / DB-PRIN-018)');
                    END;
                    """
                ))
                conn.execute(text(
                    f"""
                    CREATE TRIGGER {table}_no_delete
                    BEFORE DELETE ON {table}
                    BEGIN
                        SELECT RAISE(ABORT, '{table} is constitutional and append-only: DELETE is forbidden (Constitution Article XX / DB-PRIN-018)');
                    END;
                    """
                ))
    elif dialect == "postgresql":
        with engine.begin() as conn:
            for table in targets:
                # Idempotent: drop any prior triggers we may have installed.
                for trig in (f"{table}_no_update", f"{table}_no_delete"):
                    conn.execute(text(f"DROP TRIGGER IF EXISTS {trig} ON {table}"))
                # BEFORE UPDATE trigger.
                conn.execute(text(
                    f"""
                    CREATE OR REPLACE FUNCTION {table}_no_update_fn() RETURNS trigger AS $$
                    BEGIN
                        RAISE EXCEPTION '{table} is constitutional and append-only: UPDATE is forbidden (Constitution Article XX / DB-PRIN-018)';
                        RETURN NULL;
                    END;
                    $$ LANGUAGE plpgsql;
                    """
                ))
                conn.execute(text(
                    f"""
                    DROP TRIGGER IF EXISTS {table}_no_update ON {table};
                    CREATE TRIGGER {table}_no_update
                    BEFORE UPDATE ON {table}
                    FOR EACH ROW EXECUTE FUNCTION {table}_no_update_fn();
                    """
                ))
                # BEFORE DELETE trigger.
                conn.execute(text(
                    f"""
                    CREATE OR REPLACE FUNCTION {table}_no_delete_fn() RETURNS trigger AS $$
                    BEGIN
                        RAISE EXCEPTION '{table} is constitutional and append-only: DELETE is forbidden (Constitution Article XX / DB-PRIN-018)';
                        RETURN NULL;
                    END;
                    $$ LANGUAGE plpgsql;
                    """
                ))
                conn.execute(text(
                    f"""
                    DROP TRIGGER IF EXISTS {table}_no_delete ON {table};
                    CREATE TRIGGER {table}_no_delete
                    BEFORE DELETE ON {table}
                    FOR EACH ROW EXECUTE FUNCTION {table}_no_delete_fn();
                    """
                ))
    else:
        # Unknown dialect: skip (not the constitutional DB we're supporting).
        return


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
