"""Encryption at Rest — pgcrypto + AES-256-GCM (dialect-aware).

HD-PHASE8-004: Production Encryption at Rest.

This module provides thin, dialect-aware wrappers for column-level
encryption at rest. The application calls `encrypt_text(session, plaintext)`
on write and `decrypt_text(session, ciphertext)` on read; the underlying
cipher depends on the SQLAlchemy dialect bound to the session:

- **PostgreSQL** (production): `pgp_sym_encrypt(plaintext, key)::text` and
  `pgp_sym_decrypt(ciphertext, key)`. The `pgcrypto` extension must be
  installed (`CREATE EXTENSION pgcrypto;`). The key is supplied per
  session by the application. Ciphertext is OpenPGP-formatted binary
  data cast to `text`.
- **SQLite** (test, dev): AES-256-GCM via `cryptography.hazmat`. The
  32-byte key is `SHA-256(TSAI_ENCRYPTION_KEY)`; the 12-byte nonce is
  random per call. The output is `base64(nonce || ciphertext || tag)` so
  it is safe to store in a `text` column. SQLite is used only for tests
  and ephemeral dev databases — the production deployment is PostgreSQL.

**Key source:** `TSAI_ENCRYPTION_KEY` environment variable. In dev/test,
a `dev-` prefixed default is used. The default is deliberately
distinguishable from any plausible production key.

**Constitutional constraints (HD-PHASE8-004, §8.2.6 of PRODUCTION_DEPLOYMENT.md):**

- Schema unchanged. Column types, names, and triggers are identical.
- This module is a confidentiality mechanism. The audit log immutability
  guarantee (HD-PHASE8-003) is preserved by separate triggers; encryption
  is independent.
- No new entities, no new constitutional surface.
- The hash chain (`entry_hash`) is computed **before** encryption. The
  stored ciphertext is opaque; chain integrity is unaffected by the
  encryption transformation.

**Threat model:** protects data at rest from disk theft, OS-level
unauthorised access, and backup leak. Does NOT protect against
memory-scraping of a live process holding the key.

**Out of scope:** key rotation (a future gap; would require re-encrypting
the entire `payload_json` column).
"""
from __future__ import annotations

import base64
import hashlib
import os
from typing import Final

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import text
from sqlalchemy.orm import Session


# Default cipher for `pgp_sym_encrypt` in PostgreSQL. AES-256 is the
# pgcrypto default and is the standard for production column encryption
# per ASS-PHASE8-004-001.
DEFAULT_DEV_KEY: Final[str] = "dev-key-do-not-use-in-production-x"

# AES-256-GCM nonce size (96 bits is the recommended length for GCM).
_AES_NONCE_SIZE: Final[int] = 12


def get_encryption_key() -> str:
    """Return the encryption key for the current process.

    The key is read from the `TSAI_ENCRYPTION_KEY` environment variable.
    In dev/test, a `dev-` prefixed default is used. The default is
    deliberately distinguishable from any plausible production key.
    """
    key = os.environ.get("TSAI_ENCRYPTION_KEY")
    if key:
        return key
    return DEFAULT_DEV_KEY


def _dialect_name(session: Session) -> str:
    """Return the SQLAlchemy dialect name of the session's bind."""
    bind = session.get_bind()
    return bind.dialect.name if bind is not None else ""


# ---------------------------------------------------------------------------
# PostgreSQL path (production)
# ---------------------------------------------------------------------------


def _encrypt_postgres(session: Session, plaintext: str) -> str:
    """Encrypt via pgcrypto's `pgp_sym_encrypt`. Returns base64 ciphertext.

    The `pgp_sym_encrypt` result is `bytea`. A plain `::text` cast would
    yield the bytea hex/escape representation (`\\x...`), which is not
    a useful round-trip target. We instead `encode(..., 'base64')` to
    get a portable base64 string that is safe to store in a `text`
    column and decodes back to bytes via `decode(..., 'base64')` on
    the read path.
    """
    key = get_encryption_key()
    sql = text(
        "SELECT encode(pgp_sym_encrypt(:plaintext, :key), 'base64') AS ciphertext"
    )
    row = session.execute(sql, {"plaintext": plaintext, "key": key}).first()
    return row.ciphertext if row else ""


def _decrypt_postgres(session: Session, ciphertext: str) -> str:
    """Decrypt via pgcrypto's `pgp_sym_decrypt`. Returns the decoded text.

    `pgp_sym_decrypt` returns `bytea`. SQLAlchemy + psycopg2 auto-decode
    UTF-8 bytea to a Python `str`. The ciphertext was stored as
    `encode(..., 'base64')` on the write path; we `decode(..., 'base64')`
    here to recover the bytes before passing to `pgp_sym_decrypt`.

    Note: we deliberately do NOT use `convert_from(..., 'UTF8')` here.
    The combination of `pgp_sym_decrypt` + `convert_from` interacts
    poorly with the bind-parameter parser in SQLAlchemy in some
    dialects; the auto-decode via the driver is more portable.
    """
    key = get_encryption_key()
    sql = text(
        "SELECT pgp_sym_decrypt(decode(:ciphertext, 'base64'), :key) AS plaintext"
    )
    row = session.execute(sql, {"ciphertext": ciphertext, "key": key}).first()
    pt = row.plaintext if row else ""
    # SQLAlchemy + psycopg2 may return `bytes` for bytea columns. Decode
    # if so; otherwise return as-is.
    if isinstance(pt, (bytes, bytearray)):
        try:
            return pt.decode("utf-8")
        except UnicodeDecodeError:
            return pt.decode("utf-8", errors="replace")
    return pt or ""


# ---------------------------------------------------------------------------
# SQLite path (test, dev) — AES-256-GCM
# ---------------------------------------------------------------------------


def _aes_key() -> bytes:
    """Derive a 32-byte AES-256 key from the process key string."""
    return hashlib.sha256(get_encryption_key().encode("utf-8")).digest()


def _encrypt_sqlite(plaintext: str) -> str:
    """Encrypt using AES-256-GCM. Output is base64(nonce || ct || tag)."""
    if not plaintext:
        return ""
    nonce = os.urandom(_AES_NONCE_SIZE)
    ct = AESGCM(_aes_key()).encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.b64encode(nonce + ct).decode("ascii")


def _decrypt_sqlite(ciphertext: str) -> str:
    """Decrypt AES-256-GCM payload produced by `_encrypt_sqlite`."""
    if not ciphertext:
        return ""
    raw = base64.b64decode(ciphertext.encode("ascii"))
    nonce, ct = raw[:_AES_NONCE_SIZE], raw[_AES_NONCE_SIZE:]
    pt = AESGCM(_aes_key()).decrypt(nonce, ct, None)
    return pt.decode("utf-8")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def encrypt_text(session: Session, plaintext: str) -> str:
    """Encrypt `plaintext` with the process key, return the ciphertext.

    The dialect of the session's bind determines the cipher:
    PostgreSQL → pgcrypto; SQLite → AES-256-GCM.

    Empty / None input is passed through as the empty string. This is
    intentional: audit rows with no payload are common, and storing the
    empty string is cheaper than encrypting an empty string and matches
    the prior behaviour (empty string in the column).
    """
    if plaintext is None or plaintext == "":
        return ""
    dialect = _dialect_name(session)
    if dialect == "postgresql":
        return _encrypt_postgres(session, plaintext)
    if dialect == "sqlite":
        return _encrypt_sqlite(plaintext)
    raise RuntimeError(
        f"encrypt_text: unsupported dialect {dialect!r}. "
        "Only PostgreSQL (pgcrypto) and SQLite (AES-256-GCM) are supported."
    )


def decrypt_text(session: Session, ciphertext: str) -> str:
    """Decrypt `ciphertext` with the process key, return the plaintext.

    Empty / None input is passed through as the empty string, matching
    the convention in `encrypt_text`.

    If decryption fails (e.g. wrong key, or legacy plaintext that was
    never encrypted), the function returns the original input unchanged
    rather than raising. This makes the migration path forgiving: audit
    rows written before this gate will continue to be readable. Rows
    written after the gate will decrypt normally.
    """
    if ciphertext is None or ciphertext == "":
        return ""
    dialect = _dialect_name(session)
    try:
        if dialect == "postgresql":
            return _decrypt_postgres(session, ciphertext)
        if dialect == "sqlite":
            return _decrypt_sqlite(ciphertext)
        # Unknown dialect — try the input as-is, then fall back to
        # returning it unchanged. This is the safest behaviour for a
        # migration window.
        return ciphertext
    except Exception:
        # Legacy plaintext (pre-HD-PHASE8-004) or wrong key. Return as-is
        # so the application stays forward-readable.
        return ciphertext
