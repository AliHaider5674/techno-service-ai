# Decision and Assumption Register

**Project:** Techno Service AI Intelligence System
**Phase:** 8 — Production Hardening and Launch (current phase)
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

# Phase 7 Update — Every Office Alive

**Status:** Issued for the Phase 7 release.

## Summary

Phase 7 activates 31 Principal Agents across 7 Offices
(Performance and Learning, Reporting and Decision Support,
Notification and Monitoring, Risk and Compliance, Security and
Data Governance, Relationship Management, Executive AI). After
Phase 7, every Office listed in Document 02 §4.1, §4.11, §4.12,
§4.14, §4.15, §4.16, §4.17 is alive. The S24 (Continuous
Learning) engine is implemented (closes GAP-PHASE6-001). The
Performance and Learning Office is fully activated
(closes GAP-PHASE6-002).

## New Temporary Technical Assumptions

**None.** Phase 7 introduces no new TTA. The 16 Phase 1-3 TTAs
(6 + 5 + 5) remain in force through Phase 8 or until permanent
decision.

## GAP-PHASE6-001 — S24 Continuous Learning engine (CLOSED)

`ContinuousLearningEngine` implements the 4-step review path
(scope validation, reversibility check, Constitutional Impact
Review, Human Approval gate for `CONSTITUTIONAL_AMENDMENT`).
The 12 invariable constitutional clauses (Articles I-VIII, XII,
XVII, XX, XXVIII) are encoded as a constant and consulted on
every proposal. Five outcomes are produced (`APPROVED`,
`REJECTED_CONSTITUTIONAL_IMPACT`, `REJECTED_IRREVERSIBLE`,
`REJECTED_MISSING_APPROVAL`, `REJECTED_INVALID_SCOPE`).

## GAP-PHASE6-002 — Performance and Learning Office (CLOSED)

The 4 agents of Document 02 §4.17 are activated: Commercial
Outcomes Analyst, Performance Measurement, Learning
Coordination, Constitutional Learning. The `PerformanceEngine`
implements ON_TRACK / AT_RISK / OFF_TRACK bands (95% / 90% of
target), bottleneck detection, and SLA breach detection.

## New Records (no new entities)

Phase 7 introduces no new constitutional entities. The existing
Phase 2 schema is sufficient. The 26 entities the Phase 7
engine layer operates on are:

- Reporting: `Report`, `ReportTemplate`, `ReportExportRecord`,
  `BoardReport`
- Notification: `NotificationRecord`, `NotificationChannel`,
  `NotificationPreference`
- Risk and Compliance: `EnterpriseRisk`,
  `ComplianceReviewReport`, `ConstitutionalIncident`
- Security and Data Governance: `SecurityEvent`,
  `AccessControlEntry`, `DataClassificationEntry`,
  `ContinuityEvent`, `ContinuityPlan`, `RecoveryTestReport`,
  `RecoveryReport`
- Relationship Management: `CustomerProfile`,
  `CustomerRelationshipHistory`, `PartnerProfile`,
  `PartnerRelationshipHistory`,
  `ManufacturerRelationshipRecord`, `GovernmentEntityProfile`,
  `DisclosurePermission`

The Phase 2 canonical count remains 91 (unchanged).

## Architectural decisions

1. **Pure-logic engine layer for Phase 7** (mirrors Phase 3-6):
   `continuous_learning.py` (S24) and `phase7_engines.py`
   (Reporting, Notification, Risk, Compliance, Constitutional
   Incident, Performance). No DB coupling. All error classes are
   typed exceptions whose messages are the constitutional text.

2. **Notification suppression of Class 3/4 is FORBIDDEN at the
   engine level** — the engine raises `SuppressionForbiddenError`
   on any attempt to suppress a Class 3 or Class 4 notification.
   The service layer cannot bypass this.

3. **Constitutional Incident requires `reporter_id`** — the
   engine raises a typed error on any attempt to record an
   incident without a reporter. Per Constitution Article XX
   paragraph 7, every constitutional event must be attributable.

4. **`ChiefOrchestrationAgent` placed in §4.16** — deviation
   from canonical Document 02 §4.1.1 placement. The agent is a
   single instance; its function is identical. No constitutional
   rule is affected.

5. **Combined engines file** — `phase7_engines.py` holds the 6
   engine classes for the remaining 6 Offices; `continuous_learning.py`
   holds the S24 engine alone. The split reflects the
   historical placement of S24 (deferred to Phase 7 per
   GAP-PHASE6-001) vs. the other engines (in scope for Phase 7
   from the start).

6. **Reporting Engine produces `ComplianceAttestation` on every
   Report** — the engine raises `ReportMissingClaimSourceError`
   on any material claim without a Verification reference, and
   `ReportMissingFreshnessError` on any Report without a
   `freshness_date`. Both are typed exceptions.

## What did NOT change

No new Office (beyond the 7 activated), Agent (beyond the 31),
Decision Class, workflow stage, gate, status, screen, or
architectural layer has been introduced. The Constitution has
not been modified.

---

*End of Decision and Assumption Register — Phase 7.*

---

# Phase 8 Update — Production Hardening and Launch

**Status:** Issued for the Phase 8 release. The Constitutional
Compliance Attestation is **signed** (Implementation Lead +
Constitutional Compliance). The Class 4 sign-off (HD-PHASE8-001,
Authorised Executive) is the production-launch gate and is
**PENDING** until the production environment is provisioned.

## Summary

Phase 8 activates the last Office (Quality Assurance §4.10),
implements the production-hardening deliverables, and produces
the 25 Readiness Criteria checklist. The system is **READY FOR
PRODUCTION MIGRATION** subject to the Class 4 sign-off and
the production-environment execution items.

After Phase 8, every Office listed in Document 02 is alive,
and every Charter-defined Principal Agent is activated.

## New Temporary Technical Assumptions

#### ASS-PHASE8-001 — Dev-environment performance ceiling as a working SLA

- **Description:** Per Document 05 Gap 20.2-3 (Specific KPI
  Thresholds — Pending Lower Document, Schedule A Item 15),
  the constitutional performance SLAs (latency, throughput,
  concurrency, scalability, mobile response, dashboard
  response) are not yet defined in a Lower Document. Phase 8
  establishes a **dev-environment working ceiling** of
  <500 ms p95 for dashboard renders as a Temporary Technical
  Assumption, measured by
  `tests/test_phase8.py:test_performance_dashboard_endpoint_under_sla`.
- **Governing source:** Constitution Article XIV (Performance);
  Document 05 Gap 20.2-3.
- **Owner:** Implementation Engineer.
- **Expiry / review:** When Schedule A Item 15 is adopted as a
  Lower Document, the production-environment SLAs replace this
  TTA. The dev-environment ceiling is recorded as a transitional
  value and is superseded by the production SLO.
- **Constitutional impact:** None — the assumption is
  technical, not constitutional.
- **Rationale:** The Performance, Commercial Outcome, and
  Lessons Learned Standard is a Pending Lower Document.
  Without it, no specific SLA can be asserted. The dev-environment
  ceiling is a working number to keep the Performance and
  Learning Office operational; the production SLO is the
  production-environment verification item (HD-PHASE8-006).

#### ASS-PHASE8-002 — Production database engine: PostgreSQL 15+ (TTA)

- **Description:** The dev-environment database engine is
  SQLite (ASS-PHASE1-003). For the production environment,
  PostgreSQL 15+ is selected as the constitutional-grade RDBMS.
  The selection is a Temporary Technical Assumption per
  Implementer README §6. HD-PHASE8-002 records the
  production-engine selection for Human Approval.
- **Governing source:** Document 05 §3 (Information Domain
  model); Document 04 §1.4 (Database Layer).
- **Owner:** Implementation Engineer.
- **Expiry / review:** Re-evaluate when the production
  deployment plan is finalised.
- **Constitutional impact:** None — the engine is an
  implementation choice; the constitutional rules (no-silent-
  amendment triggers; canonical entity pattern) are portable
  to PostgreSQL with the standard DDL translation.
- **Rationale:** PostgreSQL provides native `CREATE TRIGGER`
  semantics equivalent to the SQLite `RAISE(ABORT)` pattern;
  TDE / column-level encryption (HD-PHASE8-004); row-level
  security; JSONB; mature migration tooling. The constitutional
  triggers are translated from SQLite
  `BEFORE UPDATE/DELETE RAISE(ABORT)` to PostgreSQL
  `BEFORE UPDATE/DELETE RAISE EXCEPTION`. The migration
  framework (`migrations.apply_all`) is portable with one
  DDL translation step.
- **Status (2026-07-20):** **APPLIED.** HD-PHASE8-002 complete.
  PostgreSQL 15.18 installed. `tsai_prod` database + `tsai_app`
  user created. Constitutional migration applied: 98 entities +
  3 Registers + 3 Status dimensions + audit log + 206 triggers.
  **333/333 tests pass against PostgreSQL.** FastAPI smoke test
  verified. Performance p95 = 17.7ms (manual runs), 7.9ms
  (dashboard renders), 500ms ceiling holds with >96% margin.
  Full deployment guide: `docs/PRODUCTION_DEPLOYMENT.md`.

## Closed Gaps

- **GAP-PHASE1-001** — 2FA mechanism selection. **Closed in
  Phase 8** with TOTP (RFC 6238 / RFC 4226). See
  `src/techno_service_ai/twofa.py`.
- **GAP-PHASE1-002** — WCAG 2.1 AA test suite. **Closed in
  Phase 8** with the baseline audit at
  `src/techno_service_ai/wcag.py`. The full axe-core / pa11y
  integration is a production-environment follow-up.
- **GAP-PHASE1-003** — Default SoD class bucketing. **Closed
  in Phase 4** (Office-specific SoD activation) and verified
  end-to-end in Phase 8.
- **GAP-PHASE1-004** — Audit retention period. **Closed in
  Phase 8** with `retention_class = PERMANENT` (Constitution
  Article XX §6) as the constitutional default; specific
  retention periods are deferred to the Knowledge, Data,
  Records, and Institutional Memory Standard (Schedule A
  Item 11).
- **GAP-PHASE1-005** — Performance SLAs. **Closed in Phase 8
  (dev-environment)** with ASS-PHASE8-001; production SLAs
  remain deferred to Schedule A Item 15.

## New Records (constitutional entities)

- **OutputAuditReport (ENT-QA-003)** — declared in Document 02
  §4.10.2 but missing from the Phase 2 schema. Added in
  Phase 8 as a constitutional table with auto-installed
  triggers. Phase 2 entity count 91 → 92.

## TTA inventory (Phase 8 close)

| ID | Title | Status |
|---|---|---|
| ASS-PHASE1-001..006 | Phase 1 tech stack | In force (carried forward) |
| ASS-PHASE2-001..005 | Phase 2 data foundation | In force (carried forward) |
| ASS-PHASE3-001..005 | Phase 3 workflow / verification / approval | In force (carried forward) |
| ASS-PHASE8-001 | Dev-environment performance ceiling | **New — in force** |
| ASS-PHASE8-002 | Production database engine: PostgreSQL 15+ | **New — in force — APPLIED 2026-07-20** |
| **Total** | | **17 TTAs** |

## Architectural decisions

1. **Quality Assurance Office is the last Office activated**;
   all 17 Offices per Document 02 §4.1..4.17 are now alive.
   The Charter-defined Principal Agent count is **69** (the
   5 Verifier Agents of the Verification Office §4.9 are
   included in the full roster via a thin adapter).
2. **2FA (TOTP)** is selected as the default enterprise
   mechanism (constant-time, offline-capable, auditable).
   The selection is per Document 04 §1.7 (Security Layer) and
   Constitution Article XXV.
3. **WCAG 2.1 AA baseline** is implemented as a pure-Python
   audit (`src/techno_service_ai/wcag.py`) covering the
   constitutional-floor checks (lang / title / main / h1 /
   input labels / img alt). The full axe-core integration is
   a production-environment follow-up.
4. **Continuity and Recovery** is verified at the backup /
   restore layer by
   `tests/test_phase8.py:test_continuity_and_recovery_backup_and_restore`.
   The Rollback path is the Phase 2 migration framework
   (`REC-ROLL-001..003`).
5. **Production migration** is documented in
   `docs/PRODUCTION_LAUNCH_SUMMARY.md` and recorded as
   HD-PHASE8-001 (Class 4 sign-off gate).

## What did NOT change

No new Office (beyond the 1 activated in Phase 8), Agent
(beyond the 3), Decision Class, workflow stage, gate, status,
screen, or architectural layer has been introduced. The
Constitution has not been modified.

## Open items for production-environment execution

1. **HD-PHASE8-001** — Authorised Executive Class 4 sign-off
   on the Production Launch.
2. **HD-PHASE8-002** — Production database engine selection
   (PostgreSQL 15+) — recorded as ASS-PHASE8-002; awaits
   Authorised Executive confirmation.
3. **HD-PHASE8-003** — Production Audit Log initialisation
   with the production-migration event.
4. **HD-PHASE8-004** — Production encryption at rest
   (TDE / column-level).
5. **HD-PHASE8-005** — Production UAT with named personas.
6. **HD-PHASE8-006** — Production SLO verification
   (Schedule A Item 15; 30-day post-launch window).

---

*End of Decision and Assumption Register — Phase 8.*

---

# Phase 8 (Post-Sign-Off) — DAR-E-002: Proactive Product Discovery as Constitutional Extension

**Status:** ✅ **APPROVED (2026-07-19) — Class 4 adoption of Constitution v2.4.**
**Phase 9 implementation in progress under the v2.4 authority.**

## DAR-E-002 (Major — Constitutional Owner Direction)

- **Date:** 2026-07-19
- **Title:** Proactive Product Discovery as constitutional extension
- **Severity:** **Major — Constitution Amendment Required**
- **Originating Document:** Constitutional Owner direction (new goal)
- **Approval Status:** ✅ **APPROVED (2026-07-19)** — Class 4 adoption of Constitution v2.4

**Description.** The Constitutional Owner has directed that the
System shall additionally support **Proactive Product
Discovery** across all sectors, with explicit qualification
filters for:

1. **Kuwait climate suitability** (heat, wind, dust
   tolerance).
2. **Retrofit-friendliness** (no major system / machine /
   pipe change required to install).
3. **No agent in Kuwait** (exclusive representation
   opportunity available).
4. **Low operating cost** (no specialised training burden;
   no engineering team required to operate).
5. **Focus on medium / emerging companies** (not just
   established tier-1 manufacturers).

**End goal:** **exclusive agency acquisition in Kuwait** for
the industrial maintenance and oil & gas sectors.

**Class 4 Authorisation (recorded 2026-07-19):**

- **Approver:** Authorised Executive (Constitutional Owner).
- **Constitutional Concurrence:** Constitutional Compliance
  Coordination.
- **Amendment file:** `techno_service_constitution_v2.4_amendment.md`
  (336 lines, 27 KB).
- **Effective Date:** 2026-07-19.
- **Next Review Date:** 2026-10-19 (3 months).

**Constitutional Surface to be Added (v2.4) — APPROVED:**

- 1 new Office (Office 18, Product Discovery Proactive).
- 4 new Principal Agents (Global Product Monitor; New
  Product Detector; Emerging Company Scout; Patent Watch).
- 1 new Discovery Order stage (Stage 8.5, Proactive
  Discovery — runs BEFORE the existing 24 stages).
- 5 new qualification filters (No Agent in Kuwait;
  Operating Cost; Training Burden; Company Size;
  Kuwait Suitability for Climate).
- 1 new workflow (Exclusive Agency Acquisition Workflow,
  10 steps; Class 3 approval at step 6; Class 4 approval
  at step 8).
- 6 new canonical entities (ENT-PD-001..006).
- 7 new UI/UX screens (SCR-PD-001..007).
- 3 new external service integrations (Web Search; Patent
  Search; Trade Publications).
- 1 new Phase (Phase 9, Proactive Product Discovery).
- 3 new Permanent Rules (PR-PD-001..003).

**Constitutional Surface PRESERVED (v2.3 → v2.4) — UNCHANGED:**

- 17 Offices alive (Document 02 §4.1..4.17) — unchanged.
- 69 Principal Agents activated — unchanged.
- 24 stages of the Discovery Order — unchanged (Stage 8.5
  is ADDED, not substituted).
- 92 canonical entities — unchanged (6 new entities are
  ADDED to the schema; existing 92 are PRESERVED).
- 25/25 Readiness Criteria — unchanged.
- 259/259 tests green (v1.0 build) — unchanged.
- 17 TTAs in force — unchanged.
- Document Hierarchy and Change Control (Article XXIX) —
  unchanged.
- Constitution v2.3 — **UNCHANGED** (32 articles, all
  preserved).

**Phase 9 Authorization:** **PROCEED** (per Class 4
sign-off in this message).

**Closure of GAP-CONST-001:** Recorded in
`docs/IMPLEMENTATION_GAP_REGISTER.md` with reference to the
v2.4 adoption.

---

## Phase 9 Continuous Proactive Discovery Sprint (2026-07-19)

**Scope:** Real, continuous, team-like Proactive Discovery.
Within Constitution v2.4 Charter. PR-PD-001..003 in force.
Office 18, 4 agents, 5 filters, 3 Registers, 10-step workflow
all PRESERVED. No new Permanent Rules, Offices, or Agents.

### New Temporary Technical Assumptions

#### ASS-PHASE9-001 — In-process threading scheduler for Continuous Discovery

The Continuous Proactive Discovery scheduler uses Python's
standard library `threading` module (in-process, single-thread
loop) instead of APScheduler. Rationale:

- APScheduler is not currently installed; per the Implementer
  README §6, no auto-install without explicit approval.
- The Constitutional Owner explicitly chose "in-process
  Python threading" over a 3rd-party scheduler for the demo.
- Production migration to APScheduler (or a proper
  distributed scheduler) is recorded as an HD-PHASE8
  operational gate, NOT a constitutional requirement.

Behaviour:
- The scheduler runs a daemon thread that sleeps for the
  configured interval, then runs one ContinuousDiscoveryEngine
  pass.
- PAUSE stops new runs but the thread keeps alive; RESUME
  re-enables new runs; STOP ends the thread.
- Interval is configurable per Constitutional Owner (1-168
  hours, default 6).
- Manual trigger always works regardless of schedule status.
- A singleton SchedulerState row in `impl_scheduler_state`
  holds the configuration.

#### ASS-PHASE9-002 — DataSource interface with simulated default

The default data source for Continuous Discovery is
`SimulatedDataSource`, which produces realistic-looking
industrial maintenance / oil & gas / water treatment / HVAC /
electrical / instrumentation candidates. The simulated source
is ALWAYS marked `DEMO_DATA` and is clearly labelled in the UI
as "DEMO DATA — simulated for the demo."

The `DataSource` interface is in place for future real sources
(USPTO, OpenCorporates, trade publications) to be added when
API keys become available. The interface enforces:

- `data_source` identifier (e.g. "SIMULATED", "USPTO")
- `data_source_marker` (DEMO_DATA or REAL)
- `fetch_candidates(max_n)` method

Constitutional constraint: the system MUST NEVER present
simulated data as if it were real. Every candidate record
carries `data_source` + `data_source_marker`. If the marker is
missing or invalid, the candidate is REJECTED at the register
layer.

### New Records (NOT canonical entities)

The following 4 implementation entities are added to the data
model. They are explicitly EXEMPT from constitutional-trigger
protection (`__constitutional__` is NOT set), so they may be
updated / deleted by the scheduler itself. Per the Sprint
Brief: "The new scheduler entities must be marked as
implementation entities in the data model, not canonical
entities — they're orchestration, not constitutional content."

- **IMPL-001** `SchedulerState` — singleton scheduler state.
- **IMPL-002** `ContinuousSearchRun` — every run record.
- **IMPL-003** `ContinuousDiscoveryCandidate` — every
  evaluated candidate.
- **IMPL-004** `ContinuousDiscoveryNotification` — every
  bilingual notification.

### Counts at a glance

| Metric | v2.4 baseline | After P9 continuous | Delta |
|---|---|---|---|
| Offices | 18 / 18 | 18 / 18 | unchanged |
| Charter Agents | 73 / 73 | 73 / 73 | unchanged |
| Constitutional entities | 98 | 98 | unchanged |
| Implementation entities | 0 | 4 | +4 (IMPL-001..004) |
| Screens | 7 (SCR-PD-001..007) | 10 (+SCR-PD-008..010) | +3 |
| TTA inventory | 17 | 19 | +2 (ASS-PHASE9-001, 002) |
| Tests | 289 / 289 | 333 / 333 | +44 |

### Constitutional completeness

- Constitution v2.3 — UNCHANGED.
- Constitution v2.4 — IN FORCE (additive, 3 PRs, 1 Office,
  4 Agents, 1 Stage, 5 Filters, 6 Entities, 7 Screens, 3
  Integrations, 1 Workflow, 1 Phase — all preserved).
- No new Permanent Rules, Offices, or Agents added.
- Office 18 alive, 4 agents activated, 5 filters applied,
  3 Registers checked, 10-step workflow intact.
- Continuous Proactive Discovery operational: scheduler
  + console + manual trigger + pause/resume + bilingual
  notifications.

### Open Human Decisions (operational, not constitutional)

- HD-PHASE8-002..006 — operational gates (PostgreSQL, prod
  audit init, TDE, UAT, SLO verification).
- HD-PHASE9-001 — production migration to APScheduler (or
  equivalent proper scheduler) when the system moves from
  dev to production. Same HD-PHASE8 family.
- HD-PHASE9-002 — enable real data sources (USPTO,
  OpenCorporates) when API keys become available.

### PR-013 — clarification

The Sprint Brief referenced "PR-013" but the canonical v2.4
amendment added 3 Permanent Rules named **PR-PD-001/002/003**
(Proactive Discovery Permitted under Charter). The Sprint
Brief was interpreted as a reference to those rules (the
"3 PRs" of v2.4 that authorise Proactive Product Discovery).
This was confirmed in the Constitutional Owner's directive
of 2026-07-19.

---

*End of Decision and Assumption Register — Phase 9 Continuous Proactive Discovery Sprint (2026-07-19).*


