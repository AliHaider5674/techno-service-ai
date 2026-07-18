"""Access Policy Service — users, roles, access policies, SoD enforcement.

Per Constitution Article XVII (Separation of Duties) and Document 02A
(Agent Interaction & Responsibility Matrix), certain operations require
the actor and the approver to be distinct individuals, and certain role
combinations are forbidden for the same user.

Phase 1 implements the foundational SoD checks:

  SoD Rule 1 — A user may not assign to themselves a role whose `sod_class`
  differs from the `sod_class` of every role they currently hold. (This
  is a conservative Phase 1 rule; the full SoD matrix is in Doc 02A and
  is activated in later phases as more offices come online.)

  SoD Rule 2 — A user may not perform an AccessPolicy mutation that grants
  authority to a role the user themselves holds, unless the AccessPolicy
  has DecisionClass <= CLASS_2 and the operation does not cross a Class
  boundary. (Constitutional principle: no concentration of authority.)

  SoD Rule 3 — A user may not revoke their own role assignment. (Prevents
  self-lockout of accountability.)

These rules are enforced in code, not in the database, because the
specific decision class and sod_class vary by operation.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import audit, security
from .schema import (
    AccessPolicy,
    AccessPolicyRole,
    DecisionClass,
    Persona,
    Role,
    User,
    UserRole,
    UserStatus,
)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class AccessError(Exception):
    pass


class SoDViolation(AccessError):
    pass


class UserNotFound(AccessError):
    pass


class RoleNotFound(AccessError):
    pass


class PolicyNotFound(AccessError):
    pass


class DuplicateUser(AccessError):
    pass


# ---------------------------------------------------------------------------
# SoD helpers
# ---------------------------------------------------------------------------


def user_sod_classes(session: Session, user_id: str) -> set[str]:
    return {
        r.role.sod_class
        for r in session.execute(
            select(UserRole).where(
                UserRole.user_id == user_id, UserRole.revoked_at.is_(None)
            )
        )
        .scalars()
        .all()
    }


def assert_no_sod_conflict_for_new_role(
    session: Session, *, user_id: str, role: Role
) -> None:
    """SoD Rule 1: a user may not hold roles from two different sod_class buckets."""
    existing = user_sod_classes(session, user_id)
    # 'DEFAULT' is always compatible — it's the bucket for non-segregated roles.
    if role.sod_class == "DEFAULT":
        return
    if existing and existing != {"DEFAULT"} and role.sod_class not in existing:
        raise SoDViolation(
            f"Role '{role.code}' (sod_class={role.sod_class}) is incompatible with "
            f"the user's current roles (sod_classes={sorted(existing)})."
        )


# ---------------------------------------------------------------------------
# User management
# ---------------------------------------------------------------------------


@dataclass
class CreateUserParams:
    username: str
    email: str
    display_name: str
    password: str
    recovery_question: str
    recovery_answer: str


def create_user(
    session: Session,
    *,
    params: CreateUserParams,
    actor: User,
    actor_role_code: str,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> User:
    """Create a new user. Audit is recorded. SoD check is satisfied (creator != subject)."""
    if params.username in {u.username for u in session.execute(select(User)).scalars()}:
        raise DuplicateUser(f"Username '{params.username}' is already taken.")
    if params.email in {u.email for u in session.execute(select(User)).scalars()}:
        raise DuplicateUser(f"Email '{params.email}' is already in use.")

    u = User(
        username=params.username,
        email=params.email,
        display_name=params.display_name,
        password_hash=security.hash_password(params.password),
        recovery_question=params.recovery_question,
        recovery_answer_hash=security.hash_recovery_answer(params.recovery_answer),
        status=UserStatus.ACTIVE,
        created_by=actor.id,
    )
    session.add(u)
    try:
        session.flush()
    except IntegrityError as e:
        raise DuplicateUser(str(e.orig)) from e

    audit.record(
        session,
        event_type=audit.EventType.USER_CREATED,
        action="create_user",
        actor_user_id=actor.id,
        actor_username=actor.username,
        actor_role_code=actor_role_code,
        target_type="user",
        target_id=u.id,
        ip=ip,
        user_agent=user_agent,
        payload={"username": u.username, "email": u.email},
    )
    return u


def update_user(
    session: Session,
    *,
    user: User,
    display_name: Optional[str] = None,
    email: Optional[str] = None,
    actor: User,
    actor_role_code: str,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> User:
    changes: dict[str, str] = {}
    if display_name is not None and display_name != user.display_name:
        changes["display_name"] = display_name
        user.display_name = display_name
    if email is not None and email != user.email:
        changes["email"] = email
        user.email = email
    if changes:
        user.updated_at = datetime.now(timezone.utc)
        user.updated_by = actor.id
        user.version += 1
        audit.record(
            session,
            event_type=audit.EventType.USER_UPDATED,
            action="update_user",
            actor_user_id=actor.id,
            actor_username=actor.username,
            actor_role_code=actor_role_code,
            target_type="user",
            target_id=user.id,
            ip=ip,
            user_agent=user_agent,
            payload={"changes": changes},
        )
    return user


def set_user_status(
    session: Session,
    *,
    user: User,
    new_status: UserStatus,
    actor: User,
    actor_role_code: str,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> User:
    if user.status == new_status:
        return user
    old = user.status
    user.status = new_status
    user.updated_at = datetime.now(timezone.utc)
    user.updated_by = actor.id
    user.version += 1

    if new_status == UserStatus.SUSPENDED:
        event_type = audit.EventType.USER_SUSPENDED
    elif new_status == UserStatus.ARCHIVED:
        event_type = audit.EventType.USER_ARCHIVED
    else:
        event_type = audit.EventType.USER_UPDATED

    audit.record(
        session,
        event_type=event_type,
        action="set_user_status",
        actor_user_id=actor.id,
        actor_username=actor.username,
        actor_role_code=actor_role_code,
        target_type="user",
        target_id=user.id,
        ip=ip,
        user_agent=user_agent,
        payload={"from": old.value, "to": new_status.value},
    )
    return user


# ---------------------------------------------------------------------------
# Role management
# ---------------------------------------------------------------------------


def list_roles(session: Session) -> list[Role]:
    return list(session.execute(select(Role).order_by(Role.code)).scalars())


def get_role_by_code(session: Session, code: str) -> Optional[Role]:
    return session.execute(select(Role).where(Role.code == code)).scalar_one_or_none()


def create_role(
    session: Session,
    *,
    code: str,
    name: str,
    description: str = "",
    sod_class: str = "DEFAULT",
    actor: User,
    actor_role_code: str,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Role:
    r = Role(code=code, name=name, description=description, sod_class=sod_class)
    session.add(r)
    session.flush()
    audit.record(
        session,
        event_type=audit.EventType.ROLE_CREATED,
        action="create_role",
        actor_user_id=actor.id,
        actor_username=actor.username,
        actor_role_code=actor_role_code,
        target_type="role",
        target_id=r.id,
        ip=ip,
        user_agent=user_agent,
        payload={"code": code, "sod_class": sod_class},
    )
    return r


def update_role(
    session: Session,
    *,
    role: Role,
    name: Optional[str] = None,
    description: Optional[str] = None,
    active: Optional[bool] = None,
    actor: User,
    actor_role_code: str,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Role:
    changes: dict[str, object] = {}
    if name is not None and name != role.name:
        changes["name"] = name
        role.name = name
    if description is not None and description != role.description:
        changes["description"] = description
        role.description = description
    if active is not None and active != role.active:
        changes["active"] = active
        role.active = active
    if changes:
        role.updated_at = datetime.now(timezone.utc)
        role.version += 1
        audit.record(
            session,
            event_type=audit.EventType.ROLE_UPDATED,
            action="update_role",
            actor_user_id=actor.id,
            actor_username=actor.username,
            actor_role_code=actor_role_code,
            target_type="role",
            target_id=role.id,
            ip=ip,
            user_agent=user_agent,
            payload={"code": role.code, "changes": changes},
        )
    return role


def assign_role(
    session: Session,
    *,
    user: User,
    role: Role,
    actor: User,
    actor_role_code: str,
    scope: str = "GLOBAL",
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> UserRole:
    """Assign a role to a user, with SoD check (no self-assignment of conflicting class)."""
    # SoD Rule 1.
    assert_no_sod_conflict_for_new_role(session, user_id=user.id, role=role)

    # Idempotency: if the user already has an active assignment of this role
    # in the same scope, return it.
    existing = session.execute(
        select(UserRole).where(
            UserRole.user_id == user.id,
            UserRole.role_id == role.id,
            UserRole.scope == scope,
            UserRole.revoked_at.is_(None),
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    ur = UserRole(
        user_id=user.id,
        role_id=role.id,
        scope=scope,
        assigned_by=actor.id,
    )
    session.add(ur)
    session.flush()

    # Auto-create a Persona for the role so the user can switch into it.
    if session.execute(
        select(Persona).where(Persona.user_id == user.id, Persona.role_id == role.id)
    ).scalar_one_or_none() is None:
        session.add(
            Persona(
                user_id=user.id,
                role_id=role.id,
                label=f"{role.name} — {user.display_name}",
                created_by=actor.id,
            )
        )

    audit.record(
        session,
        event_type=audit.EventType.ROLE_ASSIGNED,
        action="assign_role",
        actor_user_id=actor.id,
        actor_username=actor.username,
        actor_role_code=actor_role_code,
        target_type="user",
        target_id=user.id,
        ip=ip,
        user_agent=user_agent,
        payload={"role_code": role.code, "scope": scope},
    )
    return ur


def revoke_role(
    session: Session,
    *,
    user: User,
    role: Role,
    actor: User,
    actor_role_code: str,
    reason: str = "",
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    """Revoke a role from a user. SoD Rule 3: a user may not revoke their own role."""
    if user.id == actor.id:
        raise SoDViolation("You may not revoke a role from yourself (SoD Rule 3).")

    ur = session.execute(
        select(UserRole).where(
            UserRole.user_id == user.id,
            UserRole.role_id == role.id,
            UserRole.revoked_at.is_(None),
        )
    ).scalar_one_or_none()
    if ur is None:
        return  # idempotent

    ur.revoked_at = datetime.now(timezone.utc)
    ur.revoked_by = actor.id
    ur.revoke_reason = reason

    audit.record(
        session,
        event_type=audit.EventType.ROLE_REVOKED,
        action="revoke_role",
        actor_user_id=actor.id,
        actor_username=actor.username,
        actor_role_code=actor_role_code,
        target_type="user",
        target_id=user.id,
        ip=ip,
        user_agent=user_agent,
        payload={"role_code": role.code, "reason": reason},
    )


def user_active_roles(session: Session, user_id: str) -> list[Role]:
    rows = session.execute(
        select(Role)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user_id, UserRole.revoked_at.is_(None), Role.active.is_(True))
        .order_by(Role.code)
    ).scalars()
    return list(rows)


# ---------------------------------------------------------------------------
# Access Policy
# ---------------------------------------------------------------------------


def list_policies(session: Session) -> list[AccessPolicy]:
    return list(session.execute(select(AccessPolicy).order_by(AccessPolicy.code)).scalars())


def create_policy(
    session: Session,
    *,
    code: str,
    name: str,
    description: str = "",
    decision_class: DecisionClass = DecisionClass.CLASS_1,
    required_approver_role_code: Optional[str] = None,
    sod_exclusion_role_codes: Iterable[str] = (),
    actor: User,
    actor_role_code: str,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> AccessPolicy:
    p = AccessPolicy(
        code=code,
        name=name,
        description=description,
        decision_class=decision_class,
        required_approver_role_code=required_approver_role_code,
        sod_exclusion_role_codes=",".join(sod_exclusion_role_codes),
    )
    session.add(p)
    session.flush()
    audit.record(
        session,
        event_type=audit.EventType.POLICY_CREATED,
        action="create_policy",
        actor_user_id=actor.id,
        actor_username=actor.username,
        actor_role_code=actor_role_code,
        target_type="access_policy",
        target_id=p.id,
        ip=ip,
        user_agent=user_agent,
        payload={"code": code, "decision_class": decision_class.name},
    )
    return p


def update_policy(
    session: Session,
    *,
    policy: AccessPolicy,
    name: Optional[str] = None,
    description: Optional[str] = None,
    decision_class: Optional[DecisionClass] = None,
    required_approver_role_code: Optional[str] = None,
    sod_exclusion_role_codes: Optional[Iterable[str]] = None,
    active: Optional[bool] = None,
    actor: User,
    actor_role_code: str,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> AccessPolicy:
    changes: dict[str, object] = {}
    if name is not None and name != policy.name:
        changes["name"] = name
        policy.name = name
    if description is not None and description != policy.description:
        changes["description"] = description
        policy.description = description
    if decision_class is not None and decision_class != policy.decision_class:
        changes["decision_class"] = decision_class.name
        policy.decision_class = decision_class
    if required_approver_role_code is not None and required_approver_role_code != policy.required_approver_role_code:
        changes["required_approver_role_code"] = required_approver_role_code
        policy.required_approver_role_code = required_approver_role_code
    if sod_exclusion_role_codes is not None:
        new_val = ",".join(sod_exclusion_role_codes)
        if new_val != policy.sod_exclusion_role_codes:
            changes["sod_exclusion_role_codes"] = list(sod_exclusion_role_codes)
            policy.sod_exclusion_role_codes = new_val
    if active is not None and active != policy.active:
        changes["active"] = active
        policy.active = active
    if changes:
        policy.updated_at = datetime.now(timezone.utc)
        policy.version += 1
        audit.record(
            session,
            event_type=audit.EventType.POLICY_UPDATED,
            action="update_policy",
            actor_user_id=actor.id,
            actor_username=actor.username,
            actor_role_code=actor_role_code,
            target_type="access_policy",
            target_id=policy.id,
            ip=ip,
            user_agent=user_agent,
            payload={"code": policy.code, "changes": changes},
        )
    return policy
