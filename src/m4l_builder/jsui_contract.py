"""Validation helpers for ES5-targeted Max jsui engines."""

from __future__ import annotations

import re


class JsuiContractError(ValueError):
    """Raised when jsui source violates the shared engine contract."""


_REQUIRED_SNIPPETS = (
    ("mgraphics.init()", "missing mgraphics.init() bootstrap"),
    ("mgraphics.relative_coords = 0", "missing mgraphics.relative_coords bootstrap"),
    ("mgraphics.autofill = 0", "missing mgraphics.autofill bootstrap"),
    ("function paint()", "missing paint() entry point"),
    ("mgraphics.redraw()", "missing redraw hook"),
)

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
)


def find_jsui_contract_issues(js_code: str) -> list[str]:
    """Return human-readable contract violations for jsui source."""
    if not isinstance(js_code, str) or not js_code.strip():
        return ["jsui code must be a non-empty string"]

    issues: list[str] = []
    for snippet, message in _REQUIRED_SNIPPETS:
        if snippet not in js_code:
            issues.append(message)

    for pattern, message in _FORBIDDEN_PATTERNS:
        if pattern.search(js_code):
            issues.append(message)

    return issues


def validate_jsui_contract(js_code: str) -> str:
    """Raise when jsui source violates the shared ES5 contract."""
    issues = find_jsui_contract_issues(js_code)
    if issues:
        raise JsuiContractError("Invalid jsui contract: " + "; ".join(issues))
    return js_code
