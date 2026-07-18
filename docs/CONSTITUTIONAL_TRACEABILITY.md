# Constitutional Traceability — Phase 1

**Project:** Techno Service AI Intelligence System
**Phase:** 1 — Identity, Access, and Audit Foundation

This matrix is the bidirectional trace between the Phase 1 implementation
artefacts and the constitutional clauses / Lower Documents that authorise
them. Every row is a Phase 1 item; every column is the constitutional
source that authorises it.

---

## A. Implementation items → constitutional source

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

## B. Constitutional clauses → implementation evidence

| Clause | Test file(s) proving compliance |
|---|---|
| Article XVII — SoD (rules 1, 3) | `test_article_xvii_and_xx.py:test_article_xvii_sod_*` |
| Article XX §6 — No Silent Amendment | `test_article_xvii_and_xx.py:test_article_xx_audit_log_table_has_no_update_trigger`, `test_article_xx_audit_log_table_has_no_delete_trigger`, `test_article_xx_user_records_carry_version_for_audit_trail` |
| Article XX — Audit completeness | `test_ac_aud_001_to_005.py:test_ac_aud_001_*` |
| Article XX — Audit immutability | `test_ac_aud_001_to_005.py:test_ac_aud_002_*` |
| Article XX — Audit exportability | `test_ac_aud_001_to_005.py:test_ac_aud_003_*` |
| Article XX — Audit queryability | `test_ac_aud_001_to_005.py:test_ac_aud_004_*` |
| Article XX — Audit retention | `test_ac_aud_001_to_005.py:test_ac_aud_005_*` |
| Article XXV — Security (auth + access control) | `test_ac_sec_001_to_005.py` |
| Article XXVIII — Document Hierarchy (no overrides) | `docs/DECISION_AND_ASSUMPTION_REGISTER.md` + `docs/IMPLEMENTATION_GAP_REGISTER.md` (no rule changed) |
| AC-P1-001 Sign in / out / recover | `test_ac_p1_001_sign_in_out_recover.py` |
| AC-P1-002 Persona selection | `test_ac_p1_002_persona.py` |
| AC-P1-003 Admin user/role/policy management | `test_ac_p1_003_admin_manage.py` |
| AC-P1-004 Audit log queryable, complete, immutable, exportable | `test_ac_p1_004_audit.py` |
| Document 04 §1.7 — Independence of Audit Service | `audit.record` is the only path to the audit_log table; the trigger makes any direct write fail. |
| Document 07 §1, §12 — Mobile First | `static/styles.css` is mobile-first; breakpoints at 600/900/1400 px. |

---

*End of Constitutional Traceability — Phase 1.*
