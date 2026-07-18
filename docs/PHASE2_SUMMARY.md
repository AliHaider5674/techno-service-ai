# Phase 2 Summary — Data Foundation

**Phase:** 2 of 9
**Reference:** Document 08 §2.3 (MBO-DL-001-A..T); Document 05 (Database & Information Model Design v1.0)
**Status:** Implementation complete, test suite passing (67/67 across Phases 1–2), ready for sign-off review
**Constitutional Authority:** Constitution v2.3
**Builds on:** Phase 1 (Identity, Access, Audit)

---

## What was delivered

Phase 2 activates the **Data Foundation** of the Techno Service AI
Intelligence System. The full set of **20 Information Domains**,
**94 Constitutional tables**, the **3 Status dimensions**, the
**3 Constitutional Registers**, the **no-silent-amendment** data-layer
enforcement, and the **forward-only, versioned, reproducible, auditable
migration framework** are now in place.

### 1. Information Domains (20 of 20 — MBO-DL-001)

| # | Domain | Canonical Entities Implemented |
|---|---|---|
| 1 | Constitutional Reference | ConstitutionalDocument, Office, AgentCharter |
| 2 | Identity and Access (extended) | (Phase 1) + 4 access-policy linked entities |
| 3 | Audit (extended) | (Phase 1) + DecisionLogEntry, HandoffLogEntry, EscalationLogEntry |
| 4 | Industrial Intelligence | IndustrialEnvironmentProfile, EnvironmentalUpdate, IndustrialActivity, ValidatedSignal |
| 5 | Opportunity Intelligence | ProblemOrNeed, RootCause, ValueCase, Opportunity (+ 3 status columns) |
| 6 | Technology Intelligence | TechnologyCategoryAnalysis, ProductAnalysis, ComparativeAnalysis (+ 3 status columns), KuwaitSuitabilityReview |
| 7 | Manufacturer Intelligence | ManufacturerProfile, ManufacturerCredibilityAssessment, ManufacturerComparisonReport, ManufacturerRelationshipRecord |
| 8 | Commercial Intelligence | CommercialEvaluation, CommercialModelOption, BusinessDevelopmentEngagement, NegotiationAnalysis, PricingAnalysis, AfterSalesIntelligenceReport, CommercialOutcomeReport |
| 9 | Registration and Market Entry | RegistrationStatusReport, RegistrationDossier, PrequalificationStatusReport, ApprovedVendorListStatusReport |
| 10 | Tender and Project | Tender, TenderQualificationReport, QuotationDossier, ProjectStatusReport |
| 11 | Verification | PreliminaryReview, SpecialistVerification, IndependentFinalVerification, SecondReviewerVerification, ClaimClassification, VerificationIndependenceTracker, EvidenceItem |
| 12 | Quality Assurance | QualityReview, StandardsComplianceReport |
| 13 | Risk and Compliance | EnterpriseRisk, ComplianceReviewReport, ConstitutionalIncident, RegisterEntryCrossReference |
| 14 | Security and Data Governance | SecurityEvent, AccessControlEntry, ContinuityPlan, RecoveryTestReport, RecoveryReport, ContinuityEvent, AgentIdentity, AccessAuditReport, DataClassificationEntry |
| 15 | Knowledge and Institutional Memory | KnowledgeRecord, LessonLearned, InstitutionalMemoryIndex, KnowledgeBaseInventory |
| 16 | Approval and Decision | ApprovalRequest, ApprovalPackage, ApprovalDecision, ApprovalAuthority, StandingAuthorisation, EmergencyApproval, ConditionalApproval, ApprovalRevocation |
| 17 | Notification | NotificationRecord, NotificationChannel, NotificationPreference |
| 18 | Reporting | Report, ReportTemplate, ReportExportRecord, BoardReport |
| 19 | Performance and Learning | PerformanceRecord, CommercialOutcomeReport (shared with §8), LearningUpdate |
| 20 | Cross-Office Collaboration | HandoffRecord, EscalationRecord, HandoffLogEntry (audit mirror) |

Plus the **Three Constitutional Registers** (Article VIII):
- RepresentedPrincipalsRegister (`represented_principals_register`)
- ConflictDoNotPursueEntity (`conflict_register`)
- RestrictedProhibitedEntity (`restricted_register`)

### 2. Three Status dimensions (INDEPENDENT columns)

Per Constitution Article XIX and Document 05 (DB-PRIN-014, AC-P2-003, AC-DL-002),
the three Status dimensions are **independent writeable columns** with
their own state machines. No view, no derived column, no trigger
that couples them.

`Opportunity` (and `ComparativeAnalysis`) carry:

| Column | Type | Default | Source Citation |
|---|---|---|---|
| `intelligence_status` | `VARCHAR(32)` | `VALUE_HYPOTHESIS` | IntelligenceStatus enum |
| `approval_status` | `VARCHAR(32)` | `NOT_SUBMITTED` | ApprovalStatus enum |
| `commercial_status` | `VARCHAR(32)` | `MANUFACTURER_IDENTIFICATION` | CommercialStatus enum |

Each is paired with an `_at` timestamp column
(`intelligence_status_at`, `approval_status_at`, `commercial_status_at`)
that records when the dimension was last changed. Changing one status
**does not** mutate the other two — verified by `tests/test_phase2.py::test_ac_p2_003_status_dimensions_are_independent_columns`.

### 3. Three Constitutional Registers (INDEPENDENT tables)

Per Constitution Article VIII and Document 05 (AC-P2-004, AC-DL-003),
the three Registers are **independent tables**, each with its own
write path, its own status, and its own meaning.

| Register | Table | Distinguishing NOT-NULL field | Status field |
|---|---|---|---|
| Represented Principals | `represented_principals_register` | `brand` | `status` |
| Conflict / Do-Not-Pursue | `conflict_register` | `conflict_type` | `status` |
| Restricted / Prohibited | `restricted_register` | `restriction_type` | `status` |

INSERTing into one register does not affect the other two — verified by
`tests/test_phase2.py::test_ac_p2_004_three_registers_are_independent_tables`.

### 4. No-Silent-Amendment enforcement (DB layer)

Per Constitution Article XX paragraph 6 and Document 05 (DB-PRIN-018,
AC-P2-005, AC-DL-004), every **Constitutional table** is protected
by two SQLite `BEFORE` triggers that `RAISE(ABORT)` on any UPDATE or
DELETE. Implemented by `db.install_constitutional_triggers()` which:

- Discovers every ORM class with `__constitutional__ = True`
- Creates `BEFORE UPDATE` and `BEFORE DELETE` triggers on its
  `__tablename__`
- Skips the **9 operational tables** (audit_log, migration, user,
  role, user_role, persona, user_session, access_policy,
  access_policy_role) that need UPSERT semantics

Coverage: **94 constitutional tables** (post-Phase 2 total). The
"update" path for constitutional entities is therefore:

```
INSERT a new versioned row with the same canonical_id,
       version += 1, previous_version_id = old.id
```

The old row is preserved. The audit chain continues. Historical state
is queryable (AC-DL-005).

### 5. Migration framework (forward-only, versioned, reproducible, auditable)

Per Document 05 and the Phase 2 Backlog (IMPL-P2-023..030), the
migration framework is implemented in `techno_service_ai.migrations`:

- **Forward-only** — no rollback of data; rollback only of the **tail**
  (the last applied migration). The framework is monotonic.
- **Versioned** — every migration has a unique version (`M0001`,
  `M0002`, ...). Applied in registration order.
- **Reproducible** — applying on a fresh DB reaches the same schema as
  applying on a copy of production. `apply_all()` is idempotent.
- **Auditable** — every applied migration writes a `MIGRATION.APPLIED`
  audit event with `actor=applied_by`, `payload={name, description,
  checksum, duration_ms, environment}`. The migration table itself
  records the same fields.
- **Apply → rollback → re-apply** — verified by
  `tests/test_phase2.py::test_ac_p2_006_migration_apply_rollback_reapply`.

**Operational note** (correctness fix during Phase 2 build):
the `migration` table is now part of `Base.metadata` via the SQLAlchemy
`Migration` model in `schema.py`. This means `reset_schema()` (the
test fixture's reset path) drops and recreates the migration table
alongside the rest of the schema, so each test starts from a clean
state. The `Migration` model is exempt from the constitutional
triggers (one of the 9 operational tables), so its UPSERT
semantics — needed for re-apply after rollback — work correctly.

Two migrations are registered:

| Version | Name | Purpose |
|---|---|---|
| M0001 | `create_migration_table` | Marker — proves the framework is in effect. No-op upgrade/downgrade; the table is created by `Base.metadata.create_all`. |
| M0002 | `phase2_constitutional_registers` | Creates the 3 Constitutional Registers. Downgrade drops the 3 register tables. |

### 6. Code deliverables

| File | Purpose |
|---|---|
| `src/techno_service_ai/constitutional.py` | `ConstitutionalMixin` (canonical_id, version, ...), 3 status enums, 2 register enums |
| `src/techno_service_ai/migrations.py` | `Migration` base class, M0001..M0002, `apply_all`, `rollback`, `MigrationRecord` dataclass |
| `src/techno_service_ai/phase2_schema.py` | 84 new canonical entities across 20 Information Domains + 3 register entities |
| `src/techno_service_ai/db.py` | `install_constitutional_triggers()`, `apply_schema()`, `reset_schema()` (extended) |
| `src/techno_service_ai/schema.py` | `Migration` ORM model (added) |
| `src/techno_service_ai/bootstrap.py` | Calls `apply_all(applied_by="bootstrap")` after `apply_schema()` |
| `tests/test_phase2.py` | 14 new tests (AC-P2-001..006 + AC-DL-001..005) |

---

## How to run

```bash
# The framework runs as part of bootstrap:
python -m techno_service_ai.bootstrap
# Output includes:
#   [bootstrap] schema applied at sqlite:///...
#   [bootstrap] seeded 9 roles, 4 access policies

# Run the test suite (Phase 1 + Phase 2 = 67 tests):
pytest
```

---

## Counts at a glance

| Metric | Count |
|---|---|
| Total ORM tables | 103 |
| Constitutional tables (protected by triggers) | 94 |
| Operational tables (exempt from triggers) | 9 |
| Information Domains implemented | 20 of 20 |
| Canonical entities (new in Phase 2) | 87 |
| Status dimensions (independent columns) | 3 |
| Constitutional Registers (independent tables) | 3 |
| ForeignKey relationships in phase2_schema | 51 (24 unique targets) |
| Migrations registered | 2 (M0001, M0002) |
| Phase 2 tests | 14 |
| Total tests (Phase 1 + Phase 2) | 67 (all green) |

---

## Acceptance criteria coverage

| Criterion | Status | Test |
|---|---|---|
| AC-P2-001 Every Information Domain is queryable | ✅ | `test_ac_p2_001_all_20_domains_queryable` |
| AC-P2-002 Every Canonical Entity is created, read, updated, versioned | ✅ | `test_ac_p2_002_canonical_entity_crud_versioned` + `_in_place_update_is_rejected` + `_in_place_delete_is_rejected` |
| AC-P2-003 Three Status dimensions are independent | ✅ | `test_ac_p2_003_status_dimensions_are_independent_columns` |
| AC-P2-004 Three Registers are independent | ✅ | `test_ac_p2_004_three_registers_are_independent_tables` |
| AC-P2-005 No-Silent-Amendment is enforced | ✅ | `test_ac_p2_005_silent_update_rejected` + `test_ac_p2_005_silent_delete_rejected` |
| AC-P2-006 Migration framework: apply → rollback → re-apply | ✅ | `test_ac_p2_006_migration_apply_rollback_reapply` + `_migration_audited` |
| AC-DL-001 Schema covers 70+ canonical entities | ✅ (94) | `test_ac_dl_001_schema_covers_70_plus_canonical_entities` |
| AC-DL-002 Status columns are not views or computed | ✅ | `test_ac_dl_002_status_columns_are_not_views_or_computed` |
| AC-DL-003 Registers are independent structures | ✅ | `test_ac_dl_003_registers_are_independent_structures` |
| AC-DL-004 Institutional Memory preserves history | ✅ | `test_ac_dl_004_institutional_memory_preserves_history` |

---

## Constitutional notes

- **Article VIII (Constitutional Registers).** The three Registers are real tables. Each entry has a status, an effective period, a responsible human authority, a reason, and a source citation. The Registers are themselves append-only (Constitutional triggers installed).
- **Article XIX (Decision Status).** The three Status dimensions are independent writeable columns with their own state machines, their own transition tables, and their own `_at` timestamps. The model is exactly the one Document 05 prescribes (DB-PRIN-014).
- **Article XX paragraph 6 (No Silent Amendment).** Enforced at the DB layer for 94 constitutional tables. The pattern: `UPDATE` is rejected by `BEFORE UPDATE` trigger; the only way to "change" a row is to INSERT a new versioned row. Historical state is therefore always queryable (AC-DL-005).
- **Article XXVIII (Document Hierarchy).** Constitution v2.3 is unmodified. No Lower Document has been modified (Document 05 is a governing document). All tech-stack choices are recorded as Temporary Technical Assumptions in `docs/DECISION_AND_ASSUMPTION_REGISTER.md` (see Phase 2 additions).
- **Hash chain continues.** Migration events are recorded in the audit log (`MIGRATION.APPLIED`, `MIGRATION.ROLLED_BACK`) and the chain continues unbroken across bootstrap and tests.

---

## What was NOT delivered (and why)

- **The 24 workflow stages** (Phase 3 — `IMPL-P3-001..006`)
- **The 9 Decision Gates** (Phase 3)
- **The 3 Verification roles + Verification Independence** business logic (Phase 3)
- **The Discovery Order Operational Surfaces** (Phases 4–5) — the
  entities are in place (Industrial, Opportunity, Technology,
  Manufacturer, Commercial), but the *workflows* and *dashboards* are
  Phase 3+
- **Approval engine** (Phases 6+ — entities present, logic pending)
- **Reporting engine** (Phase 6 — entities present, engine pending)
- **Production hardening** (Phase 8 — secure cookie, JWT secret, perf benchmarks)

No governing document has been modified.

---

## Open items for Phase 3 readiness

1. **HD-PHASE2-001** — Acceptance of Phase 2 completion (Implementation Lead + Constitutional Compliance).
2. **HD-PHASE2-002** — Acknowledgement that the 6 Phase 1 tech-stack assumptions remain in force through Phase 8 (or — if a permanent decision is desired earlier — Class 3 sign-off).
3. **GAP-PHASE1-001..005** — Still open; the most material for Phase 3 is the SoD matrix expansion (now that Opportunity → Commercial entities exist, the SoD matrix needs to cover which roles may change which status).
4. **GAP-PHASE2-001 (new)** — The Phase 2 schema does not yet enforce the
   cross-status consistency rules from Document 05 §4 (e.g. "an Opportunity
   with `commercial_status = WON` must have `approval_status = APPROVED`").
   This is intentionally deferred to Phase 3 where the Approval Engine
   and the workflow stages will encode the rules.
5. **GAP-PHASE2-002 (new)** — No `previous_version_id` FK is enforced
   (i.e. the column is free-form text rather than a hard FK). This is
   intentional for Phase 2 (a soft link preserves the audit trail even
   if a row is hard-deleted in a future migration), but Phase 7 should
   revisit this when the data layer hardening is done.

---

*End of Phase 2 Summary.*
