"""Phase 5 Presentation Layer — Manufacturer, Commercial, and Registration.

Mounts the screens for the three Offices activated in Phase 5:

  - Manufacturer Intelligence Office (§4.5): list, workspace, profile,
    credibility, comparison, Kuwait Representation, qualification.
  - Commercial Development Office (§4.6): commercial dashboard,
    business development, quotation dossier.
  - Registration and Market Entry Office (§4.7): registration,
    prequalification, market entry, market status.
  - Two new Dashboards: Manufacturer Intelligence + Commercial
    Intelligence.

The screens render real data from the Phase 2 entities. The
Register Compliance Gate is invoked at the entry of every commercial
action — its result is shown on the relevant screens.

Constitutional source:
  - Constitution Articles VI, VIII, XII, XIV, XVII, XIX, XX
  - Document 06 §2.11..2.18 (Stages 11-18)
  - Document 07 §4.4, §4.5, §4.6, §4.7, §5
  - Document 02 §4.5, §4.6, §4.7
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import SessionLocal
from .deps import Principal, current_principal
from .phase2_schema import (
    BusinessDevelopmentEngagement,
    CommercialEvaluation,
    ManufacturerComparisonReport,
    ManufacturerCredibilityAssessment,
    ManufacturerProfile,
    MarketEntryOptionsReport,
    Opportunity,
    PrequalificationStatusReport,
    PricingAnalysis,
    RegistrationStatusReport,
)


TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _from_json(value):
    """Jinja filter: parse a JSON string into a Python value."""
    if not value:
        return []
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return []


templates.env.filters["from_json"] = _from_json


def add_phase5_routes(app: FastAPI) -> None:
    """Mount the 13+ Phase 5 screens onto the FastAPI app."""

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
            request, f"phase5/{template_name}", context=ctx, status_code=status_code
        )

    def _db() -> Session:
        return SessionLocal()

    # ==================================================================
    # MANUFACTURER INTELLIGENCE — 7 screens
    # ==================================================================

    @app.get("/manufacturers", response_class=HTMLResponse)
    def manufacturers_list(
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """Manufacturer List screen — Manufacturer Intelligence Dashboard entry."""
        with _db() as s:
            manufacturers = s.execute(
                select(ManufacturerProfile).order_by(ManufacturerProfile.created_at.desc()).limit(100)
            ).scalars().all()
        return _render(
            request, "manufacturers_list.html",
            principal=principal, manufacturers=manufacturers,
        )

    @app.get("/manufacturers/{mfr_id}", response_class=HTMLResponse)
    def manufacturer_workspace(
        mfr_id: str,
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """Manufacturer Workspace — the manufacturer home."""
        with _db() as s:
            mfr = s.get(ManufacturerProfile, mfr_id)
            if mfr is None:
                return _render(
                    request, "manufacturers_list.html",
                    principal=principal, manufacturers=[],
                    not_found=mfr_id, status_code=404,
                )
            # Load credibility assessments and comparison reports.
            creds = s.execute(
                select(ManufacturerCredibilityAssessment)
                .where(ManufacturerCredibilityAssessment.manufacturer_id == mfr_id)
                .order_by(ManufacturerCredibilityAssessment.created_at.desc())
            ).scalars().all()
            comparisons = s.execute(
                select(ManufacturerComparisonReport)
                .order_by(ManufacturerComparisonReport.created_at.desc())
                .limit(20)
            ).scalars().all()

            # Determine Kuwait Representation status (from the registers).
            from .services import WorkflowService
            svc = WorkflowService()
            kuwait_status = svc.get_kuwait_representation_status(
                manufacturer_id=mfr_id, manufacturer_name=mfr.manufacturer_name,
            )
        return _render(
            request, "manufacturer_workspace.html",
            principal=principal, mfr=mfr, creds=creds,
            comparisons=comparisons, kuwait_status=kuwait_status,
        )

    @app.get("/manufacturers/{mfr_id}/credibility", response_class=HTMLResponse)
    def manufacturer_credibility(
        mfr_id: str,
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """Credibility Assessment screen — multi-dimensional scorecard."""
        with _db() as s:
            mfr = s.get(ManufacturerProfile, mfr_id)
            creds = s.execute(
                select(ManufacturerCredibilityAssessment)
                .where(ManufacturerCredibilityAssessment.manufacturer_id == mfr_id)
                .order_by(ManufacturerCredibilityAssessment.created_at.desc())
            ).scalars().all()
        return _render(
            request, "manufacturer_credibility.html",
            principal=principal, mfr=mfr, creds=creds,
            dimensions=(
                "financial_stability", "quality_systems", "delivery_track_record",
                "after_sales_capability", "references", "reputation",
            ),
        )

    @app.get("/manufacturers/{mfr_id}/comparison", response_class=HTMLResponse)
    def manufacturer_comparison(
        mfr_id: str,
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """Manufacturer Comparison screen — multi-criteria, vendor-neutral."""
        with _db() as s:
            mfr = s.get(ManufacturerProfile, mfr_id)
            comparisons = s.execute(
                select(ManufacturerComparisonReport)
                .order_by(ManufacturerComparisonReport.created_at.desc())
                .limit(50)
            ).scalars().all()
        return _render(
            request, "manufacturer_comparison.html",
            principal=principal, mfr=mfr, comparisons=comparisons,
        )

    @app.get("/manufacturers/{mfr_id}/kuwait-representation", response_class=HTMLResponse)
    def kuwait_representation(
        mfr_id: str,
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """Kuwait Representation screen — status, agreement, expiry, conflict flag."""
        with _db() as s:
            mfr = s.get(ManufacturerProfile, mfr_id)
            from .services import WorkflowService
            svc = WorkflowService()
            kuwait_status = svc.get_kuwait_representation_status(
                manufacturer_id=mfr_id, manufacturer_name=mfr.manufacturer_name if mfr else "",
            )
            # Pull the relevant register entries for the screen.
            from .phase2_schema import (
                RepresentedPrincipal, ConflictDoNotPursueEntity, RestrictedProhibitedEntity,
            )
            rps = s.query(RepresentedPrincipal).filter(
                (RepresentedPrincipal.manufacturer_id == mfr_id)
            ).all()
            conflicts = s.query(ConflictDoNotPursueEntity).filter(
                (ConflictDoNotPursueEntity.entity_id == mfr_id)
            ).all()
            restricted = s.query(RestrictedProhibitedEntity).filter(
                (RestrictedProhibitedEntity.entity_id == mfr_id)
            ).all()
        return _render(
            request, "kuwait_representation.html",
            principal=principal, mfr=mfr, kuwait_status=kuwait_status,
            rps=rps, conflicts=conflicts, restricted=restricted,
        )

    @app.get("/manufacturers/{mfr_id}/qualification", response_class=HTMLResponse)
    def manufacturer_qualification(
        mfr_id: str,
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """Qualification Status screen — Prequalification (ENT-REG-002)."""
        with _db() as s:
            mfr = s.get(ManufacturerProfile, mfr_id)
            quals = s.execute(
                select(PrequalificationStatusReport)
                .order_by(PrequalificationStatusReport.created_at.desc())
                .limit(50)
            ).scalars().all()
        return _render(
            request, "manufacturer_qualification.html",
            principal=principal, mfr=mfr, quals=quals,
        )

    @app.get("/manufacturers/{mfr_id}/profile", response_class=HTMLResponse)
    def manufacturer_profile_screen(
        mfr_id: str,
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """Manufacturer Profile screen — the profile record itself."""
        with _db() as s:
            mfr = s.get(ManufacturerProfile, mfr_id)
        return _render(
            request, "manufacturer_profile.html",
            principal=principal, mfr=mfr,
        )

    # ==================================================================
    # COMMERCIAL DEVELOPMENT — 3 screens
    # ==================================================================

    @app.get("/commercial", response_class=HTMLResponse)
    def commercial_dashboard(
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """Commercial Intelligence Dashboard — the persona-appropriate Home for BD."""
        with _db() as s:
            evaluations = s.execute(
                select(CommercialEvaluation).order_by(CommercialEvaluation.created_at.desc()).limit(50)
            ).scalars().all()
            pricings = s.execute(
                select(PricingAnalysis).order_by(PricingAnalysis.created_at.desc()).limit(50)
            ).scalars().all()
            engagements = s.execute(
                select(BusinessDevelopmentEngagement).order_by(BusinessDevelopmentEngagement.created_at.desc()).limit(50)
            ).scalars().all()
        return _render(
            request, "commercial_dashboard.html",
            principal=principal, evaluations=evaluations,
            pricings=pricings, engagements=engagements,
        )

    @app.get("/commercial/engagement/{opp_id}", response_class=HTMLResponse)
    def bd_engagement(
        opp_id: str,
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """Business Development screen — engagement material, meeting brief, follow-up plan, pipeline update."""
        with _db() as s:
            engagements = s.execute(
                select(BusinessDevelopmentEngagement)
                .where(BusinessDevelopmentEngagement.opportunity_id == opp_id)
                .order_by(BusinessDevelopmentEngagement.created_at.desc())
            ).scalars().all()
            opp = s.get(Opportunity, opp_id)
        return _render(
            request, "bd_engagement.html",
            principal=principal, engagements=engagements, opp=opp, opp_id=opp_id,
        )

    @app.get("/commercial/quotation/{opp_id}", response_class=HTMLResponse)
    def quotation_dossier(
        opp_id: str,
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """Quotation Dossier screen — pricing + commercial case."""
        with _db() as s:
            pricing = s.execute(
                select(PricingAnalysis)
                .where(PricingAnalysis.opportunity_id == opp_id)
                .order_by(PricingAnalysis.created_at.desc())
            ).scalars().all()
            eval_ = s.execute(
                select(CommercialEvaluation)
                .where(CommercialEvaluation.opportunity_id == opp_id)
                .order_by(CommercialEvaluation.created_at.desc())
            ).scalars().all()
            opp = s.get(Opportunity, opp_id)
        return _render(
            request, "quotation_dossier.html",
            principal=principal, pricing=pricing, evaluations=eval_, opp=opp, opp_id=opp_id,
        )

    # ==================================================================
    # REGISTRATION AND MARKET ENTRY — 4 screens
    # ==================================================================

    @app.get("/registration", response_class=HTMLResponse)
    def registration_screen(
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """Registration screen — registration status, dossier, filing log."""
        with _db() as s:
            regs = s.execute(
                select(RegistrationStatusReport).order_by(RegistrationStatusReport.created_at.desc()).limit(100)
            ).scalars().all()
        return _render(
            request, "registration.html",
            principal=principal, registrations=regs,
        )

    @app.get("/registration/prequalification", response_class=HTMLResponse)
    def prequalification_screen(
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """Prequalification screen — qualification criteria, status, last update, source."""
        with _db() as s:
            quals = s.execute(
                select(PrequalificationStatusReport).order_by(PrequalificationStatusReport.created_at.desc()).limit(100)
            ).scalars().all()
        return _render(
            request, "prequalification.html",
            principal=principal, qualifications=quals,
        )

    @app.get("/market-entry/{opp_id}", response_class=HTMLResponse)
    def market_entry_screen(
        opp_id: str,
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """Market Entry screen — multi-path options, stakeholder map, risk map."""
        with _db() as s:
            options = s.execute(
                select(MarketEntryOptionsReport)
                .where(MarketEntryOptionsReport.opportunity_id == opp_id)
                .order_by(MarketEntryOptionsReport.created_at.desc())
            ).scalars().all()
            opp = s.get(Opportunity, opp_id)
        return _render(
            request, "market_entry.html",
            principal=principal, options=options, opp=opp, opp_id=opp_id,
        )

    @app.get("/market-status", response_class=HTMLResponse)
    def market_status_screen(
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """Market Status screen — market data, channel data, regulatory data."""
        with _db() as s:
            from .phase2_schema import (
                RepresentedPrincipal, ConflictDoNotPursueEntity, RestrictedProhibitedEntity,
            )
            rps = s.query(RepresentedPrincipal).limit(100).all()
            conflicts = s.query(ConflictDoNotPursueEntity).limit(100).all()
            restricted = s.query(RestrictedProhibitedEntity).limit(100).all()
            options = s.execute(
                select(MarketEntryOptionsReport).order_by(MarketEntryOptionsReport.created_at.desc()).limit(50)
            ).scalars().all()
        return _render(
            request, "market_status.html",
            principal=principal, rps=rps, conflicts=conflicts,
            restricted=restricted, options=options,
        )

    # ==================================================================
    # DASHBOARDS — 2 new (Phase 5 introduces)
    # ==================================================================

    @app.get("/dashboards/manufacturer", response_class=HTMLResponse)
    def dashboard_manufacturer(
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """Manufacturer Intelligence Dashboard."""
        with _db() as s:
            mfrs = s.execute(
                select(ManufacturerProfile).order_by(ManufacturerProfile.created_at.desc()).limit(50)
            ).scalars().all()
            creds = s.execute(
                select(ManufacturerCredibilityAssessment).order_by(ManufacturerCredibilityAssessment.created_at.desc()).limit(50)
            ).scalars().all()
            comparisons = s.execute(
                select(ManufacturerComparisonReport).order_by(ManufacturerComparisonReport.created_at.desc()).limit(50)
            ).scalars().all()
        return _render(
            request, "dashboard_manufacturer.html",
            principal=principal, mfrs=mfrs, creds=creds, comparisons=comparisons,
        )

    @app.get("/dashboards/commercial", response_class=HTMLResponse)
    def dashboard_commercial(
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """Commercial Intelligence Dashboard."""
        with _db() as s:
            evals_ = s.execute(
                select(CommercialEvaluation).order_by(CommercialEvaluation.created_at.desc()).limit(50)
            ).scalars().all()
            pricing = s.execute(
                select(PricingAnalysis).order_by(PricingAnalysis.created_at.desc()).limit(50)
            ).scalars().all()
            engagements = s.execute(
                select(BusinessDevelopmentEngagement).order_by(BusinessDevelopmentEngagement.created_at.desc()).limit(50)
            ).scalars().all()
            regs = s.execute(
                select(RegistrationStatusReport).order_by(RegistrationStatusReport.created_at.desc()).limit(50)
            ).scalars().all()
        return _render(
            request, "dashboard_commercial.html",
            principal=principal, evaluations=evals_, pricing=pricing,
            engagements=engagements, registrations=regs,
        )


# i18n (lite): register the 	 filter + i18n globals on this phase's templates.
from .i18n import apply_to_jinja
apply_to_jinja(templates)
