# Constitutional Traceability

**Project:** Techno Service AI Intelligence System
**Phase:** 2 — Data Foundation (current phase)

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
| Document 04 §1.7 — Independence of Audit Service | `audit.record` is the only path to the audit_log table; the trigger makes any direct write fail. |
| Document 05 §2.3 — Canonical Entity attributes (canonical_id, version) | `constitutional.py:ConstitutionalMixin`; verified in `test_ac_p2_002_canonical_entity_crud_versioned` |
| Document 05 §3 — Migration framework (forward-only, versioned, reproducible, auditable) | `migrations.py`; verified in `test_ac_p2_006_*` |
| Document 05 DB-PRIN-014 — Three Status dimensions are independent columns | `phase2_schema.py:Opportunity`; verified in `test_ac_p2_003_*` |
| Document 05 DB-PRIN-018 — No-Silent-Amendment enforced at DB layer | `db.py:install_constitutional_triggers`; verified in `test_ac_p2_005_*` |
| Document 07 §1, §12 — Mobile First | `static/styles.css` is mobile-first; breakpoints at 600/900/1400 px. |

---

*End of Constitutional Traceability — Phase 2.*
