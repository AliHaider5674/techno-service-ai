"""Phase 7 Presentation Layer — Every Office Alive.

Mounts the closing surfaces for the 7 Offices activated in Phase 7:

  - 5 Dashboards (Operations, Verification, Commercial, AI Activity, KPI).
  - 4 Reports Centers (Executive, Operational, Compliance, Commercial).
  - Notification Center + Settings.
  - Incident Response.
  - Performance / Bottleneck / SLA / Office Workload reports.
  - Continuous Learning workflow.

The screens render real data from the Phase 2 entities. Every
Report carries a Constitutional Compliance Attestation. The
Notification engine enforces the 6 categories × 5 channels with
suppression of Class 3/4 REJECTED.

Constitutional source:
  - Constitution Articles XII, XVII, XX, XXV, XXVIII
  - Document 02 §4.1, §4.11, §4.12, §4.14, §4.15, §4.16, §4.17
  - Document 07 §4.3, §4.4, §4.10, §4.12, §4.13
"""
from __future__ import annotations

import json
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
    ComplianceReviewReport,
    ConstitutionalIncident,
    ContinuityEvent,
    CustomerProfile,
    CustomerRelationshipHistory,
    DataClassificationEntry,
    DisclosurePermission,
    EnterpriseRisk,
    KnowledgeBaseInventory,
    KnowledgeRecord,
    LearningUpdate,
    LessonLearned,
    ManufacturerRelationshipRecord,
    NotificationChannel,
    NotificationPreference,
    NotificationRecord,
    PartnerProfile,
    PartnerRelationshipHistory,
    PerformanceRecord,
    Report,
    ReportTemplate,
    SecurityEvent,
)


TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _from_json(value):
    """Jinja filter: parse a JSON string."""
    if not value:
        return []
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return []


templates.env.filters["from_json"] = _from_json


def add_phase7_routes(app: FastAPI) -> None:
    """Mount the Phase 7 screens onto the FastAPI app."""

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
            request, f"phase7/{template_name}", context=ctx, status_code=status_code
        )

    def _db() -> Session:
        return SessionLocal()

    # ==================================================================
    # 5 NEW DASHBOARDS
    # ==================================================================

    @app.get("/dashboards/operations", response_class=HTMLResponse)
    def dashboard_operations(
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """Operations Dashboard — workflow throughput + active risks."""
        with _db() as s:
            risks = s.execute(
                select(EnterpriseRisk).order_by(EnterpriseRisk.created_at.desc()).limit(50)
            ).scalars().all()
            incidents = s.execute(
                select(ConstitutionalIncident).order_by(ConstitutionalIncident.created_at.desc()).limit(50)
            ).scalars().all()
        return _render(
            request, "dashboard_operations.html",
            principal=principal, risks=risks, incidents=incidents,
        )

    @app.get("/dashboards/verification", response_class=HTMLResponse)
    def dashboard_verification(
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """Verification Dashboard — verification activity."""
        from .phase2_schema import (
            PreliminaryReview, SpecialistVerification, IndependentFinalVerification,
        )
        with _db() as s:
            pre = s.execute(select(PreliminaryReview).order_by(PreliminaryReview.created_at.desc()).limit(20)).scalars().all()
            spec = s.execute(select(SpecialistVerification).order_by(SpecialistVerification.created_at.desc()).limit(20)).scalars().all()
            ind = s.execute(select(IndependentFinalVerification).order_by(IndependentFinalVerification.created_at.desc()).limit(20)).scalars().all()
        return _render(
            request, "dashboard_verification.html",
            principal=principal, preliminaries=pre, specialists=spec, independents=ind,
        )

    @app.get("/dashboards/commercial", response_class=HTMLResponse)
    def dashboard_commercial(
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """Commercial Dashboard — Commercial Outcomes + Pricing."""
        from .phase2_schema import CommercialEvaluation, PricingAnalysis
        with _db() as s:
            evals = s.execute(select(CommercialEvaluation).order_by(CommercialEvaluation.created_at.desc()).limit(50)).scalars().all()
            prices = s.execute(select(PricingAnalysis).order_by(PricingAnalysis.created_at.desc()).limit(50)).scalars().all()
        return _render(
            request, "dashboard_commercial.html",
            principal=principal, evaluations=evals, pricings=prices,
        )

    @app.get("/dashboards/ai-activity", response_class=HTMLResponse)
    def dashboard_ai_activity(
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """AI Activity Dashboard — recent AI recommendations + history."""
        from .phase2_schema import AIRecommendationLog
        with _db() as s:
            ai_logs = s.execute(select(AIRecommendationLog).order_by(AIRecommendationLog.created_at.desc()).limit(50)).scalars().all()
        return _render(
            request, "dashboard_ai_activity.html",
            principal=principal, ai_logs=ai_logs,
        )

    @app.get("/dashboards/kpi", response_class=HTMLResponse)
    def dashboard_kpi(
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """KPI Monitoring Dashboard — performance metrics."""
        with _db() as s:
            # The LearningUpdate is reused for performance metrics in Phase 7.
            metrics = s.execute(select(LearningUpdate).order_by(LearningUpdate.created_at.desc()).limit(50)).scalars().all()
            incidents = s.execute(select(ConstitutionalIncident).order_by(ConstitutionalIncident.created_at.desc()).limit(20)).scalars().all()
        return _render(
            request, "dashboard_kpi.html",
            principal=principal, metrics=metrics, incidents=incidents,
        )

    # ==================================================================
    # 4 REPORTS CENTERS
    # ==================================================================

    @app.get("/reports/executive", response_class=HTMLResponse)
    def reports_executive(
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """Executive Reports Center — board-grade + executive reports."""
        with _db() as s:
            reports = s.execute(
                select(Report).order_by(Report.created_at.desc()).limit(50)
            ).scalars().all()
        return _render(
            request, "reports_executive.html",
            principal=principal, reports=reports, report_type="EXECUTIVE",
        )

    @app.get("/reports/operational", response_class=HTMLResponse)
    def reports_operational(
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """Operational Reports Center — operational dashboards."""
        with _db() as s:
            reports = s.execute(
                select(Report).order_by(Report.created_at.desc()).limit(50)
            ).scalars().all()
            templates_ = s.execute(
                select(ReportTemplate).order_by(ReportTemplate.created_at.desc()).limit(20)
            ).scalars().all()
        return _render(
            request, "reports_operational.html",
            principal=principal, reports=reports, templates=templates_, report_type="OPERATIONAL",
        )

    @app.get("/reports/compliance", response_class=HTMLResponse)
    def reports_compliance(
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """Compliance Reports Center — constitutional compliance reports."""
        with _db() as s:
            reports = s.execute(
                select(Report).order_by(Report.created_at.desc()).limit(50)
            ).scalars().all()
            reviews = s.execute(
                select(ComplianceReviewReport).order_by(ComplianceReviewReport.created_at.desc()).limit(50)
            ).scalars().all()
        return _render(
            request, "reports_compliance.html",
            principal=principal, reports=reports, reviews=reviews, report_type="COMPLIANCE",
        )

    @app.get("/reports/commercial", response_class=HTMLResponse)
    def reports_commercial(
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """Commercial Reports Center — commercial reports."""
        from .phase2_schema import CommercialOutcomeReport
        with _db() as s:
            reports = s.execute(
                select(Report).order_by(Report.created_at.desc()).limit(50)
            ).scalars().all()
            outcomes = s.execute(
                select(CommercialOutcomeReport).order_by(CommercialOutcomeReport.created_at.desc()).limit(50)
            ).scalars().all()
        return _render(
            request, "reports_commercial.html",
            principal=principal, reports=reports, outcomes=outcomes, report_type="COMMERCIAL",
        )

    # ==================================================================
    # NOTIFICATION CENTER
    # ==================================================================

    @app.get("/notifications/center", response_class=HTMLResponse)
    def notifications_center(
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """Notification Center — 6 categories × 5 channels."""
        with _db() as s:
            notifications = s.execute(
                select(NotificationRecord).order_by(NotificationRecord.created_at.desc()).limit(100)
            ).scalars().all()
            channels = s.execute(
                select(NotificationChannel).order_by(NotificationChannel.created_at.desc()).limit(20)
            ).scalars().all()
        return _render(
            request, "notifications_center.html",
            principal=principal, notifications=notifications, channels=channels,
        )

    @app.get("/notifications/settings", response_class=HTMLResponse)
    def notifications_settings(
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """Notification Settings — user preferences per channel × category."""
        with _db() as s:
            prefs = s.execute(
                select(NotificationPreference).order_by(NotificationPreference.created_at.desc()).limit(100)
            ).scalars().all()
        return _render(
            request, "notifications_settings.html",
            principal=principal, prefs=prefs,
        )

    # ==================================================================
    # INCIDENT RESPONSE
    # ==================================================================

    @app.get("/incidents", response_class=HTMLResponse)
    def incidents_list(
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """Incident Response — Constitutional Incidents."""
        with _db() as s:
            incidents = s.execute(
                select(ConstitutionalIncident).order_by(ConstitutionalIncident.created_at.desc()).limit(100)
            ).scalars().all()
        return _render(
            request, "incidents.html",
            principal=principal, incidents=incidents,
        )

    # ==================================================================
    # PERFORMANCE / BOTTLENECK / SLA / OFFICE WORKLOAD
    # ==================================================================

    @app.get("/performance-report", response_class=HTMLResponse)
    def performance_report(
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """Performance Report — KPIs + trends."""
        with _db() as s:
            metrics = s.execute(
                select(LearningUpdate).order_by(LearningUpdate.created_at.desc()).limit(50)
            ).scalars().all()
        return _render(
            request, "performance_report.html",
            principal=principal, metrics=metrics,
        )

    @app.get("/bottleneck-report", response_class=HTMLResponse)
    def bottleneck_report(
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """Bottleneck Report — workflow bottlenecks detected."""
        with _db() as s:
            incidents = s.execute(
                select(ConstitutionalIncident).order_by(ConstitutionalIncident.created_at.desc()).limit(20)
            ).scalars().all()
        return _render(
            request, "bottleneck_report.html",
            principal=principal, incidents=incidents,
        )

    @app.get("/sla-monitor", response_class=HTMLResponse)
    def sla_monitor(
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """SLA Monitor — SLA performance."""
        with _db() as s:
            metrics = s.execute(
                select(LearningUpdate).order_by(LearningUpdate.created_at.desc()).limit(20)
            ).scalars().all()
        return _render(
            request, "sla_monitor.html",
            principal=principal, metrics=metrics,
        )

    @app.get("/office-workload", response_class=HTMLResponse)
    def office_workload(
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """Office Workload — activity per Office."""
        with _db() as s:
            # Show counts of recent activity by entity type.
            risk_count = s.query(EnterpriseRisk).count()
            incident_count = s.query(ConstitutionalIncident).count()
            notification_count = s.query(NotificationRecord).count()
            report_count = s.query(Report).count()
            knowledge_count = s.query(KnowledgeRecord).count()
            lesson_count = s.query(LessonLearned).count()
        return _render(
            request, "office_workload.html",
            principal=principal,
            risk_count=risk_count, incident_count=incident_count,
            notification_count=notification_count, report_count=report_count,
            knowledge_count=knowledge_count, lesson_count=lesson_count,
        )

    # ==================================================================
    # CONTINUOUS LEARNING WORKFLOW
    # ==================================================================

    @app.get("/continuous-learning", response_class=HTMLResponse)
    def continuous_learning(
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """Continuous Learning workflow — review + approve proposals."""
        with _db() as s:
            learning_updates = s.execute(
                select(LearningUpdate).order_by(LearningUpdate.created_at.desc()).limit(50)
            ).scalars().all()
        return _render(
            request, "continuous_learning.html",
            principal=principal, learning_updates=learning_updates,
        )
