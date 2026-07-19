"""i18n runtime — thread-local current language.

Stores the per-request language so Jinja globals (and any other
code that needs the active language without access to the
request) can read it. The i18n middleware sets it before the
route handler runs, and clears it after the response is sent.
"""
from __future__ import annotations

import contextvars
from typing import Optional

from . import i18n as _i18n

_lang_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "tsai_lang", default=_i18n.DEFAULT_LANG
)


def set_lang(lang: str) -> None:
    """Set the active language for the current request context."""
    _lang_var.set(_i18n.normalize_lang(lang))


def current_lang() -> str:
    """Return the active language (default: en)."""
    return _lang_var.get()


def get_token():
    """Return the context var token (for reset on response)."""
    return _lang_var.set(_i18n.DEFAULT_LANG)
