# Implementation Gap Register — Phase 1

**Project:** Techno Service AI Intelligence System
**Phase:** 1 — Identity, Access, and Audit Foundation
**Document Reference:** TS-AI-IGP-001
**Governing Authority:** Constitution v2.3
**Status:** Issued for the Phase 1 release

This register is the single source of truth for everything the approved
documents do not say, that affects Phase 1. Per Constitution Article XXXII
(Compliance Attestation) and the Implementer README §5, no assumption is
silently made; every gap is recorded, impact-assessed, and routed to a
Decision Register entry.

---

## Open Gaps (Phase 1)

### GAP-PHASE1-001 — Second-factor mechanism not specified in Phase 1 governing docs

- **Description:** The governing documents reference "second factor" as part of Account & Security Settings (Document 04) but do not mandate a specific mechanism (TOTP / WebAuthn / SMS / push).
- **Impact:** `Major` for the AC-P1-005 (account and security settings) full coverage; `Cosmetic` for Phase 1 completion (the screen exists; the 2FA mechanism is deferred).
- **Recommended resolution:** Phase 2 introduces a TOTP second factor; WebAuthn / push options follow in Phase 7 with the rest of the security features.
- **Human Approval Required:** `Yes` (selection of 2FA mechanism is a Class 3 decision per Article XII).
- **Status:** `Open`.

### GAP-PHASE1-002 — No specific accessibility standard (WCAG level) named in UI/UX

- **Description:** Document 07 Section 1 references accessibility but does not name a specific WCAG level (e.g. 2.1 AA).
- **Impact:** `Major` for AC-UI-006 (when activated in later phases). `Cosmetic` for Phase 1.
- **Recommended resolution:** Phase 7 introduces a formal accessibility test suite; the level (AA) is the de-facto enterprise standard and is applied as a technical assumption in Phase 1 templates (semantic HTML, labelled form fields, sufficient contrast).
- **Human Approval Required:** `Yes` (when the test suite is introduced).
- **Status:** `Open`.

### GAP-PHASE1-003 — Default SoD class bucketing is a working assumption

- **Description:** The Agent Interaction & Responsibility Matrix (Document 02A) defines the full SoD matrix across all 17 Offices and 61 Principal Agents. The detailed cross-Office SoD rules are not yet activated because Phases 4–7 have not introduced those Offices.
- **Impact:** `Major` for the full SoD regime. `Minor` for Phase 1 (the foundational SoD check on role assignment is implemented and tested in `test_article_xvii_and_xx.py`).
- **Recommended resolution:** Re-open this gap at the end of each phase as new Offices come online. Phase 3 activates the SoD matrix for the Workflow / Verification / Approval Office.
- **Human Approval Required:** `No` (mechanical expansion once the matrix is loaded).
- **Status:** `Open`.

### GAP-PHASE1-004 — Audit retention period not specified

- **Description:** The Constitution (Article XX paragraph 2) requires "retention classification" but does not specify a default period. Document 04 and 05 leave this to operational standards.
- **Impact:** `Cosmetic` for Phase 1. The `retention_class` column exists on every audit entry and defaults to `PERMANENT` per the constitutional principle that audit is a constitutional asset.
- **Recommended resolution:** Phase 7 introduces a Lower Document "Audit Retention Standard" that defines per-class retention periods. Until then, the default `PERMANENT` is used.
- **Human Approval Required:** `Yes` (when the standard is introduced).
- **Status:** `Open`.

### GAP-PHASE1-005 — Performance SLAs (latency, throughput) not specified for Phase 1

- **Description:** Constitution Article XIV and Document 04 require performance and scalability from the foundation. Specific latency and throughput numbers are reserved for Document 04 §1.6 and a Lower Document "Performance Standard".
- **Impact:** `Major` for Phase 8 sign-off. `Minor` for Phase 1 (the foundation is built with async I/O, indexed audit log, and a portable ORM; no specific SLO is asserted).
- **Recommended resolution:** Phase 7 introduces the Performance Standard. Phase 8 asserts conformance.
- **Human Approval Required:** `Yes` (when the standard is introduced).
- **Status:** `Open`.

### GAP-PHASE1-006 — No implementation toolchain on the implementer machine at the start of Phase 1

- **Description:** Python 3 and Git were not installed on the implementer machine. Resolved during Phase 1 with explicit user approval to install via `winget`. Recorded for traceability.
- **Impact:** `Blocker` for AC-P1-001..004 verification (the test runner requires Python). `None` after the install.
- **Recommended resolution:** Resolved — both Python 3.12 and Git 2.55 were installed with the user's approval. Future implementations should assume a pre-provisioned build host.
- **Human Approval Required:** `Yes` (was given).
- **Status:** `Resolved`.

---

## Resolved Gaps

| ID | Description | Resolution |
|---|---|---|
| GAP-PHASE1-006 | No implementation toolchain on the implementer machine | Installed Python 3.12.10 and Git 2.55.0.3 via `winget` with explicit user approval. |

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

*End of Implementation Gap Register — Phase 1.*
