# Quick Start — Live Demo (Constitution v2.4)

**Live server URL:** `http://127.0.0.1:8000/`
**Constitutional authority:** Constitution v2.4 (Class 4 adoption 2026-07-19)
**v1.0 baseline:** FROZEN (8 commits; 259/259 tests; 17 Offices; 69 Agents; 92 entities)
**v2.4 surface:** 18 Offices; 73 Agents; 98 entities; 289/289 tests

---

## 1. Start the server (SQLite dev)

```powershell
cd C:\Users\malhu\.mavis\workspace\techno-service-ai
$env:TSAI_DATABASE_URL = "sqlite:///./data/live_demo.db"
$env:TSAI_JWT_SECRET  = "live-demo-secret-2026-07-19"
$env:TSAI_DEFAULT_ADMIN_PASSWORD = "Admin!2026"
$env:PYTHONPATH = "src"
python -c "from techno_service_ai import bootstrap, db; db.apply_schema(); bootstrap.seed()"
python -m uvicorn techno_service_ai.app:app --host 127.0.0.1 --port 8000
```

Swagger UI: `http://127.0.0.1:8000/docs`

## 2. Production database (PostgreSQL 15+)

```powershell
# Install (admin elevation required)
winget install --id PostgreSQL.PostgreSQL.15 --accept-package-agreements --accept-source-agreements

# Create dev DB
createdb -U postgres tsai_demo

# Set env var
$env:TSAI_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/tsai_demo"

# Run constitutional migration framework
python -c "from techno_service_ai import bootstrap, db; db.apply_schema(); bootstrap.seed()"

# Restart uvicorn pointing to PostgreSQL
python -m uvicorn techno_service_ai.app:app --host 127.0.0.1 --port 8000
```

The constitutional trigger pattern is portable to PostgreSQL with
one DDL translation step
(`BEFORE UPDATE/DELETE RAISE(ABORT)` → `RAISE EXCEPTION`).

## 3. 8 Demo Steps (Proactive Product Discovery, Office 18)

1. **Sign in** as `admin` / `Admin!2026` at `http://127.0.0.1:8000/sign-in`.
2. **Open Proactive Discovery Dashboard** at `http://127.0.0.1:8000/proactive/`.
3. **Trigger Global Product Monitor** at `http://127.0.0.1:8000/proactive/scan`
   with: product name, category, sector, manufacturer, source URL.
4. **Apply 5 Qualification Filters** at `http://127.0.0.1:8000/proactive/qualify`:
   F1 Kuwait climate, F2 retrofit, F3 no agent in Kuwait, F4 low operating
   cost, F5 medium/emerging company. All 5 must PASS for QUALIFIED.
5. **Surface a Patent Alert** at `http://127.0.0.1:8000/proactive/patents`.
6. **Initiate Exclusive Agency Acquisition Workflow** at
   `http://127.0.0.1:8000/proactive/agency-workflow`:
   - Steps 1-5: no approval needed.
   - **Step 6: Class 3 approval REQUIRED** to proceed with outreach.
   - **Step 8: Class 4 approval REQUIRED** to sign exclusive agency.
7. **Persist Daily Proactive Discovery Report** at
   `http://127.0.0.1:8000/proactive/report` (source citation REQUIRED).
8. **Verify the 3 Constitutional Registers** are checked at the gate
   (RESTRICTED / CONFLICT / NON_REPRESENTED).

## 4. Default admin credentials

- **Username:** `admin`
- **Password:** `Admin!2026` (change in any non-demo environment)
- **Roles:** ADMIN, COMPLIANCE, AUDITOR, COMMERCIAL, EXECUTIVE, DISCOVERY

## 5. Other constitutional surfaces (v1.0 baseline)

| Office | Section | Path |
|---|---|---|
| Executive AI | §4.1 | `/home` |
| Industrial Intelligence | §4.2 | `/discovery/industrial` |
| Opportunity Intelligence | §4.3 | `/opportunities` |
| Technology Intelligence | §4.4 | `/discovery/tech` |
| Manufacturer Intelligence | §4.5 | `/manufacturers` |
| Commercial Development | §4.6 | `/commercial/dashboard` |
| Registration and Market Entry | §4.7 | `/registration` |
| Tender and Project | §4.8 | `/tenders` |
| Verification | §4.9 | `/verification/dashboard` |
| Quality Assurance | §4.10 | `/quality/` |
| Risk and Compliance | §4.11 | `/incidents` |
| Security and Data Governance | §4.12 | (operational) |
| Knowledge and Institutional Memory | §4.13 | `/knowledge` |
| Relationship Management | §4.14 | (operational) |
| Reporting and Decision Support | §4.15 | `/reports/executive` |
| Notification and Monitoring | §4.16 | `/notifications` |
| Performance and Learning | §4.17 | `/performance/report` |
| **Product Discovery Proactive (v2.4)** | **§4.18** | **`/proactive/`** |

## 6. Test suite

```powershell
$env:PYTHONPATH = "src"
python -m pytest tests/ -q
# 289 passed, 161 warnings in ~7m
```

## 7. What changed in v2.4 (additive, v1.0 preserved)

- 1 new Office (Office 18, Product Discovery Proactive).
- 4 new Principal Agents (§4.18.1-4).
- 1 new Discovery Order stage (Stage 8.5, Proactive Discovery).
- 5 new Qualification Filters (F1..F5).
- 1 new Workflow (Exclusive Agency Acquisition, 10 steps).
- 6 new Canonical Entities (ENT-PD-001..006).
- 7 new UI/UX Screens (SCR-PD-001..007).
- 3 new External Integrations (Web Search, Patent Search, Trade Publications).

**v2.3 unchanged.** Document Hierarchy and Change Control (Article XXIX) observed.

## 8. Operational follow-ups (HD-PHASE8-002..006)

These are operational, not constitutional:

- HD-PHASE8-002: Production DB engine confirmation (PostgreSQL 15+).
- HD-PHASE8-003: Production Audit Log initialisation.
- HD-PHASE8-004: Production encryption at rest (TDE).
- HD-PHASE8-005: Production UAT with named personas.
- HD-PHASE8-006: Production SLO verification (Schedule A Item 15, 30-day window).

See `docs/PRODUCTION_LAUNCH_SUMMARY.md` for the full migration plan.
