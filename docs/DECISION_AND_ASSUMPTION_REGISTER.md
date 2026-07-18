# Decision and Assumption Register — Phase 1

**Project:** Techno Service AI Intelligence System
**Phase:** 1 — Identity, Access, and Audit Foundation
**Governing Authority:** Constitution v2.3
**Document Reference:** TS-AI-DAR-001
**Status:** Issued for the Phase 1 release

This register is the single source of truth for every decision and temporary
technical assumption taken during Phase 1. It is required by the Implementer
README §9. **An assumption is not an approved requirement.** An assumption
that becomes permanent without approval is a constitutional violation.

---

## 1. Approved Decisions (Permanent)

(none in Phase 1 — every Phase 1 choice is a temporary technical assumption)

---

## 2. Temporary Technical Assumptions

Per the Implementer README §6, the implementing party may decide the
**language, framework, libraries, cloud, database engine, AI model,
development methodology, internal code structure, naming, and style** within
the boundaries of the approved documents. These selections are recorded
here as temporary technical assumptions. None of them modify governance,
business meaning, or any provision of the approved documents.

### ASS-PHASE1-001 — Programming language: Python 3.12

- **Description:** Implementation is in Python 3.12.
- **Governing source:** Implementer README §6.
- **Owner:** Implementation Engineer.
- **Expiry / review:** Re-evaluate at end of Phase 3.
- **Constitutional impact:** None.
- **Rationale:** Python has a small surface area for the Identity / Access / Audit scope, mature web and crypto libraries, and the FastAPI dependency injection model maps directly to the constitutional separation of concerns (auth dependency, principal dependency, role-check dependency).

### ASS-PHASE1-002 — Web framework: FastAPI + Uvicorn (ASGI)

- **Description:** HTTP layer uses FastAPI with Uvicorn.
- **Governing source:** Implementer README §6.
- **Owner:** Implementation Engineer.
- **Expiry / review:** Re-evaluate at end of Phase 3.
- **Constitutional impact:** None.
- **Rationale:** FastAPI's dependency-injection model naturally separates the constitutional concerns: `current_principal` enforces authentication, `require_any_role` enforces authorisation, route handlers contain the request/response logic. The OpenAPI schema is auto-generated, which supports Document 04's interface-disciplined design.

### ASS-PHASE1-003 — Database engine: SQLite (development) / SQLAlchemy 2.x (portable)

- **Description:** Development uses SQLite via SQLAlchemy 2.0. SQLAlchemy's URL abstraction means a swap to PostgreSQL or another engine is a config change.
- **Governing source:** Implementer README §6 ("database engine").
- **Owner:** Implementation Engineer.
- **Expiry / review:** Re-evaluate at end of Phase 7 (Performance & Reporting) when load tests begin.
- **Constitutional impact:** None.
- **Rationale:** SQLite supports the SQL DDL we need (including the BEFORE UPDATE/DELETE triggers that enforce Article XX's immutability), needs no external service, and ships with Python tooling. Production hardening (Phase 8) will consider PostgreSQL for concurrency and replication.

### ASS-PHASE1-004 — Frontend: server-rendered Jinja2 templates with mobile-first responsive CSS

- **Description:** No client-side SPA framework in Phase 1. Templates are Jinja2; CSS is a single mobile-first stylesheet with breakpoints at 600/900/1400 px.
- **Governing source:** Document 07 (UI/UX) and Implementer README §6.
- **Owner:** Implementation Engineer.
- **Expiry / review:** Re-evaluate at end of Phase 4 (when the Discovery Order Operational Surfaces require richer client interactions).
- **Constitutional impact:** None.
- **Rationale:** Phase 1 is form-driven (sign in, persona select, account & security, user/role/policy management, audit log). Server-rendered templates with progressive enhancement satisfy the Mobile First principle of Document 07 without the build-chain complexity of a SPA. A future phase can introduce a richer client framework without changing the server contract.

### ASS-PHASE1-005 — Authentication: JWT in HttpOnly cookies; bcrypt for password hashes

- **Description:** Users sign in by POSTing username + password. The server returns an HttpOnly, SameSite=Lax cookie carrying a signed JWT. Passwords are bcrypt-hashed; recovery answers are normalised and bcrypt-hashed.
- **Governing source:** Constitution Article XXV (Security) and Implementer README §6.
- **Owner:** Implementation Engineer.
- **Expiry / review:** Re-evaluate at end of Phase 7 (when the second-factor story is fully specified per Document 07).
- **Constitutional impact:** None.
- **Rationale:** JWT in HttpOnly cookies is the industry standard for session handling. The cookie is `Secure=False` in development; production deployments must set `TSAI_COOKIE_SECURE=1` per the operational hardening checklist in Phase 8.

### ASS-PHASE1-006 — Default admin password for development

- **Description:** The bootstrap module creates a default `admin` user with password `ChangeMe!2026`.
- **Governing source:** Implementer README §6 (development tooling); Document 08 §2.1.
- **Owner:** Implementation Engineer.
- **Expiry / review:** Removed in Phase 8 (Production Hardening) — production deployments MUST set `TSAI_DEFAULT_ADMIN_PASSWORD` to a unique value or delete the default admin after onboarding the real administrator.
- **Constitutional impact:** None — this is a local convenience for the implementer, not a constitutional rule.
- **Rationale:** Without a default account, the implementer cannot sign in to the freshly bootstrapped system. The README and `bootstrap.py` print a warning that the password MUST be changed in any non-test environment.

---

## 3. Rejected Assumptions

(none)

---

## 4. Human Decisions Required

Per the Implementer README §8 and the Authority Matrix, the following items
require explicit Human Approval (Class 3 or Class 4) before Phase 2 begins:

| ID | Item | Trigger | Required Approver Role |
|---|---|---|---|
| HD-PHASE1-001 | Acceptance of Phase 1 completion | Phase 1 sign-off | Implementation Lead + Constitutional Compliance |
| HD-PHASE1-002 | Approval of tech-stack assumptions above for use in later phases | Phase 1 → Phase 2 transition | Authorised Executive (Class 3) |
| HD-PHASE1-003 | Decision on production-grade cookie `Secure` flag and JWT secret storage | Phase 8 (Production Hardening) | Authorised Executive (Class 3) |

No new Office, Agent, Decision Class, workflow stage, gate, status, screen, or
architectural layer has been introduced. The Constitution has not been modified.

---

*End of Decision and Assumption Register — Phase 1.*
