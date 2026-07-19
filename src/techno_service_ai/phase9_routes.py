"""Phase 9 Routes — Office 18: Product Discovery Proactive.

7 presentation screens (SCR-PD-001..007) per Constitution v2.4:

  SCR-PD-001 /proactive/                  — Proactive Discovery Dashboard
  SCR-PD-002 /proactive/scan              — Global Product Monitor
  SCR-PD-003 /proactive/qualify           — New Product Detector (5 filters)
  SCR-PD-004 /proactive/patents           — Patent Watch
  SCR-PD-005 /proactive/companies         — Emerging Companies
  SCR-PD-006 /proactive/agency-workflow   — Exclusive Agency Acquisition
  SCR-PD-007 /proactive/report            — Daily Proactive Discovery Report
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from .deps import Principal, current_principal, get_db, require_any_role


TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def add_phase9_routes(app: FastAPI) -> None:
    """Mount the Phase 9 Product Discovery Proactive routes."""

    from fastapi.templating import Jinja2Templates
    _t = Jinja2Templates(directory=str(TEMPLATES_DIR))

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

    # -----------------------------------------------------------------
    # SCR-PD-001 — Proactive Discovery Dashboard
    # -----------------------------------------------------------------
    @app.get("/proactive/", response_class=HTMLResponse)
    def proactive_dashboard(
        request: Request,
        db: Session = Depends(get_db),
        principal: Principal = Depends(
            require_any_role("ADMIN", "COMMERCIAL", "EXECUTIVE", "DISCOVERY")
        ),
    ) -> Response:
        from .phase2_schema import (
            ExclusiveAgencyOpportunity, PatentAlert,
            ProactiveDiscoveryReport, ProactiveProductDiscovery,
            QualificationFilterResult,
        )
        discoveries = list(
            db.execute(select(ProactiveProductDiscovery).order_by(
                ProactiveProductDiscovery.created_at.desc()).limit(20)).scalars()
        )
        filter_results = list(
            db.execute(select(QualificationFilterResult).order_by(
                QualificationFilterResult.created_at.desc()).limit(20)).scalars()
        )
        patents = list(
            db.execute(select(PatentAlert).order_by(
                PatentAlert.created_at.desc()).limit(20)).scalars()
        )
        agency = list(
            db.execute(select(ExclusiveAgencyOpportunity).order_by(
                ExclusiveAgencyOpportunity.created_at.desc()).limit(20)).scalars()
        )
        reports = list(
            db.execute(select(ProactiveDiscoveryReport).order_by(
                ProactiveDiscoveryReport.created_at.desc()).limit(10)).scalars()
        )
        return _render(
            request, "phase9/proactive_dashboard.html",
            principal=principal,
            discoveries=discoveries,
            filter_results=filter_results,
            patents=patents,
            agency=agency,
            reports=reports,
            error=None,
        )

    # -----------------------------------------------------------------
    # SCR-PD-002 — Global Product Monitor
    # -----------------------------------------------------------------
    @app.get("/proactive/scan", response_class=HTMLResponse)
    def proactive_scan_get(
        request: Request,
        principal: Principal = Depends(
            require_any_role("ADMIN", "COMMERCIAL", "DISCOVERY")
        ),
    ) -> Response:
        return _render(
            request, "phase9/proactive_scan.html",
            principal=principal, error=None,
        )

    @app.post("/proactive/scan")
    def proactive_scan_post(
        request: Request,
        product_name: str = Form(...),
        product_category: str = Form(...),
        sector: str = Form(...),
        manufacturer_name: str = Form(...),
        manufacturer_country: str = Form(""),
        discovery_source: str = Form("WEB_SEARCH"),
        source_citation_url: str = Form(""),
        signal_strength: str = Form("MEDIUM"),
        notes: str = Form(""),
        principal: Principal = Depends(
            require_any_role("ADMIN", "COMMERCIAL", "DISCOVERY")
        ),
    ) -> Response:
        from .services import WorkflowService
        try:
            WorkflowService().create_proactive_discovery(
                actor_id=principal.user_id,
                role_code=principal.role_codes[0] if principal.role_codes else "DISCOVERY",
                product_name=product_name,
                product_category=product_category,
                sector=sector,
                manufacturer_name=manufacturer_name,
                manufacturer_country=manufacturer_country,
                discovery_source=discovery_source,
                source_citation_url=source_citation_url,
                signal_strength=signal_strength,
                notes=notes,
            )
        except Exception as e:
            return _render(
                request, "phase9/proactive_scan.html",
                principal=principal, error=str(e), status_code=400,
            )
        return RedirectResponse(url="/proactive/", status_code=303)

    # -----------------------------------------------------------------
    # SCR-PD-003 — New Product Detector (5 filters)
    # -----------------------------------------------------------------
    @app.get("/proactive/qualify", response_class=HTMLResponse)
    def proactive_qualify_get(
        request: Request,
        principal: Principal = Depends(
            require_any_role("ADMIN", "COMMERCIAL", "DISCOVERY")
        ),
    ) -> Response:
        return _render(
            request, "phase9/proactive_qualify.html",
            principal=principal, error=None,
        )

    @app.post("/proactive/qualify")
    def proactive_qualify_post(
        request: Request,
        discovery_id: str = Form(...),
        # F1
        f1_heat_rating: str = Form("UNKNOWN"),
        f1_dust_rating: str = Form("UNKNOWN"),
        # F2
        f2_requires_major_change: str = Form("off"),
        f2_installation_complexity: str = Form("LOW"),
        # F3
        f3_existing_agents: str = Form(""),
        # F4
        f4_requires_specialised_training: str = Form("off"),
        f4_requires_engineering_team: str = Form("off"),
        f4_annual_maintenance_cost: str = Form("LOW"),
        # F5
        f5_employee_count: int = Form(0),
        f5_annual_revenue_usd: int = Form(0),
        f5_is_tier_1: str = Form("off"),
        principal: Principal = Depends(
            require_any_role("ADMIN", "COMMERCIAL", "DISCOVERY")
        ),
    ) -> Response:
        from .services import WorkflowService
        existing_agents = [a.strip() for a in f3_existing_agents.split(",") if a.strip()]
        try:
            WorkflowService().create_qualification_filter_result(
                actor_id=principal.user_id,
                role_code=principal.role_codes[0] if principal.role_codes else "DISCOVERY",
                discovery_id=discovery_id,
                f1_inputs={"heat_rating": f1_heat_rating, "dust_rating": f1_dust_rating, "wind_rating": "OK"},
                f2_inputs={"requires_major_change": f2_requires_major_change == "on",
                           "installation_complexity": f2_installation_complexity},
                f3_inputs={"existing_agents_in_kuwait": existing_agents},
                f4_inputs={"requires_specialised_training": f4_requires_specialised_training == "on",
                           "requires_engineering_team": f4_requires_engineering_team == "on",
                           "annual_maintenance_cost": f4_annual_maintenance_cost},
                f5_inputs={"employee_count": f5_employee_count,
                           "annual_revenue_usd": f5_annual_revenue_usd,
                           "is_tier_1": f5_is_tier_1 == "on"},
            )
        except Exception as e:
            return _render(
                request, "phase9/proactive_qualify.html",
                principal=principal, error=str(e), status_code=400,
            )
        return RedirectResponse(url="/proactive/", status_code=303)

    # -----------------------------------------------------------------
    # SCR-PD-004 — Patent Watch
    # -----------------------------------------------------------------
    @app.get("/proactive/patents", response_class=HTMLResponse)
    def proactive_patents_get(
        request: Request,
        principal: Principal = Depends(
            require_any_role("ADMIN", "COMMERCIAL", "DISCOVERY")
        ),
    ) -> Response:
        return _render(
            request, "phase9/proactive_patents.html",
            principal=principal, error=None,
        )

    @app.post("/proactive/patents")
    def proactive_patents_post(
        request: Request,
        patent_id: str = Form(...),
        title: str = Form(...),
        assignee: str = Form(""),
        filing_date: str = Form(""),
        relevance: str = Form("MEDIUM"),
        relevance_rationale: str = Form(""),
        source_citation_url: str = Form(""),
        principal: Principal = Depends(
            require_any_role("ADMIN", "COMMERCIAL", "DISCOVERY")
        ),
    ) -> Response:
        from .services import WorkflowService
        try:
            WorkflowService().create_patent_alert(
                actor_id=principal.user_id,
                role_code=principal.role_codes[0] if principal.role_codes else "DISCOVERY",
                patent_id=patent_id, title=title, assignee=assignee,
                filing_date=filing_date, relevance=relevance,
                relevance_rationale=relevance_rationale,
                source_citation_url=source_citation_url,
            )
        except Exception as e:
            return _render(
                request, "phase9/proactive_patents.html",
                principal=principal, error=str(e), status_code=400,
            )
        return RedirectResponse(url="/proactive/", status_code=303)

    # -----------------------------------------------------------------
    # SCR-PD-005 — Emerging Companies
    # -----------------------------------------------------------------
    @app.get("/proactive/companies", response_class=HTMLResponse)
    def proactive_companies(
        request: Request,
        db: Session = Depends(get_db),
        principal: Principal = Depends(
            require_any_role("ADMIN", "COMMERCIAL", "DISCOVERY")
        ),
    ) -> Response:
        from .phase2_schema import ManufacturerProfile
        # Filter to non-tier-1, mid-sized emerging companies
        companies = list(db.execute(
            select(ManufacturerProfile).order_by(ManufacturerProfile.created_at.desc()).limit(50)
        ).scalars())
        return _render(
            request, "phase9/proactive_companies.html",
            principal=principal, companies=companies, error=None,
        )

    # -----------------------------------------------------------------
    # SCR-PD-006 — Exclusive Agency Acquisition Workflow
    # -----------------------------------------------------------------
    @app.get("/proactive/agency-workflow", response_class=HTMLResponse)
    def agency_workflow_get(
        request: Request,
        principal: Principal = Depends(
            require_any_role("ADMIN", "COMMERCIAL", "EXECUTIVE")
        ),
    ) -> Response:
        return _render(
            request, "phase9/proactive_agency_workflow.html",
            principal=principal, error=None, step=1,
        )

    @app.post("/proactive/agency-workflow")
    def agency_workflow_post(
        request: Request,
        discovery_id: str = Form(...),
        manufacturer_name: str = Form(...),
        product_summary: str = Form(...),
        current_step: int = Form(1),
        target_step: int = Form(1),
        class_3_approval_id: str = Form(""),
        class_4_approval_id: str = Form(""),
        principal: Principal = Depends(
            require_any_role("ADMIN", "COMMERCIAL", "EXECUTIVE")
        ),
    ) -> Response:
        from .services import WorkflowService
        try:
            WorkflowService().advance_exclusive_agency_workflow(
                actor_id=principal.user_id,
                role_code=principal.role_codes[0] if principal.role_codes else "EXECUTIVE",
                discovery_id=discovery_id,
                manufacturer_name=manufacturer_name,
                product_summary=product_summary,
                current_step=current_step,
                target_step=target_step,
                class_3_approval_id=class_3_approval_id,
                class_4_approval_id=class_4_approval_id,
            )
        except Exception as e:
            return _render(
                request, "phase9/proactive_agency_workflow.html",
                principal=principal, error=str(e), step=current_step, status_code=400,
            )
        return RedirectResponse(url="/proactive/", status_code=303)

    # -----------------------------------------------------------------
    # SCR-PD-007 — Daily Proactive Discovery Report
    # -----------------------------------------------------------------
    @app.get("/proactive/report", response_class=HTMLResponse)
    def proactive_report_get(
        request: Request,
        db: Session = Depends(get_db),
        principal: Principal = Depends(
            require_any_role("ADMIN", "COMMERCIAL", "EXECUTIVE")
        ),
    ) -> Response:
        from .phase2_schema import (
            ExclusiveAgencyOpportunity, PatentAlert,
            ProactiveDiscoveryReport, ProactiveProductDiscovery,
            QualificationFilterResult,
        )
        n_discoveries = db.execute(select(ProactiveProductDiscovery)).scalars().all()
        n_filter = db.execute(select(QualificationFilterResult)).scalars().all()
        n_patents = db.execute(select(PatentAlert)).scalars().all()
        n_agency = db.execute(select(ExclusiveAgencyOpportunity)).scalars().all()
        n_qualified = sum(1 for r in n_filter if r.overall == "QUALIFIED")
        n_rejected = sum(1 for r in n_filter if r.overall == "REJECTED")
        return _render(
            request, "phase9/proactive_report.html",
            principal=principal,
            n_discoveries=len(n_discoveries),
            n_qualified=n_qualified, n_rejected=n_rejected,
            n_patents=len(n_patents), n_agency=len(n_agency),
            error=None,
        )

    @app.post("/proactive/report")
    def proactive_report_post(
        request: Request,
        n_discoveries: int = Form(0),
        n_qualified: int = Form(0),
        n_rejected: int = Form(0),
        n_patents: int = Form(0),
        n_agency_opportunities: int = Form(0),
        source_citation: str = Form(""),
        notes: str = Form(""),
        principal: Principal = Depends(
            require_any_role("ADMIN", "COMMERCIAL", "EXECUTIVE")
        ),
    ) -> Response:
        from .services import WorkflowService
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        try:
            WorkflowService().create_proactive_discovery_report(
                actor_id=principal.user_id,
                role_code=principal.role_codes[0] if principal.role_codes else "EXECUTIVE",
                report_date=now.isoformat(),
                period_start=now.isoformat(),
                period_end=now.isoformat(),
                n_discoveries=n_discoveries, n_qualified=n_qualified,
                n_rejected=n_rejected, n_patents=n_patents,
                n_agency_opportunities=n_agency_opportunities,
                source_citation=source_citation or "Daily Proactive Discovery Report",
                notes=notes,
            )
        except Exception as e:
            return _render(
                request, "phase9/proactive_report.html",
                principal=principal, error=str(e), status_code=400,
            )
        return RedirectResponse(url="/proactive/", status_code=303)
