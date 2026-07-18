"""Identity and Session services — sign in, sign out, recover, password change.

Per Constitution Article XII paragraph 3 (Class 1 Internal Intelligence
Decisions) these are operational, not approval-gated. The audit trail
records every action (AC-P1-004 / AC-AUD-001).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import audit, security
from .config import SETTINGS
from .schema import SessionStatus, User, UserSession, UserStatus, _as_utc


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class AuthError(Exception):
    """Base authentication / identity error."""


class InvalidCredentials(AuthError):
    pass


class AccountInactive(AuthError):
    pass


class AccountLocked(AuthError):
    pass


class InvalidRecovery(AuthError):
    pass


# ---------------------------------------------------------------------------
# Sign in
# ---------------------------------------------------------------------------


@dataclass
class SignInResult:
    user_id: str
    username: str
    session_id: str
    jwt: str
    expires_at: datetime


def sign_in(
    session: Session,
    *,
    username: str,
    password: str,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> SignInResult:
    """Authenticate a user and create a session. Records audit on success and failure.

    AC-P1-001 (sign in) is satisfied by this function.
    """
    user = session.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if user is None:
        audit.record(
            session,
            event_type=audit.EventType.SIGN_IN_FAILED,
            action="sign_in",
            actor_username=username,
            outcome="FAILURE",
            ip=ip,
            user_agent=user_agent,
            payload={"reason": "unknown_user"},
        )
        raise InvalidCredentials("Invalid username or password.")

    if user.status != UserStatus.ACTIVE:
        audit.record(
            session,
            event_type=audit.EventType.SIGN_IN_FAILED,
            action="sign_in",
            actor_user_id=user.id,
            actor_username=user.username,
            outcome="FAILURE",
            ip=ip,
            user_agent=user_agent,
            payload={"reason": "inactive", "status": user.status.value},
        )
        raise AccountInactive(f"Account is {user.status.value}.")

    if not security.verify_password(password, user.password_hash):
        audit.record(
            session,
            event_type=audit.EventType.SIGN_IN_FAILED,
            action="sign_in",
            actor_user_id=user.id,
            actor_username=user.username,
            outcome="FAILURE",
            ip=ip,
            user_agent=user_agent,
            payload={"reason": "bad_password"},
        )
        raise InvalidCredentials("Invalid username or password.")

    # Success — create session, sign JWT.
    now = datetime.now(timezone.utc)
    expires = now + timedelta(seconds=SETTINGS.session_lifetime_seconds)
    # First, create the session row so we have a session id to bind into the JWT.
    sess = UserSession(
        user_id=user.id,
        token_hash="pending",  # will be replaced once the JWT is signed
        ip=ip,
        user_agent=user_agent,
        status=SessionStatus.ACTIVE,
        created_at=now,
        last_activity_at=now,
        expires_at=expires,
    )
    session.add(sess)
    session.flush()
    # Now sign the JWT bound to the real session id and re-hash.
    jwt_token, jwt_exp = security.sign_jwt(subject=user.id, session_id=sess.id)
    sess.token_hash = security.hash_token(jwt_token)

    # Re-sign JWT now that we have a real session id.
    jwt_token, jwt_exp = security.sign_jwt(subject=user.id, session_id=sess.id)
    # Re-hash because the token changed.
    sess.token_hash = security.hash_token(jwt_token)

    audit.record(
        session,
        event_type=audit.EventType.SIGN_IN,
        action="sign_in",
        actor_user_id=user.id,
        actor_username=user.username,
        actor_session_id=sess.id,
        outcome="SUCCESS",
        ip=ip,
        user_agent=user_agent,
    )
    return SignInResult(
        user_id=user.id,
        username=user.username,
        session_id=sess.id,
        jwt=jwt_token,
        expires_at=jwt_exp,
    )


# ---------------------------------------------------------------------------
# Sign out
# ---------------------------------------------------------------------------


def sign_out(
    session: Session,
    *,
    sess: UserSession,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    """Invalidate the given session. Records audit.

    AC-P1-001 (sign out) is satisfied by this function.
    """
    if sess.status == SessionStatus.INVALIDATED:
        return  # idempotent
    sess.status = SessionStatus.INVALIDATED
    sess.invalidated_at = datetime.now(timezone.utc)
    sess.invalidated_reason = "user_sign_out"
    audit.record(
        session,
        event_type=audit.EventType.SIGN_OUT,
        action="sign_out",
        actor_user_id=sess.user_id,
        actor_session_id=sess.id,
        outcome="SUCCESS",
        ip=ip,
        user_agent=user_agent,
    )


# ---------------------------------------------------------------------------
# Recovery
# ---------------------------------------------------------------------------


def recover(
    session: Session,
    *,
    username: str,
    recovery_answer: str,
    new_password: str,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> User:
    """Reset a user's password via the recovery answer. Records audit.

    AC-P1-001 (recover) is satisfied by this function. The recovery answer
    is verified against the stored bcrypt hash; the new password replaces
    the old hash and invalidates all existing sessions.
    """
    user = session.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if user is None or user.status != UserStatus.ACTIVE:
        audit.record(
            session,
            event_type=audit.EventType.RECOVERY_INITIATED,
            action="recover",
            actor_username=username,
            outcome="FAILURE",
            ip=ip,
            user_agent=user_agent,
            payload={"reason": "unknown_or_inactive_user"},
        )
        raise InvalidRecovery("Recovery is not available for this account.")

    audit.record(
        session,
        event_type=audit.EventType.RECOVERY_INITIATED,
        action="recover",
        actor_user_id=user.id,
        actor_username=user.username,
        outcome="SUCCESS",
        ip=ip,
        user_agent=user_agent,
    )

    if not security.verify_recovery_answer(recovery_answer, user.recovery_answer_hash):
        audit.record(
            session,
            event_type=audit.EventType.RECOVERY_COMPLETED,
            action="recover",
            actor_user_id=user.id,
            actor_username=user.username,
            outcome="FAILURE",
            ip=ip,
            user_agent=user_agent,
            payload={"reason": "bad_recovery_answer"},
        )
        raise InvalidRecovery("Recovery answer did not match.")

    # Apply new password and invalidate all active sessions.
    user.password_hash = security.hash_password(new_password)
    user.updated_at = datetime.now(timezone.utc)
    user.version += 1

    invalidated_now = datetime.now(timezone.utc)
    active_sessions = (
        session.execute(
            select(UserSession).where(
                UserSession.user_id == user.id,
                UserSession.status == SessionStatus.ACTIVE,
            )
        )
        .scalars()
        .all()
    )
    for s in active_sessions:
        s.status = SessionStatus.INVALIDATED
        s.invalidated_at = invalidated_now
        s.invalidated_reason = "password_recovery"

    audit.record(
        session,
        event_type=audit.EventType.RECOVERY_COMPLETED,
        action="recover",
        actor_user_id=user.id,
        actor_username=user.username,
        outcome="SUCCESS",
        ip=ip,
        user_agent=user_agent,
        payload={"invalidated_sessions": len(active_sessions)},
    )
    return user


# ---------------------------------------------------------------------------
# Password change (signed-in user)
# ---------------------------------------------------------------------------


def change_password(
    session: Session,
    *,
    user: User,
    current_password: str,
    new_password: str,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    if not security.verify_password(current_password, user.password_hash):
        raise InvalidCredentials("Current password is incorrect.")
    user.password_hash = security.hash_password(new_password)
    user.updated_at = datetime.now(timezone.utc)
    user.version += 1
    audit.record(
        session,
        event_type=audit.EventType.PASSWORD_CHANGED,
        action="change_password",
        actor_user_id=user.id,
        actor_username=user.username,
        outcome="SUCCESS",
        ip=ip,
        user_agent=user_agent,
    )


# ---------------------------------------------------------------------------
# Session validation
# ---------------------------------------------------------------------------


def validate_session(
    session: Session,
    *,
    jwt_token: str,
) -> Optional[tuple[User, UserSession, dict]]:
    """Return (user, session, claims) if the JWT is valid and the session is ACTIVE; else None.

    Used by request dependencies to authenticate every protected request.
    AC-SEC-002 (authentication enforced) is satisfied by `app.py` calling
    this from a dependency on every protected route.
    """
    try:
        claims = security.decode_jwt(jwt_token)
    except Exception:
        return None

    sid = claims.get("sid")
    sub = claims.get("sub")
    if not sid or not sub:
        return None

    sess = session.get(UserSession, sid)
    if sess is None or sess.user_id != sub:
        return None
    if sess.status != SessionStatus.ACTIVE:
        return None
    if _as_utc(sess.expires_at) < datetime.now(timezone.utc):
        return None

    user = session.get(User, sub)
    if user is None or user.status != UserStatus.ACTIVE:
        return None

    # Update last-activity (audit-friendly, not security-critical).
    sess.last_activity_at = datetime.now(timezone.utc)
    return user, sess, claims
