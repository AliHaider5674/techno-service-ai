"""Phase 9 Continuous Proactive Discovery Routes.

Adds the 3 new screens (SCR-PD-008..010) per the Continuous
Proactive Discovery Sprint (2026-07-19):

  SCR-PD-008  /phase9/continuous-discovery/console
                — the main console: scheduler state, run history,
                  recent candidates, notifications.

  SCR-PD-009  /phase9/continuous-discovery/settings
                — settings: interval, data source.

  SCR-PD-010  /phase9/continuous-discovery/history
                — full run history.

Actions (POST):
  POST /phase9/continuous-discovery/trigger  — manual run
  POST /phase9/continuous-discovery/pause     — pause schedule
  POST /phase9/continuous-discovery/resume    — resume schedule
  POST /phase9/continuous-discovery/start     — start scheduler
  POST /phase9/continuous-discovery/stop      — stop scheduler

All routes are bilingual (EN + AR) via the i18n framework.

Constitutional basis:
  - Constitution v2.4 (Office 18 in force, 4 agents, 5 filters,
    3 Registers).
  - Document 02 §4.18 (Office 18 — Product Discovery Proactive).
  - Constitution Article VIII (Constitutional Registers).
  - Constitution Article XII (Human Approval).
  - ASS-PHASE9-001 (in-process threading scheduler).
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from .deps import Principal, current_principal, get_db, require_any_role


TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def add_phase9_continuous_routes(app: FastAPI) -> None:
    """Mount the Continuous Discovery console / settings / history routes."""

    from fastapi.templating import Jinja2Templates
    _t = Jinja2Templates(directory=str(TEMPLATES_DIR))
    from .i18n import apply_to_jinja
    apply_to_jinja(_t)

    def _render(
        request: Request,
        template_name: str,
        *,
        principal: Optional[Principal] = None,
        status_code: int = 200,
        **context,
    ) -> HTMLResponse:
        from datetime import datetime, timezone
        ctx = {"request": request, "principal": principal,
               "now": datetime.now(timezone.utc)}
        ctx.update(context)
        return _t.TemplateResponse(
            request, template_name, ctx, status_code=status_code,
        )

    def _read_state(db_session: Session):
        """Read the SchedulerState singleton (or None if absent)."""
        from .phase2_schema import SchedulerState as _State
        return db_session.execute(
            select(_State).order_by(_State.id)
        ).scalars().first()

    def _read_history(db_session: Session, limit: int = 10):
        from .phase2_schema import ContinuousSearchRun
        return list(db_session.execute(
            select(ContinuousSearchRun).order_by(
                desc(ContinuousSearchRun.started_at)
            ).limit(limit)
        ).scalars())

    def _read_candidates(db_session: Session, limit: int = 20):
        from .phase2_schema import ContinuousDiscoveryCandidate
        return list(db_session.execute(
            select(ContinuousDiscoveryCandidate).order_by(
                desc(ContinuousDiscoveryCandidate.discovered_at)
            ).limit(limit)
        ).scalars())

    def _read_notifications(db_session: Session, limit: int = 20):
        from .phase2_schema import ContinuousDiscoveryNotification
        return list(db_session.execute(
            select(ContinuousDiscoveryNotification).order_by(
                desc(ContinuousDiscoveryNotification.created_at)
            ).limit(limit)
        ).scalars())

    # =====================================================================
    # SCR-PD-008 — Continuous Discovery Console
    # =====================================================================

    @app.get("/phase9/continuous-discovery/console", response_class=HTMLResponse)
    def continuous_discovery_console(
        request: Request,
        db: Session = Depends(get_db),
        principal: Principal = Depends(
            require_any_role("ADMIN", "COMMERCIAL", "EXECUTIVE", "DISCOVERY")
        ),
    ) -> Response:
        state = _read_state(db)
        history = _read_history(db, limit=10)
        candidates = _read_candidates(db, limit=20)
        notifications = _read_notifications(db, limit=10)
        # Scheduler in-process status.
        from .scheduler import get_scheduler
        sched = get_scheduler().status()
        return _render(
            request, "phase9/continuous_discovery_console.html",
            principal=principal,
            state=state,
            history=history,
            candidates=candidates,
            notifications=notifications,
            sched=sched,
            flash=request.query_params.get("flash"),
            error=request.query_params.get("error"),
        )

    # =====================================================================
    # SCR-PD-009 — Continuous Discovery Settings
    # =====================================================================

    @app.get("/phase9/continuous-discovery/settings", response_class=HTMLResponse)
    def continuous_discovery_settings_get(
        request: Request,
        db: Session = Depends(get_db),
        principal: Principal = Depends(
            require_any_role("ADMIN", "COMMERCIAL", "EXECUTIVE", "DISCOVERY")
        ),
    ) -> Response:
        state = _read_state(db)
        from .simulated_sources import get_default_registry
        available = get_default_registry().available()
        return _render(
            request, "phase9/continuous_discovery_settings.html",
            principal=principal,
            state=state,
            available_sources=available,
        )

    @app.post("/phase9/continuous-discovery/settings")
    def continuous_discovery_settings_post(
        request: Request,
        interval_hours: int = Form(6),
        data_source: str = Form("SIMULATED"),
        principal: Principal = Depends(
            require_any_role("ADMIN", "COMMERCIAL", "EXECUTIVE", "DISCOVERY")
        ),
    ) -> Response:
        from .scheduler import get_scheduler
        sched = get_scheduler()
        # Clamp interval.
        if interval_hours < 1:
            interval_hours = 1
        if interval_hours > 168:
            interval_hours = 168
        sched.update_interval(interval_hours, updated_by=principal.user_id)
        sched.update_data_source(data_source, updated_by=principal.user_id)
        return RedirectResponse(
            url="/phase9/continuous-discovery/console?flash=settings_saved",
            status_code=303,
        )

    # =====================================================================
    # SCR-PD-010 — Continuous Discovery Run History
    # =====================================================================

    @app.get("/phase9/continuous-discovery/history", response_class=HTMLResponse)
    def continuous_discovery_history(
        request: Request,
        db: Session = Depends(get_db),
        principal: Principal = Depends(
            require_any_role("ADMIN", "COMMERCIAL", "EXECUTIVE", "DISCOVERY")
        ),
    ) -> Response:
        history = _read_history(db, limit=50)
        return _render(
            request, "phase9/continuous_discovery_history.html",
            principal=principal,
            history=history,
        )

    # =====================================================================
    # Actions
    # =====================================================================

    @app.post("/phase9/continuous-discovery/trigger")
    def continuous_discovery_trigger(
        request: Request,
        principal: Principal = Depends(
            require_any_role("ADMIN", "COMMERCIAL", "EXECUTIVE", "DISCOVERY")
        ),
    ) -> Response:
        from .scheduler import get_scheduler
        try:
            result = get_scheduler().trigger_manual(
                triggered_by=principal.user_id,
                max_candidates=5,
            )
            msg = (
                f"Manual search triggered. Run ID: {result.run_id}. "
                f"{len(result.evaluated)} candidates surfaced, "
                f"{sum(1 for c in result.evaluated if c.overall.value == 'QUALIFIED')} qualified, "
                f"{sum(1 for c in result.evaluated if c.overall.value == 'REJECTED')} rejected."
            )
            return RedirectResponse(
                url=f"/phase9/continuous-discovery/console?flash={msg}",
                status_code=303,
            )
        except Exception as e:
            return RedirectResponse(
                url=f"/phase9/continuous-discovery/console?error={e}",
                status_code=303,
            )

    @app.post("/phase9/continuous-discovery/pause")
    def continuous_discovery_pause(
        request: Request,
        principal: Principal = Depends(
            require_any_role("ADMIN", "COMMERCIAL", "EXECUTIVE", "DISCOVERY")
        ),
    ) -> Response:
        from .scheduler import get_scheduler
        get_scheduler().pause(updated_by=principal.user_id)
        return RedirectResponse(
            url="/phase9/continuous-discovery/console?flash=paused",
            status_code=303,
        )

    @app.post("/phase9/continuous-discovery/resume")
    def continuous_discovery_resume(
        request: Request,
        principal: Principal = Depends(
            require_any_role("ADMIN", "COMMERCIAL", "EXECUTIVE", "DISCOVERY")
        ),
    ) -> Response:
        from .scheduler import get_scheduler
        get_scheduler().resume(updated_by=principal.user_id)
        return RedirectResponse(
            url="/phase9/continuous-discovery/console?flash=resumed",
            status_code=303,
        )

    @app.post("/phase9/continuous-discovery/start")
    def continuous_discovery_start(
        request: Request,
        principal: Principal = Depends(
            require_any_role("ADMIN", "COMMERCIAL", "EXECUTIVE", "DISCOVERY")
        ),
    ) -> Response:
        from .scheduler import get_scheduler
        sched = get_scheduler()
        from .db import session_scope
        with session_scope() as s:
            state = _read_state(s)
            interval = state.interval_hours if state else 6
            ds = state.data_source if state else "SIMULATED"
        sched.start(interval_hours=interval, data_source=ds, updated_by=principal.user_id)
        return RedirectResponse(
            url="/phase9/continuous-discovery/console?flash=started",
            status_code=303,
        )

    @app.post("/phase9/continuous-discovery/stop")
    def continuous_discovery_stop(
        request: Request,
        principal: Principal = Depends(
            require_any_role("ADMIN", "COMMERCIAL", "EXECUTIVE", "DISCOVERY")
        ),
    ) -> Response:
        from .scheduler import get_scheduler
        get_scheduler().stop(updated_by=principal.user_id)
        return RedirectResponse(
            url="/phase9/continuous-discovery/console?flash=stopped",
            status_code=303,
        )
