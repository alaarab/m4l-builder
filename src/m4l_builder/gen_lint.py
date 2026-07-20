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

__all__ = ["find_function_defs", "lint_genexpr"]

_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.S)


def _strip_comments(code: str) -> list[str]:
    """Drop /* */ blocks and // line comments; return the remaining lines."""
    code = _BLOCK_COMMENT.sub(" ", code)
    out = []
    for line in code.splitlines():
        i = line.find("//")
        out.append(line if i < 0 else line[:i])
    return out


# Block-openers that read like ``name(...) {`` but are control flow, not defs.
_CONTROL_KEYWORDS = frozenset({"if", "else", "for", "while", "return", "switch"})
_IDENT = re.compile(r"[A-Za-z_]\w*")
# An identifier in EXPRESSION position (preceded by one of these) is a call,
# never a definition — kills ``y = f(x)`` / ``delay.write(x)`` false positives.
_EXPR_PRECEDERS = frozenset("=+-*/%<>!&|?:,(.")
_STRINGS = re.compile(r'"[^"\n]*"')


def find_function_defs(code: str) -> list[str]:
    """Names of user functions DEFINED at brace depth 0: ``name(args) { ... }``.

    Why this matters: a gen~ codebox loaded from an EXTERNAL ``.gendsp`` support
    file is SILENCED by Live's gen compiler when the source defines any function
    (Live-verified, ZZGenFuncEmbed — see :func:`gen_patcher.embed_gendsp`), while
    the same code EMBEDDED inline compiles and passes audio. This detector is the
    build-time tripwire for that trap: :meth:`Device.add_gendsp` refuses
    function-bearing source, and the fleet lint sweep flags any shipped
    ``.gendsp`` asset that carries one.

    Mechanics: comments and string literals are stripped, then the source is
    scanned tracking brace depth; a def is an identifier at depth 0, in
    statement position (not after ``=``/an operator/a comma), whose balanced
    ``(...)`` group is followed by ``{``. ``if``/``for``/``while`` etc. are
    excluded, and declarations (``Param p(0);``, ``History h(0.);``,
    ``Buffer b("x");``) never match because no ``{`` follows. Function CALLS
    never match (no ``{``). Returns the def names in source order (deduped).
    """
    body = _STRINGS.sub('""', "\n".join(_strip_comments(code)))
    defs: list[str] = []
    depth = 0
    i, n = 0, len(body)
    while i < n:
        ch = body[i]
        if ch == "{":
            depth += 1
            i += 1
            continue
        if ch == "}":
            depth = max(0, depth - 1)
            i += 1
            continue
        m = _IDENT.match(body, i)
        if not m:
            i += 1
            continue
        name, j = m.group(0), m.end()
        if depth != 0 or name in _CONTROL_KEYWORDS:
            i = j
            continue
        back = i - 1
        while back >= 0 and body[back] in " \t\r\n":
            back -= 1
        if back >= 0 and body[back] in _EXPR_PRECEDERS:
            i = j          # expression position -> a call, not a def
            continue
        k = j
        while k < n and body[k] in " \t":
            k += 1
        if k >= n or body[k] != "(":
            i = j
            continue
        pdepth, p = 0, k
        while p < n:
            if body[p] == "(":
                pdepth += 1
            elif body[p] == ")":
                pdepth -= 1
                if pdepth == 0:
                    break
            p += 1
        if p >= n:
            break          # unbalanced parens; nothing more to find
        q = p + 1
        while q < n and body[q] in " \t\r\n":
            q += 1
        if q < n and body[q] == "{":
            if name not in defs:
                defs.append(name)
            i = q          # resume at '{' so depth tracking stays exact
            continue
        i = j
    return defs


def lint_genexpr(code: str, numins: int, numouts: int) -> list[str]:
    """Return a list of structural issues in GenExpr ``code``; empty == clean.

    Checks (all deterministic from the source + the declared i/o counts):
      * every ``out1``..``out<numouts>`` is assigned (LHS of ``=``) at least once
        — an unassigned signal out silently emits 0 (dead/passthrough output);
      * no ``in N`` is referenced past ``numins`` and no ``out N`` is assigned
        past ``numouts`` (a mis-wired index);
      * no non-comment line ends in ``?`` (a ternary split across lines, which
        GenExpr can silently compile as a passthrough — see the runtime
        pitfalls memory);
    See also :func:`lint_param_order` (advisory Param-position check) and
    :func:`lint_denormals` (advisory fixdenorm check).
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


def lint_denormals(code: str) -> list[str]:
    """ADVISORY denormal check (T35/Q18, pairs with the T02 flush primitive).

    Flags feedback state that decays multiplicatively — the classic denormal
    generator on Intel when the input goes silent:

    * a ``History h`` updated as ``h = h + k * (x - h)`` (one-pole) or
      ``h = <expr> * coeff`` (decay) with no ``fixdenorm`` anywhere in the
      kernel;
    * any ``Delay`` read feeding back through a multiply without
      ``fixdenorm``.

    Returns advisory strings (NOT wired into the default build policy —
    Apple-silicon FTZ makes this Intel-portability advice).
    """
    lines = _strip_comments(code)
    body = "\n".join(lines)
    if "fixdenorm" in body:
        return []
    issues: list[str] = []
    hist_names = re.findall(r"\bHistory\s+([A-Za-z_][A-Za-z0-9_]*)", body)
    for h in hist_names:
        pat = re.compile(
            rf"(?<![A-Za-z0-9_]){h}\s*=\s*[^;]*(?<![A-Za-z0-9_]){h}(?![A-Za-z0-9_])[^;]*[*][^;]*;"
            rf"|(?<![A-Za-z0-9_]){h}\s*=\s*[^;]*[*][^;]*(?<![A-Za-z0-9_]){h}(?![A-Za-z0-9_])[^;]*;")
        if pat.search(body):
            issues.append(
                f"History '{h}' decays through a multiply with no fixdenorm "
                f"in the kernel -> denormal risk on Intel when input goes "
                f"silent (wrap the update: {h} = fixdenorm(...))")
    if re.search(r"\bDelay\s+\w+", body) and re.search(r"\.read\(", body) \
            and re.search(r"\.write\([^)]*[*]", body):
        issues.append(
            "Delay feedback path multiplies with no fixdenorm in the kernel "
            "-> denormal risk on Intel (fixdenorm the written sample)")
    return issues


def lint_param_order(code: str) -> list[str]:
    """ADVISORY Param-position check (T31/T35).

    A byte-identical A/B on Dynamic EQ proved that reordering ONLY the
    declarations flipped the kernel from silently dead (all gen outs 0,
    dry passthrough audible) to working — the dead variant declared
    ``Param``s after executable statements. Yet the poly-LFO engine ships
    mid-code Params and runs fine in Live, so the failure is
    construct-dependent, not universal. Until the exact trigger is pinned
    (needs a Max-console probe), HOIST ALL PARAMS — this advisory flags
    any kernel that doesn't.
    """
    lines = _strip_comments(code)
    issues: list[str] = []
    decl = re.compile(r"^\s*(Param|History|Delay|Data|Buffer)\b")
    param = re.compile(r"^\s*Param\b")
    seen_exec = False
    first_exec_line = 0
    for i, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped:
            continue
        stmts = [st.strip() for st in stripped.split(";") if st.strip()]
        if not stmts:
            continue
        if seen_exec and any(param.match(st) for st in stmts):
            issues.append(
                f"line {i}: Param declaration after executable code (first "
                f"statement at line {first_exec_line}) -> gen~ MAY silently "
                f"fail to compile in Live (Dynamic EQ A/B); hoist Params")
        if not all(decl.match(st) for st in stmts) and not seen_exec:
            seen_exec = True
            first_exec_line = i
    return issues
