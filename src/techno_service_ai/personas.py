"""Persona Service — list and select the active persona for a session.

Per Constitution Article XII paragraph 3 (Class 1) and the Phase 1 Backlog
IMPL-P1-004, persona selection is an operational decision that the user
performs; the system context changes accordingly. Per AC-P1-002 the
selection must be reflected in the session and the audit log.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import audit
from .schema import Persona, User, UserSession


def list_for_user(session: Session, user: User) -> list[Persona]:
    return list(
        session.execute(
            select(Persona)
            .where(Persona.user_id == user.id, Persona.status == "ACTIVE")  # noqa: E711
            .order_by(Persona.label)
        ).scalars()
    )


def select_persona(
    session: Session,
    *,
    sess: UserSession,
    persona: Persona,
    user: User,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> UserSession:
    if persona.user_id != user.id:
        raise ValueError("Persona does not belong to the current user.")
    sess.persona_id = persona.id
    audit.record(
        session,
        event_type=audit.EventType.PERSONA_SELECTED,
        action="select_persona",
        actor_user_id=user.id,
        actor_username=user.username,
        actor_session_id=sess.id,
        target_type="persona",
        target_id=persona.id,
        ip=ip,
        user_agent=user_agent,
        payload={"persona_label": persona.label, "role_id": persona.role_id},
    )
    return sess
