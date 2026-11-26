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
* ``Param name(default[, min=.., max=..]);`` — a held scalar the test overrides.
* ``in1``..``inN`` per-sample inputs, the ``samplerate`` constant, ``pi`` /
  ``twopi`` / ``halfpi`` and ``mstosamps()`` / ``sampstoms()``.
* ``lhs = expr;`` statements (``lhs`` a scratch var, an ``outK``, or a History
  var), ``a, b = f(...);`` multi-assignment from a function returning two values,
  and ``if (c) {...} else if (c) {...} else {...}`` blocks (incl. nesting).
* ``+ - * /`` arithmetic and the ``cond ? a : b`` ternary, parsed
  parenthesis/precedence-correct (gen ternary binds BELOW arithmetic and is
  right-associative — reproduced exactly, NOT via Python's ``a if c else b``).
* comparison / logic ``> < >= <= == != && || !`` inside conditions.
* the pure scalar function table in :data:`_FUNCS`.
* ``Delay name(size);`` lines (``size`` may use ``samplerate``) with
  ``name.write(expr);`` statements and ``name.read(taps)`` /
  ``name.read(taps, interp="linear")`` in expressions. A read before the
  sample's write sees past input only (``read(1)`` = previous sample), matching
  gen's read-then-write idiom; a read after the write sees it at tap 0.
* user function definitions at the top of the codebox
  (``name(a, b) { ...; return x[, y]; }``), with their own ``History`` state.
  Every call SITE gets its own state, as in gen, and a function may call an
  earlier one. ``Delay`` lines pass into functions as arguments. The body must
  end in exactly one top-level ``return``.

Explicitly NOT modelled (refused): ``Buffer``/``Data`` and
``peek``/``poke``/``index``/``pfft``/``filtercoeff``/``biquad`` access, stateful
operators such as ``noise``/``cycle``/``sah``, other ``Delay`` interpolation
modes, indexed history ``h[n]``, ``for``/``while`` loops, and ``Delay``/``Param``
declarations inside a function. Those kernels need the live render path; the
simulator refuses them so such a path is never reported as passing.
"""

from __future__ import annotations

import functools
import math
import re

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
    "minimum": min,
    "maximum": max,
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
    # gen constants
    "pi": math.pi,
    "twopi": 2.0 * math.pi,
    "halfpi": 0.5 * math.pi,
    # denormal guard: gen fixdenorm flushes SUBNORMALS to 0 and passes
    # everything else (incl. 0/inf/nan) through — bit-exact for normal values.
    # 2.2250738585072014e-308 is DBL_MIN (the smallest normal double).
    "fixdenorm": lambda x: 0.0 if (
        x != 0.0 and math.isfinite(x) and abs(x) < 2.2250738585072014e-308
    ) else x,
}

# Tokens that put a kernel outside the supported subset.
_REFUSE_TOKENS = (
    "Buffer", "Data", "buffer", "peek", "poke", "index",
    "pfft", "filtercoeff", "biquad", "cycle", "noise", "sah",
)


class _DelayLine:
    """A gen ``Delay``: a ring of ``size`` past samples with integer/linear reads."""

    def __init__(self, size: int):
        self.buf = [0.0] * max(int(size), 1)
        self.pos = 0            # slot the current sample writes into
        self.written = False

    def advance(self) -> None:
        self.pos = (self.pos + 1) % len(self.buf)
        self.written = False

    def write(self, value: float) -> float:
        self.buf[self.pos] = float(value)
        self.written = True
        return value

    def _tap(self, k: int) -> float:
        if k == 0 and not self.written:
            k = len(self.buf)   # nothing written yet this sample: oldest sample
        k = min(max(k, 0), len(self.buf) - 1 + (0 if self.written else 1))
        return self.buf[(self.pos - k) % len(self.buf)]

    def read(self, taps: float, interp: str = "none") -> float:
        if interp not in ("none", "linear"):
            raise UnsupportedKernel(f"Delay interp {interp!r} is not simulated")
        if interp == "none":
            return self._tap(int(math.floor(taps)))
        whole = math.floor(taps)
        frac = taps - whole
        return self._tap(int(whole)) * (1 - frac) + self._tap(int(whole) + 1) * frac


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


_FN_HEAD = re.compile(r"([A-Za-z_]\w*)\s*\(([^()]*)\)\s*\{")
_CONTROL_WORDS = frozenset({"if", "else", "for", "while"})


def _split_top_commas(expr: str) -> list[str]:
    """Split ``expr`` on commas that sit outside any parentheses."""
    parts, depth, start = [], 0, 0
    for i, ch in enumerate(expr):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == "," and depth == 0:
            parts.append(expr[start:i])
            start = i + 1
    parts.append(expr[start:])
    return parts


def _mangle_calls(text: str, names, sites: dict) -> str:
    """Give every call of a user function in ``text`` its own site name.

    gen keeps separate state per call site, so ``f(a) + f(b)`` is two
    instances; the rewrite ``f(`` -> ``_gfnN_(`` lets the runtime bind each
    site to its own :class:`_FnInstance`.
    """
    if not names:
        return text
    pattern = re.compile(r"(?<![\w.])(" + "|".join(map(re.escape, names)) + r")\s*\(")

    def _site(match):
        site = f"_gfn{len(sites)}_"
        sites[site] = match.group(1)
        return site + "("

    return pattern.sub(_site, text)


def _has_return(nodes) -> bool:
    for node in nodes:
        if node[0] == "return":
            return True
        if node[0] == "if":
            if any(_has_return(block) for _, block in node[1]):
                return True
            if node[2] and _has_return(node[2]):
                return True
    return False


class _GenFunction:
    """A parsed user function: parameters, local Histories, body, return."""

    def __init__(self, kernel: GenKernel, name: str, params, body: str, names):
        if re.search(r"(?<![\w.])(Delay|Param)\s", body):
            raise UnsupportedKernel(
                f"function {name!r}: Delay/Param declarations inside a function "
                f"are not simulated")
        self.name = name
        self.params = list(params)
        self.sites: dict[str, str] = {}
        body = _mangle_calls(body, names, self.sites)
        self.histories, _ = GenKernel._parse_decls(body)
        nodes = kernel._parse_block(body, 0, top=True)
        if not nodes or nodes[-1][0] != "return" or _has_return(nodes[:-1]):
            raise UnsupportedKernel(
                f"function {name!r} must end in exactly one top-level return")
        self.nodes = nodes[:-1]
        self.ret = nodes[-1][1]


class _FnInstance:
    """One call site of a user function, holding that site's History state."""

    def __init__(self, fn: _GenFunction, functions: dict, depth: int = 0):
        if depth > 32:
            raise UnsupportedKernel("recursive gen function calls are not supported")
        self.fn = fn
        self.hist = dict(fn.histories)
        self.children = {site: _FnInstance(functions[callee], functions, depth + 1)
                         for site, callee in fn.sites.items()}

    def call(self, base: dict, *args):
        fn = self.fn
        if len(args) != len(fn.params):
            raise UnsupportedKernel(
                f"{fn.name}() takes {len(fn.params)} arguments, got {len(args)}")
        ns = dict(base)
        ns.update(self.hist)
        ns.update(zip(fn.params, args, strict=True))
        for site, child in self.children.items():
            ns[site] = functools.partial(child.call, base)
        GenKernel._exec_nodes(fn.nodes, ns)
        result = eval(fn.ret, {"__builtins__": {}}, ns)  # noqa: S307
        for h in self.hist:
            self.hist[h] = ns[h]
        return result


class GenKernel:
    """A parsed, simulatable gen~ codebox kernel.

    The body is parsed into a small node tree of assignments and ``if`` /
    ``else if`` / ``else`` blocks; per sample the tree is walked over a
    persistent namespace (History values carry across samples). A History var
    written in several mutually-exclusive branches is fine — only the taken
    branch runs — and a sequential re-write within one block is last-wins, both
    matching gen. Leading function definitions are parsed separately and run
    per call site (see :class:`_FnInstance`).
    """

    def __init__(self, code: str):
        body = "\n".join(_strip_comments(code))
        self._refuse_unsupported(body)
        defs, body = self._split_functions(body)
        self.functions: dict[str, _GenFunction] = {}
        for name, (params, fn_body) in defs.items():
            # a function may call any function defined before it
            self.functions[name] = _GenFunction(self, name, params, fn_body,
                                                list(self.functions))
        self.sites: dict[str, str] = {}
        body = _mangle_calls(body, list(self.functions), self.sites)
        self.histories, self.params = self._parse_decls(body)
        self.delays = dict(re.findall(
            r"(?<![\w.])Delay\s+([A-Za-z_]\w*)\s*\(([^;]*?)\)\s*;", body))
        self.nodes = self._parse_block(body, 0, top=True)
        if _has_return(self.nodes):
            raise UnsupportedKernel("'return' outside a function definition")
        self.num_outs = self._count_outs(self.nodes)

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
        # if/else ARE supported; loops are not.
        for kw in ("for", "while", "function"):
            if re.search(rf"(?<![A-Za-z0-9_]){kw}(?![A-Za-z0-9_])", body):
                raise UnsupportedKernel(
                    f"control-flow keyword {kw!r} is not supported"
                )

    @staticmethod
    def _split_functions(body: str):
        """Peel the leading ``name(params) { ... }`` definitions off ``body``."""
        defs: dict[str, tuple[list[str], str]] = {}
        pos, n = 0, len(body)
        while True:
            while pos < n and body[pos] in " \t\r\n":
                pos += 1
            head = _FN_HEAD.match(body, pos)
            if not head or head.group(1) in _CONTROL_WORDS:
                break
            close = GenKernel._match(body, head.end() - 1, "{", "}")
            params = [p.strip() for p in head.group(2).split(",") if p.strip()]
            defs[head.group(1)] = (params, body[head.end():close])
            pos = close + 1
        return defs, body[pos:]

    @staticmethod
    def _parse_decls(body: str):
        histories: dict[str, float] = {}
        params: dict[str, float] = {}
        for kind, name, init in re.findall(
            r"(History|Param)\s+([A-Za-z_]\w*)\s*\(\s*(-?[\d.]+)\s*(?:,[^)]*)?\)", body
        ):
            (histories if kind == "History" else params)[name] = float(init)
        return histories, params

    @staticmethod
    def _match(body: str, pos: int, open_ch: str, close_ch: str):
        """Return the index of the close char matching the open char at ``pos``."""
        depth = 0
        for i in range(pos, len(body)):
            if body[i] == open_ch:
                depth += 1
            elif body[i] == close_ch:
                depth -= 1
                if depth == 0:
                    return i
        raise UnsupportedKernel(f"unbalanced {open_ch!r} in kernel")

    @staticmethod
    def _compile_expr(expr: str):
        return compile(_ternary_to_py(_logic_to_py(expr.strip())), "<gen>", "eval")

    def _parse_block(self, body: str, pos: int, top: bool = False):
        """Parse a sequence of statements until ``}`` (or end-of-body if top)."""
        nodes: list = []
        n = len(body)
        while pos < n:
            while pos < n and body[pos] in " \t\r\n":
                pos += 1
            if pos >= n:
                break
            if body[pos] == "}":
                if top:
                    raise UnsupportedKernel("unexpected '}' at top level")
                return nodes, pos
            if re.match(r"if(?![A-Za-z0-9_])", body[pos:]):
                node, pos = self._parse_if(body, pos)
                nodes.append(node)
                continue
            semi = body.find(";", pos)
            if semi < 0:
                raise UnsupportedKernel(f"statement without ';': {body[pos:pos + 40]!r}")
            stmt = body[pos:semi].strip()
            pos = semi + 1
            if not stmt or stmt.startswith(("History ", "Param ", "Delay ")):
                continue
            ret = re.fullmatch(r"return(?![A-Za-z0-9_])\s*(.*)", stmt, re.S)
            if ret:
                parts = [_ternary_to_py(_logic_to_py(part.strip()))
                         for part in _split_top_commas(ret.group(1))]
                expr = parts[0] if len(parts) == 1 else (
                    "(" + ", ".join(f"({part})" for part in parts) + ")")
                nodes.append(("return", compile(expr, "<gen>", "eval")))
                continue
            write = re.fullmatch(r"([A-Za-z_]\w*)\.write\((.*)\)", stmt, re.S)
            if write:
                nodes.append(("write", write.group(1), self._compile_expr(write.group(2))))
                continue
            nodes.append(self._parse_assign(stmt))
        if top:
            return nodes
        raise UnsupportedKernel("unterminated block (missing '}')")

    def _parse_assign(self, stmt: str):
        if "=" not in stmt:
            raise UnsupportedKernel(f"non-assignment statement: {stmt!r}")
        lhs, rhs = stmt.split("=", 1)
        targets = [t.strip() for t in lhs.split(",")]
        for target in targets:
            if not re.fullmatch(r"[A-Za-z_]\w*", target):
                raise UnsupportedKernel(f"unsupported assignment target: {lhs.strip()!r}")
        if len(targets) > 1:
            return ("massign", targets, self._compile_expr(rhs))
        return ("assign", targets[0], self._compile_expr(rhs))

    def _parse_if(self, body: str, pos: int):
        """Parse ``if (c){...} else if (c){...} else {...}`` into an if-node."""
        branches = []           # list of (compiled_cond, [nodes])
        else_nodes = None
        while True:
            pos += 2            # skip 'if'
            while body[pos] in " \t\r\n":
                pos += 1
            if body[pos] != "(":
                raise UnsupportedKernel("expected '(' after 'if'")
            close = self._match(body, pos, "(", ")")
            cond = body[pos + 1:close].strip()
            pos = close + 1
            while body[pos] in " \t\r\n":
                pos += 1
            if body[pos] != "{":
                raise UnsupportedKernel("expected '{' after if-condition")
            end = self._match(body, pos, "{", "}")
            block, _ = self._parse_block(body, pos + 1)
            branches.append((self._compile_expr(cond), block))
            pos = end + 1
            # look for a following 'else' / 'else if'
            save = pos
            while pos < len(body) and body[pos] in " \t\r\n":
                pos += 1
            if not re.match(r"else(?![A-Za-z0-9_])", body[pos:]):
                pos = save
                break
            pos += 4
            while body[pos] in " \t\r\n":
                pos += 1
            if re.match(r"if(?![A-Za-z0-9_])", body[pos:]):
                continue        # 'else if' -> another branch
            if body[pos] != "{":
                raise UnsupportedKernel("expected '{' or 'if' after 'else'")
            end = self._match(body, pos, "{", "}")
            else_nodes, _ = self._parse_block(body, pos + 1)
            pos = end + 1
            break
        return ("if", branches, else_nodes), pos

    def _count_outs(self, nodes) -> int:
        num = 0
        for node in nodes:
            if node[0] == "write":
                continue
            if node[0] in ("assign", "massign"):
                targets = node[1] if node[0] == "massign" else [node[1]]
                for target in targets:
                    m = re.fullmatch(r"out(\d+)", target)
                    if m:
                        num = max(num, int(m.group(1)))
            else:  # if-node
                for _, block in node[1]:
                    num = max(num, self._count_outs(block))
                if node[2]:
                    num = max(num, self._count_outs(node[2]))
        return num

    @staticmethod
    def _exec_nodes(nodes, ns) -> None:
        for node in nodes:
            if node[0] == "write":
                ns[node[1]].write(eval(node[2], {"__builtins__": {}}, ns))  # noqa: S307
            elif node[0] == "assign":
                ns[node[1]] = eval(node[2], {"__builtins__": {}}, ns)  # noqa: S307
            elif node[0] == "massign":
                values = eval(node[2], {"__builtins__": {}}, ns)  # noqa: S307
                if not isinstance(values, tuple) or len(values) != len(node[1]):
                    raise UnsupportedKernel(
                        f"{len(node[1])} targets but the call returned "
                        f"{len(values) if isinstance(values, tuple) else 1} value(s)")
                ns.update(zip(node[1], values, strict=True))
            else:  # ("if", branches, else_nodes)
                for cond_code, block in node[1]:
                    if eval(cond_code, {"__builtins__": {}}, ns):  # noqa: S307
                        GenKernel._exec_nodes(block, ns)
                        break
                else:
                    if node[2] is not None:
                        GenKernel._exec_nodes(node[2], ns)

    def run(self, inputs=None, params=None, samplerate=48000.0, num_samples=None):
        """Run the kernel and return ``{outK: [values...]}``.

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

        sr = float(samplerate)
        base = dict(_FUNCS)
        base["samplerate"] = sr
        base["mstosamps"] = lambda ms: ms * sr * 0.001
        base["sampstoms"] = lambda samps: samps * 1000.0 / sr

        outs = {f"out{k}": [0.0] * num_samples for k in range(1, self.num_outs + 1)}
        delays = {name: _DelayLine(int(eval(size, {"__builtins__": {}}, base)))  # noqa: S307
                  for name, size in self.delays.items()}
        sites = {site: functools.partial(
                     _FnInstance(self.functions[callee], self.functions).call, base)
                 for site, callee in self.sites.items()}
        for n in range(num_samples):
            ns = dict(base)
            ns.update(delays)
            ns.update(hist)
            ns.update(pvals)
            ns.update(sites)
            for name, seq in inputs.items():
                ns[name] = float(seq[n]) if n < len(seq) else 0.0
            self._exec_nodes(self.nodes, ns)
            for h in hist:
                hist[h] = ns[h]
            for line in delays.values():
                line.advance()
            for k in range(1, self.num_outs + 1):
                outs[f"out{k}"][n] = ns[f"out{k}"]
        return outs


def simulate(code: str, inputs=None, params=None, samplerate=48000.0,
             num_samples=None):
    """Parse + run a gen kernel in one call. See :meth:`GenKernel.run`."""
    return GenKernel(code).run(inputs, params, samplerate, num_samples)
