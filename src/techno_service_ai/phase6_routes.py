"""Phase 6 Presentation Layer — Tender, Project, Knowledge, and the 24-Stage Walk.

Mounts the screens for the last two Offices activated in Phase 6:

  - Tender and Project Intelligence Office (§4.8): Tender Workspace,
    Quotation Dossier, Tender Submission Dossier, Project Status,
    After-Sales.
  - Knowledge and Institutional Memory Office (§4.13): Knowledge
    Records, Knowledge Record (single), Lessons Learned, Institutional
    Memory Index, Knowledge Base Inventory.

The screens render real data from the Phase 2 entities. The
Tender Gate (GATE-TENDER), Project Gate (GATE-PROJECT), and
Closure Gate (GATE-CLOSURE) are invoked at the entry of every
relevant action.

Constitutional source:
  - Constitution Articles VI, VIII, XII, XVII, XIX, XX, XXVIII
  - Document 02 §4.8, §4.13
  - Document 06 §2.19..2.24 (Stages 19-24)
  - Document 07 §4.3, §4.4, §4.12
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
    AfterSalesIntelligenceReport,
    CommercialOutcomeReport,
    InstitutionalMemoryIndex,
    KnowledgeBaseInventory,
    KnowledgeRecord,
    LessonLearned,
    ProjectStatusReport,
    QuotationDossier,
    Tender,
    TenderQualificationReport,
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


def add_phase6_routes(app: FastAPI) -> None:
    """Mount the 9+ Phase 6 screens onto the FastAPI app."""

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
            request, f"phase6/{template_name}", context=ctx, status_code=status_code
        )

    def _db() -> Session:
        return SessionLocal()

    # ==================================================================
    # TENDER AND PROJECT INTELLIGENCE — 4 screens
    # ==================================================================

    @app.get("/tenders", response_class=HTMLResponse)
    def tenders_list(
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """Tender Workspace — the tender list and entry."""
        with _db() as s:
            tenders = s.execute(
                select(Tender).order_by(Tender.created_at.desc()).limit(100)
            ).scalars().all()
        return _render(
            request, "tenders_list.html",
            principal=principal, tenders=tenders,
        )

    @app.get("/tenders/{tender_id}", response_class=HTMLResponse)
    def tender_workspace(
        tender_id: str,
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """Tender Workspace — the tender home."""
        with _db() as s:
            tender = s.get(Tender, tender_id)
            if tender is None:
                return _render(
                    request, "tenders_list.html",
                    principal=principal, tenders=[],
                    not_found=tender_id, status_code=404,
                )
            quals = s.execute(
                select(TenderQualificationReport)
                .where(TenderQualificationReport.tender_id == tender_id)
                .order_by(TenderQualificationReport.created_at.desc())
            ).scalars().all()
            quotations = s.execute(
                select(QuotationDossier)
                .where(QuotationDossier.tender_id == tender_id)
                .order_by(QuotationDossier.created_at.desc())
            ).scalars().all()
        return _render(
            request, "tender_workspace.html",
            principal=principal, tender=tender, quals=quals, quotations=quotations,
        )

    @app.get("/tenders/{tender_id}/quotation-dossier", response_class=HTMLResponse)
    def quotation_dossier_screen(
        tender_id: str,
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """Quotation Dossier screen — the dossier record."""
        with _db() as s:
            tender = s.get(Tender, tender_id)
            quotations = s.execute(
                select(QuotationDossier)
                .where(QuotationDossier.tender_id == tender_id)
                .order_by(QuotationDossier.created_at.desc())
            ).scalars().all()
        return _render(
            request, "quotation_dossier.html",
            principal=principal, tender=tender, quotations=quotations,
        )

    @app.get("/tenders/{tender_id}/submission-dossier", response_class=HTMLResponse)
    def tender_submission_dossier(
        tender_id: str,
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """Tender Submission Dossier screen — submission package."""
        with _db() as s:
            tender = s.get(Tender, tender_id)
            quotations = s.execute(
                select(QuotationDossier)
                .where(QuotationDossier.tender_id == tender_id)
                .order_by(QuotationDossier.created_at.desc())
            ).scalars().all()
        return _render(
            request, "tender_submission_dossier.html",
            principal=principal, tender=tender, quotations=quotations,
        )

    @app.get("/projects", response_class=HTMLResponse)
    def projects_list(
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """Project Status — list of awarded projects."""
        with _db() as s:
            projects = s.execute(
                select(ProjectStatusReport).order_by(ProjectStatusReport.created_at.desc()).limit(100)
            ).scalars().all()
            after_sales = s.execute(
                select(AfterSalesIntelligenceReport).order_by(AfterSalesIntelligenceReport.created_at.desc()).limit(50)
            ).scalars().all()
        return _render(
            request, "projects_list.html",
            principal=principal, projects=projects, after_sales=after_sales,
        )

    # ==================================================================
    # KNOWLEDGE AND INSTITUTIONAL MEMORY — 4 screens
    # ==================================================================

    @app.get("/knowledge", response_class=HTMLResponse)
    def knowledge_records_list(
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """Knowledge Records list."""
        with _db() as s:
            records = s.execute(
                select(KnowledgeRecord).order_by(KnowledgeRecord.created_at.desc()).limit(100)
            ).scalars().all()
            inventory = s.execute(
                select(KnowledgeBaseInventory).order_by(KnowledgeBaseInventory.created_at.desc()).limit(50)
            ).scalars().all()
        return _render(
            request, "knowledge_records.html",
            principal=principal, records=records, inventory=inventory,
        )

    @app.get("/knowledge/{kr_id}", response_class=HTMLResponse)
    def knowledge_record_view(
        kr_id: str,
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """Knowledge Record (single record view)."""
        with _db() as s:
            record = s.get(KnowledgeRecord, kr_id)
        return _render(
            request, "knowledge_record.html",
            principal=principal, record=record,
        )

    @app.get("/lessons-learned", response_class=HTMLResponse)
    def lessons_learned_list(
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """Lessons Learned list."""
        with _db() as s:
            lessons = s.execute(
                select(LessonLearned).order_by(LessonLearned.created_at.desc()).limit(100)
            ).scalars().all()
        return _render(
            request, "lessons_learned.html",
            principal=principal, lessons=lessons,
        )

    @app.get("/institutional-memory", response_class=HTMLResponse)
    def institutional_memory_index(
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """Institutional Memory Index screen."""
        with _db() as s:
            entries = s.execute(
                select(InstitutionalMemoryIndex).order_by(InstitutionalMemoryIndex.created_at.desc()).limit(100)
            ).scalars().all()
            outcomes = s.execute(
                select(CommercialOutcomeReport).order_by(CommercialOutcomeReport.created_at.desc()).limit(50)
            ).scalars().all()
        return _render(
            request, "institutional_memory.html",
            principal=principal, entries=entries, outcomes=outcomes,
        )
