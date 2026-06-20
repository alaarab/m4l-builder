"""Offline numeric simulator for the gen~ signal path.

This is the *behavioural* half of the gen test harness; the *static* half is
:mod:`m4l_builder.gen_lint`. ``gen_lint`` proves structure (no dead output, no
out-of-range index, no split ternary); ``gen_sim`` proves BEHAVIOUR — it executes
a gen~ codebox kernel sample-by-sample in pure Python so tests can assert what
the DSP actually does (bypass == identity, silence -> silence, no NaN at full
scale, a detector really catches what it claims) instead of only its shape.

Supported subset (anything else raises :class:`UnsupportedKernel` — the simulator
never silently mis-evaluates and reports a false green):

* ``History name(init);`` — per-voice state read at the TOP of the per-sample
  block (previous sample's value) and committed at the END.
* ``Param name(default);`` — a held scalar the test overrides.
* ``in1``..``inN`` per-sample inputs and the ``samplerate`` constant.
* straight-line ``lhs = expr;`` statements (``lhs`` a scratch var, an ``outK``,
  or a History var).
* ``+ - * /`` arithmetic and the ``cond ? a : b`` ternary, parsed
  parenthesis/precedence-correct (gen ternary binds BELOW arithmetic and is
  right-associative — reproduced exactly, NOT via Python's ``a if c else b``).
* comparison / logic ``> < >= <= == != && || !`` inside conditions.
* the pure scalar function table in :data:`_FUNCS`.

Explicitly NOT modelled (refused): ``Delay``/``Buffer``/``Data`` and any
``.read``/``.write``/``peek``/``poke``/``index``/``pfft``/``filtercoeff``/
``biquad`` ring access, indexed history ``h[n]``, ``if``/``else``/loops, and
multiple writes to the same History var in one sample. Those kernels (delay
lines, FFT, LUFS integration windows) need the live render path; the simulator
refuses them so a delay-dependent path is never reported as passing.
"""

from __future__ import annotations

import math

from .gen_lint import _strip_comments

__all__ = ["UnsupportedKernel", "GenKernel", "simulate"]


class UnsupportedKernel(ValueError):
    """Raised when a kernel uses a construct outside the simulator's subset."""


# ── pure scalar function table (gen builtins) ────────────────────────────────
def _clamp(x, lo, hi):
    return min(max(x, lo), hi)


def _sign(x):
    return (x > 0) - (x < 0)


def _scale(x, in_lo, in_hi, out_lo, out_hi):
    return out_lo + (x - in_lo) * (out_hi - out_lo) / (in_hi - in_lo)


_FUNCS = {
    # decibels <-> linear
    "dbtoa": lambda x: 10.0 ** (x / 20.0),
    "atodb": lambda x: 20.0 * math.log10(x),
    # range
    "clamp": _clamp,
    "clip": _clamp,  # gen alias
    "min": min,
    "max": max,
    "abs": abs,
    "sign": _sign,
    "wrap": lambda x, lo, hi: lo + ((x - lo) % (hi - lo)),
    "fold": lambda x, lo, hi: x,  # not in subset; defined to avoid NameError only
    "scale": _scale,
    "mix": lambda a, b, t: a + (b - a) * t,
    # transcendental
    "exp": math.exp,
    "log": math.log,
    "log10": math.log10,
    "log2": math.log2,
    "pow": math.pow,
    "sqrt": math.sqrt,
    "tanh": math.tanh,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "atan2": math.atan2,
    # rounding (gen round() is round-half-up, not Python banker's rounding)
    "floor": math.floor,
    "ceil": math.ceil,
    "round": lambda x: math.floor(x + 0.5),
    "trunc": math.trunc,
    "fract": lambda x: x - math.floor(x),
    "int": math.trunc,  # gen int() truncates toward zero
}

# Tokens that put a kernel outside the supported subset.
_REFUSE_TOKENS = (
    "Delay", "Buffer", "Data", "buffer", "peek", "poke", "index",
    "pfft", "filtercoeff", "biquad", "cycle", "noise", "sah",
    ".read", ".write",
)


def _strip_outer_parens(expr: str) -> str:
    """Drop a redundant paren pair that wraps the ENTIRE expression.

    ``((a)?b:c)`` -> ``(a)?b:c`` exposes the inner top-level ternary; ``(a)?(b):(c)``
    is left alone (its first ``(`` does not match its last ``)``).
    """
    expr = expr.strip()
    while len(expr) >= 2 and expr[0] == "(" and expr[-1] == ")":
        depth = 0
        wraps_all = True
        for i, ch in enumerate(expr):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0 and i != len(expr) - 1:
                    wraps_all = False
                    break
        if wraps_all:
            expr = expr[1:-1].strip()
        else:
            break
    return expr


def _ternary_to_py(expr: str) -> str:
    """Rewrite a gen ``cond ? a : b`` expression as a Python conditional.

    gen's ``?:`` is the lowest-precedence operator and right-associative, so the
    top-level ``?`` splits the whole expression: everything before it is the
    condition, everything between it and its matching ``:`` (skipping nested
    ternaries) is the true branch, and everything after is the false branch. Each
    part is parenthesised and recursively converted, which reproduces gen
    precedence exactly without a full parser.
    """
    expr = _strip_outer_parens(expr)
    depth = 0
    qpos = -1
    for i, ch in enumerate(expr):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == "?" and depth == 0:
            qpos = i
            break
    if qpos < 0:
        return expr  # no ternary at this level

    depth = 0
    nested = 0
    cpos = -1
    for i in range(qpos + 1, len(expr)):
        ch = expr[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif depth == 0:
            if ch == "?":
                nested += 1
            elif ch == ":":
                if nested == 0:
                    cpos = i
                    break
                nested -= 1
    if cpos < 0:
        raise UnsupportedKernel(f"ternary '?' without matching ':' in: {expr!r}")

    cond = _ternary_to_py(expr[:qpos])
    tbranch = _ternary_to_py(expr[qpos + 1:cpos])
    fbranch = _ternary_to_py(expr[cpos + 1:])
    return f"(({tbranch}) if ({cond}) else ({fbranch}))"


def _logic_to_py(expr: str) -> str:
    """Translate gen logical operators to Python (``&&``->and, ``||``->or, ``!``->not)."""
    expr = expr.replace("&&", " and ").replace("||", " or ")
    # '!' is logical-not, but '!=' is a comparison — replace only standalone '!'.
    out = []
    i = 0
    while i < len(expr):
        if expr[i] == "!" and not (i + 1 < len(expr) and expr[i + 1] == "="):
            out.append(" not ")
        else:
            out.append(expr[i])
        i += 1
    return "".join(out)


class GenKernel:
    """A parsed, simulatable gen~ codebox kernel."""

    def __init__(self, code: str):
        body = "\n".join(_strip_comments(code))
        self._refuse_unsupported(body)
        self.histories, self.params = self._parse_decls(body)
        self.statements, self.num_outs = self._parse_body(body)
        self._check_single_history_writes()

    @staticmethod
    def _refuse_unsupported(body: str) -> None:
        for tok in _REFUSE_TOKENS:
            if tok in body:
                raise UnsupportedKernel(
                    f"kernel uses unsupported construct {tok!r} "
                    f"(delay/buffer/FFT/IIR-object paths need the live render harness)"
                )
        if "[" in body:
            raise UnsupportedKernel("indexed access '[' is not supported")
        for kw in ("if", "else", "for", "while", "function"):
            # word-boundary check so 'diff'/'forest' don't trip it
            import re as _re
            if _re.search(rf"(?<![A-Za-z0-9_]){kw}(?![A-Za-z0-9_])", body):
                raise UnsupportedKernel(
                    f"control-flow keyword {kw!r} is not supported (straight-line only)"
                )

    @staticmethod
    def _parse_decls(body: str):
        import re
        histories: dict[str, float] = {}
        params: dict[str, float] = {}
        for kind, name, init in re.findall(
            r"(History|Param)\s+([A-Za-z_]\w*)\s*\(\s*(-?[\d.]+)\s*\)", body
        ):
            (histories if kind == "History" else params)[name] = float(init)
        return histories, params

    def _parse_body(self, body: str):
        import re
        # strip declaration statements, keep `lhs = rhs;` assignments
        statements = []
        num_outs = 0
        for raw in body.split(";"):
            stmt = raw.strip()
            if not stmt:
                continue
            if stmt.startswith(("History ", "Param ")):
                continue
            if "=" not in stmt:
                raise UnsupportedKernel(f"non-assignment statement: {stmt!r}")
            lhs, rhs = stmt.split("=", 1)
            lhs = lhs.strip()
            if not re.fullmatch(r"[A-Za-z_]\w*", lhs):
                raise UnsupportedKernel(f"unsupported assignment target: {lhs!r}")
            m = re.fullmatch(r"out(\d+)", lhs)
            if m:
                num_outs = max(num_outs, int(m.group(1)))
            py_rhs = _ternary_to_py(_logic_to_py(rhs.strip()))
            statements.append((lhs, compile(py_rhs, "<gen>", "eval")))
        return statements, num_outs

    def _check_single_history_writes(self) -> None:
        seen = set()
        for lhs, _ in self.statements:
            if lhs in self.histories:
                if lhs in seen:
                    raise UnsupportedKernel(
                        f"History {lhs!r} written more than once per sample "
                        f"(only-last-write is ambiguous; refused)"
                    )
                seen.add(lhs)

    def run(self, inputs=None, params=None, samplerate=48000.0, num_samples=None):
        """Run the kernel and return ``{outK: [values...]}`` plus the History trace.

        inputs: dict ``{"in1": [...], "in2": [...]}`` (or a single list for in1).
        params: dict overriding Param defaults (held constant across the run).
        """
        if isinstance(inputs, (list, tuple)):
            inputs = {"in1": list(inputs)}
        inputs = inputs or {}
        if num_samples is None:
            num_samples = max((len(v) for v in inputs.values()), default=1)

        hist = dict(self.histories)
        pvals = dict(self.params)
        if params:
            pvals.update({k: float(v) for k, v in params.items()})

        outs = {f"out{k}": [0.0] * num_samples for k in range(1, self.num_outs + 1)}
        for n in range(num_samples):
            ns = dict(_FUNCS)
            ns.update(hist)
            ns.update(pvals)
            ns["samplerate"] = float(samplerate)
            for name, seq in inputs.items():
                ns[name] = float(seq[n]) if n < len(seq) else 0.0
            for lhs, code in self.statements:
                ns[lhs] = eval(code, {"__builtins__": {}}, ns)  # noqa: S307 - sandboxed ns
            for h in hist:
                hist[h] = ns[h]
            for k in range(1, self.num_outs + 1):
                outs[f"out{k}"][n] = ns[f"out{k}"]
        return outs


def simulate(code: str, inputs=None, params=None, samplerate=48000.0,
             num_samples=None):
    """Parse + run a gen kernel in one call. See :meth:`GenKernel.run`."""
    return GenKernel(code).run(inputs, params, samplerate, num_samples)
