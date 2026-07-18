"""FastAPI application — Phase 1 routes (Identity, Access, Audit).

Screens delivered:
  Identity & Access  (4)   sign_in, recover, persona_select, account_security
  Administration     (6)   users, user_edit, roles, role_edit, access_policies, access_policy_edit
  Audit              (1)   audit_log

This module wires the route handlers to the services. The actual business
logic lives in `auth`, `access`, `personas`, and `audit` — these handlers
only translate HTTP <-> service calls and render templates.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import (
    Cookie,
    Depends,
    FastAPI,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    status,
)
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response as FastResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import access, audit, auth, personas
from .config import SETTINGS
from .db import SessionLocal, apply_schema, session_scope
from .deps import Principal, client_ip, client_ua, current_principal, get_db, require_any_role
from .schema import (
    AccessPolicy,
    DecisionClass,
    Persona,
    Role,
    User,
    UserRole,
    UserSession,
    UserStatus,
)


TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
STATIC_DIR = Path(__file__).resolve().parent / "static"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def create_app() -> FastAPI:
    app = FastAPI(
        title="Techno Service AI Intelligence System",
        version="1.0.0-phase3",
        description="Phases 1-3: Identity, Access, Audit (1); Data Foundation (2); "
                    "Workflow, Verification, and Approval Foundation (3). "
                    "Constitutional Authority: Constitution v2.3.",
    )
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # Phase 3 routes (Verification, Approval, Notification screens).
    from .phase3_routes import add_phase3_routes
    add_phase3_routes(app)

    @app.on_event("startup")
    def _startup() -> None:
        apply_schema()

    # ---- Helpers --------------------------------------------------------

    def _render(
        request: Request,
        template_name: str,
        *,
        principal: Optional[Principal] = None,
        status_code: int = 200,
        headers: Optional[dict] = None,
        **context,
    ) -> HTMLResponse:
        ctx = {
            "request": request,
            "principal": principal,
            "now": datetime.now(timezone.utc),
        }
        ctx.update(context)
        return templates.TemplateResponse(
            request, template_name, ctx, status_code=status_code, headers=headers
        )

    def _set_session_cookie(response: Response, jwt_token: str) -> None:
        response.set_cookie(
            key=SETTINGS.cookie_name,
            value=jwt_token,
            httponly=True,
            secure=SETTINGS.cookie_secure,
            samesite="lax",
            max_age=SETTINGS.session_lifetime_seconds,
            path="/",
        )

    def _clear_session_cookie(response: Response) -> None:
        response.delete_cookie(SETTINGS.cookie_name, path="/")

    # ====================================================================
    # Public / semi-public routes
    # ====================================================================

    @app.get("/", response_class=HTMLResponse)
    def home(
        request: Request,
        principal: Optional[Principal] = Depends(_optional_principal),
    ) -> Response:
        if principal is None:
            return RedirectResponse(url="/sign-in", status_code=status.HTTP_303_SEE_OTHER)
        return RedirectResponse(url="/home", status_code=status.HTTP_303_SEE_OTHER)

    @app.get("/sign-in", response_class=HTMLResponse)
    def sign_in_get(
        request: Request,
        principal: Optional[Principal] = Depends(_optional_principal),
    ) -> Response:
        if principal is not None:
            return RedirectResponse(url="/home", status_code=status.HTTP_303_SEE_OTHER)
        return _render(request, "sign_in.html", error=None, username="")

    @app.post("/sign-in")
    def sign_in_post(
        request: Request,
        username: str = Form(...),
        password: str = Form(...),
        db: Session = Depends(get_db),
    ) -> Response:
        ip = client_ip(request)
        ua = client_ua(request)
        # We capture (jwt, n_personas) in a single session to avoid detached
        # instance access. `auth.sign_in` returns the JWT and the user; the
        # persona count is queried in the same session.
        jwt_token: str = ""
        n_personas = 0
        try:
            with session_scope() as s:
                result = auth.sign_in(
                    s, username=username, password=password, ip=ip, user_agent=ua
                )
                jwt_token = result.jwt
                ps = personas.list_for_user(s, s.get(User, result.user_id))
                n_personas = len(ps)
        except auth.AuthError as e:
            return _render(
                request, "sign_in.html", error=str(e), username=username, status_code=401
            )
        resp = RedirectResponse(
            url="/persona/select" if n_personas > 1 else "/home",
            status_code=status.HTTP_303_SEE_OTHER,
        )
        _set_session_cookie(resp, jwt_token)
        return resp

    @app.get("/sign-out", response_class=HTMLResponse)
    def sign_out_get(
        request: Request,
        db: Session = Depends(get_db),
        tsai_session: Optional[str] = Cookie(default=None, alias=SETTINGS.cookie_name),
    ) -> Response:
        if tsai_session:
            with session_scope() as s:
                validated = auth.validate_session(s, jwt_token=tsai_session)
                if validated is not None:
                    _user, sess, _ = validated
                    auth.sign_out(s, sess=sess, ip=client_ip(request), user_agent=client_ua(request))
        resp = RedirectResponse(url="/sign-in", status_code=status.HTTP_303_SEE_OTHER)
        _clear_session_cookie(resp)
        return resp

    @app.post("/sign-out")
    def sign_out_post(
        request: Request,
        db: Session = Depends(get_db),
        tsai_session: Optional[str] = Cookie(default=None, alias=SETTINGS.cookie_name),
    ) -> Response:
        return sign_out_get(request, db, tsai_session)

    @app.get("/recover", response_class=HTMLResponse)
    def recover_get(request: Request) -> Response:
        return _render(request, "recover.html", error=None, step="challenge", username="")

    @app.post("/recover")
    def recover_post(
        request: Request,
        username: str = Form(...),
        recovery_answer: str = Form(...),
        new_password: str = Form(...),
        new_password_confirm: str = Form(...),
    ) -> Response:
        if new_password != new_password_confirm:
            return _render(
                request, "recover.html",
                error="New password and confirmation do not match.",
                step="challenge", username=username,
                status_code=400,
            )
        ip = client_ip(request)
        ua = client_ua(request)
        try:
            with session_scope() as s:
                auth.recover(
                    s, username=username, recovery_answer=recovery_answer,
                    new_password=new_password, ip=ip, user_agent=ua,
                )
        except auth.AuthError as e:
            return _render(
                request, "recover.html", error=str(e),
                step="challenge", username=username, status_code=400,
            )
        return RedirectResponse(url="/sign-in?recovered=1", status_code=status.HTTP_303_SEE_OTHER)

    # ====================================================================
    # Authenticated routes
    # ====================================================================

    @app.get("/home", response_class=HTMLResponse)
    def home_authed(
        request: Request,
        principal: Principal = Depends(current_principal),
    ) -> Response:
        return _render(request, "home.html", principal=principal)

    @app.get("/persona/select", response_class=HTMLResponse)
    def persona_select_get(
        request: Request,
        db: Session = Depends(get_db),
        principal: Principal = Depends(current_principal),
    ) -> Response:
        ps = personas.list_for_user(db, db.get(User, principal.user_id))
        return _render(
            request, "persona_select.html",
            principal=principal, personas=ps, error=None,
        )

    @app.post("/persona/select")
    def persona_select_post(
        request: Request,
        persona_id: str = Form(...),
        db: Session = Depends(get_db),
        principal: Principal = Depends(current_principal),
    ) -> Response:
        ps = personas.list_for_user(db, db.get(User, principal.user_id))
        chosen = next((p for p in ps if p.id == persona_id), None)
        if chosen is None:
            return _render(
                request, "persona_select.html",
                principal=principal, personas=ps,
                error="Invalid persona selection.", status_code=400,
            )
        with session_scope() as s:
            sess = s.get(UserSession, principal.session_id)
            user = s.get(User, principal.user_id)
            personas.select_persona(
                s, sess=sess, persona=chosen, user=user,
                ip=client_ip(request), user_agent=client_ua(request),
            )
        return RedirectResponse(url="/home", status_code=status.HTTP_303_SEE_OTHER)

    @app.get("/account/security", response_class=HTMLResponse)
    def account_security_get(
        request: Request,
        principal: Principal = Depends(current_principal),
    ) -> Response:
        return _render(request, "account_security.html", principal=principal, error=None, success=None)

    @app.post("/account/security")
    def account_security_post(
        request: Request,
        current_password: str = Form(...),
        new_password: str = Form(...),
        new_password_confirm: str = Form(...),
        db: Session = Depends(get_db),
        principal: Principal = Depends(current_principal),
    ) -> Response:
        if new_password != new_password_confirm:
            return _render(
                request, "account_security.html",
                principal=principal, error="New password and confirmation do not match.",
                status_code=400,
            )
        try:
            with session_scope() as s:
                user = s.get(User, principal.user_id)
                auth.change_password(
                    s, user=user, current_password=current_password,
                    new_password=new_password, ip=client_ip(request),
                    user_agent=client_ua(request),
                )
        except auth.AuthError as e:
            return _render(
                request, "account_security.html",
                principal=principal, error=str(e), status_code=400,
            )
        return _render(
            request, "account_security.html",
            principal=principal, success="Password changed.", error=None,
        )

    # ====================================================================
    # Administration routes (require ADMIN or COMPLIANCE role)
    # ====================================================================

    @app.get("/admin/users", response_class=HTMLResponse)
    def admin_users(
        request: Request,
        db: Session = Depends(get_db),
        principal: Principal = Depends(require_any_role("ADMIN", "COMPLIANCE", "AUDITOR")),
    ) -> Response:
        users = list(db.execute(select(User).order_by(User.username)).scalars())
        for u in users:
            u._role_codes = access.user_active_roles(db, u.id)  # type: ignore[attr-defined]
        return _render(request, "admin/users.html", principal=principal, users=users, error=None)

    @app.get("/admin/users/new", response_class=HTMLResponse)
    def admin_user_new_get(
        request: Request,
        principal: Principal = Depends(require_any_role("ADMIN")),
    ) -> Response:
        return _render(request, "admin/user_new.html", principal=principal, error=None)

    @app.post("/admin/users/new")
    def admin_user_new_post(
        request: Request,
        username: str = Form(...),
        email: str = Form(...),
        display_name: str = Form(...),
        password: str = Form(...),
        recovery_question: str = Form(...),
        recovery_answer: str = Form(...),
        db: Session = Depends(get_db),
        principal: Principal = Depends(require_any_role("ADMIN")),
    ) -> Response:
        new_user_id: Optional[str] = None
        with session_scope() as s:
            actor = s.get(User, principal.user_id)
            actor_role_code = principal.role_codes[0] if principal.role_codes else None
            try:
                u = access.create_user(
                    s,
                    params=access.CreateUserParams(
                        username=username, email=email, display_name=display_name,
                        password=password, recovery_question=recovery_question,
                        recovery_answer=recovery_answer,
                    ),
                    actor=actor, actor_role_code=actor_role_code,
                    ip=client_ip(request), user_agent=client_ua(request),
                )
                new_user_id = u.id  # captured while session is still alive
            except access.AccessError as e:
                return _render(
                    request, "admin/user_new.html",
                    principal=principal, error=str(e), status_code=400,
                )
        return RedirectResponse(url=f"/admin/users/{new_user_id}", status_code=status.HTTP_303_SEE_OTHER)

    @app.get("/admin/users/{user_id}", response_class=HTMLResponse)
    def admin_user_edit_get(
        user_id: str,
        request: Request,
        db: Session = Depends(get_db),
        principal: Principal = Depends(require_any_role("ADMIN", "COMPLIANCE")),
    ) -> Response:
        u = db.get(User, user_id)
        if u is None:
            raise HTTPException(status_code=404, detail="User not found.")
        active_roles = access.user_active_roles(db, u.id)
        all_roles = access.list_roles(db)
        return _render(
            request, "admin/user_edit.html",
            principal=principal, target_user=u, active_roles=active_roles,
            all_roles=all_roles, error=None, success=None,
        )

    @app.post("/admin/users/{user_id}")
    def admin_user_edit_post(
        user_id: str,
        request: Request,
        display_name: str = Form(...),
        email: str = Form(...),
        status_value: str = Form(...),
        db: Session = Depends(get_db),
        principal: Principal = Depends(require_any_role("ADMIN", "COMPLIANCE")),
    ) -> Response:
        u = db.get(User, user_id)
        if u is None:
            raise HTTPException(status_code=404, detail="User not found.")
        try:
            new_status = UserStatus(status_value)
        except ValueError:
            new_status = u.status
        with session_scope() as s:
            target = s.get(User, user_id)
            actor = s.get(User, principal.user_id)
            actor_role_code = principal.role_codes[0] if principal.role_codes else None
            access.update_user(
                s, user=target, display_name=display_name, email=email,
                actor=actor, actor_role_code=actor_role_code,
                ip=client_ip(request), user_agent=client_ua(request),
            )
            if new_status != target.status:
                access.set_user_status(
                    s, user=target, new_status=new_status,
                    actor=actor, actor_role_code=actor_role_code,
                    ip=client_ip(request), user_agent=client_ua(request),
                )
        return RedirectResponse(url=f"/admin/users/{user_id}", status_code=status.HTTP_303_SEE_OTHER)

    @app.post("/admin/users/{user_id}/roles/assign")
    def admin_user_assign_role(
        user_id: str,
        request: Request,
        role_id: str = Form(...),
        db: Session = Depends(get_db),
        principal: Principal = Depends(require_any_role("ADMIN")),
    ) -> Response:
        with session_scope() as s:
            target = s.get(User, user_id)
            role = s.get(Role, role_id)
            actor = s.get(User, principal.user_id)
            actor_role_code = principal.role_codes[0] if principal.role_codes else None
            if target is None or role is None:
                raise HTTPException(status_code=404, detail="User or role not found.")
            try:
                access.assign_role(
                    s, user=target, role=role, actor=actor, actor_role_code=actor_role_code,
                    ip=client_ip(request), user_agent=client_ua(request),
                )
            except access.SoDViolation as e:
                # Render the user-edit page with the error.
                active_roles = access.user_active_roles(s, target.id)
                all_roles = access.list_roles(s)
                return _render(
                    request, "admin/user_edit.html",
                    principal=principal, target_user=target, active_roles=active_roles,
                    all_roles=all_roles, error=str(e), success=None,
                    status_code=400,
                )
        return RedirectResponse(url=f"/admin/users/{user_id}", status_code=status.HTTP_303_SEE_OTHER)

    @app.post("/admin/users/{user_id}/roles/{role_id}/revoke")
    def admin_user_revoke_role(
        user_id: str,
        role_id: str,
        request: Request,
        reason: str = Form(""),
        db: Session = Depends(get_db),
        principal: Principal = Depends(require_any_role("ADMIN")),
    ) -> Response:
        with session_scope() as s:
            target = s.get(User, user_id)
            role = s.get(Role, role_id)
            actor = s.get(User, principal.user_id)
            actor_role_code = principal.role_codes[0] if principal.role_codes else None
            if target is None or role is None:
                raise HTTPException(status_code=404, detail="User or role not found.")
            try:
                access.revoke_role(
                    s, user=target, role=role, actor=actor, actor_role_code=actor_role_code,
                    reason=reason, ip=client_ip(request), user_agent=client_ua(request),
                )
            except access.SoDViolation as e:
                return _render(
                    request, "admin/user_edit.html",
                    principal=principal, target_user=target,
                    active_roles=access.user_active_roles(s, target.id),
                    all_roles=access.list_roles(s),
                    error=str(e), success=None, status_code=400,
                )
        return RedirectResponse(url=f"/admin/users/{user_id}", status_code=status.HTTP_303_SEE_OTHER)

    @app.get("/admin/roles", response_class=HTMLResponse)
    def admin_roles(
        request: Request,
        db: Session = Depends(get_db),
        principal: Principal = Depends(require_any_role("ADMIN", "COMPLIANCE")),
    ) -> Response:
        return _render(
            request, "admin/roles.html",
            principal=principal, roles=access.list_roles(db), error=None,
        )

    @app.post("/admin/roles")
    def admin_role_create(
        request: Request,
        code: str = Form(...),
        name: str = Form(...),
        description: str = Form(""),
        sod_class: str = Form("DEFAULT"),
        db: Session = Depends(get_db),
        principal: Principal = Depends(require_any_role("ADMIN")),
    ) -> Response:
        with session_scope() as s:
            actor = s.get(User, principal.user_id)
            actor_role_code = principal.role_codes[0] if principal.role_codes else None
            try:
                access.create_role(
                    s, code=code, name=name, description=description, sod_class=sod_class,
                    actor=actor, actor_role_code=actor_role_code,
                    ip=client_ip(request), user_agent=client_ua(request),
                )
            except Exception as e:  # duplicate, etc.
                return _render(
                    request, "admin/roles.html",
                    principal=principal, roles=access.list_roles(s), error=str(e),
                    status_code=400,
                )
        return RedirectResponse(url="/admin/roles", status_code=status.HTTP_303_SEE_OTHER)

    @app.get("/admin/access-policies", response_class=HTMLResponse)
    def admin_access_policies(
        request: Request,
        db: Session = Depends(get_db),
        principal: Principal = Depends(require_any_role("ADMIN", "COMPLIANCE")),
    ) -> Response:
        return _render(
            request, "admin/access_policies.html",
            principal=principal, policies=access.list_policies(db), error=None,
        )

    @app.post("/admin/access-policies")
    def admin_access_policy_create(
        request: Request,
        code: str = Form(...),
        name: str = Form(...),
        description: str = Form(""),
        decision_class: str = Form("CLASS_1"),
        required_approver_role_code: str = Form(""),
        sod_exclusion_role_codes: str = Form(""),
        db: Session = Depends(get_db),
        principal: Principal = Depends(require_any_role("ADMIN")),
    ) -> Response:
        try:
            dc = DecisionClass[decision_class]
        except KeyError:
            dc = DecisionClass.CLASS_1
        exclusions = [c.strip() for c in sod_exclusion_role_codes.split(",") if c.strip()]
        with session_scope() as s:
            actor = s.get(User, principal.user_id)
            actor_role_code = principal.role_codes[0] if principal.role_codes else None
            try:
                access.create_policy(
                    s, code=code, name=name, description=description,
                    decision_class=dc, required_approver_role_code=required_approver_role_code or None,
                    sod_exclusion_role_codes=exclusions,
                    actor=actor, actor_role_code=actor_role_code,
                    ip=client_ip(request), user_agent=client_ua(request),
                )
            except Exception as e:
                return _render(
                    request, "admin/access_policies.html",
                    principal=principal, policies=access.list_policies(s), error=str(e),
                    status_code=400,
                )
        return RedirectResponse(url="/admin/access-policies", status_code=status.HTTP_303_SEE_OTHER)

    @app.get("/admin/access-policies/{policy_id}", response_class=HTMLResponse)
    def admin_access_policy_edit_get(
        policy_id: str,
        request: Request,
        db: Session = Depends(get_db),
        principal: Principal = Depends(require_any_role("ADMIN", "COMPLIANCE")),
    ) -> Response:
        p = db.get(AccessPolicy, policy_id)
        if p is None:
            raise HTTPException(status_code=404, detail="Access policy not found.")
        return _render(
            request, "admin/access_policy_edit.html",
            principal=principal, policy=p, error=None, success=None,
        )

    @app.post("/admin/access-policies/{policy_id}")
    def admin_access_policy_edit_post(
        policy_id: str,
        request: Request,
        name: str = Form(...),
        description: str = Form(""),
        decision_class: str = Form("CLASS_1"),
        required_approver_role_code: str = Form(""),
        sod_exclusion_role_codes: str = Form(""),
        active: str = Form(""),
        db: Session = Depends(get_db),
        principal: Principal = Depends(require_any_role("ADMIN")),
    ) -> Response:
        p = db.get(AccessPolicy, policy_id)
        if p is None:
            raise HTTPException(status_code=404, detail="Access policy not found.")
        try:
            dc = DecisionClass[decision_class]
        except KeyError:
            dc = p.decision_class
        exclusions = [c.strip() for c in sod_exclusion_role_codes.split(",") if c.strip()]
        with session_scope() as s:
            policy = s.get(AccessPolicy, policy_id)
            actor = s.get(User, principal.user_id)
            actor_role_code = principal.role_codes[0] if principal.role_codes else None
            access.update_policy(
                s, policy=policy, name=name, description=description,
                decision_class=dc,
                required_approver_role_code=required_approver_role_code or None,
                sod_exclusion_role_codes=exclusions,
                active=(active == "on"),
                actor=actor, actor_role_code=actor_role_code,
                ip=client_ip(request), user_agent=client_ua(request),
            )
        return RedirectResponse(url=f"/admin/access-policies/{policy_id}", status_code=status.HTTP_303_SEE_OTHER)

    # ====================================================================
    # Audit log (Administrator, Compliance, Auditor)
    # ====================================================================

    @app.get("/admin/audit-log", response_class=HTMLResponse)
    def admin_audit_log(
        request: Request,
        event_type: Optional[str] = Query(default=None),
        actor_username: Optional[str] = Query(default=None),
        target_id: Optional[str] = Query(default=None),
        limit: int = Query(default=200, ge=1, le=1000),
        db: Session = Depends(get_db),
        principal: Principal = Depends(require_any_role("ADMIN", "COMPLIANCE", "AUDITOR")),
    ) -> Response:
        actor_user_id = None
        if actor_username:
            u = db.execute(select(User).where(User.username == actor_username)).scalar_one_or_none()
            actor_user_id = u.id if u else None
        entries = audit.query(
            db,
            event_type=event_type or None,
            actor_user_id=actor_user_id,
            target_id=target_id or None,
            limit=limit,
        )
        chain_ok, _ = audit.verify_chain(db)
        return _render(
            request, "admin/audit_log.html",
            principal=principal, entries=entries, chain_ok=chain_ok,
            filters={
                "event_type": event_type or "",
                "actor_username": actor_username or "",
                "target_id": target_id or "",
                "limit": limit,
            },
        )

    @app.get("/admin/audit-log/export.csv")
    def admin_audit_log_export_csv(
        request: Request,
        event_type: Optional[str] = Query(default=None),
        actor_username: Optional[str] = Query(default=None),
        target_id: Optional[str] = Query(default=None),
        db: Session = Depends(get_db),
        principal: Principal = Depends(require_any_role("ADMIN", "COMPLIANCE", "AUDITOR")),
    ) -> Response:
        actor_user_id = None
        if actor_username:
            u = db.execute(select(User).where(User.username == actor_username)).scalar_one_or_none()
            actor_user_id = u.id if u else None
        entries = audit.query(
            db, event_type=event_type or None,
            actor_user_id=actor_user_id, target_id=target_id or None, limit=10000,
        )
        csv_text = audit.export_csv(entries)
        with session_scope() as s:
            actor = s.get(User, principal.user_id)
            actor_role_code = principal.role_codes[0] if principal.role_codes else None
            audit.record(
                s,
                event_type=audit.EventType.AUDIT_EXPORT,
                action="export_audit_log_csv",
                actor_user_id=actor.id, actor_username=actor.username,
                actor_role_code=actor_role_code,
                target_type="audit_log", target_id=None,
                ip=client_ip(request), user_agent=client_ua(request),
                payload={"format": "csv", "rows": len(entries),
                         "filters": {"event_type": event_type, "actor_username": actor_username,
                                     "target_id": target_id}},
            )
        return Response(
            content=csv_text,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=audit_log.csv"},
        )

    @app.get("/admin/audit-log/export.json")
    def admin_audit_log_export_json(
        request: Request,
        event_type: Optional[str] = Query(default=None),
        actor_username: Optional[str] = Query(default=None),
        target_id: Optional[str] = Query(default=None),
        db: Session = Depends(get_db),
        principal: Principal = Depends(require_any_role("ADMIN", "COMPLIANCE", "AUDITOR")),
    ) -> Response:
        actor_user_id = None
        if actor_username:
            u = db.execute(select(User).where(User.username == actor_username)).scalar_one_or_none()
            actor_user_id = u.id if u else None
        entries = audit.query(
            db, event_type=event_type or None,
            actor_user_id=actor_user_id, target_id=target_id or None, limit=10000,
        )
        body = audit.export_json(entries)
        with session_scope() as s:
            actor = s.get(User, principal.user_id)
            actor_role_code = principal.role_codes[0] if principal.role_codes else None
            audit.record(
                s,
                event_type=audit.EventType.AUDIT_EXPORT,
                action="export_audit_log_json",
                actor_user_id=actor.id, actor_username=actor.username,
                actor_role_code=actor_role_code,
                target_type="audit_log", target_id=None,
                ip=client_ip(request), user_agent=client_ua(request),
                payload={"format": "json", "rows": len(entries),
                         "filters": {"event_type": event_type, "actor_username": actor_username,
                                     "target_id": target_id}},
            )
        return Response(
            content=body,
            media_type="application/json; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=audit_log.json"},
        )

    @app.get("/api/audit-log/verify", response_class=JSONResponse)
    def api_audit_verify(
        db: Session = Depends(get_db),
        principal: Principal = Depends(require_any_role("ADMIN", "COMPLIANCE", "AUDITOR")),
    ) -> JSONResponse:
        ok, bad_seq = audit.verify_chain(db)
        return JSONResponse({"ok": ok, "first_bad_sequence": bad_seq})

    # ====================================================================
    # Error handlers
    # ====================================================================

    @app.exception_handler(404)
    async def not_found(request: Request, exc):  # noqa: ARG001
        return _render(request, "errors/not_found.html", principal=None, status_code=404)

    return app


# ---------------------------------------------------------------------------
# Optional principal (does not require sign-in)
# ---------------------------------------------------------------------------


def _optional_principal(
    request: Request,
    db: Session = Depends(get_db),
    tsai_session: Optional[str] = Cookie(default=None, alias=SETTINGS.cookie_name),
) -> Optional[Principal]:
    if not tsai_session:
        return None
    validated = auth.validate_session(db, jwt_token=tsai_session)
    if validated is None:
        return None
    user, sess, _ = validated
    role_codes = tuple(
        r.role.code
        for r in user.roles
        if r.revoked_at is None and r.role.active
    )
    persona_label = None
    if sess.persona_id:
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


# Module-level app for `uvicorn techno_service_ai.app:app`.
app = create_app()


def main() -> None:
    """Run the FastAPI app under uvicorn for local development."""
    import uvicorn
    uvicorn.run("techno_service_ai.app:app", host="127.0.0.1", port=8000, reload=True)
