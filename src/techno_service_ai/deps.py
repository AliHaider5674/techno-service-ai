"""Request dependencies used by FastAPI route handlers.

`current_principal` is the single point where the JWT cookie is validated
on every protected request. It is the gate that satisfies AC-SEC-002
(authentication enforced) and AC-SEC-003 (authorisation enforced via
`require_role` / `require_any_role`).

The Principal carries only IDs (user_id, session_id, persona_id) and the
list of active role codes. Handlers that need a fully-attached User
object re-fetch it in their own session scope. This avoids the
DetachedInstanceError that arises from the dependency's session being
closed before the handler runs.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import Cookie, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from .auth import validate_session
from .config import SETTINGS
from .db import SessionLocal
from .schema import UserStatus


def get_db() -> Session:
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


@dataclass
class Principal:
    user_id: str
    username: str
    display_name: str
    session_id: str
    persona_id: Optional[str] = None
    persona_label: Optional[str] = None
    role_codes: tuple[str, ...] = ()


def current_principal(
    request: Request,
    db: Session = Depends(get_db),
    tsai_session: Optional[str] = Cookie(default=None, alias=SETTINGS.cookie_name),
) -> Principal:
    if not tsai_session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated.")
    validated = validate_session(db, jwt_token=tsai_session)
    if validated is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session invalid or expired.")
    user, sess, _claims = validated
    if user.status != UserStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is not active.")

    role_codes = tuple(
        r.role.code
        for r in user.roles
        if r.revoked_at is None and r.role.active
    )
    persona_label = None
    if sess.persona_id:
        # Use raw SQL to read persona.label without keeping the persona attached.
        from sqlalchemy import text
        row = db.execute(
            text("SELECT label FROM persona WHERE id = :i"),
            {"i": sess.persona_id},
        ).first()
        persona_label = row[0] if row else None
    return Principal(
        user_id=user.id,
        username=user.username,
        display_name=user.display_name,
        session_id=sess.id,
        persona_id=sess.persona_id,
        persona_label=persona_label,
        role_codes=role_codes,
    )


def require_any_role(*required_codes: str):
    """Dependency factory: the principal must hold at least one of the given role codes."""
    required = tuple(required_codes)

    def _dep(principal: Principal = Depends(current_principal)) -> Principal:
        if not required:
            return principal
        if not any(code in principal.role_codes for code in required):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {', '.join(required)}.",
            )
        return principal

    return _dep


def client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    if request.client:
        return request.client.host
    return ""


def client_ua(request: Request) -> str:
    return request.headers.get("user-agent", "")[:255]
