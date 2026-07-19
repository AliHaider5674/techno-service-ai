"""TOTP 2FA — Closes GAP-PHASE1-001.

Implements RFC 6238 TOTP for the second-factor mechanism. The
specific mechanism (TOTP vs WebAuthn vs SMS vs push) was a
Phase 1 open gap; Phase 8 selects TOTP as the default
enterprise mechanism (constant-time, offline-capable,
auditable).

Constitutional source:
  - Document 04 (Account & Security Settings) — references
    "second factor" without prescribing a mechanism.
  - Constitution Article XXV (Security).
  - Constitution Article XII (Human Approval / access).
  - Document 06 §9 (Notification channel eligibility).

This module is pure logic. It does not depend on a third-party
TOTP library — the algorithm is short and well-defined
(RFC 6238 + RFC 4226 HMAC-SHA1).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
from dataclasses import dataclass
from enum import Enum


# ---------------------------------------------------------------------------
# RFC 6238 / RFC 4226 — pure-Python implementation
# ---------------------------------------------------------------------------


def _hotp(secret: bytes, counter: int, digits: int = 6) -> str:
    """RFC 4226 HOTP."""
    counter_bytes = struct.pack(">Q", counter)
    h = hmac.new(secret, counter_bytes, hashlib.sha1).digest()
    offset = h[-1] & 0x0F
    code_int = (
        ((h[offset] & 0x7F) << 24)
        | ((h[offset + 1] & 0xFF) << 16)
        | ((h[offset + 2] & 0xFF) << 8)
        | (h[offset + 3] & 0xFF)
    )
    return str(code_int % (10 ** digits)).zfill(digits)


def _base32_decode(secret: str) -> bytes:
    """Decode a base32 secret (with or without padding)."""
    pad = "=" * (-len(secret) % 8)
    return base64.b32decode(secret.upper() + pad)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class TotpStatus(str, Enum):
    """The status of a TOTP verification attempt."""

    VALID = "VALID"
    INVALID_CODE = "INVALID_CODE"
    EXPIRED = "EXPIRED"
    REPLAY = "REPLAY"  # same code used twice (anti-replay)


@dataclass(frozen=True)
class TotpSpec:
    """A TOTP challenge."""

    secret: str  # base32-encoded
    code: str  # 6-digit code supplied by the user
    timestamp: int  # unix timestamp; defaults to now()
    window: int = 1  # ±window steps (30s each)


class TotpEngine:
    """The TOTP 2FA engine.

    Generates secrets, computes the current code, and verifies
    a supplied code with replay protection.

    Per Constitution Article XXV (Security), the secret is generated
    using `secrets.token_bytes` (CSPRNG) and never written to logs.

    Per Document 06 §9 + UI/UX §10 NOT-001..005, 2FA delivery
    follows the Notification channel eligibility — SMS / push for
    Class 3/4; in-app for Class 1/2.
    """

    DIGITS = 6
    PERIOD = 30  # seconds

    def generate_secret(self, n_bytes: int = 20) -> str:
        """Generate a new base32-encoded TOTP secret (default 160 bits)."""
        raw = secrets.token_bytes(n_bytes)
        return base64.b32encode(raw).decode("ascii").rstrip("=")

    def current_code(self, secret: str, timestamp: int | None = None) -> str:
        """Compute the current TOTP code (for testing / provisioning)."""
        ts = timestamp if timestamp is not None else int(time.time())
        counter = ts // self.PERIOD
        key = _base32_decode(secret)
        return _hotp(key, counter, self.DIGITS)

    def verify(self, spec: TotpSpec, used_codes: set[int] | None = None) -> TotpStatus:
        """Verify a supplied code.

        `used_codes` is the set of counter values already accepted
        (anti-replay). The verification window is ±`spec.window`
        steps of 30s each. Codes outside the window are
        `EXPIRED`; codes within the window but already used are
        `REPLAY`.
        """
        ts = spec.timestamp
        counter = ts // self.PERIOD
        key = _base32_decode(spec.secret)
        used = used_codes or set()

        for offset in range(-spec.window, spec.window + 1):
            c = counter + offset
            if c in used:
                continue
            if _hotp(key, c, self.DIGITS) == spec.code:
                return TotpStatus.VALID

        # Re-check expired vs replay
        for offset in range(-spec.window, spec.window + 1):
            c = counter + offset
            if c in used and _hotp(key, c, self.DIGITS) == spec.code:
                return TotpStatus.REPLAY
        return TotpStatus.EXPIRED
