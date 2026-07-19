# Constitutional Traceability

**Project:** Techno Service AI Intelligence System
**Phase:** 5 — Manufacturer, Commercial, and Registration Offices (current phase)

This matrix is the bidirectional trace between the implementation
artefacts (Phase 1 + Phase 2) and the constitutional clauses / Lower
Documents that authorise them. Every row is an implementation item; every
column is the constitutional source that authorises it.

---

## A. Implementation items → constitutional source

### Phase 1 (carried forward)

| Backlog ID | Title | Constitutional / Lower Document clause | Code location |
|---|---|---|---|
| IMPL-P1-001 | Identity Service | Document 04 §1.2 Layered Architecture; Implementer README §6 | `src/techno_service_ai/auth.py` |
| IMPL-P1-002 | Authentication | Constitution Article XXV §4 (Security); Document 04 §1.7 Security Layer | `src/techno_service_ai/auth.py:sign_in / sign_out / recover / change_password` |
| IMPL-P1-003 | Session Management | Constitution Article XXV §4; Document 04 §1.7 | `src/techno_service_ai/schema.py:UserSession` + `auth.validate_session` |
| IMPL-P1-004 | Persona Selection | Constitution Article XII §3 (Class 1); Document 02 §6.2; Document 07 §2 | `src/techno_service_ai/personas.py` + `templates/persona_select.html` |
| IMPL-P1-005 | Account & Security Settings | Document 04 §1.2; Document 07 §4.1 | `templates/account_security.html` + `auth.change_password` |
| IMPL-P1-006 | Access Policy Service | Constitution Article XII (Authority Hierarchy); Authority Matrix; Document 04 §1.7 | `src/techno_service_ai/access.py` |
| IMPL-P1-007 | Role Assignment | Constitution Article XIV (AI Organization); Document 02 §5.1 | `access.assign_role` / `revoke_role` |
| IMPL-P1-008 | Access Enforcement | Constitution Article XII (Decision Classes); Authority Matrix | `src/techno_service_ai/deps.py:require_any_role` |
| IMPL-P1-009 | Separation of Duties | Constitution Article XVII (full) | `access.SoDViolation` + `assert_no_sod_conflict_for_new_role`; tested in `test_article_xvii_and_xx.py` |
| IMPL-P1-010 | User entity | Document 05 §3 Information Domain 2 (Identity and Access) | `schema.User` |
| IMPL-P1-011 | Role entity | Document 05 §3 Information Domain 2 | `schema.Role` + `UserRole` + `Persona` |
| IMPL-P1-012 | Audit Service | Constitution Article XX (Institutional Memory); Article XXVII (Compliance Review) | `src/techno_service_ai/audit.py` |
| IMPL-P1-013 | Audit Log entity (immutable) | Constitution Article XX §6 (No Silent Amendment); Document 05 §3 Information Domain 3 | `schema.AuditLog` + triggers in `db.apply_schema` |
| IMPL-P1-014 | 11 screens | Document 07 §4.1 (Identity and Access) + §4.12 (Administration) + §4.13 (Audit) | `templates/` directory |

### Phase 2 (new)

| Backlog ID | Title | Constitutional / Lower Document clause | Code location |
|---|---|---|---|
| IMPL-P2-001 | ConstitutionalMixin + base entity pattern | Document 05 §2.3 (Canonical Entity Attributes); Article XX §6 (No Silent Amendment) | `src/techno_service_ai/constitutional.py:ConstitutionalMixin` |
| IMPL-P2-002 | Three Status dimensions as independent columns | Constitution Article XIX (Decision Status); Document 05 §2.4 + DB-PRIN-014 | `phase2_schema.py:Opportunity`, `ComparativeAnalysis` (3 columns each) |
| IMPL-P2-003 | Three Constitutional Registers as independent tables | Constitution Article VIII (Constitutional Registers); Document 05 §3 Domain 22 (Registers) | `phase2_schema.py:RepresentedPrincipal`, `ConflictDoNotPursueEntity`, `RestrictedProhibitedEntity` |
| IMPL-P2-004 | No-Silent-Amendment triggers on 94 constitutional tables | Constitution Article XX §6; Document 05 DB-PRIN-018; AC-P2-005 | `db.py:install_constitutional_triggers` |
| IMPL-P2-005 | Forward-only, versioned, reproducible, auditable migration framework | Document 05 §3 (Migration Framework); AC-P2-006 | `src/techno_service_ai/migrations.py` |
| IMPL-P2-006 | 20 Information Domains, 87 canonical entities | Document 05 §3 (all 20 Information Domains) | `src/techno_service_ai/phase2_schema.py` |
| IMPL-P2-007 | `Migration` ORM model in `Base.metadata` (operational) | Document 05 §3; AC-P2-006 reproducibility | `schema.py:Migration` |
| IMPL-P2-008 | Bootstrap calls `apply_all()` after `apply_schema()` | Document 05 §3 (Migrations are part of bootstrap) | `bootstrap.py:seed` |
| IMPL-P2-009 | Test suite for AC-P2-001..006 + AC-DL-001..005 | Document 06 (Acceptance Criteria); Document 05 §4 | `tests/test_phase2.py` |

### Phase 3 (new)

| Backlog ID | Title | Constitutional / Lower Document clause | Code location |
|---|---|---|---|
| IMPL-P3-001 | Orchestration State Machine (10 states) | Document 06 §8 (STATE-001..010); Article XVIII, XIX, XX | `src/techno_service_ai/states.py` |
| IMPL-P3-002 | 9 Decision Gates (non-bypassable) | Document 06 §4.1..4.9 (GATE-EV/VE/QA/HA/CO/RG/TN/PJ/CL-001..006) | `src/techno_service_ai/gates.py` |
| IMPL-P3-003 | 24 Stages of the Discovery Order | Document 06 §2.1..2.24 (ORCH-SEQ-002) | `src/techno_service_ai/stages.py` |
| IMPL-P3-004 | Verification Engine (5 agents + Independence Tracker) | Document 06 §6 (VER-PRE/SPE/IFV/IND-001..003); Article XVII paragraph 2(1) | `src/techno_service_ai/verification.py` |
| IMPL-P3-005 | Approval Engine (4 classes, Required Approver, Conditional, Revocation, Silence != Approval) | Authority Matrix §1, §3, §5, §8, §9, §10; Article XII paragraph 7, Article XVII paragraph 2(15); GATE-HA-006; REQ-RULE-005 | `src/techno_service_ai/approval.py` |
| IMPL-P3-006 | Notification Engine (6 categories, 5 channels, priority) | Document 06 §9; UI/UX §10 NOT-001..005; Article XVII paragraph 7 | `src/techno_service_ai/notification.py` |
| IMPL-P3-007 | Escalation Engine (6 channels, unacknowledged promotion) | Document 06 §3.7 (ORCH-ESC-001..004); Interaction Matrix §7 | `src/techno_service_ai/escalation.py` |
| IMPL-P3-008 | Handoff Service (Initiation, Acceptance, Audit) | Interaction Matrix §4; Document 06 §9.1, §9.6 (COLLAB-OWN-001..003, COLLAB-HO-001..002) | `src/techno_service_ai/handoff.py` |
| IMPL-P3-009 | Exception Engine (9 scenarios) | Document 06 §7 (EXC-EV/DUP/CON/REG/COM/INC/AGT/HUM/EXT-001..003) | `src/techno_service_ai/exceptions.py` |
| IMPL-P3-010 | Recovery Engine (Interrupted, Restart, Resume, Rollback) | Document 06 §12 (REC-INT/RES/RESUME/ROLL/AUD-001..003); Article XXV | `src/techno_service_ai/recovery.py` |
| IMPL-P3-011 | Workflow Orchestrator (top-level engine) | Document 06 §3 (ORCH-SEQ-001..003, ORCH-ESC, ORCH-HUM); Article VI | `src/techno_service_ai/orchestration.py` |
| IMPL-P3-012 | 11 Presentation Screens | UI/UX §4.6, §4.7, §10 (SCR-VER-001..006, SCR-APR-001..004, NOT-003) | `src/techno_service_ai/phase3_routes.py` + `templates/phase3/*.html` |
| IMPL-P3-013 | Test suite for AC-P3-001..008, AC-VER-001..005, AC-APR-001..006 | Document 06 (Acceptance Criteria); Authority Matrix | `tests/test_phase3.py`, `tests/test_phase3_routes.py` |

## B. Constitutional clauses → implementation evidence

| Clause | Test file(s) proving compliance |
|---|---|
| Article VIII — Constitutional Registers (3, independent) | `test_phase2.py:test_ac_p2_004_three_registers_are_independent_tables`, `test_ac_dl_003_registers_are_independent_structures` |
| Article XVII — SoD (rules 1, 3) | `test_article_xvii_and_xx.py:test_article_xvii_sod_*` |
| Article XIX — Decision Status (3 independent dimensions) | `test_phase2.py:test_ac_p2_003_status_dimensions_are_independent_columns`, `test_ac_dl_002_status_columns_are_not_views_or_computed` |
| Article XX §6 — No Silent Amendment | `test_article_xvii_and_xx.py:test_article_xx_audit_log_table_has_no_update_trigger`, `test_article_xx_audit_log_table_has_no_delete_trigger`, `test_article_xx_user_records_carry_version_for_audit_trail` |
| Article XX §6 (extended) — No Silent Amendment on constitutional entities | `test_phase2.py:test_ac_p2_002_in_place_update_is_rejected`, `test_ac_p2_002_in_place_delete_is_rejected`, `test_ac_p2_005_silent_update_rejected`, `test_ac_p2_005_silent_delete_rejected` |
| Article XX — Audit completeness | `test_ac_aud_001_to_005.py:test_ac_aud_001_*` |
| Article XX — Audit immutability | `test_ac_aud_001_to_005.py:test_ac_aud_002_*` |
| Article XX — Audit exportability | `test_ac_aud_001_to_005.py:test_ac_aud_003_*` |
| Article XX — Audit queryability | `test_ac_aud_001_to_005.py:test_ac_aud_004_*` |
| Article XX — Audit retention | `test_ac_aud_001_to_005.py:test_ac_aud_005_*` |
| Article XX — Migration audit | `test_phase2.py:test_ac_p2_006_migration_audited` |
| Article XX — Institutional Memory preserves history | `test_phase2.py:test_ac_dl_004_institutional_memory_preserves_history` |
| Article XXV — Security (auth + access control) | `test_ac_sec_001_to_005.py` |
| Article XXVIII — Document Hierarchy (no overrides) | `docs/DECISION_AND_ASSUMPTION_REGISTER.md` + `docs/IMPLEMENTATION_GAP_REGISTER.md` (no rule changed) |
| AC-P1-001 Sign in / out / recover | `test_ac_p1_001_sign_in_out_recover.py` |
| AC-P1-002 Persona selection | `test_ac_p1_002_persona.py` |
| AC-P1-003 Admin user/role/policy management | `test_ac_p1_003_admin_manage.py` |
| AC-P1-004 Audit log queryable, complete, immutable, exportable | `test_ac_p1_004_audit.py` |
| AC-P2-001 All 20 Information Domains queryable | `test_phase2.py:test_ac_p2_001_all_20_domains_queryable` |
| AC-P2-002 Canonical Entity CRUD + versioned | `test_phase2.py:test_ac_p2_002_canonical_entity_crud_versioned` |
| AC-P2-003 Three Status dimensions independent | `test_phase2.py:test_ac_p2_003_status_dimensions_are_independent_columns` |
| AC-P2-004 Three Registers independent | `test_phase2.py:test_ac_p2_004_three_registers_are_independent_tables` |
| AC-P2-005 No-Silent-Amendment enforced (all constitutional) | `test_phase2.py:test_ac_p2_005_silent_update_rejected`, `test_ac_p2_005_silent_delete_rejected` |
| AC-P2-006 Migration apply → rollback → re-apply | `test_phase2.py:test_ac_p2_006_migration_apply_rollback_reapply` |
| AC-DL-001 Schema covers 70+ canonical entities (94 implemented) | `test_phase2.py:test_ac_dl_001_schema_covers_70_plus_canonical_entities` |
| AC-DL-002 Status columns are not views / computed | `test_phase2.py:test_ac_dl_002_status_columns_are_not_views_or_computed` |
| AC-DL-003 Registers are independent structures | `test_phase2.py:test_ac_dl_003_registers_are_independent_structures` |
| AC-DL-004 Institutional Memory preserves history | `test_phase2.py:test_ac_dl_004_institutional_memory_preserves_history` |
| AC-DL-005 (covered by AC-DL-004 — no silent erasure) | `test_phase2.py:test_ac_dl_004_institutional_memory_preserves_history` |
| AC-P3-001 Workflow can be initiated, executed, transitioned, closed | `test_phase3.py:test_ac_p3_001_workflow_initiated_executed_transitioned_closed` |
| AC-P3-002 Every Decision Gate enforces its conditions (9 gates, bypass REJECTED) | `test_phase3.py:test_ac_p3_002_nine_gates_registered` + parametrized `test_ac_p3_002_every_gate_bypass_rejected` |
| AC-P3-003 Orchestration State Machine enforces allowed/forbidden | `test_phase3.py:test_ac_p3_003_ten_states_implemented` + `_forbidden_transition_rejected` + `_allowed_transitions_match_doc` |
| AC-P3-004 Producer ≠ Verifier (REJECT same role) | `test_phase3.py:test_ac_p3_004_producer_not_equal_to_verifier_rejected` + `test_producer_equals_verifier_rejected_with_each_role` |
| AC-P3-005 Approval routed to Required Approver Role; decision recorded | `test_phase3.py:test_ac_p3_005_approval_routed_to_required_approver` |
| AC-P3-006 Notification: created, delivered, acknowledged | `test_phase3.py:test_ac_p3_006_notification_create_deliver_acknowledge` + `_six_categories_five_channels_priority_order` + `_suppression_of_class_3_or_4_forbidden` + `_sms_reserved_for_class_3_4` |
| AC-P3-007 Independence of Verification preserved | `test_phase3.py:test_ac_p3_007_independence_preserved_throughout_workflow` |
| AC-P3-008 Human Approval Gate cannot be bypassed | `test_phase3.py:test_ac_p3_008_human_approval_gate_not_bypassable` + 5 individual signal tests + 4 direct-bypass tests |
| AC-VER-001 Five Verifier Roles implemented | `test_phase3.py:test_ac_ver_001_five_verifier_roles_implemented` |
| AC-VER-002 Producer-Verifier separation | `test_phase3.py:test_ac_ver_002_producer_verifier_separation` |
| AC-VER-003 Second Reviewer required for IFV on material claim | `test_phase3.py:test_ac_ver_003_second_reviewer_required_for_independent_final` |
| AC-VER-004 Claim Classification (5 categories) | `test_phase3.py:test_ac_ver_004_claim_classification_enum` |
| AC-VER-005 Verification outcomes (4 outcomes) | `test_phase3.py:test_ac_ver_005_verification_outcomes_recorded` |
| AC-APR-001 Silence is not approval (5 signals REJECTED) | `test_phase3.py:test_ac_apr_001_silence_is_not_approval` |
| AC-APR-002 Self-Approval Prohibited | `test_phase3.py:test_ac_apr_002_self_approval_prohibited` |
| AC-APR-003 Conditional Approval requires terms | `test_phase3.py:test_ac_apr_003_conditional_approval_requires_terms` |
| AC-APR-004 Approval Revocation | `test_phase3.py:test_ac_apr_004_approval_revocation` |
| AC-APR-005 Decision Audit Trail | `test_phase3.py:test_ac_apr_005_decision_audit_trail` |
| AC-APR-006 4 Decision Classes | `test_phase3.py:test_ac_apr_006_four_decision_classes` |
| Discovery Order cannot be skipped / abbreviated / reordered | `test_phase3.py:test_discovery_order_cannot_be_skipped` + `_reordered` + `_abbreviated` |
| 6 Escalation Channels | `test_phase3.py:test_escalation_six_channels` |
| Unacknowledged escalation promotes | `test_phase3.py:test_escalation_unacknowledged_promotes` |
| Handoff Initiation / Acceptance / Audit | `test_phase3.py:test_handoff_initiation_acceptance_audit` |
| Handoff Rejected on missing criteria | `test_phase3.py:test_handoff_rejected_when_criteria_missing` |
| 9 Exception Scenarios registered | `test_phase3.py:test_exception_engine_nine_scenarios` |
| Rollback requires Human Approval (REC-ROLL-001) | `test_phase3.py:test_recovery_rollback_requires_approval` + `_rollback_with_approval_accepted` |
| Resume Class 3/4 requires Human Approval (REC-RESUME-003) | `test_phase3.py:test_recovery_resume_class_3_or_4_requires_approval` |
| 11 Phase 3 routes registered + render | `tests/test_phase3_routes.py` (4 tests) |
| Document 04 §1.7 — Independence of Audit Service | `audit.record` is the only path to the audit_log table; the trigger makes any direct write fail. |
| Document 05 §2.3 — Canonical Entity attributes (canonical_id, version) | `constitutional.py:ConstitutionalMixin`; verified in `test_ac_p2_002_canonical_entity_crud_versioned` |
| Document 05 §3 — Migration framework (forward-only, versioned, reproducible, auditable) | `migrations.py`; verified in `test_ac_p2_006_*` |
| Document 05 DB-PRIN-014 — Three Status dimensions are independent columns | `phase2_schema.py:Opportunity`; verified in `test_ac_p2_003_*` |
| Document 05 DB-PRIN-018 — No-Silent-Amendment enforced at DB layer | `db.py:install_constitutional_triggers`; verified in `test_ac_p2_005_*` |
| Document 06 §2 — 24 End-to-End Constitutional Workflow stages | `stages.py:STAGES`, `DISCOVERY_ORDER`; verified by `test_ac_p2_002` (entities) and `test_ac_p3_001` (24-stage run) |
| Document 06 §3.1 ORCH-SEQ-002..003 — Discovery Order enforcement | `stages.py:is_valid_progression`; verified by `test_discovery_order_cannot_be_skipped/_reordered/_abbreviated` |
| Document 06 §4 — 9 Decision Gates non-bypassable | `gates.py:GATES`, `GateEngine.bypass_attempt`; verified by parametrized test |
| Document 06 §5 — Human Approval Workflow | `approval.py:ApprovalEngine`; verified by `test_ac_p3_005`, `test_ac_apr_001..005` |
| Document 06 §6 — Verification Workflow + VER-IND-001..003 | `verification.py:IndependenceTracker`; verified by `test_ac_p3_004`, `test_ac_ver_*` |
| Document 06 §7 — 9 Exception Scenarios | `exceptions.py:ExceptionEngine`; verified by `test_exception_engine_nine_scenarios` |
| Document 06 §8 — Orchestration State Model | `states.py:ALLOWED_TRANSITIONS`, `StateMachine`; verified by `test_ac_p3_003_*` |
| Document 06 §9 — Notification Engine (6 categories, 5 channels) | `notification.py:NotificationEngine`; verified by `test_ac_p3_006_*` |
| Document 06 §12 — Recovery Model | `recovery.py:RecoveryEngine`; verified by `test_recovery_*` |
| Document 07 §1, §12 — Mobile First | `static/styles.css` is mobile-first; breakpoints at 600/900/1400 px. |
| Document 07 §4.6 — Verification Screens (SCR-VER-001..006) | `phase3_routes.py`; verified by `test_phase3_routes.py` |
| Document 07 §4.7 — Approval Screens (SCR-APR-001..004) | `phase3_routes.py`; verified by `test_phase3_routes.py` |
| Document 07 §10 — Notification Inbox (NOT-003) | `phase3_routes.py:notification_inbox`; verified by `test_phase3_routes.py` |

---

## C. Phase 5 — Manufacturer, Commercial, Registration Offices

| Clause / AC | Test file(s) proving compliance |
|---|---|
| Article VIII §2 — Represented Principal at Commercial Gate | `test_phase5.py:test_register_compliance_rejects_non_represented_at_commercial_gate`, `test_register_compliance_cleared_for_represented_principal` |
| Article VIII §3 — Conflict / Do-Not-Pursue rejected everywhere | `test_phase5.py:test_register_compliance_rejects_conflict_entity_everywhere` |
| Article VIII §4 — Restricted / Prohibited rejected everywhere | `test_phase5.py:test_register_compliance_rejects_restricted_entity_everywhere` |
| Article VIII — 3 Registers honored at every commercial gate (AC-P5-008) | `test_phase5.py:test_three_registers_honored_at_every_commercial_gate` |
| Document 02 §4.5.1 — Manufacturer Profiler (no representation status alone) | `test_phase5.py:test_kuwait_representation_status_derived_from_register` |
| Document 02 §4.5.2 — Credibility multi-dimensional (AC-P5-002) | `test_phase5.py:test_credibility_assessment_requires_all_six_dimensions` |
| Document 02 §4.5.3 — Comparison multi-criteria, no selection (AC-P5-001) | `test_phase5.py:test_manufacturer_comparison_requires_multi_criteria`, `test_manufacturer_comparison_prohibits_selection` |
| Document 02 §4.6.1 — Commercial Evaluation multi-dimensional + assumptions + uncertainty (AC-P5-004) | `test_phase5.py:test_commercial_evaluation_requires_seven_dimensions`, `test_commercial_evaluation_requires_assumptions`, `test_commercial_evaluation_requires_uncertainty` |
| Document 02 §4.6.3 — BD engagement requires Human Approval (AC-P5-005) | `test_phase5.py:test_bd_engagement_requires_human_approval` |
| Document 02 §4.6.3 — BD engagement requires register clearance (AC-P5-005) | `test_phase5.py:test_bd_engagement_requires_register_clearance` |
| Document 02 §4.6.5 — Pricing margin floor | `test_phase5.py:test_pricing_below_floor_requires_human_approval` |
| Document 02 §4.7.1 — Registration filing requires Human Approval (AC-P5-007) | `test_phase5.py:test_registration_filing_requires_human_approval` |
| Document 02 §4.7.2 — Prequalification submission requires Human Approval | `test_phase5.py:test_prequalification_submission_requires_human_approval` |
| Document 02 §4.7.3 — Market Entry multi-path, no selection | `test_phase5.py:test_market_entry_requires_two_path_options`, `test_market_entry_prohibits_path_selection` |
| Document 06 §3.1 — Discovery Order S11..S18 walked end-to-end | `test_phase5.py:test_discovery_order_walk_s11_to_s18_creates_real_records`, `test_discovery_order_skip_rejected_in_phase5` |
| 9 Principal Agents activated (3 Offices × 3 Agents) | `test_phase5.py:test_phase5_agent_roster_9_agents`, `test_phase5_three_offices_represented`, `test_phase5_agents_match_canonical_names` |
| 16 Phase 5 routes registered + render | `tests/test_phase5_routes.py` (3 tests) |
| Document 05 §3.9 — ENT-REG-004 MarketEntryOptions (Phase 5 schema addition) | `phase2_schema.py:MarketEntryOptionsReport`; `__constitutional__ = True`; BEFORE UPDATE/DELETE trigger auto-installed |

---

*End of Constitutional Traceability — Phase 5.*
