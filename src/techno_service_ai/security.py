"""Password hashing, JWT signing, and small crypto helpers.

Per Constitution Article XXV (Security and Continuity) and Document 04
(Security Layer), credentials and tokens use industry-standard algorithms:

  - Password hashing: bcrypt (via passlib). Slow by design, salted.
  - JWT: HS256, 1h lifetime by default. Stored in HttpOnly cookie.
  - Token-hash for session lookup: SHA-256 (no security need for a slow
    hash here, the JWT itself is the bearer credential).
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from passlib.context import CryptContext

from .config import SETTINGS


_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ---------------------------------------------------------------------------
# Passwords
# ---------------------------------------------------------------------------


def hash_password(plaintext: str) -> str:
    """Return a bcrypt hash of `plaintext`. Never store the plaintext."""
    return _pwd.hash(plaintext)


def verify_password(plaintext: str, hashed: str) -> bool:
    """Return True if `plaintext` matches `hashed`."""
    try:
        return _pwd.verify(plaintext, hashed)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Recovery answers
# ---------------------------------------------------------------------------

# Recovery answers are normalised (lower-cased, leading/trailing whitespace
# stripped) and then bcrypt-hashed. This means the system can verify an
# answer but never recover it in cleartext.

def normalise_recovery_answer(answer: str) -> str:
    return (answer or "").strip().lower()


def hash_recovery_answer(answer: str) -> str:
    return _pwd.hash(normalise_recovery_answer(answer))


def verify_recovery_answer(answer: str, hashed: str) -> bool:
    return verify_password(normalise_recovery_answer(answer), hashed)


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------


def sign_jwt(*, subject: str, session_id: str, extra: dict[str, Any] | None = None) -> tuple[str, datetime]:
    """Sign a JWT for `subject` (user id) bound to `session_id`. Returns (jwt, expires_at)."""
    now = datetime.now(timezone.utc)
    exp = now + timedelta(seconds=SETTINGS.jwt_lifetime_seconds)
    payload: dict[str, Any] = {
        "sub": subject,
        "sid": session_id,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    if extra:
        payload.update(extra)
    token = jwt.encode(payload, SETTINGS.jwt_secret, algorithm=SETTINGS.jwt_algorithm)
    return token, exp


def decode_jwt(token: str) -> dict[str, Any]:
    """Decode and verify a JWT. Raises jwt.PyJWTError on failure."""
    return jwt.decode(token, SETTINGS.jwt_secret, algorithms=[SETTINGS.jwt_algorithm])


def hash_token(token: str) -> str:
    """Return a SHA-256 hex digest of `token` for session lookup storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
