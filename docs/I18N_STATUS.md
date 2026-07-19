# i18n Status — Arabic (lite)

**Date:** 2026-07-19
**Sprint:** Arabic i18n (lite) + Bug Audit
**Scope:** 8 constitutional-critical screens
**Default language:** English (UNCHANGED; opt-in Arabic via language switcher)
**Constitutional status:** Constitution v2.3 + v2.4 UNCHANGED; i18n is a pure presentation surface

---

## 1. The 8 constitutional-critical screens

Per the 8-step demo path in `docs/QUICK_START.md` §3:

| # | Screen | Route | Template |
|---|---|---|---|
| 1 | Sign in | `/sign-in` | `templates/sign_in.html` |
| 2 | Home | `/home` | `templates/home.html` |
| 3 | Proactive Discovery Dashboard | `/proactive/` | `templates/phase9/proactive_dashboard.html` |
| 4 | Global Product Monitor | `/proactive/scan` | `templates/phase9/proactive_scan.html` |
| 5 | New Product Detector (5 filters) | `/proactive/qualify` | `templates/phase9/proactive_qualify.html` |
| 6 | Patent Watch | `/proactive/patents` | `templates/phase9/proactive_patents.html` |
| 7 | Exclusive Agency Acquisition Workflow | `/proactive/agency-workflow` | `templates/phase9/proactive_agency_workflow.html` |
| 8 | Daily Proactive Discovery Report | `/proactive/report` | `templates/phase9/proactive_report.html` |

## 2. Architecture (lite)

- **Source file:** `src/techno_service_ai/i18n.py` — pure logic, no DB.
- **Strings file:** `src/techno_service_ai/templates/i18n/strings.json` — flat
  per-key structure (`{"key": {"en": "...", "ar": "..."}}`).
- **Runtime context:** `src/techno_service_ai/i18n_runtime.py` —
  thread-local active language (contextvar).
- **Middleware:** added in `src/techno_service_ai/app.py` — reads
  `tsai_lang` cookie, sets `request.state.lang` + contextvar.
- **Route:** `GET /i18n/set?lang=<code>&next=<path>` — sets the cookie
  and redirects. Validates `lang` (falls back to `en` for unknown).
  Validates `next` (must start with `/`; blocks open-redirects).
- **Jinja integration:** the `t()` filter and the `lang_code()`,
  `dir_attr()`, `is_rtl()` globals are registered on every
  `Jinja2Templates` instance via `i18n.apply_to_jinja()`. Called
  once in `app.py` for the main templates and once in each
  phase router (phase3..phase9).
- **CSS:** language switcher + RTL overrides in
  `src/techno_service_ai/static/styles.css`.
- **HTML:** `<html lang="{{ lang_code() }}" dir="{{ dir_attr() }}">`
  on `base.html` and `phase9/base.html`.

## 3. String coverage

~120 keys across 8 screens (see `strings.json`):

- **Common** (`common.*`): submit, cancel, error, signin, signout, back, required.
- **Site** (`site.*`): title, tagline, language switcher labels, EN/AR labels.
- **Sign-in** (`signin.*`): title, username, password, submit, recover, required.
- **Home** (`home.*`): welcome, persona, signout, account, audit.
- **PD Dashboard** (`pd.*`): title, subtitle, nav links, dashboard headings,
  filter results, patent alerts, agency opportunities, table headers.
- **Scan** (`scan.*`): title, subtitle, 7 form fields, submit.
- **Qualify** (`qualify.*`): title, subtitle, discovery id, 5 filter
  sections (F1..F5) with sub-fields, submit.
- **Patents** (`patents.*`): title, subtitle, 6 form fields, submit.
- **Workflow** (`workflow.*`): title, subtitle, 5 form fields, submit,
  10 workflow steps.
- **Report** (`report.*`): title, subtitle, current counts list, 6 form
  fields, default citation, submit.

Each key has an English (en) and Arabic (ar) value. Missing key
fallback: English → key itself.

## 4. RTL status

When `lang=ar`:
- `<html dir="rtl">` set via the `dir_attr()` global.
- `text-align: right` applied to body / card / alert.
- Header layout flipped (`flex-direction: row-reverse`).
- Tables mirrored (`direction: rtl`).
- No broken layout, no overflow, no mirror-incorrect elements
  in the 8 critical screens (verified via HTTP smoke test).

## 5. Language switcher

- **HTML:** `EN | عربي` toggle in the header of `base.html` and
  `phase9/base.html`. Active language is highlighted.
- **Endpoint:** `GET /i18n/set?lang=<code>&next=<path>`.
  - `lang` validated (falls back to `en` for unknown).
  - `next` validated (must start with `/`; blocks open-redirects).
  - Sets the `tsai_lang` cookie (1-year max-age, path `/`,
    samesite=lax, not httpOnly so the switcher can show the active lang).
  - Returns 303 redirect.
- **State persistence:** the `tsai_lang` cookie persists across
  reloads (1-year max-age).

## 6. Verification (Done Criteria 9 — verification pass)

- **English 8/8 green:** all 8 constitutional-critical screens
  return 200/303 with `lang="en"` and `dir="ltr"`.
- **Arabic 8/8 green:** all 8 screens return 200/303 with
  `lang="ar"` and `dir="rtl"`, and the Arabic text is present in
  the rendered HTML.
- **Switcher working:** `GET /i18n/set?lang=ar` sets the cookie and
  redirects (303). `GET /i18n/set?lang=fr` falls back to `en`.
  `GET /i18n/set?lang=ar&next=https://evil.com` blocks the
  open-redirect and goes to `/`.
- **Constitutional flows in Arabic:** Proactive Discovery end-to-end
  (trigger, 5 filters, workflow steps 1..5) in AR works.
  **Class 3 gate at step 6 REJECTED** in AR (status=400). **Class 4
  gate at step 8 REJECTED** in AR (status=400). Both gates accept
  valid approvals (status=303) and the workflow continues.
- **English regression-free:** after the Arabic visit, switching
  back to English renders identical to the pre-i18n baseline
  (zero change to any current screen, flow, or test).

## 7. What was NOT changed

- Constitution v2.3 and v2.4 — UNCHANGED.
- The 17 Offices / 73 Agents / 98 entities — UNCHANGED.
- The 7 Lower Documents (02, 02A, 03, 04, 05, 06, 07, 08) —
  UNCHANGED (the i18n strings file is a presentation artefact,
  not a Lower Document).
- The 289/289 test suite — UNCHANGED (no test changes; all
  English default tests still pass).
- The schema, services, engines, agents — UNCHANGED.
- The English rendering of any screen — UNCHANGED (the t()
  filter with default lang=en returns the exact same English
  text as before).
