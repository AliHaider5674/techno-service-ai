# Decision and Assumption Register

**Project:** Techno Service AI Intelligence System
**Phase:** 6 — Tender, Project, Knowledge, and the 24-Stage Walk (current phase)
**Governing Authority:** Constitution v2.3
**Document Reference:** TS-AI-DAR-001
**Status:** Issued for the Phase 6 release

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

# Phase 5 Update — Manufacturer, Commercial, and Registration Offices

**Status:** Issued for the Phase 5 release.

## Summary

Phase 5 activates 9 of the 13 Principal Agents listed in
Document 02 §4.5-4.7 (3 Manufacturer + 3 Commercial + 3 Registration).
The remaining 4 agents (Commercial Model Designer, Negotiation
Support, After-Sales Intelligence, Approved Vendor List Manager)
are deferred to Phase 6+ per the Implementation Roadmap.

The Register Compliance Gate (Constitution Article VIII) is
introduced as a service-layer helper backed by a pure-logic
engine. The engine enforces the three constitutional rules
(Restricted / Conflict / Non-Represented) at every commercial
gate. The Register Compliance check is invoked at the entry of
S16 (BD), S18 (Market Entry), and at the `manufacturer_id` lookup
in S11 (Kuwait Representation derivation).

## New Temporary Technical Assumptions

**None.** Phase 5 introduces no new TTA. The 16 Phase 1-3 TTAs
(6 + 5 + 5) remain in force through Phase 8 or until permanent
decision.

## New Records (constitutional entities)

- `MarketEntryOptionsReport` (ENT-REG-004, schema ENT-REG-005) —
  declared in Document 05 §3.9 but missing from the Phase 2
  schema. Added in Phase 5 as a constitutional table. The
  Phase 2 entity count is 91 (up from 90).

## Architectural decisions

1. **Pure-logic engine layer for Phase 5** (mirrors Phase 3/4):
   `manufacturer.py`, `commercial.py`, `registration.py`,
   `register_compliance.py`. No DB coupling. All error classes
   are typed exceptions whose messages are the constitutional text.

2. **Register Compliance is a separate engine**, not a method on
   the WorkflowService. The Service Layer wraps the engine and
   exposes `check_register_compliance(entity_id, entity_name, gate)`
   for the service-layer callers.

3. **BD engagement requires BOTH (a) Human Approval reference AND
   (b) register clearance** (Constitution Article VIII + Article
   XII). Missing either is REJECTED at the service-layer with a
   typed exception.

4. **Kuwait Representation status is derived from the Represented
   Principals register** — the Manufacturer Profiler Agent does
   NOT declare representation status alone (Document 02 §4.5.1
   Authority Limits). The status is one of: REPRESENTED,
   UNRESOLVED, SUPERSEDED.

5. **S13, S14, S15 placeholders in the walker** — the underlying
   engines exist (Phase 3 verification, approval). The walker
   invokes thin wrappers that record stage completion. The full
   service-layer wiring is deferred (GAP-PHASE5-001).

## What did NOT change

No new Office, Agent (beyond the 9 activated), Decision Class,
workflow stage, gate, status, screen, or architectural layer has
been introduced. The Constitution has not been modified.

---

# Phase 6 Update — Tender, Project, Knowledge, and the 24-Stage Walk

**Status:** Issued for the Phase 6 release.

## Summary

Phase 6 activates 11 Principal Agents across 4 Offices (4
Tender/Project + 3 Knowledge + 4 deferred Commercial/Registration
agents). All 4 deferred agents from GAP-PHASE5-003 have
Charters in Document 02 and are activated in Phase 6.

The 24-stage Discovery Order walk (S01..S24) is now complete on
real data — the constitutional lifecycle is closed.

## New Temporary Technical Assumptions

**None.** Phase 6 introduces no new TTA. The 16 Phase 1-3 TTAs
remain in force through Phase 8 or until permanent decision.

## GAP-PHASE5-001 — DecisionLogEntry reconciliation (CLOSED)

The schema's `DecisionLogEntry` table was extended with 7 nullable
fields (`decision_summary`, `decided_by_role`,
`material_canonical_id`, `opportunity_canonical_id`, `rationale`,
`conditions`, `related_approval_id`) to accept the LogService's
field names. The `decision_class` column type was changed from
`Integer` to `String(16)` to accept the `CLASS_1`..`CLASS_4` values
the LogService writes. The change is additive (no data lost; the
append-only triggers prevent any UPDATE on existing rows).

The LogService.write_decision_log was updated to map the
LogService field names to the schema's canonical names. The
legacy `decision` field is built from `decision_summary` for
backward compatibility with Phase 2/3 writers.

## GAP-PHASE5-003 — 4 Deferred agents (CLOSED)

All 4 deferred agents from Phase 5 are activated in Phase 6:

  - Commercial Model Designer (§4.6.2)
  - Negotiation Support (§4.6.4)
  - After-Sales Intelligence (§4.6.6)
  - Approved Vendor List Manager (§4.7.4)

The 3-of-N partial activation recorded in HD-PHASE5-001 is now
closed; the full Charter coverage for the Commercial Development
and Registration/Market Entry offices is achieved.

## New Records (no new entities)

Phase 6 introduces no new constitutional entities. The existing
Phase 2 entities are sufficient:

  - Tender (ENT-TEN-001)
  - TenderQualificationReport (ENT-TEN-002)
  - QuotationDossier (ENT-TEN-003)
  - ProjectStatusReport (ENT-TEN-004)
  - AfterSalesIntelligenceReport (ENT-COM-006)
  - CommercialModelOption (ENT-COM-002)
  - NegotiationAnalysis (ENT-COM-004)
  - ApprovedVendorListStatusReport (ENT-REG-003)
  - KnowledgeRecord (ENT-KNO-001)
  - LessonLearned (ENT-KNO-002)
  - InstitutionalMemoryIndex (ENT-KNO-003)
  - KnowledgeBaseInventory (ENT-KNO-004)
  - CommercialOutcomeReport (ENT-PER-002)
  - PerformanceRecord (ENT-PER-001)
  - LearningUpdate (ENT-PER-003)

The Phase 2 canonical count remains 91 (corrected from the
original 90 in Phase 5 sign-off).

## Architectural decisions

1. **Pure-logic engine layer for Phase 6** (mirrors Phase 3/4/5):
   `tender_project.py`, `knowledge.py`, and extensions to
   `commercial.py` / `registration.py`. No DB coupling. All error
   classes are typed exceptions whose messages are the
   constitutional text.

2. **GAP-PHASE5-001 reconciliation is additive and
   backward-compatible.** Existing data is preserved; the
   triggers prevent in-place updates so the schema can be
   extended without violating Article XX.

3. **S24 (Continuous Learning) engine is deferred to Phase 7.**
   The walker records the stage as a `LearningUpdate` record;
   the engine that consumes these updates (the Performance and
   Learning Office agents per Document 02 §4.17) is out of
   Phase 6 scope per the Implementation Roadmap.

## What did NOT change

No new Office, Agent (beyond the 11 activated), Decision Class,
workflow stage, gate, status, screen, or architectural layer has
been introduced. The Constitution has not been modified.

---

*End of Decision and Assumption Register — Phase 6.*


