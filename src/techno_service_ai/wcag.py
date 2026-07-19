"""WCAG 2.1 AA accessibility audit — Closes GAP-PHASE1-002.

A baseline HTML accessibility audit. The full WCAG 2.1 AA
test suite is a Phase 8 deliverable; the comprehensive
axe-core / pa11y integration is out of scope for this
session. This module implements the constitutional-floor
checks that every rendered page must pass:

  - One <main> landmark per page.
  - One <h1> per page.
  - All <input> elements have an associated <label> or aria-label.
  - <html> has a lang attribute.
  - <title> is present and non-empty.
  - <img> elements have an alt attribute.

Each finding is a dict with: rule, severity, message.
Severity is one of: critical, serious, moderate, minor.

Constitutional source:
  - Document 07 Section 1 (accessibility).
  - Constitution Article XXV (Security / inclusion).
  - Document 08 §2.9 (Phase 8: WCAG test suite).
"""
from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import List, Dict


class _PageParser(HTMLParser):
    """Minimal HTML parser that records landmarks, headings, and inputs."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.has_main = False
        self.heading_levels: List[int] = []
        self.inputs: List[Dict] = []  # {id, name, has_label, aria_label}
        self.images: List[Dict] = []  # {alt, src}
        self.title = ""
        self.in_title = False
        self.lang = ""
        self._current_label_for: List[str] = []  # stack of label `for` attrs
        self._open_label_for: str | None = None

    def handle_starttag(self, tag: str, attrs):
        a = dict(attrs)
        if tag == "main":
            self.has_main = True
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.heading_levels.append(int(tag[1]))
        elif tag == "input":
            self.inputs.append({
                "id": a.get("id", ""),
                "name": a.get("name", ""),
                "type": a.get("type", "text"),
                "aria_label": a.get("aria-label", ""),
                "aria_labelledby": a.get("aria-labelledby", ""),
            })
        elif tag == "img":
            self.images.append({
                "alt": a.get("alt"),
                "src": a.get("src", ""),
            })
        elif tag == "label":
            self._open_label_for = a.get("for")
        elif tag == "html":
            self.lang = a.get("lang", "")

    def handle_endtag(self, tag: str):
        if tag == "title":
            self.in_title = False
        elif tag == "label":
            self._open_label_for = None

    def handle_data(self, data: str):
        if self.in_title:
            self.title += data

    def handle_startendtag(self, tag: str, attrs):
        # self-closing tags
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)


def _label_for_input(parser: _PageParser, input_id: str) -> bool:
    """A simple way: look for explicit <label for=id> in the raw HTML."""
    if not input_id:
        return False
    return bool(re.search(rf'<label[^>]*for=["\']{re.escape(input_id)}["\']', parser.raw, re.I))


def audit_html(html: str) -> List[Dict]:
    """Run the constitutional-floor WCAG checks on an HTML string.

    Returns a list of findings; empty list means the page passes
    the floor. Each finding has:
        - rule: short identifier (e.g. "missing-label")
        - severity: critical | serious | moderate | minor
        - message: human-readable
    """
    findings: List[Dict] = []
    parser = _PageParser()
    parser.raw = html
    try:
        parser.feed(html)
    except Exception as e:  # pragma: no cover
        findings.append({
            "rule": "parse-error",
            "severity": "critical",
            "message": f"HTML parse error: {e}",
        })
        return findings

    # 1. <html lang>
    if not parser.lang:
        findings.append({
            "rule": "html-lang",
            "severity": "serious",
            "message": "<html> element is missing the lang attribute.",
        })

    # 2. <title>
    if not parser.title.strip():
        findings.append({
            "rule": "page-title",
            "severity": "serious",
            "message": "<title> is missing or empty.",
        })

    # 3. <main> landmark
    if not parser.has_main:
        findings.append({
            "rule": "main-landmark",
            "severity": "serious",
            "message": "No <main> landmark found.",
        })

    # 4. <h1>
    h1_count = sum(1 for h in parser.heading_levels if h == 1)
    if h1_count == 0:
        findings.append({
            "rule": "page-h1",
            "severity": "moderate",
            "message": "No <h1> heading on page.",
        })
    elif h1_count > 1:
        findings.append({
            "rule": "page-h1-multiple",
            "severity": "moderate",
            "message": f"Multiple <h1> headings ({h1_count}); pages should have exactly one.",
        })

    # 5. <input> with associated label
    for inp in parser.inputs:
        if inp["type"] in ("hidden", "submit", "button"):
            continue
        has_label = (
            bool(inp["aria_label"])
            or bool(inp["aria_labelledby"])
            or _label_for_input(parser, inp["id"])
        )
        if not has_label:
            findings.append({
                "rule": "missing-label",
                "severity": "critical",
                "message": f"<input name={inp['name']!r}> has no associated <label> or aria-label.",
            })

    # 6. <img alt>
    for img in parser.images:
        if img["alt"] is None:
            findings.append({
                "rule": "img-alt",
                "severity": "serious",
                "message": f"<img src={img['src']!r}> is missing alt attribute.",
            })

    return findings
