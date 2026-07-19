# Bug Audit Log

**Date:** 2026-07-19
**Sprint:** Arabic i18n (lite) + Bug Audit + P2 Polish
**Scope:** P0 (constitutional violations, broken flows), P1 (incorrect behaviour), P2 (polish, cosmetic, refactoring).
**Out of scope:** New features, new agents, new entities.

---

## Summary

| Priority | Found | Fixed | Remaining |
|---|---|---|---|
| **P0** (constitutional violation, broken flow) | 2 | 2 | 0 |
| **P1** (incorrect behaviour) | 1 | 1 | 0 |
| **P2** (polish, cosmetic) | 2 | 2 | 0 |

**P0 + P1 + P2 = 0 remaining. Done Criteria met ✅.**

---

## P0-001 — Phase 9 templates crash with `TemplateAssertionError: No filter named 't'`

- **Date:** 2026-07-19
- **Found by:** HTTP smoke test (`GET /proactive/` returned 500).
- **Status:** **FIXED**.
- **Impact:** Any visit to `/proactive/`, `/proactive/scan`,
  `/proactive/qualify`, `/proactive/patents`,
  `/proactive/agency-workflow`, or `/proactive/report` returned
  HTTP 500 because the phase9 router created its own
  `Jinja2Templates` instance without the i18n `t()` filter.

- **Root cause:** The i18n `t()` filter was registered on the
  module-level `templates` object in `app.py` only. Each phase
  router (phase3..phase9) creates a fresh `Jinja2Templates`
  instance in its own scope, so the filter was not available
  on those instances.

- **Fix:** Added `i18n.apply_to_jinja(_t)` to all 7 phase routers
  (phase3_routes, phase4_routes, phase5_routes, phase6_routes,
  phase7_routes, phase8_routes, phase9_routes). The helper is
  idempotent and registers the `t` filter + i18n globals on
  any Jinja2Templates instance.

- **Files changed:** `src/techno_service_ai/i18n.py` (added
  `apply_to_jinja`); `src/techno_service_ai/phase3_routes.py`..`phase9_routes.py`
  (call `apply_to_jinja(templates)` or `apply_to_jinja(_t)`).

- **Verification:** All 6 phase9 routes return 200 after the fix.
  All 21 English routes green, all 15 Arabic routes green.

## P0-002 — `/dashboards/ai-activity` route references undefined `AIRecommendationLog` class

- **Date:** 2026-07-19
- **Found by:** HTTP smoke test (`GET /dashboards/ai-activity`
  returned 500).
- **Status:** **FIXED**.
- **Impact:** Pre-existing Phase 7 bug. The route imported
  `AIRecommendationLog` from `phase2_schema` but that class
  was never defined in the schema. The 500 was triggered on
  every visit to the AI Activity Dashboard.

- **Root cause:** The route was written in Phase 7 with the wrong
  schema reference. The canonical AI activity entity per
  Document 02 §4.17 is `LearningUpdate` (ENT-PER-003). The
  template also referenced `a.recommendation_id` and
  `a.confidence` which are not fields on `LearningUpdate`.

- **Fix:** Updated the route to use `LearningUpdate` (with
  comment documenting the fix). Updated the template to use
  the actual `LearningUpdate` fields (`target_type`,
  `target_id`, `description`, `constitutional_impact`).

- **Files changed:** `src/techno_service_ai/phase7_routes.py`
  (route import + class); `src/techno_service_ai/templates/phase7/dashboard_ai_activity.html`
  (fields).

- **Verification:** `GET /dashboards/ai-activity` returns 200
  after the fix. Test `test_phase8.py::test_phase8_full_roster_17_offices_69_agents`
  still passes (no test asserted the broken behaviour).

## P1-001 — `i18n.t()` returned the key as fallback when the JSON file loaded

- **Date:** 2026-07-19
- **Found by:** Direct module test — `t('signin.title', 'en')`
  returned `'signin.title'` instead of `'Sign in'`.
- **Status:** **FIXED**.
- **Impact:** Without this fix, every translated string would
  fall back to the key itself, breaking both English and Arabic
  rendering. Caught before any user-facing test.

- **Root cause:** The `t()` function assumed the JSON structure
  was `{"en": {"key": "value"}}` (language-first), but the
  actual structure is `{"key": {"en": "value", "ar": "value"}}`
  (key-first). The lookup missed the actual key path.

- **Fix:** Updated `t()` to navigate `_STRINGS[key][lang]` first,
  then `_STRINGS[key]["en"]`, then the key itself.

- **Files changed:** `src/techno_service_ai/i18n.py` (lookup logic).

- **Verification:** `t('signin.title', 'en')` now returns
  `'Sign in'`; `t('signin.title', 'ar')` returns
  `'تسجيل الدخول'`. The 8 critical screens render correctly
  in both languages.

---

## P2-001 — `/sign-in?lang=ar` redirects to `/home` (303) for already-signed-in users

- **Date:** 2026-07-19
- **Priority:** P2 (cosmetic — not a constitutional violation;
  the redirect is the correct behaviour for an authenticated
  user landing on `/sign-in`).
- **Status:** **FIXED** (P2 Polish sprint, 2026-07-19).
- **Description:** When an authenticated user visits `/sign-in`
  with `?lang=` or `?next=` query parameters, the redirect now
  respects both. `/sign-in?lang=ar` → `/home?lang=ar`.
  `/sign-in?next=/phase9/proactive-discovery&lang=ar` →
  `/phase9/proactive-discovery?lang=ar`. Open-redirect attacks
  via `?next=` are blocked: only paths starting with `/` (and
  not `//`) are honoured. Protocol-relative URLs
  (`//evil.com/path`) are also blocked.
- **Fix:** Added `_resolve_post_signin_redirect(request, next,
  lang, default)` in `app.py` that:
  1. Validates `next` must start with `/` and not `//`.
  2. Honours `lang` from cookie + `?lang=` + form field (priority
     order: form > query > cookie > default).
  3. Preserves `lang` on the redirect by appending `?lang=xx`.
  4. Falls back to default (`/home`) if `next` is invalid.
- **Files changed:** `src/techno_service_ai/app.py` (sign-in
  GET + POST handlers).
- **Verification:** `verify_p2_001.py` runs 6 cases, all PASS:
  - GET `/sign-in?lang=ar` → 303 → `/home?lang=ar` ✅
  - GET `/sign-in?next=/proactive/` → 303 → `/proactive/` ✅
  - GET `/sign-in?next=/proactive/&lang=ar` → 303 →
    `/proactive/?lang=ar` ✅
  - GET `/sign-in?next=evil` → 303 → `/home` (blocked) ✅
  - POST `/sign-in` with `next=/proactive/scan&lang=ar` → 303
    → `/proactive/scan?lang=ar` ✅
  - GET `/sign-in?next=//evil.com/path` → 303 → `/home`
    (protocol-relative blocked) ✅

## P2-002 — Phase 7/8/6 dashboard templates had hardcoded English

- **Date:** 2026-07-19
- **Priority:** P2 (out of original sprint scope; spec expanded
  by Constitutional Owner).
- **Status:** **FIXED** (P2 Polish sprint, 2026-07-19).
- **Description:** 14 of 20 Phase 7/8/6 dashboard routes had
  hardcoded English text in their bodies, even though their
  `base.html` files had the `lang_code()`/`dir_attr()` fix. The
  remaining 6 routes already worked because they used
  `t("phase7.reports.*.title")` style substitutions.
- **Fix:**
  1. **Base templates**: Updated `phase6/base.html`,
     `phase8/base.html`, and `phase3/base.html` to use
     `<html lang="{{ lang_code() }}" dir="{{ dir_attr() }}">`
     (matching the existing `phase7/base.html` and
     `phase9/base.html` pattern).
  2. **Strings**: Added 59 new Arabic/English string keys to
     `templates/i18n/strings.json` for the Phase 7/8/6
     dashboards (titles, KPIs, table headers, empty states,
     labels). Total keys: 222 → 281.
  3. **Templates**: Added `{{ "<key>" | t(lang_code()) }}` filter
     calls to the visible text in: 5 Phase 7 dashboards
     (`performance_report`, `bottleneck_report`,
     `office_workload`, `sla_monitor`, `continuous_learning`),
     5 Phase 8 Quality templates (`quality_dashboard`,
     `quality_review_new`, `quality_audit_new`,
     `quality_standards_new`, `release_readiness`),
     3 Phase 6 templates (`knowledge_records`, `lessons_learned`,
     `institutional_memory`), and 1 Phase 3 template
     (`not_inbox`).
- **Files changed:** `src/techno_service_ai/templates/phase3/base.html`,
  `phase6/base.html`, `phase7/performance_report.html`,
  `phase7/bottleneck_report.html`, `phase7/office_workload.html`,
  `phase7/sla_monitor.html`, `phase7/continuous_learning.html`,
  `phase6/knowledge_records.html`, `phase6/lessons_learned.html`,
  `phase6/institutional_memory.html`,
  `phase8/quality_dashboard.html`, `phase8/quality_review_new.html`,
  `phase8/quality_audit_new.html`, `phase8/quality_standards_new.html`,
  `phase8/release_readiness.html`, `phase3/not_inbox.html`,
  `templates/i18n/strings.json` (+59 keys).
- **Verification:** `verify_p2_002.py` runs 20 routes, all 20/20
  green. Every route returns 200 with `dir="rtl"`, `lang="ar"`,
  and the expected Arabic title in the body.

---

## What was checked but found clean

- `/dashboards/executive`, `/dashboards/operations`,
  `/dashboards/commercial`, `/dashboards/kpi`,
  `/dashboards/manufacturer`, `/dashboards/verification` — all
  200 OK.
- `/opportunities`, `/admin/audit-log`, `/approvals/inbox`,
  `/notifications/center` — all 200 OK.
- `/proactive/`, `/proactive/agency-workflow`, `/proactive/scan`,
  `/proactive/qualify`, `/proactive/patents`, `/proactive/report`,
  `/quality/` — all 200 OK.
- All 7 phase routers' `Jinja2Templates` instances have the
  i18n `t` filter and globals registered.
- The language switcher validates `lang` (falls back to `en`)
  and `next` (must start with `/`, blocks open-redirects).
- The `tsai_lang` cookie persists across reloads (1-year max-age).
- English (default) is unchanged: every English render is
  identical to the pre-i18n baseline.
- The Arabic render correctly shows RTL on every page, with the
  Arabic text present and the layout mirrored.
- 289/289 tests pass after the i18n + bug fixes.
