# Implementation Gap Register

**Project:** Techno Service AI Intelligence System
**Phase:** 2 — Data Foundation (current phase)
**Document Reference:** TS-AI-IGP-001
**Governing Authority:** Constitution v2.3
**Status:** Issued for the Phase 2 release

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

---

## Resolved Gaps

| ID | Description | Resolution |
|---|---|---|
| GAP-PHASE1-006 | No implementation toolchain on the implementer machine | Installed Python 3.12.10 and Git 2.55.0.3 via `winget` with explicit user approval (Phase 1). |

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

*End of Implementation Gap Register — Phase 2.*

