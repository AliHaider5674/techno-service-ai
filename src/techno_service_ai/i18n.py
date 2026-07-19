"""i18n (lite) — Constitutional Owner Arabic + English support.

Externalises the strings of the 8 constitutional-critical screens
into a JSON file. Supports:

  - English (default) — `lang=en` or no cookie.
  - Arabic (RTL)      — `lang=ar`.

The default language is English; the system is unchanged unless
the user opts in to Arabic via the language switcher.

Design constraints:
  - Pure logic, no DB coupling.
  - One strings file: `templates/i18n/strings.json`.
  - No new constitutional surface; no new TTA; no schema change.
  - Falls back to English if a key is missing in Arabic.
  - Falls back to the key itself if missing in both.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional


# The default language. Per the user's instruction: "English is the
# default and MUST work unchanged."
DEFAULT_LANG = "en"
SUPPORTED_LANGS = ("en", "ar")
RTL_LANGS = frozenset({"ar"})


_STRINGS_PATH = Path(__file__).resolve().parent / "templates" / "i18n" / "strings.json"
_STRINGS: dict = {}


def _load_strings() -> None:
    """Load the strings file once at module import."""
    global _STRINGS
    if not _STRINGS_PATH.exists():
        _STRINGS = {"en": {}, "ar": {}}
        return
    with _STRINGS_PATH.open(encoding="utf-8") as f:
        _STRINGS = json.load(f)


def t(key: str, lang: str = DEFAULT_LANG) -> str:
    """Translate a key for the given language.

    Strings file structure (per-key dict with language sub-keys):
        {
          "key.name": {"en": "English value", "ar": "القيمة العربية"},
          ...
        }

    Lookup order:
      1. _STRINGS[key][lang]    (e.g. _STRINGS["signin.title"]["ar"])
      2. _STRINGS[key]["en"]    (English fallback)
      3. key itself              (last-resort so the UI never breaks)
    """
    if not _STRINGS:
        _load_strings()
    entry = _STRINGS.get(key)
    if isinstance(entry, dict):
        if lang in entry and entry[lang]:
            return entry[lang]
        if "en" in entry and entry["en"]:
            return entry["en"]
    return key


def is_rtl(lang: str) -> bool:
    """Return True if the given language is right-to-left."""
    return lang in RTL_LANGS


def dir_attr(lang: str) -> str:
    """Return the HTML `dir` attribute value for the given language."""
    return "rtl" if is_rtl(lang) else "ltr"


def lang_attr(lang: str) -> str:
    """Return the HTML `lang` attribute value for the given language."""
    if lang in SUPPORTED_LANGS:
        return lang
    return DEFAULT_LANG


def normalize_lang(raw: Optional[str]) -> str:
    """Normalise a user-supplied language code to a supported one.

    Examples:
      "EN" -> "en"
      "ar-SA" -> "ar"
      "fr" -> "en"  (unsupported -> default)
      None -> DEFAULT_LANG
    """
    if not raw:
        return DEFAULT_LANG
    raw = raw.strip().lower()
    if raw in SUPPORTED_LANGS:
        return raw
    # Accept the base of locale strings (e.g. "ar-SA" -> "ar")
    base = raw.split("-", 1)[0]
    if base in SUPPORTED_LANGS:
        return base
    return DEFAULT_LANG


# Load strings at import time.
_load_strings()


def apply_to_jinja(templates_obj) -> None:
    """Register the `t` filter and i18n globals on a Jinja2Templates
    instance.

    The codebase creates one Jinja2Templates per phase router
    (phase3_routes, phase4_routes, ...). They all need the `t`
    filter and the i18n globals to render i18n text correctly.

    This helper is idempotent — calling it twice on the same env
    is a no-op (Jinja2 silently overwrites).
    """
    from fastapi.templating import Jinja2Templates  # noqa: F401

    def _t_filter(key: str, lang: str = DEFAULT_LANG) -> str:
        return t(key, lang)

    templates_obj.env.filters["t"] = _t_filter

    def _g_lang() -> str:
        try:
            from . import i18n_runtime as _i18n_rt
            return _i18n_rt.current_lang()
        except Exception:
            return DEFAULT_LANG

    templates_obj.env.globals["lang_code"] = _g_lang
    templates_obj.env.globals["dir_attr"] = lambda: dir_attr(_g_lang())
    templates_obj.env.globals["is_rtl"] = lambda: is_rtl(_g_lang())
    templates_obj.env.globals["supported_langs"] = SUPPORTED_LANGS
