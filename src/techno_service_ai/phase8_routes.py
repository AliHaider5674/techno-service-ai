"""Phase 8 Routes — Quality Assurance Office.

The Quality Assurance Office produces 3 types of records:

  - Quality Review (ENT-QA-001) — §4.10.1
  - Output Audit Report (ENT-QA-003) — §4.10.2
  - Standards Compliance Report (ENT-QA-002) — §4.10.3

The presentation layer exposes:

  - /quality/             — Quality Office dashboard
  - /quality/review/new   — Create a Quality Review
  - /quality/audit/new    — Create an Output Audit Sample
  - /quality/standards/new — Create a Standards Compliance Report
  - /quality/release-readiness — The 25 Readiness Criteria (read-only)
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import SETTINGS
from .db import SessionLocal, session_scope
from .deps import Principal, client_ip, client_ua, current_principal, get_db, require_any_role
from .schema import User


TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def _readiness_checklist_html() -> str:
    """Render the 25 Readiness Criteria from the canonical markdown."""
    from pathlib import Path
    p = Path(__file__).resolve().parents[3] / "docs" / "RELEASE_READINESS_CHECKLIST.md"
    if not p.exists():
        return "<p>Release Readiness Checklist not yet generated.</p>"
    text = p.read_text(encoding="utf-8")
    # Minimal markdown -> HTML conversion: paragraphs + headings + tables.
    out: list[str] = []
    in_table = False
    in_code = False
    for line in text.splitlines():
        if line.startswith("```"):
            in_code = not in_code
            out.append("<pre>" if in_code else "</pre>")
            continue
        if in_code:
            out.append(line + "\n")
            continue
        if line.startswith("# "):
            out.append(f"<h1>{line[2:]}</h1>")
        elif line.startswith("## "):
            out.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith("### "):
            out.append(f"<h3>{line[4:]}</h3>")
        elif line.startswith("|") and line.endswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if all(set(c) <= set("-: ") for c in cells):
                continue  # separator
            if not in_table:
                out.append("<table class='rrc-table'>")
                in_table = True
            tag = "th" if out[-1].endswith("</tr>") or not any(s.endswith("</tr>") for s in out[-3:]) else "td"
            out.append("<tr>" + "".join(f"<{tag}>{c}</{tag}>" for c in cells) + "</tr>")
        elif line.startswith("|---") or set(line.strip()) <= set("|-:"):
            continue
        elif line.strip() == "":
            if in_table:
                out.append("</table>")
                in_table = False
            out.append("<br/>")
        elif line.startswith("- "):
            out.append(f"<li>{line[2:]}</li>")
        else:
            out.append(f"<p>{line}</p>")
    if in_table:
        out.append("</table>")
    return "\n".join(out)


def add_phase8_routes(app: FastAPI) -> None:
    """Mount the Phase 8 Quality Assurance Office routes."""

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

    @app.get("/quality/", response_class=HTMLResponse)
    def quality_dashboard(
        request: Request,
        db: Session = Depends(get_db),
        principal: Principal = Depends(
            require_any_role("ADMIN", "COMPLIANCE", "QUALITY", "AUDITOR")
        ),
    ) -> Response:
        from .phase2_schema import (
            OutputAuditReport, QualityReview, StandardsComplianceReport,
        )
        quality_reviews = list(
            db.execute(select(QualityReview).order_by(QualityReview.created_at.desc()).limit(20)).scalars()
        )
        audit_reports = list(
            db.execute(select(OutputAuditReport).order_by(OutputAuditReport.created_at.desc()).limit(20)).scalars()
        )
        standards_reports = list(
            db.execute(select(StandardsComplianceReport).order_by(StandardsComplianceReport.created_at.desc()).limit(20)).scalars()
        )
        return _render(
            request, "phase8/quality_dashboard.html",
            principal=principal,
            quality_reviews=quality_reviews,
            audit_reports=audit_reports,
            standards_reports=standards_reports,
            error=None,
        )

    @app.get("/quality/review/new", response_class=HTMLResponse)
    def quality_review_new_get(
        request: Request,
        principal: Principal = Depends(
            require_any_role("ADMIN", "QUALITY")
        ),
    ) -> Response:
        return _render(
            request, "phase8/quality_review_new.html",
            principal=principal, error=None,
        )

    @app.post("/quality/review/new")
    def quality_review_new_post(
        request: Request,
        target_type: str = Form(...),
        target_id: str = Form(...),
        verification_record_id: str = Form(...),
        review_date: str = Form(...),
        criterion_names: str = Form(""),  # newline-separated
        criterion_weights: str = Form(""),  # newline-separated
        criterion_statuses: str = Form(""),  # newline-separated
        notes: str = Form(""),
        principal: Principal = Depends(
            require_any_role("ADMIN", "QUALITY")
        ),
    ) -> Response:
        from .services import WorkflowService
        names = [n.strip() for n in criterion_names.splitlines() if n.strip()]
        weights = [float(w.strip()) for w in criterion_weights.splitlines() if w.strip()]
        statuses = [s.strip() for s in criterion_statuses.splitlines() if s.strip()]
        if not (len(names) == len(weights) == len(statuses)):
            return _render(
                request, "phase8/quality_review_new.html",
                principal=principal,
                error="criterion_names / weights / statuses must have the same count.",
                status_code=400,
            )
        criteria = [
            {"name": n, "weight": w, "status": s, "description": n, "finding": ""}
            for n, w, s in zip(names, weights, statuses)
        ]
        try:
            WorkflowService().create_quality_review(
                actor_id=principal.user_id,
                role_code=principal.role_codes[0] if principal.role_codes else "QUALITY",
                target_type=target_type,
                target_id=target_id,
                reviewer_id=principal.user_id,
                criteria_specs=criteria,
                verification_record_id=verification_record_id,
                review_date=review_date,
                notes=notes,
            )
        except Exception as e:
            return _render(
                request, "phase8/quality_review_new.html",
                principal=principal, error=str(e), status_code=400,
            )
        return RedirectResponse(url="/quality/", status_code=303)

    @app.get("/quality/audit/new", response_class=HTMLResponse)
    def quality_audit_new_get(
        request: Request,
        principal: Principal = Depends(
            require_any_role("ADMIN", "QUALITY", "AUDITOR")
        ),
    ) -> Response:
        return _render(
            request, "phase8/quality_audit_new.html",
            principal=principal, error=None,
        )

    @app.post("/quality/audit/new")
    def quality_audit_new_post(
        request: Request,
        sample_id: str = Form(...),
        target_type: str = Form(...),
        target_id: str = Form(...),
        selection_method: str = Form("RANDOM"),
        audit_date: str = Form(...),
        notes: str = Form(""),
        principal: Principal = Depends(
            require_any_role("ADMIN", "QUALITY", "AUDITOR")
        ),
    ) -> Response:
        from .services import WorkflowService
        try:
            WorkflowService().create_audit_sample(
                actor_id=principal.user_id,
                role_code=principal.role_codes[0] if principal.role_codes else "QUALITY",
                sample_id=sample_id,
                target_type=target_type,
                target_id=target_id,
                selection_method=selection_method,
                audit_criteria=["accuracy", "completeness", "constitutional_compliance"],
                audit_date=audit_date,
                notes=notes,
            )
        except Exception as e:
            return _render(
                request, "phase8/quality_audit_new.html",
                principal=principal, error=str(e), status_code=400,
            )
        return RedirectResponse(url="/quality/", status_code=303)

    @app.get("/quality/standards/new", response_class=HTMLResponse)
    def quality_standards_new_get(
        request: Request,
        principal: Principal = Depends(
            require_any_role("ADMIN", "QUALITY", "COMPLIANCE")
        ),
    ) -> Response:
        return _render(
            request, "phase8/quality_standards_new.html",
            principal=principal, error=None,
        )

    @app.post("/quality/standards/new")
    def quality_standards_new_post(
        request: Request,
        target_type: str = Form(...),
        target_id: str = Form(...),
        standard: str = Form(...),
        target_evidence: str = Form(""),
        review_date: str = Form(...),
        notes: str = Form(""),
        principal: Principal = Depends(
            require_any_role("ADMIN", "QUALITY", "COMPLIANCE")
        ),
    ) -> Response:
        from .services import WorkflowService
        try:
            WorkflowService().create_standards_compliance_report(
                actor_id=principal.user_id,
                role_code=principal.role_codes[0] if principal.role_codes else "QUALITY",
                target_type=target_type,
                target_id=target_id,
                standard=standard,
                target_evidence=target_evidence,
                review_date=review_date,
                notes=notes,
            )
        except Exception as e:
            return _render(
                request, "phase8/quality_standards_new.html",
                principal=principal, error=str(e), status_code=400,
            )
        return RedirectResponse(url="/quality/", status_code=303)

    @app.get("/quality/release-readiness", response_class=HTMLResponse)
    def release_readiness(
        request: Request,
        principal: Principal = Depends(
            require_any_role("ADMIN", "COMPLIANCE", "AUDITOR", "EXECUTIVE", "QUALITY")
        ),
    ) -> Response:
        return _render(
            request, "phase8/release_readiness.html",
            principal=principal, body=_readiness_checklist_html(),
        )
