"""Static linter for GenExpr codebox source (the gen~ signal path).

The Node js_harness only exercises jsui/v8ui DISPLAY logic — it never sees the
gen~ DSP, so a whole class of "advertised but unwired" bugs ships green: a
declared signal out that nothing assigns (silent passthrough / dead output), an
``in N`` / ``out N`` index past the object's i/o count, or the multi-line-ternary
trap that makes GenExpr load as a passthrough template with no error.

``lint_genexpr`` is a fast, dependency-free static pass that catches those
structural faults at build/test time — it cannot prove the DSP math is correct
(that still needs an offline render or a live sweep), but it stops the most
common silent failures from reaching Live.
"""

from __future__ import annotations

import re

__all__ = ["lint_genexpr"]

_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.S)


def _strip_comments(code: str) -> list[str]:
    """Drop /* */ blocks and // line comments; return the remaining lines."""
    code = _BLOCK_COMMENT.sub(" ", code)
    out = []
    for line in code.splitlines():
        i = line.find("//")
        out.append(line if i < 0 else line[:i])
    return out


def lint_genexpr(code: str, numins: int, numouts: int) -> list[str]:
    """Return a list of structural issues in GenExpr ``code``; empty == clean.

    Checks (all deterministic from the source + the declared i/o counts):
      * every ``out1``..``out<numouts>`` is assigned (LHS of ``=``) at least once
        — an unassigned signal out silently emits 0 (dead/passthrough output);
      * no ``in N`` is referenced past ``numins`` and no ``out N`` is assigned
        past ``numouts`` (a mis-wired index);
      * no non-comment line ends in ``?`` (a ternary split across lines, which
        GenExpr can silently compile as a passthrough — see the runtime
        pitfalls memory).
    """
    lines = _strip_comments(code)
    body = "\n".join(lines)
    issues: list[str] = []

    # 1. Each declared signal out must be assigned somewhere.
    for k in range(1, numouts + 1):
        if not re.search(rf"(?<![A-Za-z0-9_])out{k}\s*=", body):
            issues.append(
                f"out{k} declared (numouts={numouts}) but never assigned "
                f"(LHS of '=') -> dead/passthrough output"
            )

    # 2. No i/o index past the declared counts.
    for m in re.finditer(r"(?<![A-Za-z0-9_])in(\d+)(?![A-Za-z0-9_])", body):
        n = int(m.group(1))
        if n > numins:
            issues.append(f"references in{n} but numins={numins}")
    for m in re.finditer(r"(?<![A-Za-z0-9_])out(\d+)\s*=", body):
        n = int(m.group(1))
        if n > numouts:
            issues.append(f"assigns out{n} but numouts={numouts}")

    # 3. Multi-line ternary trap: a statement line that ends in '?'.
    for i, line in enumerate(lines, start=1):
        if line.rstrip().endswith("?"):
            issues.append(
                f"line {i} ends with '?' -> likely a multi-line ternary "
                f"(GenExpr may compile it as a silent passthrough)"
            )

    # de-dup while preserving order
    seen: set[str] = set()
    deduped: list[str] = []
    for issue in issues:
        if issue not in seen:
            seen.add(issue)
            deduped.append(issue)
    return deduped
