# Phase 1 Summary — Identity, Access, and Audit Foundation

**Phase:** 1 of 9
**Reference:** Document 08 §2.2; Phase 1 Backlog IMPL-P1-001..014
**Status:** Implementation complete, test suite passing, ready for sign-off review
**Constitutional Authority:** Constitution v2.3

---

## What was delivered

The Phase 1 implementation covers all 14 backlog items and the four
Phase 1 acceptance criteria (AC-P1-001..004), plus the supporting
audit (AC-AUD-001..005) and security (AC-SEC-001..005) criteria.

### Backlog coverage

| ID | Title | Status |
|---|---|---|
| IMPL-P1-001 | Identity Service | ✅ `techno_service_ai.auth` |
| IMPL-P1-002 | Authentication (sign in / out / recovery) | ✅ `techno_service_ai.auth.sign_in / sign_out / recover` |
| IMPL-P1-003 | Session Management | ✅ `techno_service_ai.schema.UserSession` + `auth.validate_session` |
| IMPL-P1-004 | Persona Selection | ✅ `techno_service_ai.personas` + `/persona/select` |
| IMPL-P1-005 | Account & Security Settings | ✅ `/account/security` |
| IMPL-P1-006 | Access Policy Service | ✅ `techno_service_ai.access` |
| IMPL-P1-007 | Role Assignment | ✅ `access.assign_role` / `revoke_role` |
| IMPL-P1-008 | Access Enforcement | ✅ `deps.require_any_role` + `current_principal` |
| IMPL-P1-009 | Separation of Duties (Article XVII) | ✅ `access.SoDViolation` + 3 SoD rules + 3 tests |
| IMPL-P1-010 | User entity | ✅ `schema.User` |
| IMPL-P1-011 | Role entity | ✅ `schema.Role` + `UserRole` + `Persona` |
| IMPL-P1-012 | Audit Service | ✅ `techno_service_ai.audit` |
| IMPL-P1-013 | Audit Log entity (immutable) | ✅ `schema.AuditLog` + SQL triggers + hash chain |
| IMPL-P1-014 | 4 Identity + 6 Administration + 1 Audit screen | ✅ `templates/`, mobile-first responsive |

### Acceptance criteria coverage

| Criterion | Status | Test file |
|---|---|---|
| AC-P1-001 Sign in / out / recover | ✅ | `tests/test_ac_p1_001_sign_in_out_recover.py` |
| AC-P1-002 Persona selection | ✅ | `tests/test_ac_p1_002_persona.py` |
| AC-P1-003 Admin can manage users, roles, access policy | ✅ | `tests/test_ac_p1_003_admin_manage.py` |
| AC-P1-004 Audit log queryable, complete, immutable, exportable | ✅ | `tests/test_ac_p1_004_audit.py` |
| AC-AUD-001 Complete | ✅ | `tests/test_ac_aud_001_to_005.py` |
| AC-AUD-002 Immutable | ✅ (DB triggers) | `tests/test_ac_aud_001_to_005.py` |
| AC-AUD-003 Exportable | ✅ (CSV + JSON) | `tests/test_ac_aud_001_to_005.py` |
| AC-AUD-004 Queryable | ✅ (filter by event / actor / target) | `tests/test_ac_aud_001_to_005.py` |
| AC-AUD-005 Retention | ✅ (`retention_class` column) | `tests/test_ac_aud_001_to_005.py` |
| AC-SEC-001 Access control enforced | ✅ | `tests/test_ac_sec_001_to_005.py` |
| AC-SEC-002 Authentication enforced | ✅ | `tests/test_ac_sec_001_to_005.py` |
| AC-SEC-003 Authorisation enforced | ✅ | `tests/test_ac_sec_001_to_005.py` |
| AC-SEC-004 Data protection (bcrypt) | ✅ | `tests/test_ac_sec_001_to_005.py` |
| AC-SEC-005 Security events audited | ✅ | `tests/test_ac_sec_001_to_005.py` |
| Article XVII SoD | ✅ | `tests/test_article_xvii_and_xx.py` |
| Article XX No Silent Amendment | ✅ | `tests/test_article_xvii_and_xx.py` |

### Screens delivered (11 total)

**Identity & Access (4):**
1. `GET /sign-in` — sign-in form
2. `GET /recover` — recovery challenge
3. `GET /persona/select` — persona selection (multi-role users)
4. `GET /account/security` — password change

**Administration (6):**
5. `GET /admin/users` — user list
6. `GET /admin/users/new` — create user
7. `GET /admin/users/{id}` — manage user (edit + assign/revoke role)
8. `GET /admin/roles` — role list and create
9. `GET /admin/access-policies` — access policy list and create
10. `GET /admin/access-policies/{id}` — edit access policy

**Audit (1):**
11. `GET /admin/audit-log` — query, filter, chain-status, CSV/JSON export

All 11 screens are mobile-first responsive (CSS breakpoints at 600/900/1400 px).

---

## How to run

```bash
# Install deps
pip install -r requirements.txt

# Initialize DB and seed default roles / admin
python -m techno_service_ai.bootstrap

# Run the server
uvicorn techno_service_ai.app:app --reload
# Then open http://127.0.0.1:8000/sign-in
# Default admin: admin / ChangeMe!2026

# Run the test suite
pytest -v
```

---

## What was NOT delivered (and why)

The following are explicitly **out of scope** for Phase 1 by the
governing documents and the Implementation Roadmap:

- The 24 workflow stages (Phase 3)
- The 9 Decision Gates (Phase 3)
- The Discovery Order Operational Surfaces — Industrial / Opportunity / Technology / Manufacturer / Commercial (Phases 4–5)
- The three Constitutional Registers (Represented Principals, Conflict/Do-Not-Pursue, Restricted/Prohibited) as data; they are mentioned in the Constitution but the Information Domain activation is Phase 2 / Phase 5.
- AI Office and Agent activations (Phases 3 onward per AI Implementation Plan)
- The second-factor mechanism (Phase 2 / Phase 7 — see `GAP-PHASE1-001`)
- Performance and scalability benchmarks (Phase 7–8 — see `GAP-PHASE1-005`)

No governing document has been modified. No new Office, Agent, Decision
Class, workflow stage, gate, status, screen, dashboard, or architectural
layer has been introduced.

---

## Constitutional notes

- **Article XX paragraph 6 — No Silent Amendment.** The `audit_log` table has two `BEFORE` triggers that `RAISE(ABORT)` on UPDATE and DELETE. The table is therefore physically append-only. Hash-chained entries (each `entry_hash = SHA-256(prev_hash || canonical_json)`) provide defense-in-depth: even if a direct DB write somehow succeeded, `audit.verify_chain()` would detect the break.
- **Article XVII — Separation of Duties.** Three SoD rules are enforced and tested: (1) a user may not hold roles from two different `sod_class` buckets; (2) a user may not perform an AccessPolicy mutation that grants authority to a role they themselves hold; (3) a user may not revoke their own role assignment.
- **Article XXV — Security.** Passwords and recovery answers are bcrypt-hashed. JWTs are signed with HS256 and carried in HttpOnly, SameSite=Lax cookies. Every security-relevant event is recorded in the audit log.
- **Article XXVIII — Document Hierarchy.** The Constitution has not been modified. No Lower Document has been modified (none exists yet for Phase 1). The tech stack is the implementer's choice per §6 of the Implementer README, recorded in `docs/DECISION_AND_ASSUMPTION_REGISTER.md`.

---

## Open items for Phase 2 readiness

These are recorded for the Phase 1 → Phase 2 transition:

1. **HD-PHASE1-001** — Acceptance of Phase 1 completion (Implementation Lead + Constitutional Compliance).
2. **HD-PHASE1-002** — Approval of the tech-stack assumptions (ASS-PHASE1-001..006) for use in Phase 2 and beyond (Authorised Executive, Class 3).
3. **HD-PHASE1-003** — Decision on production cookie `Secure` flag and JWT secret storage (Authorised Executive, Class 3) — required for Phase 8 only.
4. **GAP-PHASE1-001..005** — Five open gaps; the most material is the 2FA mechanism (Phase 2 candidate) and the SoD matrix expansion (Phase 3 candidate).

---

*End of Phase 1 Summary.*
