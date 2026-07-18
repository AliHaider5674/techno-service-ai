# Phase 3 Summary — Workflow, Verification, and Approval Foundation

**Phase:** 3 of 9
**Reference:** Document 08 §2.4 (PHASE-3-001..004); Document 06 §2, §3, §4, §5, §6, §7, §8, §9, §12; Authority Matrix v1.0; Document 07 §4.6, §4.7, §10
**Status:** Implementation complete, test suite passing, ready for sign-off review
**Constitutional Authority:** Constitution v2.3
**Builds on:** Phase 1 (Identity, Access, Audit) + Phase 2 (Data Foundation)

---

## What was delivered

Phase 3 activates the **Workflow, Verification, and Approval
Foundation**: the constitutional state machine, the 24-stage
Discovery Order, the 9 non-bypassable Decision Gates, the
Independence-preserving Verification Engine, the Class-aware
Approval Engine, the 6-category Notification Engine, the
6-channel Escalation Engine, the Handoff Service, the 9-scenario
Exception Engine, the Recovery Engine, and the Orchestrator that
ties everything together. The 10 presentation screens from UI/UX
§4.6 and §4.7 are mounted, plus the Notification Inbox from §10.

### 1. 24 Workflow Stages (Document 06 §2.1..2.24)

All 24 stages are registered with their constitutional spec
(Purpose, Office, Agent, Required Inputs, Produced Outputs, Entry
Conditions, Exit Conditions, Validation Rules, Failure Conditions,
Escalation Rules). The Discovery Order is the canonical sequence
per ORCH-SEQ-002:

```
S01 Industrial Environment → S02 Industrial Activity Detection →
S03 Validated Signal → S04 Problem Definition → S05 Root Cause →
S06 Commercial Value Case → S07 Technology Category →
S08 Product Discovery → S09 Replacement Analysis →
S10 Kuwait Suitability → S11 Manufacturer Intelligence →
S12 Commercial Evaluation → S13 Verification →
S14 Quality Review → S15 Human Approval →
S16 Business Development → S17 Registration → S18 Market Entry →
S19 Tender Support → S20 Project Support → S21 Commercial Outcome →
S22 Knowledge Capture → S23 Institutional Memory →
S24 Continuous Learning
```

Skipping, abbreviating, or reordering is REJECTED (WF-PRIN-007,
ORCH-SEQ-003). The only valid forward transition is
`current_stage -> next_stage(current_stage)`. A test
(`test_discovery_order_cannot_be_skipped/abbreviated/reordered`)
verifies this for all three.

### 2. 9 Decision Gates (Document 06 §4.1..4.9)

| # | Gate | Constitutional Owner | Bypass Prohibition |
|---|---|---|---|
| 1 | Evidence | Originating Office | GATE-EV-006 |
| 2 | Verification | Verification Office | GATE-VE-006 |
| 3 | Quality | Quality Assurance Office | GATE-QA-006 |
| 4 | Human Approval | Authorised Human Authority | GATE-HA-006 (silence/urgency/prior/AI ≠ approval) |
| 5 | Commercial | Commercial Development | GATE-CO-006 |
| 6 | Registration | Registration and Market Entry | GATE-RG-006 |
| 7 | Tender | Tender and Project Intelligence | GATE-TN-006 |
| 8 | Project | Tender and Project Intelligence | GATE-PJ-006 |
| 9 | Closure | Originating + Performance & Learning | GATE-CL-006 |

A bypass attempt on **any** of the 9 gates is REJECTED and
recorded (parametrized test `test_ac_p3_002_every_gate_bypass_rejected`).

### 3. 10 Orchestration States (Document 06 §8.1)

`IDLE`, `RUNNING`, `WAITING`, `SUSPENDED`, `REWORK`, `ESCALATED`,
`APPROVED`, `REJECTED`, `CLOSED`, `ARCHIVED`. Every allowed
transition is registered; every forbidden transition is
PREVENTED (STATE-G-002), not warned. A historical state is
preserved when the workflow transitions to a new state
(STATE-G-003). The state machine is independent of the three
Status dimensions (STATE-G-004).

### 4. 5 Verifier Agents + Independence Tracker (Document 06 §6)

1. Preliminary Evidence Reviewer (VER-PRE-001..003)
2. Specialist Verifier (VER-SPE-001..003)
3. Independent Final Verifier (VER-IFV-001..004)
4. Second Reviewer (supports Independent Final on material claims)
5. Claim Classifier (Constitution Article XXIII)

**Producer ≠ Verifier is REJECTED** at the data layer. The
`IndependenceTracker.create_record(...)` method raises
`IndependenceViolation` whenever producer_id == verifier_id. The
check is enforced for every one of the 5 verifier roles
(`test_producer_equals_verifier_rejected_with_each_role`).

For an Independent Final Verifier on a material claim, a
Second Reviewer is mandatory (VER-IFV-003).

### 5. 4 Decision Classes + Required Approver Role (Authority Matrix §3)

| Class | Default Approver | Examples |
|---|---|---|
| 1 — Internal Intelligence | Agent within Charter | Classification, routing |
| 2 — Qualification / Recommendation | RHFO of originating Office | Recommendation |
| 3 — External Action | RHFO (material → Authorised Executive) | Contact, sharing report |
| 4 — Binding / Financial / Legal / Strategic | Authorised Executive / Constitutional Owner | Binding offer, signing contract |

The Approval Engine resolves the Required Approver Role at
request time. A `Self-Approval Prohibited` check (Authority
Matrix §8.2) is enforced at decision time.

**Silence ≠ Approval** (Constitution Article XII paragraph 7,
Article XVII paragraph 2(15), GATE-HA-006, REQ-RULE-005). The 5
substitute signals are REJECTED:

- `SILENCE` — approver did not respond within window
- `URGENCY` — the matter is time-critical
- `PRIOR_BEHAVIOUR` — the approver has approved similar cases
- `SIMILAR_HISTORICAL_APPROVAL` — precedent
- `AI_RECOMMENDATION` — an Agent recommends approval

`Standing Authorisations` (Authority Matrix §5) are rejected for
Class 4 and the §5.3 prohibited categories
(`test_ac_apr_standing_authorisation_prohibited_categories`).

**Conditional Approvals** require conditions, duration, and
revocation conditions. The decision record carries the
expiry_date. **Revocation** is governed by Authority Matrix §10
with 6 valid grounds (Material new information, Error, Fraud,
Breach of conditions, Expiry, Higher-authority decision).

### 6. 6 Notification Categories + 5 Channels (Document 06 §9)

6 categories: `ALERT`, `APPROVAL`, `ESCALATION`, `REMINDER`,
`WORKFLOW_CHANGE`, `AI_NOTIFICATION`.

5 channels: `IN_APP`, `PUSH`, `EMAIL`, `SMS` (Class 3/4 only),
`VOICE` (Emergency only).

Priority order (Constitution Articles XII, XIII, XIV; UI/UX §10):
`CLASS_4` > `CLASS_3` > `CLASS_2` > `CLASS_1` > `OPERATIONAL` >
`INFORMATIONAL`.

**Suppression of Class 3 / Class 4 notifications is FORBIDDEN**
(Constitution Article XVII paragraph 7, REQ-FN-NOT-006,
REQ-RULE-005). The NotificationEngine raises `SuppressionForbidden`
when such a suppression is attempted.

### 7. 6 Escalation Channels (Document 06 §3.7)

`NORMAL`, `CONSTITUTIONAL`, `COMMERCIAL`, `VERIFICATION`, `HUMAN`,
`EMERGENCY`. Every escalation records trigger, route, recipient,
response window, outcome (ORCH-ESC-003). Unacknowledged
escalations are PROMOTED to a higher-priority channel
(ORCH-ESC-004, ORCH-WAIT-003). The promotion order is
NORMAL → COMMERCIAL → VERIFICATION → HUMAN → CONSTITUTIONAL →
EMERGENCY.

### 8. Handoff Service (Interaction Matrix §4)

Handoff Initiation, Acceptance, Audit. A handoff that fails
acceptance criteria is REJECTED (`HandoffRejected`), or
RETURNED for rework, or ESCALATED (COLLAB-HO-002). All three
paths are exercised in the test suite.

### 9. 9 Exception Scenarios (Document 06 §7)

`MISSING_EVIDENCE`, `DUPLICATE_OPPORTUNITY`, `CONFLICTING_SOURCES`,
`REGISTER_CONFLICT`, `COMMERCIAL_CONFLICT`, `CONSTITUTIONAL_INCIDENT`,
`AGENT_FAILURE`, `HUMAN_UNAVAILABLE`, `EXTERNAL_DEPENDENCY_UNAVAILABLE`.
Each has a spec (action + record requirement + escalation target).

### 10. Recovery Model (Document 06 §12)

Interrupted, Restart, Resume, Rollback, Recovery Audit.
**Rollback requires Human Approval** (REC-ROLL-001) — `RollbackRequiresApproval`
is raised otherwise. **Resume that affects Class 3/4 requires
Human Approval** (REC-RESUME-003) — `Class3Or4ResumeRequiresApproval`
is raised otherwise.

### 11. Orchestrator (Document 06 §3)

`WorkflowEngine` ties everything together. One instance per
workflow. Owns the StateMachine; references the other engines.
Every event is recorded (INITIATED, STAGE_STARTED, STAGE_COMPLETED,
STATE_TRANSITION, GATE_PASSED, GATE_BYPASS_REJECTED, …).

### 12. 11 Presentation Screens (UI/UX §4.6, §4.7, §10)

| # | Route | Screen | UI/UX Ref |
|---|---|---|---|
| 1 | `/verification/preliminary-queue` | Preliminary Review Queue | SCR-VER-001 |
| 2 | `/verification/specialist-queue` | Specialist Verification Queue | SCR-VER-002 |
| 3 | `/verification/independent-final-queue` | Independent Final Verification Queue | SCR-VER-003 |
| 4 | `/verification/workspace?claim_id=...` | Verification Workspace | SCR-VER-004 |
| 5 | `/verification/claim-classification` | Claim Classification | SCR-VER-005 |
| 6 | `/verification/independence-tracker` | Independence Tracker | SCR-VER-006 |
| 7 | `/approvals/inbox` | Approval Inbox | SCR-APR-001 |
| 8 | `/approvals/request?request_id=...` | Approval Request | SCR-APR-002 |
| 9 | `/approvals/records` | Approval Records | SCR-APR-003 |
| 10 | `/approvals/authority-matrix` | Approval Authority Matrix | SCR-APR-004 |
| 11 | `/notifications/inbox` | Notification Inbox | NOT-003 |

All 11 routes are mounted, return 200 for authenticated admins,
and carry a constitutional text reference (Document 06 / Constitution
/ Authority Matrix).

---

## Counts at a glance

| Metric | Count |
|---|---|
| Stages registered | 24 (Document 06 §2.1..2.24) |
| Decision Gates implemented | 9 (Document 06 §4.1..4.9) |
| Orchestration States | 10 (Document 06 §8.1) |
| Verifier Agents | 5 (Document 06 §6) |
| Decision Classes | 4 (Constitution Article XII) |
| Notification Categories | 6 (Document 06 §9) |
| Notification Channels | 5 (Document 06 §9) |
| Escalation Channels | 6 (Document 06 §3.7) |
| Exception Scenarios | 9 (Document 06 §7) |
| Recovery Actions | 5 (Document 06 §12) |
| Presentation Screens | 11 (UI/UX §4.6, §4.7, §10) |
| Engine modules | 11 (`states`, `gates`, `stages`, `verification`, `approval`, `notification`, `escalation`, `handoff`, `exceptions`, `recovery`, `orchestration`) |
| Phase 3 tests | 53 (engine) + 4 (routes) = 57 |
| Total tests (P1 + P2 + P3) | 124 (all green) |

---

## How to run

```bash
# Run the test suite (124 tests, ~5 minutes)
pytest

# Run only Phase 3 tests
pytest tests/test_phase3.py tests/test_phase3_routes.py -v
```

---

## Acceptance criteria coverage

| ID | Status | Test |
|---|---|---|
| AC-P3-001 Workflow can be initiated, executed, transitioned, closed | ✅ | `test_ac_p3_001_workflow_initiated_executed_transitioned_closed` |
| AC-P3-002 Every Decision Gate enforces its conditions (9 gates, bypass REJECTED) | ✅ | `test_ac_p3_002_nine_gates_registered` + `test_ac_p3_002_every_gate_bypass_rejected[EVIDENCE..CLOSURE]` |
| AC-P3-003 Orchestration State Machine enforces allowed/forbidden | ✅ | `test_ac_p3_003_ten_states_implemented` + `test_ac_p3_003_forbidden_transition_rejected` + `test_ac_p3_003_allowed_transitions_match_doc` |
| AC-P3-004 Producer ≠ Verifier (REJECT same role) | ✅ | `test_ac_p3_004_producer_not_equal_to_verifier_rejected` + `test_producer_equals_verifier_rejected_with_each_role` |
| AC-P3-005 Approval routed to Required Approver Role; decision recorded | ✅ | `test_ac_p3_005_approval_routed_to_required_approver` |
| AC-P3-006 Notification: created, delivered, acknowledged | ✅ | `test_ac_p3_006_notification_create_deliver_acknowledge` + `test_ac_p3_006_six_categories_five_channels_priority_order` + `test_ac_p3_006_suppression_of_class_3_or_4_forbidden` + `test_ac_p3_006_sms_reserved_for_class_3_4` |
| AC-P3-007 Independence of Verification preserved | ✅ | `test_ac_p3_007_independence_preserved_throughout_workflow` |
| AC-P3-008 Human Approval Gate cannot be bypassed (silence/urgency/prior/AI) | ✅ | `test_ac_p3_008_human_approval_gate_not_bypassable` + 4 individual signal tests |
| Discovery Order cannot be skipped / abbreviated / reordered | ✅ | `test_discovery_order_cannot_be_skipped` + `test_discovery_order_cannot_be_reordered` + `test_discovery_order_cannot_be_abbreviated` |
| AC-VER-001 Five Verifier Roles implemented | ✅ | `test_ac_ver_001_five_verifier_roles_implemented` |
| AC-VER-002 Producer-Verifier separation | ✅ | `test_ac_ver_002_producer_verifier_separation` |
| AC-VER-003 Second Reviewer required for IFV on material claim | ✅ | `test_ac_ver_003_second_reviewer_required_for_independent_final` |
| AC-VER-004 Claim Classification (5 categories) | ✅ | `test_ac_ver_004_claim_classification_enum` |
| AC-VER-005 Verification outcomes (4 outcomes) | ✅ | `test_ac_ver_005_verification_outcomes_recorded` |
| AC-APR-001 Silence is not approval (5 signals REJECTED) | ✅ | `test_ac_apr_001_silence_is_not_approval` |
| AC-APR-002 Self-Approval Prohibited | ✅ | `test_ac_apr_002_self_approval_prohibited` |
| AC-APR-003 Conditional Approval requires terms | ✅ | `test_ac_apr_003_conditional_approval_requires_terms` |
| AC-APR-004 Approval Revocation | ✅ | `test_ac_apr_004_approval_revocation` |
| AC-APR-005 Decision Audit Trail | ✅ | `test_ac_apr_005_decision_audit_trail` |
| AC-APR-006 4 Decision Classes | ✅ | `test_ac_apr_006_four_decision_classes` |
| Standing Authorisations prohibited categories | ✅ | `test_ac_apr_standing_authorisation_prohibited_categories` |
| 6 Escalation Channels | ✅ | `test_escalation_six_channels` |
| Unacknowledged escalation promotes | ✅ | `test_escalation_unacknowledged_promotes` |
| Handoff Initiation / Acceptance / Audit | ✅ | `test_handoff_initiation_acceptance_audit` |
| Handoff Rejected on missing criteria | ✅ | `test_handoff_rejected_when_criteria_missing` |
| 9 Exception Scenarios registered | ✅ | `test_exception_engine_nine_scenarios` |
| Rollback requires Human Approval | ✅ | `test_recovery_rollback_requires_approval` |
| Resume Class 3/4 requires Human Approval | ✅ | `test_recovery_resume_class_3_or_4_requires_approval` |
| 11 Phase 3 routes registered + render | ✅ | `tests/test_phase3_routes.py` (4 tests) |

---

## Constitutional notes

- **Article VIII — Constitutional Registers.** Untouched. The 3
  Registers are still independent base tables (Phase 2).
- **Article XII — Authority Hierarchy.** Enforced at the
  Approval Engine: Required Approver Role resolution per §3,
  Self-Approval Prohibited per §8.2, Silence ≠ Approval per
  Article XII paragraph 7.
- **Article XVII — Separation of Duties.** SoD check in
  `access.py` (Phase 1) + SoD checks in `approval.py` (Phase 3).
- **Article XIX — Decision Status.** The 3 Status dimensions
  are independent writeable columns (Phase 2). The
  Orchestration State Machine is independent of the 3 Status
  dimensions (STATE-G-004, Document 06 §8.2).
- **Article XX — No Silent Amendment.** Triggers on 94
  constitutional tables (Phase 2). The Phase 3 engine layer is
  pure logic; the service layer will write to the audit log
  via the existing append-only API.
- **Article XXVIII — Document Hierarchy.** No governing
  document modified. The Constitution remains as approved in
  v2.3.

---

## What was NOT delivered (and why)

- **The Service Layer (DB persistence for the engines)** — the
  engines are pure logic; the persistence layer (loading
  ApprovalRequest from DB, writing ApprovalDecision, writing
  Notification to the audit log, etc.) is the next layer in
  Phase 4. The constitutional entities exist in Phase 2.
- **Stage 1-24 service implementations** — the entities
  exist (Phase 2); the services that EXECUTE each stage
  (IndustrialEnvironmentMonitorAgent, etc.) are Phase 4+ per
  AI-IMPL-SEQ. Phase 3 implements the workflow ENGINE; Phase 4
  implements the agents.
- **Reporting Engine (BE-IMPL-009)** — Phase 7.
- **Risk and Compliance Engine (BE-IMPL-009+)** — Phase 7.
- **The Second Reviewer UI** — the engine is implemented and
  tested; the screen is deferred to Phase 4.
- **Cross-Office Conflict Resolution orchestration (Interaction
  Matrix Section 6)** — the underlying state machine and the
  5 conflict categories are referenced in the Exception Engine;
  the resolution orchestration is Phase 4+.
- **Bottleneck detection, SLA monitoring** — Phase 7.
- **Performance SLAs** — Phase 7.

---

## Open items for Phase 4 readiness

1. **HD-PHASE3-001** — Acceptance of Phase 3 completion
   (Implementation Lead + Constitutional Compliance).
2. **HD-PHASE3-002** — Acknowledgement that the 11 Phase 1+2
   Temporary Technical Assumptions remain in force through
   Phase 8 (or earlier permanent decision).
3. **GAP-PHASE3-001 (new)** — The engines are pure logic. The
   service layer that persists engine state to the DB and
   wires them to the data layer (Phase 2 entities) is the
   next step. The persistence layer is **not** blocking the
   Phase 3 acceptance — the engine is testable and the
   entities are queryable — but it is the deliverable that
   turns the foundation into a runnable system. Deferred to
   Phase 4.
4. **GAP-PHASE3-002 (new)** — The "Not Applicable" /
   "Replaced by an Equivalent Control" path (ORCH-COND-001..003)
   is documented but not yet exposed in the engine. The 9
   Exception Scenarios cover the operational case; the
   constitutional omission path requires a Decision Log Entry
   plus an equivalent control. Deferred to Phase 4.
5. **GAP-PHASE3-003 (new)** — The Decision Log Entry / Handoff
   Log Entry / Escalation Log Entry entities exist in Phase 2
   (`decision_log_entry`, `handoff_log_entry`, `escalation_log_entry`),
   but the engine layer does not yet write to them via the
   service layer. Deferred to Phase 4 (service-layer wiring).
6. **GAP-PHASE1-001..005** — Still open, no new material from
   Phase 3.

---

*End of Phase 3 Summary.*
