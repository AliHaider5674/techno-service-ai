# Techno Service AI Intelligence System

**Phase 1 Deliverable — Identity, Access, and Audit Foundation**

Implementation of the Techno Service AI Intelligence System under Constitution v2.3.
This repository contains the Phase 1 implementation: Identity, Access, and Audit Foundation.

---

## Constitutional Authority

This implementation is governed by:

- **Constitution v2.3** — supreme governing instrument. 32 articles + Schedule A.
- **Document 04** — Software Architecture Specification v1.0.
- **Document 05** — Database and Information Model Design v1.0.
- **Document 07** — User Interface & User Experience Specification v1.0.
- **Document 08** — Implementation Roadmap v1.0.

The governing documents are the only source of truth. No business rules, governance rules, approval rules, workflow stages, AI authorities, database meanings, or user permissions have been invented.

The tech stack (language, framework, database, libraries) is the implementer's choice under Article XXVIII of the Constitution and §6 of the Implementer README. All tech-stack decisions are recorded in `docs/DECISION_AND_ASSUMPTION_REGISTER.md`.

---

## Tech Stack (Phase 1)

- **Language:** Python 3.12
- **Web framework:** FastAPI + Uvicorn (ASGI)
- **Database:** SQLite (vendor-neutral per Document 04; swappable to PostgreSQL via SQLAlchemy URL)
- **ORM:** SQLAlchemy 2.0
- **Authentication:** JWT in HttpOnly cookies; bcrypt password hashing
- **Templates:** Jinja2 (server-rendered, mobile-first responsive)
- **Testing:** pytest + httpx

See `docs/DECISION_AND_ASSUMPTION_REGISTER.md` for rationale and the four Temporary Technical Assumptions recorded under §9 of the Implementer README.

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Initialize the database (creates schema + seeds default roles + admin user)
python -m techno_service_ai.bootstrap

# 3. Run the server
uvicorn techno_service_ai.app:app --reload

# 4. Run the test suite (proves AC-P1-001..004, AC-AUD-001..005, AC-SEC-001..005)
pytest -v
```

Default admin credentials (created by bootstrap, **change immediately in any non-test environment**):

- Username: `admin`
- Password: `ChangeMe!2026`
- Persona: `ADMIN`

---

## Project Layout

```
techno-service-ai/
├── README.md                            — this file
├── requirements.txt
├── .gitignore
├── docs/
│   ├── DECISION_AND_ASSUMPTION_REGISTER.md   — tech-stack and process assumptions
│   ├── IMPLEMENTATION_GAP_REGISTER.md        — open gaps with impact + resolution
│   ├── PHASE1_SUMMARY.md                     — what Phase 1 delivers and how
│   └── CONSTITUTIONAL_TRACEABILITY.md        — Phase 1 items → governing clauses
├── src/techno_service_ai/
│   ├── __init__.py
│   ├── config.py                        — settings (paths, JWT secret, retention)
│   ├── db.py                            — SQLAlchemy engine + session
│   ├── schema.py                        — DDL with audit-immutability triggers
│   ├── models.py                        — ORM: User, Role, Persona, Session, AccessPolicy, AuditLog
│   ├── audit.py                         — Audit Service: record, query, export
│   ├── auth.py                          — Identity + Session services
│   ├── access.py                        — Access Policy Service + SoD checks
│   ├── personas.py                      — Persona Service
│   ├── app.py                           — FastAPI routes (UI + JSON)
│   ├── bootstrap.py                     — create schema, seed default roles/admin
│   ├── security.py                      — password hash, JWT sign/verify
│   ├── deps.py                          — request dependencies (current user, persona, audit)
│   ├── templates/                       — Jinja2 templates, mobile-first
│   │   ├── base.html
│   │   ├── sign_in.html
│   │   ├── recover.html
│   │   ├── persona_select.html
│   │   ├── account_security.html
│   │   ├── admin/
│   │   │   ├── users.html
│   │   │   ├── user_edit.html
│   │   │   ├── roles.html
│   │   │   ├── role_edit.html
│   │   │   ├── access_policies.html
│   │   │   ├── access_policy_edit.html
│   │   │   └── audit_log.html
│   │   └── errors/permission_denied.html
│   └── static/
│       └── styles.css                   — design tokens, mobile-first, responsive
└── tests/
    ├── conftest.py                      — fresh in-memory DB per test
    ├── test_ac_p1_001_sign_in_out_recover.py
    ├── test_ac_p1_002_persona.py
    ├── test_ac_p1_003_admin_manage.py
    ├── test_ac_p1_004_audit.py
    ├── test_ac_aud_001_complete.py
    ├── test_ac_aud_002_immutable.py
    ├── test_ac_aud_003_exportable.py
    ├── test_ac_aud_004_queryable.py
    ├── test_ac_aud_005_retention.py
    ├── test_ac_sec_001_access_control.py
    ├── test_ac_sec_002_authentication.py
    ├── test_ac_sec_003_authorisation.py
    ├── test_ac_sec_004_data_protection.py
    ├── test_ac_sec_005_security_audit.py
    ├── test_article_xvii_sod.py
    └── test_article_xx_institutional_memory.py
```

---

## Phase 1 Scope

Per Document 08 (Implementation Roadmap) §2.2 and the Phase 1 Backlog:

| ID | Title |
|---|---|
| IMPL-P1-001 | Identity Service |
| IMPL-P1-002 | Authentication |
| IMPL-P1-003 | Session Management |
| IMPL-P1-004 | Persona Selection |
| IMPL-P1-005 | Account and Security Settings |
| IMPL-P1-006 | Access Policy Service |
| IMPL-P1-007 | Role Assignment |
| IMPL-P1-008 | Access Enforcement |
| IMPL-P1-009 | Separation of Duties (Article XVII) |
| IMPL-P1-010 | User entity |
| IMPL-P1-011 | Role entity |
| IMPL-P1-012 | Audit Service |
| IMPL-P1-013 | Audit Log entity (immutable) |
| IMPL-P1-014 | 4 Identity + 6 Administration + 1 Audit screen |

Completion Criteria (per `06_ACCEPTANCE_CRITERIA.md`):

- **AC-P1-001** — Sign in, sign out, recover
- **AC-P1-002** — Persona selection
- **AC-P1-003** — User, role, access-policy management
- **AC-P1-004** — Audit Log queryable, complete, immutable, exportable

Plus supporting criteria proven by the test suite:

- **AC-AUD-001..005** — complete / immutable / exportable / queryable / retention
- **AC-SEC-001..005** — access control / authentication / authorisation / data protection / audit

---

## Constitutional Compliance Notes

- **Article XX paragraph 6 — No Silent Amendment.** The audit log table has a SQLite trigger that rejects UPDATE and DELETE. Hash-chained entries make any tampering detectable.
- **Article XVII — Separation of Duties.** Role assignment and access-policy change operations record `actor_user_id` and `actor_role_code`; the SoD check rejects self-assignment of conflicting roles.
- **Article XXX paragraph 15 — Constitution Supremacy.** No business rule has been invented. Where a detail is not specified by the governing documents, a Gap has been recorded in `docs/IMPLEMENTATION_GAP_REGISTER.md` rather than guessed.

---

*Built under Constitution v2.3 — Final Adoption Candidate.*
