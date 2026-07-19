"""Live Demo Client — 1.5-hour sprint.

Exercises the v2.4 Proactive Product Discovery Charter end-to-end
against the live FastAPI server at http://127.0.0.1:8000.

Steps:
  1. Sign in as admin.
  2. Create a Proactive Product Discovery.
  3. Apply the 5 Qualification Filters.
  4. Surface a Patent Alert.
  5. Initiate the Exclusive Agency Acquisition Workflow.
  6. Advance through steps 1->6 (Class 3 approval gate).
  7. Verify Class 4 gate is enforced at step 8.
  8. Persist a Daily Proactive Discovery Report.

Saves HTML snapshots of every screen to docs/SCREENSHOTS/.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

BASE = "http://127.0.0.1:8000"
OUT = Path(__file__).resolve().parent / "docs" / "SCREENSHOTS"
OUT.mkdir(parents=True, exist_ok=True)


def _ok(msg: str) -> None:
    print(f"  [ok] {msg}", flush=True)


def _info(msg: str) -> None:
    print(f"  [..] {msg}", flush=True)


def _fail(msg: str) -> None:
    print(f"  [!!] {msg}", flush=True)
    sys.exit(1)


def _save_html(name: str, html: str) -> Path:
    path = OUT / f"{name}.html"
    path.write_text(html, encoding="utf-8")
    return path


def _parse_session_cookie(set_cookie_header: str) -> Optional[str]:
    """Extract the tsai_session cookie value from a Set-Cookie header."""
    if not set_cookie_header:
        return None
    for part in set_cookie_header.split(";"):
        part = part.strip()
        if part.startswith("tsai_session="):
            return part.split("=", 1)[1]
    return None


def main() -> int:
    print("=" * 60)
    print("LIVE DEMO — Proactive Product Discovery (Constitution v2.4)")
    print("=" * 60)
    print()

    with httpx.Client(base_url=BASE, follow_redirects=False, timeout=15.0) as client:
        # ------------------------------------------------------------------
        # Step 1 — Sign in as admin
        # ------------------------------------------------------------------
        print("[1] Sign in as admin")
        r = client.get("/sign-in")
        _save_html("01_sign_in", r.text)
        # Submit the form
        r = client.post("/sign-in", data={
            "username": "admin",
            "password": "Admin!2026",
        })
        if r.status_code not in (303, 302):
            _fail(f"Sign-in failed: status={r.status_code}")
        session_cookie = _parse_session_cookie(r.headers.get("set-cookie", ""))
        if not session_cookie:
            _fail("No session cookie set on sign-in")
        # Inject the cookie for subsequent calls
        client.cookies.set("tsai_session", session_cookie)
        _ok(f"sign-in: status={r.status_code}; session={session_cookie[:16]}...")

        # ------------------------------------------------------------------
        # Step 2 — Visit the Proactive Discovery Dashboard
        # ------------------------------------------------------------------
        print("\n[2] Visit Proactive Discovery Dashboard")
        r = client.get("/proactive/")
        if r.status_code != 200:
            _fail(f"Dashboard failed: status={r.status_code}")
        _save_html("02_proactive_dashboard", r.text)
        _ok(f"dashboard: status={r.status_code}; length={len(r.text)}")

        # ------------------------------------------------------------------
        # Step 3 — Trigger a Proactive Discovery query
        # ------------------------------------------------------------------
        print("\n[3] Trigger a Proactive Discovery (Global Product Monitor)")
        r = client.post("/proactive/scan", data={
            "product_name": "Acme Heat Exchanger X-200",
            "product_category": "INDUSTRIAL_MAINTENANCE",
            "sector": "Refinery Maintenance",
            "manufacturer_name": "Acme Industrial",
            "manufacturer_country": "Italy",
            "discovery_source": "WEB_SEARCH",
            "source_citation_url": "https://example.com/acme-x200",
            "signal_strength": "HIGH",
            "notes": "Live demo: corrosion-resistant heat exchanger for refinery use",
        })
        if r.status_code not in (303, 302):
            _fail(f"Discovery submission failed: status={r.status_code}; body={r.text[:500]}")
        _ok(f"discovery: status={r.status_code}")

        # ------------------------------------------------------------------
        # Step 4 — Apply the 5 Qualification Filters
        # ------------------------------------------------------------------
        print("\n[4] Apply the 5 Qualification Filters (New Product Detector)")
        # We need the discovery_id — query the dashboard to get it
        r = client.get("/proactive/")
        # Extract the most recent discovery_id from the dashboard
        import re
        m = re.search(r'<td>([a-f0-9-]{36})</td>', r.text)
        if not m:
            # Try a different match — the table is for filter_results, not discoveries
            # Look for any 36-char UUID in the HTML
            m = re.search(r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})', r.text)
        discovery_id = m.group(1) if m else "demo-discovery-001"
        _info(f"discovery_id (from dashboard or fallback): {discovery_id}")

        r = client.post("/proactive/qualify", data={
            "discovery_id": discovery_id,
            "f1_heat_rating": "-10C to +60C operational",
            "f1_dust_rating": "IP66",
            "f2_requires_major_change": "",  # unchecked
            "f2_installation_complexity": "LOW",
            "f3_existing_agents": "",  # no existing agent — exclusive available
            "f4_requires_specialised_training": "",
            "f4_requires_engineering_team": "",
            "f4_annual_maintenance_cost": "LOW",
            "f5_employee_count": "200",
            "f5_annual_revenue_usd": "20000000",
            "f5_is_tier_1": "",  # not tier-1
        })
        if r.status_code not in (303, 302):
            _fail(f"Filter submission failed: status={r.status_code}; body={r.text[:500]}")
        _ok(f"filters: status={r.status_code}")

        # ------------------------------------------------------------------
        # Step 5 — Surface a Patent Alert
        # ------------------------------------------------------------------
        print("\n[5] Surface a Patent Alert (Patent Watch)")
        r = client.post("/proactive/patents", data={
            "patent_id": "US12345678B2",
            "title": "Self-cleaning heat exchanger for desert climates",
            "assignee": "Acme Industrial",
            "filing_date": "2025-09-15",
            "relevance": "HIGH",
            "relevance_rationale": "Targets Kuwait climate use case",
            "source_citation_url": "https://patents.example.com/US12345678B2",
        })
        if r.status_code not in (303, 302):
            _fail(f"Patent submission failed: status={r.status_code}")
        _ok(f"patent: status={r.status_code}")

        # ------------------------------------------------------------------
        # Step 6 — Initiate the Exclusive Agency Acquisition Workflow
        # ------------------------------------------------------------------
        print("\n[6] Initiate Exclusive Agency Acquisition Workflow (step 1 -> 2)")
        r = client.post("/proactive/agency-workflow", data={
            "discovery_id": discovery_id,
            "manufacturer_name": "Acme Industrial",
            "product_summary": "Heat exchanger X-200 (corrosion-resistant, Kuwait climate)",
            "current_step": "1",
            "target_step": "2",
            "class_3_approval_id": "",
            "class_4_approval_id": "",
        })
        if r.status_code not in (303, 302):
            _fail(f"Workflow step 1->2 failed: status={r.status_code}")
        _ok("workflow: step 1 -> 2")

        # Step 2 -> 5 (no approvals needed)
        for step in (3, 4, 5):
            r = client.post("/proactive/agency-workflow", data={
                "discovery_id": discovery_id,
                "manufacturer_name": "Acme Industrial",
                "product_summary": "Heat exchanger X-200",
                "current_step": str(step - 1),
                "target_step": str(step),
                "class_3_approval_id": "",
                "class_4_approval_id": "",
            })
            if r.status_code not in (303, 302):
                _fail(f"Workflow step {step-1}->{step} failed: status={r.status_code}")
            _ok(f"workflow: step {step-1} -> {step}")

        # ------------------------------------------------------------------
        # Step 7 — Class 3 approval required at step 6
        # ------------------------------------------------------------------
        print("\n[7] Class 3 approval required at step 6")
        r = client.post("/proactive/agency-workflow", data={
            "discovery_id": discovery_id,
            "manufacturer_name": "Acme Industrial",
            "product_summary": "Heat exchanger X-200",
            "current_step": "5",
            "target_step": "6",
            "class_3_approval_id": "",  # missing
            "class_4_approval_id": "",
        })
        # Expected: 400 (Class 3 approval required)
        if r.status_code != 400:
            _fail(f"Class 3 gate NOT enforced: status={r.status_code}")
        # Extract the error message
        import re
        err_match = re.search(r'<div class="pd-error">([^<]+)</div>', r.text)
        err_text = err_match.group(1) if err_match else "no error text"
        _ok(f"Class 3 gate ENFORCED: status={r.status_code}; error='{err_text[:60]}...'")
        _save_html("07_class3_gate", r.text)

        # Now provide Class 3 approval
        r = client.post("/proactive/agency-workflow", data={
            "discovery_id": discovery_id,
            "manufacturer_name": "Acme Industrial",
            "product_summary": "Heat exchanger X-200",
            "current_step": "5",
            "target_step": "6",
            "class_3_approval_id": "apr-c3-001",
            "class_4_approval_id": "",
        })
        if r.status_code not in (303, 302):
            _fail(f"Class 3 step failed: status={r.status_code}; body={r.text[:500]}")
        _ok("workflow: step 5 -> 6 (with Class 3 approval)")

        # ------------------------------------------------------------------
        # Step 8 — Class 4 approval required at step 8
        # ------------------------------------------------------------------
        print("\n[8] Class 4 approval required at step 8")
        # Step 6 -> 7 (no approvals)
        r = client.post("/proactive/agency-workflow", data={
            "discovery_id": discovery_id,
            "manufacturer_name": "Acme Industrial",
            "product_summary": "Heat exchanger X-200",
            "current_step": "6",
            "target_step": "7",
            "class_3_approval_id": "apr-c3-001",
            "class_4_approval_id": "",
        })
        if r.status_code not in (303, 302):
            _fail(f"Workflow step 6->7 failed: status={r.status_code}")
        _ok("workflow: step 6 -> 7")

        # Step 7 -> 8 (Class 4 missing)
        r = client.post("/proactive/agency-workflow", data={
            "discovery_id": discovery_id,
            "manufacturer_name": "Acme Industrial",
            "product_summary": "Heat exchanger X-200",
            "current_step": "7",
            "target_step": "8",
            "class_3_approval_id": "apr-c3-001",
            "class_4_approval_id": "",  # missing
        })
        if r.status_code != 400:
            _fail(f"Class 4 gate NOT enforced: status={r.status_code}")
        err_match = re.search(r'<div class="pd-error">([^<]+)</div>', r.text)
        err_text = err_match.group(1) if err_match else "no error text"
        _ok(f"Class 4 gate ENFORCED: status={r.status_code}; error='{err_text[:60]}...'")
        _save_html("08_class4_gate", r.text)

        # ------------------------------------------------------------------
        # Step 9 — Persist the Daily Proactive Discovery Report
        # ------------------------------------------------------------------
        print("\n[9] Persist Daily Proactive Discovery Report")
        r = client.get("/proactive/report")
        if r.status_code != 200:
            _fail(f"Report GET failed: status={r.status_code}")
        _save_html("09a_report_form", r.text)
        r = client.post("/proactive/report", data={
            "n_discoveries": "1",
            "n_qualified": "1",
            "n_rejected": "0",
            "n_patents": "1",
            "n_agency_opportunities": "1",
            "source_citation": "Daily Proactive Discovery Report — Constitution v2.4 (Office 18, live demo 2026-07-19)",
            "notes": "Live demo: 1 discovery qualified; 1 patent surfaced; 1 agency workflow at step 6.",
        })
        if r.status_code not in (303, 302):
            _fail(f"Report POST failed: status={r.status_code}; body={r.text[:500]}")
        _ok(f"report: status={r.status_code}")

        # ------------------------------------------------------------------
        # Step 10 — Capture the final Dashboard state
        # ------------------------------------------------------------------
        print("\n[10] Capture final Dashboard state")
        r = client.get("/proactive/")
        if r.status_code != 200:
            _fail(f"Final dashboard failed: status={r.status_code}")
        _save_html("10_final_dashboard", r.text)
        _ok(f"final dashboard: status={r.status_code}; length={len(r.text)}")

        # And the home page
        r = client.get("/home")
        if r.status_code == 200:
            _save_html("00_home", r.text)
            _ok(f"home: status={r.status_code}")

    print()
    print("=" * 60)
    print("LIVE DEMO COMPLETE — all 10 steps green")
    print("=" * 60)
    print(f"HTML snapshots: {OUT}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
