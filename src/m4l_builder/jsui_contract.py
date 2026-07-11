"""Validation helpers for Max mgraphics UI engines (jsui and v8ui).

Two engines share the mgraphics drawing model but differ in their JS runtime:
  - jsui  -> the legacy ES5-only engine: the mgraphics bootstrap is REQUIRED and
             ES6 syntax (let/const/arrow/template literals/class/async) is FORBIDDEN.
  - v8ui  -> the modern V8 engine: the same mgraphics bootstrap is REQUIRED, but
             ES6+ is fully supported (and the flagship engines emit it), so the
             ES6 forbiddens MUST NOT be applied here.
"""

from __future__ import annotations

import re


class JsuiContractError(ValueError):
    """Raised when jsui source violates the shared engine contract."""


_REQUIRED_SNIPPETS = (
    ("mgraphics.init()", "missing mgraphics.init() bootstrap"),
    ("mgraphics.relative_coords = 0", "missing mgraphics.relative_coords bootstrap"),
    ("mgraphics.autofill = 0", "missing mgraphics.autofill bootstrap"),
    ("function paint()", "missing paint() entry point"),
)

# a STATIC display (legend art, fixed diagrams) paints once at creation and
# never re-renders — the redraw hook is only required for stateful displays.
_REDRAW_SNIPPET = ("mgraphics.redraw()", "missing redraw hook")

_FORBIDDEN_PATTERNS = (
    (re.compile(r"(?<![\w$])let\s"), "uses ES6 'let'"),
    (re.compile(r"(?<![\w$])const\s"), "uses ES6 'const'"),
    (re.compile(r"=>"), "uses arrow functions"),
    (re.compile(r"`"), "uses template literals"),
    (re.compile(r"(?<![\w$])class\s"), "uses ES6 class syntax"),
    (re.compile(r"\basync\b"), "uses async/await syntax"),
    (re.compile(r"\bawait\b"), "uses async/await syntax"),
    (re.compile(r"\bPromise\b"), "uses Promise APIs"),
    (re.compile(r"\bglobalThis\b"), "uses globalThis"),
    (re.compile(r"\brequire\s*\("), "uses CommonJS require()"),
    (re.compile(r"\bmodule\.exports\b"), "uses module.exports"),
    (re.compile(r"(?<![\w$])import\s"), "uses ESM import syntax"),
    (re.compile(r"(?<![\w$])export\s"), "uses ESM export syntax"),
    # v8ui pointer-event handlers NEVER fire in a classic jsui (its mouse
    # events are onclick/ondrag/onidle/onidleout) — a control wired to
    # onpointerdown ships looking fine and is silently dead to the mouse
    # (the settings_bar bug: every sidebar opener ignored clicks in Live).
    (re.compile(r"\bonpointer(?:down|up|move)\b"),
     "uses v8ui pointer events — classic jsui mouse events are "
     "onclick/ondrag/onidle (or build the box with add_v8ui)"),
)


def _required_snippet_issues(js_code: str, *, static: bool = False) -> list[str]:
    """Shared mgraphics bootstrap checks (jsui and v8ui both draw via mgraphics)."""
    required = _REQUIRED_SNIPPETS if static else _REQUIRED_SNIPPETS + (_REDRAW_SNIPPET,)
    return [
        message
        for snippet, message in required
        if snippet not in js_code
    ]


def find_jsui_contract_issues(js_code: str, *, static: bool = False) -> list[str]:
    """Return human-readable contract violations for jsui (ES5) source.

    ``static=True`` waives the redraw-hook requirement for read-only displays
    that paint once and never change (legend art, fixed diagrams).
    """
    if not isinstance(js_code, str) or not js_code.strip():
        return ["jsui code must be a non-empty string"]

    issues = _required_snippet_issues(js_code, static=static)
    for pattern, message in _FORBIDDEN_PATTERNS:
        if pattern.search(js_code):
            issues.append(message)

    return issues


def validate_jsui_contract(js_code: str, *, static: bool = False) -> str:
    """Raise when jsui source violates the shared ES5 contract."""
    issues = find_jsui_contract_issues(js_code, static=static)
    if issues:
        raise JsuiContractError("Invalid jsui contract: " + "; ".join(issues))
    return js_code


def find_v8ui_contract_issues(js_code: str, *, static: bool = False) -> list[str]:
    """Return contract violations for v8ui source.

    v8ui shares the mgraphics bootstrap requirement with jsui but runs on the V8
    engine, so ES6+ is allowed and the ES5 forbiddens are intentionally NOT
    applied (every shipped v8ui display engine emits let/const/arrow).
    """
    if not isinstance(js_code, str) or not js_code.strip():
        return ["v8ui code must be a non-empty string"]
    return _required_snippet_issues(js_code, static=static)


def validate_v8ui_contract(js_code: str, *, static: bool = False) -> str:
    """Raise when v8ui source omits the mgraphics bootstrap (no ES5 restriction)."""
    issues = find_v8ui_contract_issues(js_code, static=static)
    if issues:
        raise JsuiContractError("Invalid v8ui contract: " + "; ".join(issues))
    return js_code
