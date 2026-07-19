# Maintenance Phase

**Project:** Techno Service AI Intelligence System
**Document Reference:** TS-AI-MNT-001
**Governing Authority:** Constitution v2.3

This document defines the **Maintenance Phase** that begins
on Production Launch and continues indefinitely. The
Maintenance Phase is governed by the Document Hierarchy and
Change Control (Constitution Article XXIX) and by the
Continuous Learning workflow (Phase 7 §4.17).

---

## 1. Scope

The Maintenance Phase covers:

- **Operational monitoring** of all 17 Offices.
- **Change Control** of all Lower Documents (Document 02..08
  and any Standard, Procedure, Configuration, Prompt,
  Architecture, Design, Workflow, Operations document).
- **Constitutional Incident handling** (CRITICAL → Human
  escalation).
- **Continuous Learning** (S24) — Constitutional Impact
  Review of every Learning proposal.
- **Performance monitoring** against the constitutional
  performance SLAs (Schedule A Item 15).
- **Risk register maintenance** (Phase 7 §4.11).
- **Security posture maintenance** (Phase 7 §4.12; Document
  04 §1.7).

## 2. Change Control (Article XXIX)

Per Article XXIX, every amendment to a Lower Document is:

1. **Proposed** by an Office Lead (or a Constitutional Owner
   for amendments to the Constitution itself).
2. **Constitutional Impact Reviewed** by the Constitutional
   Compliance Coordination Agent.
3. **Approved** by the Required Approver Role (per Authority
   Matrix §3.4):
   - **Class 4** for amendments to the Constitution or
     Schedule A items.
   - **Class 3** for amendments to Document 02, 02A, 03, 04,
     05, 06, 07, 08.
   - **Class 2** for amendments to a Standard, Procedure,
     Configuration, or Workflow document.
   - **Class 1** for amendments to a Prompt, Template, or
     Operations document.
4. **Recorded** in the Decision Log with the amendment
   rationale, the Required Approver Role, and the approval
   reference.
5. **Applied** through the migration framework (for schema
   changes) or the document-hierarchy register (for Lower
   Document changes).

## 3. Continuous Learning (S24)

Every Continuous Learning proposal (`LearningUpdateProposal`)
is reviewed by `ContinuousLearningEngine` per the 4-step
path:

1. **Scope validation** — must be `SYSTEM_TUNING`,
   `POLICY_REFINEMENT`, `KNOWLEDGE_UPDATE`, or
   `CONSTITUTIONAL_AMENDMENT`.
2. **Reversibility check** — irreversible proposals are
   REJECTED.
3. **Constitutional Impact Review** — proposals affecting
   any of the 12 invariable constitutional clauses are
   REJECTED.
4. **Human Approval gate** — `CONSTITUTIONAL_AMENDMENT`
   proposals REJECT without a Human Approval reference.

The 5 outcomes are: `APPROVED`,
`REJECTED_CONSTITUTIONAL_IMPACT`, `REJECTED_IRREVERSIBLE`,
`REJECTED_MISSING_APPROVAL`, `REJECTED_INVALID_SCOPE`.

## 4. Performance monitoring

Per the constitutional performance SLAs (Schedule A Item 15
— Pending Lower Document), the Performance and Learning
Office (§4.17) measures and reports:

- **Dashboard response time** (target: TTA ceiling; production
  SLO from Schedule A Item 15).
- **Throughput** (Opportunities processed per day).
- **Concurrency** (active users / active workflows).
- **Mobile response time** (Phase 7 dashboards on mobile).
- **Audit log write rate** (audit entries per day).
- **Constitutional Incident rate** (CRITICAL incidents per
  week).
- **SLA breach rate** (Phase 7 SLA Monitor).

The Performance Reports are produced monthly (and on demand).

## 5. Security posture

- **2FA** (TOTP) — new users are required to enrol at first
  sign-in. Lost device → recovery flow (Constitution Article
  XXV + Document 04).
- **Vulnerability scan** — quarterly.
- **Penetration test** — annually.
- **Audit log review** — weekly by the Auditor role
  (ADMIN / COMPLIANCE / AUDITOR).
- **Access review** — quarterly. SoD violations must be
  remediated within 30 days.

## 6. Risk register maintenance

The Risk and Compliance Office (§4.11) maintains the
`EnterpriseRisk` table. Material risks are reviewed monthly.
New risks are added on identification. Closed risks are
recorded with a closure rationale (no silent deletion).

## 7. Constitutional Incident handling

The Constitutional Incident Investigator Agent (§4.11)
records every Constitutional Incident. CRITICAL incidents
escalate to Human (Constitution Article XX paragraph 7) and
require a `reporter_id` (no anonymous incidents). The
remediation plan is recorded and audited.

## 8. Knowledge and Institutional Memory

The Knowledge and Institutional Memory Office (§4.13)
maintains the Knowledge Base, the Institutional Memory
Index, and the Lessons Learned Index. Silent deletion is
PROHIBITED (Constitution Article XX §6). Deletions require
Human Approval (Class 3) and are recorded as a new
`InstitutionalMemoryDeletion` record (Constitutional
Article XX §6 enforcement).

---

*End of Maintenance Phase.*
