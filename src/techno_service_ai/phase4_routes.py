"""Phase 4 Presentation Layer — 20+ screens for the activated Intelligence Offices.

Mounts the Industrial, Opportunity, Technology, AI Workspace, and
Dashboard screens. Per UI/UX §4.5 (Intelligence), §4.4 (Opportunity),
§4.3 (Approval is Phase 3), and §9 (AI Workspace).

The screens render real data from the Phase 2 entities (and from
the Phase 4 service layer) where possible. The 15 zones of the
Opportunity Workspace (per JRN-REV-003 + §5.5) are included as
section placeholders.

Constitutional source:
  - Constitution Articles VI, VII, X, XII, XIV, XVII, XIX, XX
  - Document 06 §2 (24 stages)
  - Document 07 §4.4, §4.5, §4.6, §4.7, §5, §9
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import SessionLocal
from .deps import Principal, current_principal
from .phase2_schema import (
    ComparativeAnalysis, IndustrialActivity, IndustrialEnvironmentProfile,
    KuwaitSuitabilityReview, Opportunity, ProductAnalysis, ProblemOrNeed,
    RootCause, TechnologyCategoryAnalysis, ValidatedSignal, ValueCase,
)


TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def add_phase4_routes(app: FastAPI) -> None:
    """Mount the 20+ Phase 4 screens onto the FastAPI app."""

    def _render(
        request: Request,
        template_name: str,
        *,
        principal: Optional[Principal] = None,
        status_code: int = 200,
        **context,
    ) -> HTMLResponse:
        ctx = {
            "principal": principal,
            "app_name": "Techno Service AI",
            "now": datetime.now(timezone.utc).isoformat(),
        }
        ctx.update(context)
        return templates.TemplateResponse(
            request, f"phase4/{template_name}", context=ctx, status_code=status_code
        )

    def _db() -> Session:
        return SessionLocal()

    # ======================================================================
    # INDUSTRIAL INTELLIGENCE — 3 screens
    # ======================================================================

    @app.get("/industrial/environment", response_class=HTMLResponse)
    def industrial_environment(
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """SCR-INT-001 — Industrial Environment screen.

        Lists IndustrialEnvironmentProfile records (ENT-IND-ENV-001).
        """
        with _db() as s:
            profiles = s.execute(select(IndustrialEnvironmentProfile).order_by(IndustrialEnvironmentProfile.created_at.desc()).limit(50)).scalars().all()
        return _render(
            request, "industrial_environment.html",
            principal=principal, profiles=profiles, title="Industrial Environment",
        )

    @app.get("/industrial/activities", response_class=HTMLResponse)
    def industrial_activities(
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """SCR-INT-002 — Industrial Activity List screen."""
        with _db() as s:
            activities = s.execute(select(IndustrialActivity).order_by(IndustrialActivity.created_at.desc()).limit(50)).scalars().all()
        return _render(
            request, "industrial_activities.html",
            principal=principal, activities=activities, title="Industrial Activities",
        )

    @app.get("/industrial/validated-signals", response_class=HTMLResponse)
    def validated_signals(
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """SCR-INT-003 — Validated Signal List screen."""
        with _db() as s:
            signals = s.execute(select(ValidatedSignal).order_by(ValidatedSignal.created_at.desc()).limit(50)).scalars().all()
        return _render(
            request, "validated_signals.html",
            principal=principal, signals=signals, title="Validated Signals",
        )

    # ======================================================================
    # OPPORTUNITY INTELLIGENCE — 5 screens
    # ======================================================================

    @app.get("/opportunities", response_class=HTMLResponse)
    def opportunities_list(
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """SCR-OPP-001 — Opportunity List screen."""
        with _db() as s:
            opps = s.execute(select(Opportunity).order_by(Opportunity.created_at.desc()).limit(50)).scalars().all()
        return _render(
            request, "opportunities_list.html",
            principal=principal, opps=opps, title="Opportunities",
        )

    @app.get("/opportunities/new", response_class=HTMLResponse)
    def new_opportunity(
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """SCR-OPP-002 — New Opportunity screen (creates from a Validated Signal)."""
        with _db() as s:
            signals = s.execute(select(ValidatedSignal).order_by(ValidatedSignal.created_at.desc()).limit(20)).scalars().all()
        return _render(
            request, "opportunity_new.html",
            principal=principal, signals=signals, title="New Opportunity",
        )

    @app.get("/opportunities/{opportunity_id}", response_class=HTMLResponse)
    def opportunity_workspace(
        request: Request,
        opportunity_id: str,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """SCR-OPP-003 — Opportunity Workspace screen.

        The Workspace is the main surface for an Opportunity. It has
        15 zones per the UI/UX Specification §5.5:
          1. Header Zone
          2. 3-Status Zone (intelligence / approval / commercial)
          3. Workflow Zone (current stage, current gate)
          4. Timeline Zone
          5. AI Zone
          6. Evidence Zone
          7. Documents Zone
          8. Tasks Zone
          9. Notes Zone
          10. Approvals Zone
          11. Verification History Zone
          12. Commercial Progress Zone
          13. Handoffs Zone
          14. Escalations Zone
          15. Closure Zone
        """
        with _db() as s:
            opp = s.get(Opportunity, opportunity_id)
            if opp is None:
                return _render(request, "opportunity_workspace.html", principal=principal,
                               title="Opportunity Not Found", error=f"Opportunity {opportunity_id} not found",
                               status_code=404)
            value_case = s.execute(select(ValueCase).where(ValueCase.id == opp.validated_signal_id).limit(1)).scalar_one_or_none()
        return _render(
            request, "opportunity_workspace.html",
            principal=principal, opp=opp, value_case=value_case,
            zones=[  # 15 zones per UI/UX §5.5
                "Header", "3-Status", "Workflow", "Timeline", "AI",
                "Evidence", "Documents", "Tasks", "Notes", "Approvals",
                "Verification History", "Commercial Progress", "Handoffs",
                "Escalations", "Closure",
            ],
            title="Opportunity Workspace",
        )

    @app.get("/opportunities/{opportunity_id}/value-case", response_class=HTMLResponse)
    def opportunity_value_case(
        request: Request,
        opportunity_id: str,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """SCR-OPP-005 — Value Case screen."""
        return _render(
            request, "opportunity_value_case.html",
            principal=principal, opportunity_id=opportunity_id, title="Value Case",
        )

    @app.get("/opportunities/{opportunity_id}/timeline", response_class=HTMLResponse)
    def opportunity_timeline(
        request: Request,
        opportunity_id: str,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """SCR-OPP-004 — Opportunity Timeline (per workflow events)."""
        return _render(
            request, "opportunity_timeline.html",
            principal=principal, opportunity_id=opportunity_id, title="Opportunity Timeline",
        )

    # ======================================================================
    # TECHNOLOGY INTELLIGENCE — 5 screens
    # ======================================================================

    @app.get("/technologies", response_class=HTMLResponse)
    def technologies_list(
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """SCR-TEC-001 — Technology List screen."""
        with _db() as s:
            techs = s.execute(select(TechnologyCategoryAnalysis).order_by(TechnologyCategoryAnalysis.created_at.desc()).limit(50)).scalars().all()
        return _render(
            request, "technologies_list.html",
            principal=principal, techs=techs, title="Technologies",
        )

    @app.get("/technologies/{tech_id}", response_class=HTMLResponse)
    def technology_workspace(
        request: Request,
        tech_id: str,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """SCR-TEC-002 — Technology Workspace screen."""
        with _db() as s:
            tech = s.get(TechnologyCategoryAnalysis, tech_id)
            products = s.execute(
                select(ProductAnalysis).where(ProductAnalysis.technology_category_analysis_id == tech_id).limit(50)
            ).scalars().all() if tech else []
        return _render(
            request, "technology_workspace.html",
            principal=principal, tech=tech, products=products, title="Technology Workspace",
        )

    @app.get("/products", response_class=HTMLResponse)
    def products_list(
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """SCR-TEC-003 — Product List screen."""
        with _db() as s:
            products = s.execute(select(ProductAnalysis).order_by(ProductAnalysis.created_at.desc()).limit(50)).scalars().all()
        return _render(
            request, "products_list.html",
            principal=principal, products=products, title="Products",
        )

    @app.get("/products/{product_id}", response_class=HTMLResponse)
    def product_workspace(
        request: Request,
        product_id: str,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """SCR-TEC-004 — Product Workspace screen."""
        with _db() as s:
            product = s.get(ProductAnalysis, product_id)
            comparatives = s.execute(
                select(ComparativeAnalysis).where(ComparativeAnalysis.product_analysis_id == product_id).limit(50)
            ).scalars().all() if product else []
        return _render(
            request, "product_workspace.html",
            principal=principal, product=product, comparatives=comparatives, title="Product Workspace",
        )

    @app.get("/comparative-analyses", response_class=HTMLResponse)
    def comparative_analyses(
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """SCR-TEC-005 — Comparative Analysis screen (Stage 9)."""
        with _db() as s:
            cas = s.execute(select(ComparativeAnalysis).order_by(ComparativeAnalysis.created_at.desc()).limit(50)).scalars().all()
        return _render(
            request, "comparative_analyses.html",
            principal=principal, comparatives=cas, title="Comparative Analyses",
        )

    @app.get("/kuwait-suitability/{ksr_id}", response_class=HTMLResponse)
    def kuwait_suitability(
        request: Request,
        ksr_id: str,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """SCR-TEC-006 — Kuwait Suitability Review screen (Stage 10)."""
        with _db() as s:
            ksr = s.get(KuwaitSuitabilityReview, ksr_id)
        return _render(
            request, "kuwait_suitability.html",
            principal=principal, ksr=ksr, title="Kuwait Suitability Review",
        )

    # ======================================================================
    # AI WORKSPACE — 3 screens
    # ======================================================================

    @app.get("/ai/chat", response_class=HTMLResponse)
    def ai_chat(
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """SCR-AI-001 — AI Chat (UI/UX §9 AIW-001)."""
        return _render(
            request, "ai_chat.html",
            principal=principal, title="AI Chat",
        )

    @app.get("/ai/recommendations", response_class=HTMLResponse)
    def ai_recommendations(
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """SCR-AI-002 — AI Recommendations (UI/UX §9 AIW-002)."""
        return _render(
            request, "ai_recommendations.html",
            principal=principal, title="AI Recommendations",
        )

    @app.get("/ai/history", response_class=HTMLResponse)
    def ai_history(
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """SCR-AI-003 — AI History (UI/UX §9 AIW-005)."""
        return _render(
            request, "ai_history.html",
            principal=principal, title="AI History",
        )

    # ======================================================================
    # DASHBOARDS — 4 screens
    # ======================================================================

    @app.get("/dashboards/industrial", response_class=HTMLResponse)
    def dashboard_industrial(
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """DASH-INT-001 — Industrial Intelligence Dashboard."""
        with _db() as s:
            n_profiles = s.execute(select(IndustrialEnvironmentProfile)).scalars().all()
            n_activities = s.execute(select(IndustrialActivity)).scalars().all()
            n_signals = s.execute(select(ValidatedSignal)).scalars().all()
        return _render(
            request, "dashboard_industrial.html",
            principal=principal,
            n_profiles=len(n_profiles), n_activities=len(n_activities),
            n_signals=len(n_signals),
            title="Industrial Intelligence Dashboard",
        )

    @app.get("/dashboards/opportunity", response_class=HTMLResponse)
    def dashboard_opportunity(
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """DASH-INT-002 — Opportunity Intelligence Dashboard."""
        with _db() as s:
            n_opps = s.execute(select(Opportunity)).scalars().all()
            n_values = s.execute(select(ValueCase)).scalars().all()
            n_roots = s.execute(select(RootCause)).scalars().all()
            n_problems = s.execute(select(ProblemOrNeed)).scalars().all()
        return _render(
            request, "dashboard_opportunity.html",
            principal=principal,
            n_opps=len(n_opps), n_values=len(n_values),
            n_roots=len(n_roots), n_problems=len(n_problems),
            title="Opportunity Intelligence Dashboard",
        )

    @app.get("/dashboards/technology", response_class=HTMLResponse)
    def dashboard_technology(
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """DASH-INT-003 — Technology Intelligence Dashboard."""
        with _db() as s:
            n_techs = s.execute(select(TechnologyCategoryAnalysis)).scalars().all()
            n_products = s.execute(select(ProductAnalysis)).scalars().all()
            n_comparatives = s.execute(select(ComparativeAnalysis)).scalars().all()
            n_ksr = s.execute(select(KuwaitSuitabilityReview)).scalars().all()
        return _render(
            request, "dashboard_technology.html",
            principal=principal,
            n_techs=len(n_techs), n_products=len(n_products),
            n_comparatives=len(n_comparatives), n_ksr=len(n_ksr),
            title="Technology Intelligence Dashboard",
        )

    @app.get("/dashboards/executive", response_class=HTMLResponse)
    def dashboard_executive(
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """DASH-EXEC-001 — Executive Dashboard (the most important — the
        default Home for the Executive persona)."""
        with _db() as s:
            n_opps = len(s.execute(select(Opportunity)).scalars().all())
            n_signals = len(s.execute(select(ValidatedSignal)).scalars().all())
            n_comparatives = len(s.execute(select(ComparativeAnalysis)).scalars().all())
        return _render(
            request, "dashboard_executive.html",
            principal=principal,
            n_opps=n_opps, n_signals=n_signals, n_comparatives=n_comparatives,
            title="Executive Dashboard",
        )


# i18n (lite): register the 	 filter + i18n globals on this phase's templates.
from .i18n import apply_to_jinja
apply_to_jinja(templates)
