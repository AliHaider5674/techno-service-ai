"""Configuration for the Techno Service AI Intelligence System.

Per Constitution Article XXVIII and the Implementer README §6, the implementer
selects the language, framework, database, and other tech-stack items within
the boundaries of the approved documents. All such selections are recorded in
`docs/DECISION_AND_ASSUMPTION_REGISTER.md` (ASS-PHASE1-001..004).

This module is the single place where the selections are applied. Changing
a value here without first updating the Decision & Assumption Register is a
violation of the Implementer README §6.
"""
from __future__ import annotations

import os
import secrets
from dataclasses import dataclass, field
from pathlib import Path


# Repo root = two parents up from this file (src/techno_service_ai/config.py).
REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load_or_create_jwt_secret() -> str:
    """Load the JWT secret from disk, or create one for first run.

    Per Article XXV (security), the secret must not be derivable from the
    repository. For Phase 1 development we generate and persist a random
    256-bit secret in DATA_DIR/.jwt_secret (file is gitignored). Production
    deployments MUST set TSAI_JWT_SECRET via environment / secret store.
    """
    env_secret = os.environ.get("TSAI_JWT_SECRET")
    if env_secret:
        return env_secret
    secret_path = DATA_DIR / ".jwt_secret"
    if secret_path.exists():
        return secret_path.read_text(encoding="utf-8").strip()
    new_secret = secrets.token_urlsafe(32)
    secret_path.write_text(new_secret, encoding="utf-8")
    try:
        os.chmod(secret_path, 0o600)  # noqa: S103
    except OSError:
        pass
    return new_secret


@dataclass(frozen=True)
class Settings:
    # Database — SQLite, vendor-neutral per Document 04. Override via env.
    database_url: str = field(
        default_factory=lambda: os.environ.get(
            "TSAI_DATABASE_URL",
            f"sqlite:///{(DATA_DIR / 'tsai.db').as_posix()}",
        )
    )

    # JWT — signing key.
    jwt_secret: str = field(default_factory=_load_or_create_jwt_secret)
    jwt_algorithm: str = "HS256"
    jwt_lifetime_seconds: int = field(
        default_factory=lambda: int(os.environ.get("TSAI_JWT_LIFETIME", "3600"))
    )
    session_lifetime_seconds: int = field(
        default_factory=lambda: int(os.environ.get("TSAI_SESSION_LIFETIME", "28800"))
    )

    # Audit retention — per Constitution Article XX.
    audit_retention_class: str = field(
        default_factory=lambda: os.environ.get("TSAI_AUDIT_RETENTION", "PERMANENT")
    )

    # Cookie settings.
    cookie_secure: bool = field(
        default_factory=lambda: os.environ.get("TSAI_COOKIE_SECURE", "0") == "1"
    )
    cookie_name: str = "tsai_session"

    # Bootstrap defaults.
    default_admin_username: str = "admin"
    default_admin_password: str = field(
        default_factory=lambda: os.environ.get("TSAI_DEFAULT_ADMIN_PASSWORD", "ChangeMe!2026")
    )


SETTINGS = Settings()
