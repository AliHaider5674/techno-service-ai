# Decision and Assumption Register

**Project:** Techno Service AI Intelligence System
**Phase:** 2 — Data Foundation (current phase)
**Governing Authority:** Constitution v2.3
**Document Reference:** TS-AI-DAR-001
**Status:** Issued for the Phase 2 release

This register is the single source of truth for every decision and temporary
technical assumption taken during the implementation. It is required by the
Implementer README §9. **An assumption is not an approved requirement.** An
assumption that becomes permanent without approval is a constitutional
violation.

---

## 1. Approved Decisions (Permanent)

(none yet — every choice recorded here is a temporary technical assumption)

---

## 2. Temporary Technical Assumptions

Per the Implementer README §6, the implementing party may decide the
**language, framework, libraries, cloud, database engine, AI model,
development methodology, internal code structure, naming, and style** within
the boundaries of the approved documents. These selections are recorded
here as temporary technical assumptions. None of them modify governance,
business meaning, or any provision of the approved documents.

### Phase 1 assumptions (carried forward, in force through Phase 8)

The following six assumptions were recorded in the Phase 1 release of
this register and are explicitly carried forward into Phase 2+ per the
HD-PHASE1-002 approval. They are reproduced here in summary form; the
Phase 1 register contains the full rationale for each.

| ID | Title | Status |
|---|---|---|
| ASS-PHASE1-001 | Programming language: Python 3.12 | In force |
| ASS-PHASE1-002 | Web framework: FastAPI + Uvicorn (ASGI) | In force |
| ASS-PHASE1-003 | Database engine: SQLite (dev) / SQLAlchemy 2.x (portable) | In force |
| ASS-PHASE1-004 | Frontend: server-rendered Jinja2 + mobile-first CSS | In force |
| ASS-PHASE1-005 | Auth: JWT in HttpOnly cookies; bcrypt for passwords | In force |
| ASS-PHASE1-006 | Default admin password for development | In force |

### Phase 2 assumptions (new)

#### ASS-PHASE2-001 — Constitutional triggers implemented in SQLite

- **Description:** Phase 2 enforces the **no-silent-amendment** rule
  (Constitution Article XX paragraph 6, Document 05 DB-PRIN-018) at the
  DB layer using SQLite `BEFORE UPDATE` / `BEFORE DELETE` triggers
  that `RAISE(ABORT)`. The triggers are installed by
  `db.install_constitutional_triggers()` on every constitutional table
  (94 in Phase 2). The 9 operational tables (audit_log, migration,
  user, role, user_role, persona, user_session, access_policy,
  access_policy_role) are exempt and retain UPSERT semantics.
- **Governing source:** Constitution Article XX; Document 05 DB-PRIN-018.
- **Owner:** Implementation Engineer.
- **Expiry / review:** Re-evaluate when the production engine is
  selected (Phase 8). The trigger pattern is portable to PostgreSQL
  (CREATE TRIGGER ... BEFORE UPDATE ... RAISE EXCEPTION) but the
  exact DDL will change.
- **Constitutional impact:** None — the rule is constitutional; the
  trigger is the implementer's mechanism for enforcing it.
- **Rationale:** Document 05 explicitly requires that "all
  audit/security/SoD rules must be enforced at the data layer, not
  just in code". The trigger pattern is the only mechanism that
  survives an ORM bypass, a raw SQL write, or a direct DB connection
  by an admin tool.

#### ASS-PHASE2-002 — Three Status dimensions as independent writeable columns

- **Description:** `Opportunity` and `ComparativeAnalysis` carry three
  Status columns (`intelligence_status`, `approval_status`,
  `commercial_status`) as **independent writeable columns**, each
  with its own default, its own state machine, and its own `_at`
  timestamp. No view, no derived column, no trigger that couples one
  to another. Changing one does not mutate the other two.
- **Governing source:** Constitution Article XIX; Document 05 DB-PRIN-014.
- **Owner:** Implementation Engineer.
- **Expiry / review:** Permanent — the rule is constitutional.
- **Constitutional impact:** None — encodes the rule.
- **Rationale:** Per the Phase 2 review (HD-PHASE1-002 condition #1):
  "verify these remain independent in SQLite (no COLLATE tricks, no
  view-based collapsing, no triggers that update one when another
  changes)". Verified by `test_ac_p2_003_status_dimensions_are_independent_columns`
  and `test_ac_dl_002_status_columns_are_not_views_or_computed`.

#### ASS-PHASE2-003 — Three Constitutional Registers as independent tables

- **Description:** The three Registers (Represented Principals,
  Conflict/Do-Not-Pursue, Restricted/Prohibited) are three independent
  base tables, each with its own write path, its own status column, its
  own NOT-NULL distinguishing field (`brand`, `conflict_type`,
  `restriction_type`). No view, no derived table, no trigger that
  mirrors from one to another.
- **Governing source:** Constitution Article VIII; Document 05.
- **Owner:** Implementation Engineer.
- **Expiry / review:** Permanent — the rule is constitutional.
- **Constitutional impact:** None — encodes the rule.
- **Rationale:** Per the Phase 2 review (HD-PHASE1-002 condition #1):
  "no view, no derived table, no trigger that mirrors". Verified by
  `test_ac_p2_004_three_registers_are_independent_tables` and
  `test_ac_dl_003_registers_are_independent_structures`.

#### ASS-PHASE2-004 — Forward-only, versioned, reproducible, auditable migration framework

- **Description:** The schema migration framework is implemented in
  `techno_service_ai.migrations`. Properties:
    - **Forward-only on data** — rollback is allowed only on the
      last-applied migration (the tail). Earlier applied migrations
      are not reversible.
    - **Versioned** — every migration has a unique version
      (`M0001`, `M0002`, ...); applied in registration order.
    - **Reproducible** — applying on a fresh DB reaches the same
      schema as applying on a copy of production; `apply_all()` is
      idempotent.
    - **Auditable** — every applied migration writes a
      `MIGRATION.APPLIED` audit event with checksum, duration, and
      environment.
- **Governing source:** Document 05 §3; Phase 2 review HD-PHASE1-002 condition #2.
- **Owner:** Implementation Engineer.
- **Expiry / review:** Permanent — the framework is a constitutional
  property of the data layer.
- **Constitutional impact:** None.
- **Rationale:** Per the Phase 2 review (HD-PHASE1-002 condition #2):
  "implement this in Phase 2, do not defer to Phase 8". The framework
  is small, portable, and tested in `tests/test_phase2.py`.

#### ASS-PHASE2-005 — Migration table part of Base.metadata

- **Description:** The `migration` table is declared as the
  SQLAlchemy `Migration` ORM model in `schema.py` (one of the 9
  operational tables). The `M0001` migration's upgrade is a no-op
  (the table is created by `Base.metadata.create_all`); the
  `Migration` row is what proves the framework is in effect.
- **Governing source:** Phase 2 build-time decision.
- **Owner:** Implementation Engineer.
- **Expiry / review:** Permanent — structural property of the test
  reset cycle and the production migration cycle.
- **Constitutional impact:** None.
- **Rationale:** Without this, `Base.metadata.drop_all` (used by the
  test reset fixture `reset_schema`) would not drop the migration
  table, leaving stale APPLIED records between test runs and breaking
  the apply → rollback → re-apply contract. Documented in
  `docs/PHASE2_SUMMARY.md` §5 (operational note).

### Phase 3 assumptions (new)

#### ASS-PHASE3-001 — Engine layer is pure logic (no DB coupling)

- **Description:** The 11 Phase 3 engine modules (`states`,
  `gates`, `stages`, `verification`, `approval`, `notification`,
  `escalation`, `handoff`, `exceptions`, `recovery`,
  `orchestration`) are pure-logic modules with NO database coupling.
  They are testable in isolation, fast, and the constitutional
  invariants are enforced at the engine boundary.
- **Governing source:** Document 04 §1.2 (Layered Architecture);
  Document 06 (Workflow and AI Orchestration Design).
- **Owner:** Implementation Engineer.
- **Expiry / review:** Permanent.
- **Constitutional impact:** None.
- **Rationale:** Pure logic:
  - Is testable in 0.1s (the 53 Phase 3 engine tests run in 0.1s).
  - Documents the constitutional invariant in the code itself
    (the `TransitionError`, `GateBypassError`, `IndependenceViolation`,
    `SilenceNotApproval`, `SoDViolation`, `RollbackRequiresApproval`
    error classes are the constitutional text).
  - Is reusable: the same engines drive the application layer
    (Phase 4), the AI Orchestration Service, the Reporting
    Service (Phase 7), and the production deployment (Phase 8).

#### ASS-PHASE3-002 — Producer ≠ Verifier at the strictest test (identity)

- **Description:** The `IndependenceTracker` enforces independence
  by checking `producer_id != verifier_id` (identity equality). The
  broader test "the verifier may not be in the same role class as
  the producer" is an APPLICATION-LEVEL policy that the service
  layer in Phase 4 will add. The strict test matches the
  constitutional text VER-IND-001..003 exactly.
- **Governing source:** Document 06 §6.7 (VER-IND-001..003);
  Constitution Article XVII paragraph 2(1).
- **Owner:** Implementation Engineer.
- **Expiry / review:** Re-evaluate at Phase 7 (data-layer hardening)
  if a stricter role-class test is needed.
- **Constitutional impact:** None.
- **Rationale:** The constitutional text says "shall remain
  separately identifiable on every material record" — i.e. the
  identity must be distinct. The role-class test (e.g. an ANALYST
  may not verify an ANALYST's claim even with a different id) is a
  STRICTER rule that the Constitution permits but does not require.
  The engine implements the constitutional floor; the service
  layer can add the stricter rule without violating the
  constitution.

#### ASS-PHASE3-003 — 5 Verifier Agents modelled as one per role

- **Description:** The 5 Verifier Agents of Document 06 §6 are
  modelled as one `VerifierAgent` per role. The Independence
  Tracker treats each agent's identity as the verifier_id, and
  enforces producer != verifier at identity level. The roster
  factory `five_agent_roster()` returns one agent per role with
  default unique ids.
- **Governing source:** Document 06 §6.1..6.5.
- **Owner:** Implementation Engineer.
- **Expiry / review:** Permanent.
- **Constitutional impact:** None.
- **Rationale:** The constitutional text distinguishes the 5
  agents by ROLE; the engine mirrors that distinction. The
  application service layer in Phase 4 may add per-agent metadata
  (e.g. training, audit history) without changing the engine.

#### ASS-PHASE3-004 — Required Approver Role resolution uses the Authority Matrix §3.4 table

- **Description:** For Class 4 decisions, the Required Approver
  Role is resolved from the per-decision-type table in Authority
  Matrix Section 3.4 (e.g. "BINDING_BID" → "AUTHORISED_EXECUTIVE",
  "SIGN_CONTRACT" → "CONSTITUTIONAL_OWNER"). The mapping is
  encoded in the `CLASS_4_APPROVER` dict in `approval.py`.
- **Governing source:** Authority Matrix §3.4 (15 named decision
  types).
- **Owner:** Implementation Engineer.
- **Expiry / review:** Re-evaluate when the Authority Matrix is
  amended.
- **Constitutional impact:** None.
- **Rationale:** Encodes the Authority Matrix table directly in
  the engine, so the engine cannot approve a Class 4 binding
  offer with a Constitutional Owner (the matrix says it must be
  the Authorised Executive). The service layer in Phase 4 can
  add additional decision types without changing the engine.

#### ASS-PHASE3-005 — SMS is Class 3 / Class 4 only; Voice is Emergency only

- **Description:** Per UI/UX §10 (NOT-001..005), SMS is reserved
  for Class 3 and Class 4 notifications; Voice is reserved for
  Emergency. The Notification Engine rejects any attempt to issue
  a notification with the wrong channel/priority combination.
- **Governing source:** UI/UX §10; Document 06 §9.
- **Owner:** Implementation Engineer.
- **Expiry / review:** Permanent.
- **Constitutional impact:** None.
- **Rationale:** Encodes the channel-eligibility rule in the
  engine so the service layer cannot accidentally send a Class 1
  reminder by SMS or a Class 3 escalation by voice.

---

## 3. Rejected Assumptions

(none)

---

## 4. Human Decisions Required

Per the Implementer README §8 and the Authority Matrix, the following items
require explicit Human Approval (Class 3 or Class 4):

| ID | Item | Phase | Required Approver Role |
|---|---|---|---|
| HD-PHASE1-001 | Acceptance of Phase 1 completion | 1 → 2 | Implementation Lead + Constitutional Compliance |
| HD-PHASE1-002 | Approval of tech-stack assumptions for later phases | 1 → 2 | Authorised Executive (Class 3) |
| HD-PHASE1-003 | Production cookie `Secure` flag and JWT secret storage | 8 | Authorised Executive (Class 3) |
| HD-PHASE2-001 | Acceptance of Phase 2 completion | 2 → 3 | Implementation Lead + Constitutional Compliance |
| HD-PHASE2-002 | Acknowledgement that the 6 Phase 1 tech-stack assumptions remain in force through Phase 8 (or earlier permanent decision) | 2 → 3 | Authorised Executive (Class 3) |

No new Office, Agent, Decision Class, workflow stage, gate, status, screen, or
architectural layer has been introduced. The Constitution has not been modified.

---

*End of Decision and Assumption Register — Phase 2.*

