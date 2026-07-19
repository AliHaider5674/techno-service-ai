# Bug Audit Log

**Date:** 2026-07-19
**Sprint:** Arabic i18n (lite) + Bug Audit
**Scope:** P0 (constitutional violations, broken flows) and P1 (incorrect behaviour).
**Out of scope:** P2 (polish, cosmetic, refactoring).

---

## Summary

| Priority | Found | Fixed | Remaining |
|---|---|---|---|
| **P0** (constitutional violation, broken flow) | 2 | 2 | 0 |
| **P1** (incorrect behaviour) | 1 | 1 | 0 |
| **P2** (polish, cosmetic) | 2 | 0 | 2 (listed for later) |

**P0 + P1 = 0 remaining. Done Criteria 6 ✅.**

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
- **Status:** OPEN (not fixed in this sprint).
- **Description:** When an authenticated user visits `/sign-in`
  with a language cookie set, they are redirected to `/home`.
  The Arabic text on `/sign-in` is therefore not testable
  without first clearing the session cookie.
- **Why deferred:** This is a UX nit, not a bug. Users who are
  signed in don't need to see the sign-in form in any language.
  The 8 constitutional-critical screens are still all rendered
  in AR when tested with a fresh session.

## P2-002 — Phase 7 templates (`base.html`, `phase7/base.html`) have hardcoded English

- **Date:** 2026-07-19
- **Priority:** P2 (out of sprint scope; 8 critical screens do
  not include Phase 7 dashboards).
- **Status:** OPEN (listed for a future i18n sprint).
- **Description:** The Phase 7 dashboard templates
  (`base.html`, `phase7/base.html`) still have hardcoded
  English. The Phase 9 templates were externalised in this
  sprint. A future sprint can extend i18n to Phase 7.
- **Why deferred:** The 8 critical screens specified in the
  Done Criteria are all externalised. Phase 7 dashboards are
  the next priority but are out of this sprint's scope.

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
