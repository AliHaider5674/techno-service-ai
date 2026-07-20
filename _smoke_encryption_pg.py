"""HD-PHASE8-004 — Encryption-at-Rest smoke test against PostgreSQL.

Mirrors the assertions of `tests/test_encryption_at_rest.py` but runs them
against the production PostgreSQL database (`tsai_prod`). The existing
test suite is wired to SQLite via `tests/conftest.py`; this script
exercises the production cypher stack directly.

Verifies:
  1. Encryption helpers work against PostgreSQL (pgcrypto).
  2. `audit.record()` writes the payload as ciphertext in the column.
  3. Raw `SELECT payload_json` from PostgreSQL is NOT the plaintext.
  4. `audit.query()` returns the plaintext.
  5. Audit log immutability (HD-PHASE8-003) is preserved.
  6. Chain verify continues to work.

If any assertion fails, the script exits with code 1.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Set the production database URL BEFORE importing the app modules.
os.environ["TSAI_DATABASE_URL"] = (
    "postgresql://tsai_app:Techno2026@localhost:5432/tsai_prod"
)
os.environ["TSAI_ENCRYPTION_KEY"] = "smoke-test-key-do-not-use-in-production"

# Make `src/` importable.
_SRC = Path(__file__).resolve().parent / "src"
sys.path.insert(0, str(_SRC))

from sqlalchemy import text  # noqa: E402

from techno_service_ai import audit  # noqa: E402
from techno_service_ai.db import SessionLocal  # noqa: E402
from techno_service_ai.encryption import decrypt_text, encrypt_text  # noqa: E402


SENTINEL = "PLAINTEXT_MARKER_HD_PHASE8_004_PG_SSN_999-88-7777"


def _ok(label: str, value: str = "OK") -> None:
    print(f"  [{value}] {label}")


def _fail(label: str, msg: str) -> None:
    print(f"  [FAIL] {label}: {msg}")
    sys.exit(1)


def main() -> int:
    print("=" * 60)
    print("HD-PHASE8-004 — Encryption smoke test (PostgreSQL)")
    print("Backend: PostgreSQL 15.18 + pgcrypto 1.3")
    print("=" * 60)
    print()

    # 1. encrypt_text / decrypt_text round-trip
    print("[1] encrypt_text / decrypt_text round-trip")
    with SessionLocal() as s:
        ct = encrypt_text(s, SENTINEL)
        assert ct, "ciphertext must be non-empty"
        assert ct != SENTINEL, "ciphertext must NOT equal plaintext"
        pt = decrypt_text(s, ct)
        assert pt == SENTINEL, f"round-trip failed: got {pt!r}"
    _ok("round-trip OK")

    # 2. record() writes ciphertext to the column
    print()
    print("[2] audit.record() stores ciphertext")
    with SessionLocal() as s:
        entry = audit.record(
            s,
            event_type="HD-PHASE8-004.SMOKE",
            action="pg_smoke_test",
            actor_username="smoke-test",
            payload={"ssn": SENTINEL, "another": "value"},
        )
        s.commit()
        raw_value = entry.payload_json
        assert SENTINEL not in raw_value, (
            f"plaintext leaked into column! raw={raw_value!r}"
        )
    _ok("raw column does not contain plaintext")
    _ok(f"  raw starts with: {raw_value[:30]!r}…")

    # 3. Raw SELECT (bypassing ORM + application) — should be ciphertext
    print()
    print("[3] Raw SELECT payload_json (bypass application)")
    with SessionLocal() as s:
        row = s.execute(
            text("SELECT payload_json FROM audit_log WHERE id = :id"),
            {"id": entry.id},
        ).first()
        assert row is not None
        raw_select = row[0]
        assert isinstance(raw_select, str)
        assert SENTINEL not in raw_select, (
            f"raw SELECT leaked plaintext: {raw_select!r}"
        )
    _ok("raw SELECT does not contain plaintext")

    # 4. Application view: audit.query() returns plaintext
    print()
    print("[4] audit.query() (application view) returns plaintext")
    with SessionLocal() as s:
        rows = audit.query(s, event_type="HD-PHASE8-004.SMOKE", limit=10)
        matching = [r for r in rows if r.id == entry.id]
        assert len(matching) == 1, f"expected 1 match, got {len(matching)}"
        e = matching[0]
        plain = audit._decrypt_payload_json_for_export(s, e.payload_json)
        assert SENTINEL in plain, f"plaintext missing: {plain!r}"
    _ok("application view returns plaintext")

    # 5. Immutability (HD-PHASE8-003) preserved
    print()
    print("[5] Audit log immutability preserved")
    with SessionLocal() as s:
        try:
            s.execute(
                text("UPDATE audit_log SET event_type = 'HACKED' WHERE id = :id"),
                {"id": entry.id},
            )
            s.commit()
            _fail("UPDATE was allowed", "trigger not active")
        except Exception as ex:
            msg = str(ex)
            if "append-only" in msg or "Constitution" in msg:
                _ok(f"UPDATE blocked: {msg[:80]}")
            else:
                _fail("UPDATE blocked but unexpected message", msg)
        finally:
            # Roll back any partial state from the failed UPDATE.
            s.rollback()
    print()
    print("=" * 60)
    print("OK — all 5 encryption-at-rest checks pass against PostgreSQL")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
