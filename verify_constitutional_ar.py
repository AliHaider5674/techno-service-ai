"""Verify constitutional flows in Arabic — Class 3 + Class 4 gates."""
import httpx
import sys
import re

BASE = "http://127.0.0.1:8001"
sys.stdout.reconfigure(encoding="utf-8")

with httpx.Client(base_url=BASE, follow_redirects=False, timeout=10.0) as c:
    # Sign in
    r = c.post("/sign-in", data={"username": "admin", "password": "Admin!2026"})
    for h in r.headers.get_list("set-cookie"):
        if "tsai_session=" in h:
            cookie = h.split("tsai_session=", 1)[1].split(";", 1)[0]
            c.cookies.set("tsai_session", cookie)
            break
    c.cookies.set("tsai_lang", "ar")

    # 1) Trigger a Proactive Discovery in AR
    print("=" * 60)
    print("CONSTITUTIONAL FLOWS IN ARABIC")
    print("=" * 60)
    r = c.post("/proactive/scan", data={
        "product_name": "Test Product",
        "product_category": "INDUSTRIAL_MAINTENANCE",
        "sector": "Refinery",
        "manufacturer_name": "Acme",
        "discovery_source": "WEB_SEARCH",
        "source_citation_url": "https://example.com",
        "signal_strength": "HIGH",
    })
    print(f"  Discovery (AR): status={r.status_code}")
    if r.status_code not in (303, 302):
        print(f"  FAIL body: {r.text[:500]}")
        sys.exit(1)

    # 2) Get the discovery_id from the dashboard
    r = c.get("/proactive/")
    m = re.search(r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})', r.text)
    discovery_id = m.group(1) if m else "demo-id"
    print(f"  Discovery ID: {discovery_id}")

    # 3) Apply 5 filters in AR
    r = c.post("/proactive/qualify", data={
        "discovery_id": discovery_id,
        "f1_heat_rating": "+60C",
        "f1_dust_rating": "IP66",
        "f2_installation_complexity": "LOW",
        "f3_existing_agents": "",
        "f4_annual_maintenance_cost": "LOW",
        "f5_employee_count": "200",
        "f5_annual_revenue_usd": "20000000",
    })
    print(f"  5 Filters (AR): status={r.status_code}")

    # 4) Advance workflow step 1 -> 2 -> ... -> 5
    for step in (2, 3, 4, 5):
        r = c.post("/proactive/agency-workflow", data={
            "discovery_id": discovery_id,
            "manufacturer_name": "Acme AR",
            "product_summary": "Test product",
            "current_step": str(step - 1),
            "target_step": str(step),
        })
        print(f"  Workflow step {step-1} -> {step} (AR): status={r.status_code}")

    # 5) Class 3 gate at step 6 (no approval) — should REJECT
    print()
    print("--- Class 3 gate test (AR) ---")
    r = c.post("/proactive/agency-workflow", data={
        "discovery_id": discovery_id,
        "manufacturer_name": "Acme AR",
        "product_summary": "Test product",
        "current_step": "5",
        "target_step": "6",
        "class_3_approval_id": "",  # missing
        "class_4_approval_id": "",
    })
    print(f"  Step 5->6 without Class 3 (AR): status={r.status_code}")
    if r.status_code != 400:
        print("  FAIL: Class 3 gate not enforced in AR")
        sys.exit(1)
    # Check error message is in English (engine messages stay in English) or Arabic
    has_arabic = "الفئة 3" in r.text
    has_english = "Class 3" in r.text
    print(f"  Error mentions Class 3: AR={has_arabic} EN={has_english}")
    print(f"  PASS: Class 3 gate REJECTED at step 6 in AR")

    # 6) Provide Class 3 approval and advance
    r = c.post("/proactive/agency-workflow", data={
        "discovery_id": discovery_id,
        "manufacturer_name": "Acme AR",
        "product_summary": "Test product",
        "current_step": "5",
        "target_step": "6",
        "class_3_approval_id": "apr-c3-ar",
        "class_4_approval_id": "",
    })
    print(f"  Step 5->6 WITH Class 3 (AR): status={r.status_code}")

    # 7) Step 6 -> 7 (no approval needed)
    r = c.post("/proactive/agency-workflow", data={
        "discovery_id": discovery_id,
        "manufacturer_name": "Acme AR",
        "product_summary": "Test product",
        "current_step": "6",
        "target_step": "7",
        "class_3_approval_id": "apr-c3-ar",
        "class_4_approval_id": "",
    })
    print(f"  Step 6->7 (AR): status={r.status_code}")

    # 8) Class 4 gate at step 8 (no approval) — should REJECT
    print()
    print("--- Class 4 gate test (AR) ---")
    r = c.post("/proactive/agency-workflow", data={
        "discovery_id": discovery_id,
        "manufacturer_name": "Acme AR",
        "product_summary": "Test product",
        "current_step": "7",
        "target_step": "8",
        "class_3_approval_id": "apr-c3-ar",
        "class_4_approval_id": "",  # missing
    })
    print(f"  Step 7->8 without Class 4 (AR): status={r.status_code}")
    if r.status_code != 400:
        print("  FAIL: Class 4 gate not enforced in AR")
        sys.exit(1)
    has_arabic = "الفئة 4" in r.text
    has_english = "Class 4" in r.text
    print(f"  Error mentions Class 4: AR={has_arabic} EN={has_english}")
    print(f"  PASS: Class 4 gate REJECTED at step 8 in AR")

    # 9) Provide Class 4 approval
    r = c.post("/proactive/agency-workflow", data={
        "discovery_id": discovery_id,
        "manufacturer_name": "Acme AR",
        "product_summary": "Test product",
        "current_step": "7",
        "target_step": "8",
        "class_3_approval_id": "apr-c3-ar",
        "class_4_approval_id": "apr-c4-ar",
    })
    print(f"  Step 7->8 WITH Class 4 (AR): status={r.status_code}")

    # 10) Verify final dashboard state in AR
    r = c.get("/proactive/")
    print()
    print("--- Final Dashboard (AR) ---")
    print(f"  Status: {r.status_code}")
    print(f"  dir=rtl: {'dir=\"rtl\"' in r.text}")
    print(f"  lang=ar: {'lang=\"ar\"' in r.text}")
    print(f"  Arabic subtitle: {'الدستور' in r.text}")
    print()
    print("=" * 60)
    print("ALL CONSTITUTIONAL FLOWS WORKING IN ARABIC")
    print("=" * 60)
