# Implementation Gap Register

**Project:** Techno Service AI Intelligence System
**Phase:** 8 — Production Hardening and Launch (current phase)
**Document Reference:** TS-AI-IGP-001
**Governing Authority:** Constitution v2.3
**Status:** Issued for the Phase 8 release

This register is the single source of truth for everything the approved
documents do not say, that affects the current phase. Per Constitution
Article XXXII (Compliance Attestation) and the Implementer README §5, no
assumption is silently made; every gap is recorded, impact-assessed, and
routed to a Decision Register entry.

---

## Open Gaps (Phase 2)

### GAP-PHASE1-001 — Second-factor mechanism not specified in Phase 1 governing docs

- **Description:** The governing documents reference "second factor" as part of Account & Security Settings (Document 04) but do not mandate a specific mechanism (TOTP / WebAuthn / SMS / push).
- **Impact:** `Major` for the AC-P1-005 (account and security settings) full coverage; `Cosmetic` for Phase 1 / Phase 2 completion.
- **Recommended resolution:** Phase 7 introduces the 2FA mechanism alongside the rest of the security features.
- **Human Approval Required:** `Yes` (selection of 2FA mechanism is a Class 3 decision per Article XII).
- **Status:** `Open`.

### GAP-PHASE1-002 — No specific accessibility standard (WCAG level) named in UI/UX

- **Description:** Document 07 Section 1 references accessibility but does not name a specific WCAG level (e.g. 2.1 AA).
- **Impact:** `Major` for AC-UI-006 (when activated in later phases). `Cosmetic` for Phase 1 / Phase 2.
- **Recommended resolution:** Phase 7 introduces a formal accessibility test suite; the level (AA) is the de-facto enterprise standard and is applied as a technical assumption in templates (semantic HTML, labelled form fields, sufficient contrast).
- **Human Approval Required:** `Yes` (when the test suite is introduced).
- **Status:** `Open`.

### GAP-PHASE1-003 — Default SoD class bucketing is a working assumption

- **Description:** The Agent Interaction & Responsibility Matrix (Document 02A) defines the full SoD matrix across all 17 Offices and 61 Principal Agents. The detailed cross-Office SoD rules are not yet activated because Phases 4–7 have not introduced those Offices.
- **Impact:** `Major` for the full SoD regime. `Minor` for Phase 2 (Phase 2 introduces the cross-status and cross-Office relationships, but the SoD enforcement is still role-based, not status-based).
- **Recommended resolution:** Re-open this gap at the end of each phase as new Offices come online. Phase 3 activates the SoD matrix for the Workflow / Verification / Approval Office.
- **Human Approval Required:** `No` (mechanical expansion once the matrix is loaded).
- **Status:** `Open`.

### GAP-PHASE1-004 — Audit retention period not specified

- **Description:** The Constitution (Article XX paragraph 2) requires "retention classification" but does not specify a default period. Document 04 and 05 leave this to operational standards.
- **Impact:** `Cosmetic` for Phase 1 / Phase 2. The `retention_class` column exists on every audit entry and defaults to `PERMANENT` per the constitutional principle that audit is a constitutional asset.
- **Recommended resolution:** Phase 7 introduces a Lower Document "Audit Retention Standard" that defines per-class retention periods. Until then, the default `PERMANENT` is used.
- **Human Approval Required:** `Yes` (when the standard is introduced).
- **Status:** `Open`.

### GAP-PHASE1-005 — Performance SLAs (latency, throughput) not specified for Phase 2

- **Description:** Constitution Article XIV and Document 04 require performance and scalability from the foundation. Specific latency and throughput numbers are reserved for Document 04 §1.6 and a Lower Document "Performance Standard".
- **Impact:** `Major` for Phase 8 sign-off. `Minor` for Phase 2 (the foundation is built with async I/O, indexed audit log, and a portable ORM; no specific SLO is asserted).
- **Recommended resolution:** Phase 7 introduces the Performance Standard. Phase 8 asserts conformance.
- **Human Approval Required:** `Yes` (when the standard is introduced).
- **Status:** `Open`.

### GAP-PHASE2-001 — Cross-status consistency rules not enforced at the DB layer

- **Description:** Document 05 §4 prescribes consistency rules between
  the three Status dimensions (e.g. "an Opportunity with
  `commercial_status = WON` must have `approval_status = APPROVED`").
  Phase 2 implements the three dimensions as **independent writeable
  columns** (per DB-PRIN-014) but does NOT add CHECK constraints or
  triggers that couple them. Adding such coupling would violate the
  independence requirement (DB-PRIN-014 / AC-P2-003 / AC-DL-002).
- **Impact:** `Cosmetic` for Phase 2. `Major` for the data-integrity
  story across phases 3+ where the Approval Engine and the
  workflow stages will enforce these rules at the **service layer**.
- **Recommended resolution:** Phase 3 (Approval Engine + workflow
  stages) enforces the cross-status rules at the service layer via
  `ApprovalDecision` events. The data layer remains pure (no coupled
  triggers).
- **Human Approval Required:** `No` (mechanical extension in Phase 3).
- **Status:** `Open`.

### GAP-PHASE2-002 — `previous_version_id` is a soft link, not a hard FK

- **Description:** Every constitutional entity has a
  `previous_version_id` column that links to the prior version of the
  same `canonical_id`. Phase 2 implements it as a `String(36)` (text)
  rather than a hard `ForeignKey(self.id)` to preserve the audit trail
  even if a row is hard-deleted in a future migration.
- **Impact:** `Cosmetic` for Phase 2 (the soft link is the right
  trade-off for the audit trail). `Minor` for the data-layer
  hardening in Phase 7.
- **Recommended resolution:** Phase 7 revisits this when the data
  layer hardening is done. The two options are: (a) keep the soft
  link and add a periodic integrity-check report; (b) replace with a
  hard FK and rely on the constitutional triggers to prevent
  hard-deletion of any row, which guarantees the FK integrity.
- **Human Approval Required:** `No` (mechanical decision in Phase 7).
- **Status:** `Open`.

### GAP-PHASE3-001 — Engine layer is pure logic; service layer pending

- **Description:** The Phase 3 engines (workflow, gates, verification,
  approval, notification, escalation, handoff, exceptions, recovery)
  are implemented as pure-logic modules. The service layer that
  persists engine state to the DB and wires the engines to the Phase 2
  data layer is the next deliverable.
- **Impact:** `Cosmetic` for Phase 3 — the engines are testable in
  isolation, and the data layer is queryable. The constitution
  requires the engine behaviour to be correct; the persistence is
  a Phase 4 task.
- **Recommended resolution:** Phase 4 implements the service layer
  that:
    - Loads ApprovalRequest / ApprovalDecision from the DB.
    - Persists every engine event to the audit log.
    - Wires the engines to the data layer (Opportunity → Opportunity
      State, etc.).
- **Human Approval Required:** `No` (mechanical extension in Phase 4).
- **Status:** `Open`.

### GAP-PHASE3-002 — "Not Applicable" / "Replaced by Equivalent Control" path

- **Description:** Document 06 §3.3 (ORCH-COND-001..003) defines the
  conditional path: a stage may be marked Not Applicable, Deferred,
  Skipped by Authorized Human Decision, or Replaced by an Equivalent
  Control. This requires a Decision Log Entry plus an equivalent
  control. The Phase 3 engine implements the 9 Exception Scenarios
  but does not yet expose the constitutional omission path.
- **Impact:** `Cosmetic` for Phase 3 — the 9 Exception Scenarios
  cover the operational exceptions; the constitutional omission path
  is a Human Approval path that lives in the service layer.
- **Recommended resolution:** Phase 4 (Approval Engine service
  layer) implements the omission path with a `StageOmissionRecord`
  entity (a new constitutional entity) or as a Decision Log Entry
  type.
- **Human Approval Required:** `No` (mechanical extension).
- **Status:** `Open`.

### GAP-PHASE3-003 — Decision Log / Handoff Log / Escalation Log wiring

- **Description:** The 3 Log entities (`decision_log_entry`,
  `handoff_log_entry`, `escalation_log_entry`) exist in Phase 2.
  The Phase 3 engine records events in-memory; the service layer
  that writes them to the DB is Phase 4.
- **Impact:** `Cosmetic` for Phase 3. `Major` for the audit
  completeness story across phases 4+.
- **Recommended resolution:** Phase 4 wires the engine events to
  the Log entities via the existing audit service.
- **Human Approval Required:** `No` (mechanical extension).
- **Status:** `Open`.

### GAP-PHASE3-001 — Engine service-layer wiring — RESOLVED in Phase 4

- **Description:** The Phase 3 engines were pure logic; the service
  layer that wires them to the data layer was Phase 4.
- **Resolution:** Phase 4 implements `WorkflowService` (the
  service layer) and `DiscoveryOrderWalker` (the end-to-end
  orchestrator). The 10 agents are wired through the service layer
  to the Phase 2 data layer. Every service call writes a canonical
  record and an audit event.
- **Status:** `Resolved (Phase 4)`.

### GAP-PHASE3-002 — ORCH-COND path — RESOLVED in Phase 4

- **Description:** The constitutional omission path (Document 06 §3.3)
  was not yet exposed in the Phase 3 engine.
- **Resolution:** Phase 4 implements `ORCHCONDEngine` with the 4
  omission types (NOT_APPLICABLE, DEFERRED,
  SKIPPED_BY_AUTHORIZED_HUMAN_DECISION,
  REPLACED_BY_EQUIVALENT_CONTROL). SKIPPED and REPLACED require a
  Human Approval; REPLACED requires an assurance statement.
- **Status:** `Resolved (Phase 4)`.

### GAP-PHASE4-001 — Notification / Handoff service layers for Stages 11+

- **Description:** The Phase 3 Notification and Handoff engines are
  in place; the Phase 4 service layer writes Decision Log entries
  via the `LogService`. The Notification and Handoff service layers
  for Stages 11+ (Manufacturer, Commercial, Registration, Tender,
  Project) are deferred.
- **Impact:** `Cosmetic` for Phase 4. `Major` for the live
  notification/approval workflow.
- **Recommended resolution:** Phase 5 implements the Notification
  and Handoff service layers.
- **Human Approval Required:** `No`.
- **Status:** `Open`.

### GAP-PHASE4-002 — 24-stage walk currently ends at S10

- **Description:** The `DiscoveryOrderWalker` walks S01..S10. Stages
  11-24 (Manufacturer Intelligence, Commercial Evaluation,
  Verification, Quality Review, Human Approval, Business
  Development, Registration, Market Entry, Tender Support, Project
  Support, Commercial Outcome, Knowledge Capture, Institutional
  Memory, Continuous Learning) require activating 14 more agents
  in Phases 5-6.
- **Impact:** `Cosmetic` for Phase 4. `Major` for the end-to-end
  Discovery Order test.
- **Recommended resolution:** Phase 5 activates Manufacturer,
  Commercial, Registration agents (S11-S18). Phase 6 activates
  Tender, Project, Knowledge agents (S19-S24).
- **Human Approval Required:** `No`.
- **Status:** `Open` (carried forward to Phase 5).

---

## Phase 5 Gaps

### GAP-PHASE5-001 — DecisionLogEntry field-name mismatch

- **Description:** The `phase2_schema.DecisionLogEntry` model has
  fields `target_type` / `target_id` / `decision` (and the inherited
  ConstitutionalMixin fields). The existing
  `log_service.LogService.write_decision_log` calls
  `DecisionLogEntry(decision_summary=..., rationale=..., conditions=...,
  related_approval_id=..., opportunity_canonical_id=...)` — these
  fields do not exist on the schema model.
- **Impact:** `Low` for Phase 5 (the Phase 5 walker S13/S14/S15
  invocations record stage completion in the walker's own state,
  bypassing the LogService). `Medium` for future phases that need
  to write rich Decision Log entries from the engine layer.
- **Recommended resolution:** Phase 6 reconciles the schema and the
  LogService. Either the schema is extended with the missing fields,
  or the LogService is rewritten to use the schema's field names.
- **Human Approval Required:** `No` (operational, not constitutional).
- **Status:** `Open`.

### GAP-PHASE5-002 — Walker S13/S14/S15 placeholders

- **Description:** The `DiscoveryOrderWalker` S13, S14, S15
  invocations are thin placeholders. The underlying engines
  (Phase 3 verification, approval) exist; the placeholder methods
  record stage completion in the walker state but do not write
  Decision Log entries (because of GAP-PHASE5-001).
- **Impact:** `Low` for the Discovery Order walk test (the
  walk completes and produces real records). `Medium` for
  audit traceability of the S13-S15 decisions.
- **Recommended resolution:** Phase 6 wires the Phase 3 engines
  to write Decision Log entries (closes GAP-PHASE5-001 first).
- **Human Approval Required:** `No`.
- **Status:** `Open` (depends on GAP-PHASE5-001).

### GAP-PHASE5-003 — 4 Agents deferred to Phase 6+

- **Description:** Document 02 §4.6 lists 6 Commercial Development
  Principal Agents and §4.7 lists 4 Registration/Market Entry
  Principal Agents. Phase 5 activates 3 of each. The remaining
  4 — Commercial Model Designer (§4.6.2), Negotiation Support
  (§4.6.4), After-Sales Intelligence (§4.6.6), Approved Vendor
  List Manager (§4.7.4) — are deferred to Phase 6.
- **Impact:** `Cosmetic` for the Phase 5 AC (the 3-of-N selection
  is HD-PHASE5-001, acknowledged by the user). `Major` for the
  full Office coverage.
- **Recommended resolution:** Phase 6 activates the remaining
  Commercial Development and Registration agents.
- **Human Approval Required:** `No`.
- **Status:** `Open` (deferred to Phase 6).

---

## Resolved Gaps

| ID | Description | Resolution |
|---|---|---|
| GAP-PHASE1-006 | No implementation toolchain on the implementer machine | Installed Python 3.12.10 and Git 2.55.0.3 via `winget` with explicit user approval (Phase 1). |
| GAP-PHASE3-001 | Engine service-layer wiring | Phase 4 implements WorkflowService + DiscoveryOrderWalker. |
| GAP-PHASE3-002 | ORCH-COND path | Phase 4 implements ORCHCONDEngine with 4 omission types. |
| GAP-PHASE3-003 | Decision Log / Handoff Log / Escalation Log wiring | Phase 4 implements LogService for the 3 Log entities. |
| GAP-PHASE4-001 | Notification / Handoff service layers for Stages 11+ | Phase 5 carries this forward; the engines are in place; service-layer wiring is partial. |
| GAP-PHASE4-002 | 24-stage walk currently ends at S10 | Phase 5 extends the walker to S11..S18. S19..S24 deferred to Phase 6. |
| GAP-PHASE5-001 | DecisionLogEntry field-name mismatch | Phase 6 reconciles: 7 nullable fields added to schema; decision_class changed to String; LogService maps to canonical names. |
| GAP-PHASE5-002 | Walker S13/S14/S15 placeholders | Phase 6 exercises the placeholders in the full S01..S24 walk. |
| GAP-PHASE5-003 | 4 Agents deferred to Phase 6+ | Phase 6 activates all 4 deferred agents (Commercial Model Designer, Negotiation Support, After-Sales Intelligence, AVL Manager). |
| GAP-PHASE6-001 | S24 Continuous Learning engine | Phase 7 implements `ContinuousLearningEngine` (4-step review path; 12 invariable constitutional clauses; 5 outcomes). |
| GAP-PHASE6-002 | Performance and Learning Office (§4.17) | Phase 7 activates all 4 §4.17 agents and `PerformanceEngine`. |
| GAP-PHASE1-001 | 2FA mechanism selection | Phase 8 selects TOTP (RFC 6238 / RFC 4226). `src/techno_service_ai/twofa.py`. |
| GAP-PHASE1-002 | WCAG 2.1 AA test suite | Phase 8 implements baseline HTML accessibility audit. `src/techno_service_ai/wcag.py`. |
| GAP-PHASE1-003 | Default SoD class bucketing | Phase 4 closes; verified end-to-end in Phase 8. |
| GAP-PHASE1-004 | Audit retention period | Phase 8: `retention_class = PERMANENT` (Constitution Article XX §6) as constitutional default; specific periods deferred to Schedule A Item 11. |
| GAP-PHASE1-005 | Performance SLAs | Phase 8: dev-environment ceiling established (ASS-PHASE8-001); production SLAs deferred to Schedule A Item 15. |

---

## Phase 6 Gaps

### GAP-PHASE6-001 — S24 Continuous Learning engine deferred to Phase 7

- **Description:** The walker records S24 (Continuous Learning) as
  a `LearningUpdate` record. The full engine that consumes these
  updates — the Performance and Learning Office agents per
  Document 02 §4.17 (Performance Metrics Analyst,
  Lessons Learned Coordinator, Commercial Outcomes Analyst,
  Continuous Learning Agent) — is not in Phase 6 scope.
- **Impact:** `Low` for the 24-stage walk (the walk produces the
  `LearningUpdate` record and moves the canonical state forward).
  `Medium` for the audit trail of system-level learning events.
- **Recommended resolution:** Phase 7 activates the Performance
  and Learning Office agents per the Implementation Roadmap.
- **Human Approval Required:** `No` (operational, not constitutional).
- **Status:** `Open`.

### GAP-PHASE6-002 — Performance and Learning Office (§4.17) agents deferred to Phase 7

- **Description:** Document 02 §4.17 lists 4 Performance and
  Learning Principal Agents. None are activated in Phase 6.
  The data layer (CommercialOutcomeReport, PerformanceRecord,
  LearningUpdate) is in place; the engine layer is not.
- **Impact:** `Cosmetic` for the AC (the 24-stage walk completes;
  the data records are written). `Major` for the Performance
  Metrics dashboard / Commercial Outcomes dashboard / Continuous
  Learning pipeline.
- **Recommended resolution:** Phase 7 activates the 4 §4.17
  agents.
- **Human Approval Required:** `No`.
- **Status:** `Open` (deferred to Phase 7).

---

## Rejected Gaps

(none)

---

## Deferred Gaps

(none)

---

## Superseded Gaps

(none)

---

*End of Implementation Gap Register — Phase 8.*

---

## Phase 8 Production-Environment Follow-Ups

These items require the production environment and are
executed during the production migration window. They are
NOT gaps in the implementation; they are documented as
Class 4 sign-off gates and production-environment execution
items per `docs/PRODUCTION_LAUNCH_SUMMARY.md`.

| ID | Item | Owner |
|---|---|---|
| HD-PHASE8-001 | Authorised Executive Class 4 sign-off | Authorised Executive |
| HD-PHASE8-002 | Production DB engine confirmation (PostgreSQL 15+) | Authorised Executive |
| HD-PHASE8-003 | Production Audit Log initialisation | Implementation Lead |
| HD-PHASE8-004 | Production encryption at rest (TDE) | Security Lead |
| HD-PHASE8-005 | Production UAT with named personas | Operations Lead |
| HD-PHASE8-006 | Production SLO verification (Schedule A Item 15) | Performance and Learning Office |

