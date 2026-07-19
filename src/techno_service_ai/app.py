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

# i18n (lite): register the `t()` filter on the Jinja env so templates
# can call `{{ "signin.title" | t(lang) }}` to externalise strings.
# Default language is English; Arabic is opt-in via the `tsai_lang`
# cookie set by the `/i18n/set` route.
from . import i18n as _i18n  # noqa: E402


def _t_filter(key: str, lang: str = "en") -> str:
    return _i18n.t(key, lang)


templates.env.filters["t"] = _t_filter


# Register i18n globals so EVERY template (including the shared
# `base.html`) can read `lang`, `dir`, `rtl`, and the supported
# languages list. Without these globals, base.html would need its
# `<html lang="..." dir="...">` values passed per-route, which would
# require touching every render call. The globals read from a
# contextvar set by the i18n middleware below.
def _g_lang() -> str:
    """Jinja global: return the active language (default: en)."""
    try:
        from . import i18n_runtime as _i18n_rt
        return _i18n_rt.current_lang()
    except Exception:
        return _i18n.DEFAULT_LANG


templates.env.globals["lang_code"] = _g_lang
templates.env.globals["dir_attr"] = lambda: _i18n.dir_attr(_g_lang())
templates.env.globals["is_rtl"] = lambda: _i18n.is_rtl(_g_lang())
templates.env.globals["supported_langs"] = _i18n.SUPPORTED_LANGS


def create_app() -> FastAPI:
    app = FastAPI(
        title="Techno Service AI Intelligence System",
        version="1.0.0-phase3",
        description="Phases 1-3: Identity, Access, Audit (1); Data Foundation (2); "
                    "Workflow, Verification, and Approval Foundation (3). "
                    "Constitutional Authority: Constitution v2.3.",
    )
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # ------------------------------------------------------------------
    # i18n (lite) middleware — reads the `tsai_lang` cookie and stashes
    # the normalised language on `request.state.lang`. Default is "en".
    # Templates can use `{{ "key" | t(request.state.lang) }}` to render
    # translated strings. RTL is applied via `dir="rtl"` on <html>
    # when the active language is in `i18n.RTL_LANGS`.
    # ------------------------------------------------------------------
    from starlette.requests import Request as _Request
    from starlette.responses import Response as _Response

    @app.middleware("http")
    async def _i18n_middleware(request: _Request, call_next):
        from . import i18n_runtime as _i18n_rt
        cookie_lang = request.cookies.get("tsai_lang")
        lang = _i18n.normalize_lang(cookie_lang)
        request.state.lang = lang
        request.state.dir = _i18n.dir_attr(lang)
        _i18n_rt.set_lang(lang)
        try:
            return await call_next(request)
        finally:
            _i18n_rt.set_lang(_i18n.DEFAULT_LANG)

    @app.get("/i18n/set", response_class=HTMLResponse)
    def i18n_set(
        request: Request,
        lang: str = Query("en"),
        next: str = Query("/"),
    ) -> Response:
        """Set the language cookie and redirect back.

        Falls back to the default language if `lang` is not supported.
        The cookie is set with `path=/` so every page picks it up.
        """
        normalised = _i18n.normalize_lang(lang)
        # Validate `next` to prevent open-redirects: must start with `/`.
        if not next.startswith("/"):
            next = "/"
        resp = RedirectResponse(url=next, status_code=status.HTTP_303_SEE_OTHER)
        # Session cookie (not Secure by default; Secure in production).
        resp.set_cookie(
            key="tsai_lang",
            value=normalised,
            max_age=60 * 60 * 24 * 365,  # 1 year
            path="/",
            httponly=False,  # JS-readable so the switcher can show the active lang
            samesite="lax",
        )
        return resp

    # Phase 3 routes (Verification, Approval, Notification screens).
    from .phase3_routes import add_phase3_routes
    add_phase3_routes(app)
    # Phase 4 routes (Industrial, Opportunity, Technology, AI Workspace, Dashboards).
    from .phase4_routes import add_phase4_routes
    add_phase4_routes(app)
    # Phase 5 routes (Manufacturer, Commercial, Registration screens + 2 new dashboards).
    from .phase5_routes import add_phase5_routes
    add_phase5_routes(app)
    # Phase 6 routes (Tender, Project, Knowledge screens — closes the 24-stage lifecycle).
    from .phase6_routes import add_phase6_routes
    add_phase6_routes(app)
    # Phase 7 routes (Performance, Reporting, Notification, Risk, Security, Relationship, Executive — Every Office Alive).
    from .phase7_routes import add_phase7_routes
    add_phase7_routes(app)
    # Phase 8 routes (Quality Assurance Office — closes the last Charter Office; Production Hardening).
    from .phase8_routes import add_phase8_routes
    add_phase8_routes(app)
    # Phase 9 routes (Office 18 — Product Discovery Proactive, Constitution v2.4).
    from .phase9_routes import add_phase9_routes
    add_phase9_routes(app)

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
        # Pull the language and direction from request.state (set by
        # the i18n middleware). Defaults are "en" / "ltr" if the
        # middleware hasn't run for some reason.
        lang = getattr(request.state, "lang", _i18n.DEFAULT_LANG)
        dir_attr = getattr(request.state, "dir", _i18n.dir_attr(lang))
        ctx = {
            "request": request,
            "principal": principal,
            "now": datetime.now(timezone.utc),
            "lang": lang,
            "dir": dir_attr,
            "rtl": _i18n.is_rtl(lang),
            "supported_langs": _i18n.SUPPORTED_LANGS,
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

    def _resolve_post_signin_redirect(
        request: Request,
        next_param: Optional[str],
        lang_param: Optional[str],
        default: str = "/home",
    ) -> str:
        """Resolve the post-sign-in redirect URL.

        Honours the `next` query/form param (if it's a safe relative
        path) and preserves the language preference. The language is
        resolved in this order:
          1. `lang_param` (query or form value, if present and valid)
          2. The `tsai_lang` cookie
          3. The middleware's request.state.lang
          4. Default (English)

        The chosen language is appended as `?lang=xx` to the redirect
        URL so the next page renders in the same language without
        requiring the cookie to be set first.

        Args:
            request: the current FastAPI request.
            next_param: the `next` query or form parameter.
            lang_param: the `lang` query or form parameter.
            default: the default redirect target if `next` is not
                provided or fails the safety check.

        Returns:
            A safe relative URL string suitable for RedirectResponse.
        """
        # 1. Validate `next` (must start with `/`; blocks open-redirects).
        target = default
        if next_param and next_param.startswith("/") and not next_param.startswith("//"):
            target = next_param

        # 2. Resolve the language preference.
        # Prefer the explicit param, then the cookie, then the
        # middleware-stashed lang, then default ("en").
        lang = lang_param
        if not lang:
            cookie_lang = request.cookies.get("tsai_lang")
            if cookie_lang:
                lang = cookie_lang
        if not lang:
            lang = getattr(request.state, "lang", _i18n.DEFAULT_LANG)
        lang = _i18n.normalize_lang(lang)

        # 3. Only add `?lang=` if the user actively chose non-default.
        if lang and lang != _i18n.DEFAULT_LANG:
            # Avoid duplicating an existing ?lang= on the target.
            if "lang=" not in target:
                sep = "&" if "?" in target else "?"
                target = f"{target}{sep}lang={lang}"

        return target

    # ====================================================================
    # Public / semi-public routes
    # ====================================================================

    @app.get("/", response_class=HTMLResponse)
    def home(
        request: Request,
        lang: Optional[str] = Query(default=None),
        principal: Optional[Principal] = Depends(_optional_principal),
    ) -> Response:
        if principal is None:
            return RedirectResponse(url="/sign-in", status_code=status.HTTP_303_SEE_OTHER)
        # Preserve `?lang=` on the redirect to /home (so the home
        # page renders in the requested language immediately).
        target = "/home"
        if lang:
            target = _resolve_post_signin_redirect(request, next_param=None, lang_param=lang, default="/home")
        return RedirectResponse(url=target, status_code=status.HTTP_303_SEE_OTHER)

    @app.get("/sign-in", response_class=HTMLResponse)
    def sign_in_get(
        request: Request,
        next: Optional[str] = Query(default=None),
        lang: Optional[str] = Query(default=None),
        principal: Optional[Principal] = Depends(_optional_principal),
    ) -> Response:
        if principal is not None:
            # Signed-in user landing on /sign-in: redirect to the
            # appropriate page, honouring `next` (validated) and the
            # language cookie / `?lang=` param.
            target = _resolve_post_signin_redirect(request, next, lang)
            return RedirectResponse(url=target, status_code=status.HTTP_303_SEE_OTHER)
        return _render(request, "sign_in.html", error=None, username="")

    @app.post("/sign-in")
    def sign_in_post(
        request: Request,
        username: str = Form(...),
        password: str = Form(...),
        next: Optional[str] = Form(default=None),
        lang: Optional[str] = Form(default=None),
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
        # Honour `next` (validated) and the language preference.
        target = _resolve_post_signin_redirect(
            request, next, lang, default="/persona/select" if n_personas > 1 else "/home"
        )
        resp = RedirectResponse(url=target, status_code=status.HTTP_303_SEE_OTHER)
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
