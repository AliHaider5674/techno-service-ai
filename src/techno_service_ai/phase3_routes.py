"""Phase 3 Presentation Layer — 10 screens.

Wires the Workflow, Verification, Approval, Notification, Escalation,
Handoff, Exception, and Recovery engines to the FastAPI app. The
screens are the 10 from the UI/UX Specification §4.6 (Verification)
and §4.7 (Approval):

  - SCR-VER-001 Preliminary Review Queue
  - SCR-VER-002 Specialist Verification Queue
  - SCR-VER-003 Independent Final Verification Queue
  - SCR-VER-004 Verification Workspace
  - SCR-VER-005 Claim Classification
  - SCR-VER-006 Independence Tracker
  - SCR-APR-001 Approval Inbox
  - SCR-APR-002 Approval Request
  - SCR-APR-003 Approval Records
  - SCR-APR-004 Approval Authority Matrix display

  - SCR-NOT-001 Notification Inbox (UI/UX §10 NOT-003) — included
    as the 11th screen.

Constitutional source:
  - Constitution Articles VI, XII, XVII, XXIII
  - Document 06 §4.4, §5, §6
  - Document 07 §4.6, §4.7, §10
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from .approval import (
    ApprovalDecision,
    ApprovalEngine,
    ApprovalPackage,
    DecisionClass,
    REQUIRED_APPROVER_ROLE,
    StandingAuthorisationValidator,
    SilenceNotApproval,
    SoDViolation,
)
from .db import SessionLocal
from .deps import Principal, current_principal, require_any_role
from .escalation import EscalationChannel, EscalationEngine
from .exceptions import ExceptionEngine, ExceptionScenario, EXCEPTION_SPECS, all_scenarios
from .gates import GATES, GateEngine, GateName, all_gates
from .handoff import HandoffService
from .notification import (
    NotificationCategory,
    NotificationChannel,
    NotificationEngine,
    NotificationPriority,
)
from .recovery import RecoveryEngine
from .schema import Role
from .stages import DISCOVERY_ORDER, StageNumber
from .states import ALLOWED_TRANSITIONS, OrchestrationState
from .verification import (
    ClaimClassification,
    IndependenceTracker,
    ProducerRef,
    VerifierAgent,
    VerifierRef,
    VerifierRole,
    VerificationOutcome,
    five_agent_roster,
)


TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def add_phase3_routes(app: FastAPI) -> None:
    """Mount the 10 Phase 3 screens onto the FastAPI app."""

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
        # Starlette's TemplateResponse signature: (request, name, context, status_code)
        return templates.TemplateResponse(
            request, f"phase3/{template_name}", context=ctx, status_code=status_code
        )

    # ======================================================================
    # VERIFICATION SCREENS (UI/UX §4.6) — 6 screens
    # ======================================================================

    @app.get("/verification/preliminary-queue", response_class=HTMLResponse)
    def preliminary_review_queue(
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """SCR-VER-001 — Preliminary Review Queue (VER-PRE-001..003)."""
        return _render(
            request, "ver_preliminary_queue.html",
            principal=principal,
            verifier_role=VerifierRole.PRELIMINARY_EVIDENCE_REVIEWER,
            title="Preliminary Review Queue",
        )

    @app.get("/verification/specialist-queue", response_class=HTMLResponse)
    def specialist_verification_queue(
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """SCR-VER-002 — Specialist Verification Queue (VER-SPE-001..003)."""
        return _render(
            request, "ver_specialist_queue.html",
            principal=principal,
            verifier_role=VerifierRole.SPECIALIST_VERIFIER,
            title="Specialist Verification Queue",
        )

    @app.get("/verification/independent-final-queue", response_class=HTMLResponse)
    def independent_final_verification_queue(
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """SCR-VER-003 — Independent Final Verification Queue (VER-IFV-001..004)."""
        return _render(
            request, "ver_independent_final_queue.html",
            principal=principal,
            verifier_role=VerifierRole.INDEPENDENT_FINAL_VERIFIER,
            title="Independent Final Verification Queue",
        )

    @app.get("/verification/workspace", response_class=HTMLResponse)
    def verification_workspace(
        request: Request,
        claim_id: str = Query(...),
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """SCR-VER-004 — Verification Workspace (single record)."""
        return _render(
            request, "ver_workspace.html",
            principal=principal,
            claim_id=claim_id,
            title="Verification Workspace",
        )

    @app.get("/verification/claim-classification", response_class=HTMLResponse)
    def claim_classification(
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """SCR-VER-005 — Claim Classification (Constitution Article XXIII)."""
        return _render(
            request, "ver_claim_classification.html",
            principal=principal,
            classifications=list(ClaimClassification),
            title="Claim Classification",
        )

    @app.get("/verification/independence-tracker", response_class=HTMLResponse)
    def independence_tracker(
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """SCR-VER-006 — Independence Tracker (VER-IND-001..003)."""
        # The IndependenceTracker is per-workflow-instance. In Phase 3
        # the screen is a placeholder that documents the independence
        # guarantees; the live data is wired in Phase 4.
        return _render(
            request, "ver_independence_tracker.html",
            principal=principal,
            verifier_roles=list(VerifierRole),
            title="Independence Tracker",
        )

    # ======================================================================
    # APPROVAL SCREENS (UI/UX §4.7) — 4 screens
    # ======================================================================

    @app.get("/approvals/inbox", response_class=HTMLResponse)
    def approval_inbox(
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """SCR-APR-001 — Approval Inbox."""
        return _render(
            request, "apr_inbox.html",
            principal=principal,
            title="Approval Inbox",
        )

    @app.get("/approvals/request", response_class=HTMLResponse)
    def approval_request(
        request: Request,
        request_id: str = Query(...),
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """SCR-APR-002 — Approval Request."""
        return _render(
            request, "apr_request.html",
            principal=principal,
            request_id=request_id,
            decision_classes=list(DecisionClass),
            title="Approval Request",
        )

    @app.get("/approvals/records", response_class=HTMLResponse)
    def approval_records(
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """SCR-APR-003 — Approval Records (audit trail)."""
        return _render(
            request, "apr_records.html",
            principal=principal,
            title="Approval Records",
        )

    @app.get("/approvals/authority-matrix", response_class=HTMLResponse)
    def approval_authority_matrix(
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """SCR-APR-004 — Approval Authority Matrix display."""
        return _render(
            request, "apr_authority_matrix.html",
            principal=principal,
            decision_classes=list(DecisionClass),
            required_approver_roles=dict(REQUIRED_APPROVER_ROLE),
            title="Approval Authority Matrix",
        )

    # ======================================================================
    # NOTIFICATION INBOX (UI/UX §10 NOT-003) — 1 screen (the 11th)
    # ======================================================================

    @app.get("/notifications/inbox", response_class=HTMLResponse)
    def notification_inbox(
        request: Request,
        principal: Optional[Principal] = Depends(current_principal),
    ) -> HTMLResponse:
        """NOT-003 — Notification Inbox."""
        return _render(
            request, "not_inbox.html",
            principal=principal,
            categories=list(NotificationCategory),
            channels=list(NotificationChannel),
            priorities=list(NotificationPriority),
            title="Notification Inbox",
        )


# i18n (lite): register the 	 filter + i18n globals on this phase's templates.
from .i18n import apply_to_jinja
apply_to_jinja(templates)
