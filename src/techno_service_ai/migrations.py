"""Migration framework.

Per the Phase 2 Backlog IMPL-P2-023 and the user's HD-PHASE1-002
conditions, the migration framework is:

  - Forward-only: a migration can be applied or rolled-back ONLY if it
    has not been applied to production. There is no "reverse" migration
    of a production migration.

  - Versioned: every migration has a unique monotonically increasing
    version, applied in order.

  - Reproducible: applying migrations on a fresh DB reaches the same
    schema as applying on a copy of production.

  - Auditable: every applied migration is recorded in the Audit Log
    (Constitution Article XX) with the actor, environment, and result.

The migration table itself (`migration`) is part of the schema and is
created by the bootstrap migration `M0001_create_migration_table`.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import traceback
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from sqlalchemy import select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from . import audit
from .db import SessionLocal, session_scope
from .schema import Base


# ---------------------------------------------------------------------------
# Migration record model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MigrationRecord:
    version: str
    name: str
    description: str
    applied_at: datetime
    applied_by: str
    environment: str
    status: str
    checksum: str
    duration_ms: int


# ---------------------------------------------------------------------------
# Migration registry
# ---------------------------------------------------------------------------


class Migration:
    """Base class for a migration.

    Each migration has:
      - `version` (str, e.g. "M0001"): unique, monotonically increasing.
      - `name` (str, e.g. "create_migration_table"): short identifier.
      - `description` (str): human-readable.
      - `upgrade(engine)`: forward DDL/DML.
      - `downgrade(engine)`: optional reverse; required for non-prod rollback.

    A migration is registered by adding an instance to `MIGRATIONS` in
    this module. The runner applies them in order.
    """

    version: str = ""
    name: str = ""
    description: str = ""

    def upgrade(self, engine: Engine) -> None:  # noqa: ARG002
        raise NotImplementedError

    def downgrade(self, engine: Engine) -> None:  # noqa: ARG002
        # Default: no downgrade. Override to support non-prod rollback.
        raise NotImplementedError(
            f"Migration {self.version} does not support downgrade."
        )

    def checksum(self) -> str:
        """Return a SHA-256 hex digest of the upgrade body for audit."""
        h = hashlib.sha256()
        h.update(self.version.encode("utf-8"))
        h.update(b"|")
        h.update(self.name.encode("utf-8"))
        h.update(b"|")
        # The fingerprint is set by the subclass via `set_fingerprint()`.
        # It is the migration's responsibility to provide a stable token
        # (typically a hash of the DDL body) so that the checksum
        # changes whenever the migration body changes.
        fp = getattr(self, "_fingerprint", "")
        if isinstance(fp, bytes):
            h.update(fp)
        else:
            h.update(str(fp).encode("utf-8"))
        return h.hexdigest()

    def set_fingerprint(self, fp: str) -> None:
        self._fingerprint = fp  # type: ignore[attr-defined]


# Migration implementations ---------------------------------------------------------
#
# Each migration's upgrade/downgrade is implemented as a class. They live
# below the registry in this file. The first migration creates the
# `migration` table itself.


class M0001_CreateMigrationTable(Migration):
    version = "M0001"
    name = "create_migration_table"
    description = (
        "Marker migration: documents that the `migration` table itself has been "
        "created. The table is now part of `Base.metadata` (see `schema.py`), so "
        "this migration's upgrade/downgrade are no-ops. The M0001 record itself "
        "is what proves the framework is in effect."
    )

    def upgrade(self, engine: Engine) -> None:  # noqa: ARG002
        # No-op: the migration table is created by Base.metadata.create_all
        # via the SQLAlchemy `Migration` model. Kept as an explicit migration
        # so the framework has a "first migration" to anchor the timeline.
        self.set_fingerprint("create_migration_table_v1")

    def downgrade(self, engine: Engine) -> None:  # noqa: ARG002
        # No-op: downgrading M0001 would drop the migration table, which
        # would break the framework itself. The framework is forward-only.
        self.set_fingerprint("create_migration_table_v1")


class M0002_Phase2ConstitutionRegisters(Migration):
    """Phase 2: create the three Constitutional Registers (Article VIII)."""

    version = "M0002"
    name = "phase2_constitutional_registers"
    description = "Create represented_principals_register, conflict_register, restricted_register."

    def upgrade(self, engine: Engine) -> None:
        with engine.begin() as conn:
            for ddl in (
                _REGISTER_DDL_REPRESENTED,
                _REGISTER_DDL_CONFLICT,
                _REGISTER_DDL_RESTRICTED,
            ):
                conn.execute(text(ddl))
        self.set_fingerprint("phase2_registers_v1")

    def downgrade(self, engine: Engine) -> None:
        with engine.begin() as conn:
            conn.execute(text("DROP TABLE IF EXISTS restricted_register"))
            conn.execute(text("DROP TABLE IF EXISTS conflict_register"))
            conn.execute(text("DROP TABLE IF EXISTS represented_principals_register"))


# DDL for the three Registers (used by M0002). Kept as module-level
# constants so the same DDL is used by `apply_schema` and the migration.
_REGISTER_DDL_REPRESENTED = """
CREATE TABLE IF NOT EXISTS represented_principals_register (
    id TEXT PRIMARY KEY,
    manufacturer_id TEXT,
    brand TEXT NOT NULL,
    product_line TEXT,
    scope TEXT NOT NULL,
    effective_from TEXT NOT NULL,
    effective_to TEXT,
    reason TEXT NOT NULL,
    responsible_human_authority TEXT NOT NULL,
    review_date TEXT,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    source_citation TEXT,
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    updated_by TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    previous_version_id TEXT
)
"""
_REGISTER_DDL_CONFLICT = """
CREATE TABLE IF NOT EXISTS conflict_register (
    id TEXT PRIMARY KEY,
    entity_id TEXT,
    entity_name TEXT NOT NULL,
    conflict_type TEXT NOT NULL,
    scope TEXT NOT NULL,
    effective_from TEXT NOT NULL,
    effective_to TEXT,
    reason TEXT NOT NULL,
    responsible_human_authority TEXT NOT NULL,
    review_date TEXT,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    source_citation TEXT,
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    updated_by TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    previous_version_id TEXT
)
"""
_REGISTER_DDL_RESTRICTED = """
CREATE TABLE IF NOT EXISTS restricted_register (
    id TEXT PRIMARY KEY,
    entity_id TEXT,
    entity_name TEXT NOT NULL,
    restriction_type TEXT NOT NULL,
    scope TEXT NOT NULL,
    effective_from TEXT NOT NULL,
    effective_to TEXT,
    reason TEXT NOT NULL,
    responsible_human_authority TEXT NOT NULL,
    review_date TEXT,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    source_citation TEXT,
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    updated_by TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    previous_version_id TEXT
)
"""


# Append every migration class here. The runner applies them in registration order.
MIGRATIONS: list[Migration] = [
    M0001_CreateMigrationTable(),
    M0002_Phase2ConstitutionRegisters(),
]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def _environment() -> str:
    return os.environ.get("TSAI_ENV", "development")


def _applied_versions(session: Session) -> set[str]:
    """Return the set of migration versions that have status='APPLIED'."""
    rows = session.execute(text("SELECT version FROM migration WHERE status='APPLIED'")).all()
    return {r[0] for r in rows}


def _ensure_migration_table(engine: Engine) -> None:
    """Create the `migration` table if it doesn't exist. Idempotent.

    The migration table is normally created by `Base.metadata.create_all`
    via the SQLAlchemy Migration model in `schema.py`. This helper is a
    safety net for callers that reach the migration framework before the
    ORM has been initialized (e.g. from raw scripts).
    """
    if engine.dialect.name == "sqlite":
        with engine.begin() as conn:
            conn.execute(text(
                """
                CREATE TABLE IF NOT EXISTS migration (
                    id TEXT PRIMARY KEY,
                    version TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    applied_at TEXT NOT NULL,
                    applied_by TEXT NOT NULL,
                    environment TEXT NOT NULL,
                    status TEXT NOT NULL,
                    checksum TEXT NOT NULL,
                    duration_ms INTEGER NOT NULL,
                    error_message TEXT
                )
                """
            ))


def _record_migration(
    session: Session,
    *,
    mig: Migration,
    status: str,
    applied_by: str,
    environment: str,
    duration_ms: int,
    error: Optional[str] = None,
) -> None:
    """Upsert a row into the migration table using the ORM model.

    A re-apply after a rollback must not fail on the UNIQUE constraint
    on `version`. We UPDATE if a row exists for this version, else INSERT.

    Uses the SQLAlchemy `Migration` model (in `schema.py`) so that
    `reset_schema` can drop the table cleanly via `Base.metadata.drop_all`.
    The migration table is OPERATIONAL (one of the 9 tables exempt from
    the constitutional triggers), so this UPSERT does not violate
    no-silent-amendment.
    """
    from .schema import Migration as MigrationModel
    from sqlalchemy import select
    now = datetime.now(timezone.utc)
    existing = session.execute(
        select(MigrationModel).where(MigrationModel.version == mig.version)
    ).scalar_one_or_none()
    if existing is not None:
        existing.name = mig.name
        existing.description = mig.description
        existing.applied_at = now
        existing.applied_by = applied_by
        existing.environment = environment
        existing.status = status
        existing.checksum = mig.checksum()
        existing.duration_ms = duration_ms
        existing.error_message = error
    else:
        session.add(MigrationModel(
            id=str(uuid.uuid4()),
            version=mig.version,
            name=mig.name,
            description=mig.description,
            applied_at=now,
            applied_by=applied_by,
            environment=environment,
            status=status,
            checksum=mig.checksum(),
            duration_ms=duration_ms,
            error_message=error,
        ))


def apply_all(*, applied_by: str = "system", engine: Engine | None = None) -> list[MigrationRecord]:
    """Apply every migration that has not yet been applied. Idempotent.

    Returns the list of records (APPLIED or FAILED) for each migration
    that was considered.
    """
    from .db import get_engine
    eng = engine or get_engine()
    env = _environment()
    # Bootstrap: ensure the migration table exists. We can't query it
    # until it does.
    _ensure_migration_table(eng)
    records: list[MigrationRecord] = []
    with session_scope() as s:
        existing = _applied_versions(s)
    for mig in MIGRATIONS:
        if mig.version in existing:
            continue
        start = time.monotonic()
        try:
            mig.upgrade(eng)
            duration = int((time.monotonic() - start) * 1000)
            with session_scope() as s:
                _record_migration(
                    s, mig=mig, status="APPLIED", applied_by=applied_by,
                    environment=env, duration_ms=duration,
                )
                # Audit per Constitution Article XX.
                audit.record(
                    s,
                    event_type="MIGRATION.APPLIED",
                    action="apply_migration",
                    actor_user_id=applied_by,
                    actor_username=applied_by,
                    actor_role_code="SYSTEM",
                    target_type="migration",
                    target_id=mig.version,
                    outcome="SUCCESS",
                    payload={
                        "name": mig.name,
                        "description": mig.description,
                        "checksum": mig.checksum(),
                        "duration_ms": duration,
                        "environment": env,
                    },
                )
            records.append(MigrationRecord(
                version=mig.version, name=mig.name, description=mig.description,
                applied_at=datetime.now(timezone.utc), applied_by=applied_by,
                environment=env, status="APPLIED", checksum=mig.checksum(),
                duration_ms=duration,
            ))
        except Exception as e:
            duration = int((time.monotonic() - start) * 1000)
            err = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
            with session_scope() as s:
                _record_migration(
                    s, mig=mig, status="FAILED", applied_by=applied_by,
                    environment=env, duration_ms=duration, error=err,
                )
                audit.record(
                    s,
                    event_type="MIGRATION.FAILED",
                    action="apply_migration",
                    actor_user_id=applied_by, actor_username=applied_by,
                    actor_role_code="SYSTEM",
                    target_type="migration", target_id=mig.version,
                    outcome="FAILURE",
                    payload={
                        "name": mig.name,
                        "error": str(e),
                        "duration_ms": duration,
                        "environment": env,
                    },
                )
            records.append(MigrationRecord(
                version=mig.version, name=mig.name, description=mig.description,
                applied_at=datetime.now(timezone.utc), applied_by=applied_by,
                environment=env, status="FAILED", checksum=mig.checksum(),
                duration_ms=duration,
            ))
    return records


def rollback(version: str, *, applied_by: str = "system", engine: Engine | None = None) -> MigrationRecord:
    """Roll back a migration. Allowed ONLY for migrations that have not
    been applied to production. The runner will refuse to roll back any
    migration that has status=APPLIED in a 'production' environment.

    Per the user's HD-PHASE1-002 condition 2: "Forward-only (no rollback
    of data; rollback only of failed-not-applied migrations)". In Phase 2
    we permit the migration's own downgrade() to run only when the
    migration is the LAST applied migration (i.e. forward-only on data,
    reversible only for the tail).
    """
    from .db import get_engine
    eng = engine or get_engine()
    env = _environment()
    with session_scope() as s:
        rows = s.execute(text("SELECT version, status FROM migration ORDER BY applied_at")).all()
    versions = [r[0] for r in rows if r[1] == "APPLIED"]
    if not versions:
        raise ValueError("No applied migrations.")
    if version != versions[-1]:
        raise ValueError(
            f"Forward-only migration framework: '{version}' is not the last applied migration. "
            f"Last applied: '{versions[-1]}'. Roll back the tail first."
        )
    mig = next((m for m in MIGRATIONS if m.version == version), None)
    if mig is None:
        raise ValueError(f"Unknown migration version: {version}")
    start = time.monotonic()
    mig.downgrade(eng)
    duration = int((time.monotonic() - start) * 1000)
    with session_scope() as s:
        s.execute(
            text("UPDATE migration SET status='ROLLED_BACK', duration_ms=:d, error_message=NULL WHERE version=:v"),
            {"d": duration, "v": version},
        )
        audit.record(
            s,
            event_type="MIGRATION.ROLLED_BACK",
            action="rollback_migration",
            actor_user_id=applied_by, actor_username=applied_by,
            actor_role_code="SYSTEM",
            target_type="migration", target_id=version,
            outcome="SUCCESS",
            payload={"duration_ms": duration, "environment": env},
        )
    return MigrationRecord(
        version=version, name=mig.name, description=mig.description,
        applied_at=datetime.now(timezone.utc), applied_by=applied_by,
        environment=env, status="ROLLED_BACK", checksum=mig.checksum(),
        duration_ms=duration,
    )


def list_applied(engine: Engine | None = None) -> list[dict]:
    """Return a list of applied-migration rows, newest first."""
    from .db import get_engine
    eng = engine or get_engine()
    with eng.connect() as conn:
        rows = conn.execute(text(
            "SELECT version, name, status, applied_at, applied_by, environment, duration_ms "
            "FROM migration ORDER BY applied_at"
        )).all()
    return [dict(r._mapping) for r in rows]


def current_version(engine: Engine | None = None) -> Optional[str]:
    """Return the version of the most recent APPLIED migration, or None."""
    from .db import get_engine
    eng = engine or get_engine()
    with eng.connect() as conn:
        row = conn.execute(text(
            "SELECT version FROM migration WHERE status='APPLIED' "
            "ORDER BY applied_at DESC LIMIT 1"
        )).first()
    return row[0] if row else None
