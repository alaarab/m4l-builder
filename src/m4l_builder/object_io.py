"""Infer a Max object box's inlet/outlet shape from its text.

``add_newobj("gate 4")`` needs ``numinlets=2, numoutlets=4`` and an
``outlettype`` list. This module derives those from the object text so callers
can leave them out:

1. **Argument rules** for objects whose shape follows their arguments
   (``pack``/``unpack``/``route``/``sel``/``trigger``/``gate``/``switch``/
   ``selector~``/``join``/``spray``/``funnel``, int/float math, send/receive,
   ``expr``/``if``/``sprintf`` ...).
2. **The vendored maxdiff dataset** (``vendor.maxdiff.known_objects``, one
   instance per object measured from Max itself — the same data ``box_lint``
   validates against) for everything else: always for the bare object name,
   and with arguments only for objects listed in ``_ARGS_KEEP_SHAPE``, whose
   shape was checked not to change with arguments.

Anything else raises :class:`UnknownObjectIO` asking for explicit
``numinlets``/``numoutlets`` — the shape is never guessed. The rules and the
allowlist were checked against the boxes Max 9 itself saved in its help
patches and Live's factory devices.
"""

from __future__ import annotations

import re
from typing import NamedTuple

from .box_lint import known_object_spec

__all__ = ["ObjectIO", "UnknownObjectIO", "infer_object_io", "resolve_newobj_io"]


class ObjectIO(NamedTuple):
    numinlets: int
    numoutlets: int
    outlettype: list[str]


class UnknownObjectIO(ValueError):
    """The object's inlet/outlet shape can't be derived from its text."""


_INT = re.compile(r"^[-+]?\d+$")
_FLOAT = re.compile(r"^[-+]?(\d+\.\d*|\.\d+)([eE][-+]?\d+)?$|^[-+]?\d+[eE][-+]?\d+$")

# The shape comes from an embedded/loaded patcher, a script, or the voice/FFT
# context — nothing in the text says how many inlets and outlets there are.
_OPAQUE = {
    "p": "an embedded patcher", "patcher": "an embedded patcher",
    "bpatcher": "the loaded patcher", "poly~": "the voice patcher",
    "pfft~": "the FFT patcher", "gen~": "the gen patcher",
    "gen": "the gen patcher", "js": "the script", "v8": "the script",
    "jsui": "the script", "v8ui": "the script", "node.script": "the script",
    "jweb": "the page", "amxd~": "the loaded device", "vst~": "the plugin",
    "in": "the enclosing poly~/pfft~", "out": "the enclosing poly~/pfft~",
    "in~": "the enclosing poly~/pfft~", "out~": "the enclosing poly~/pfft~",
    "fftin~": "the enclosing pfft~", "fftout~": "the enclosing pfft~",
    "inlet": "the enclosing patcher", "outlet": "the enclosing patcher",
    "inlet~": "the enclosing patcher", "outlet~": "the enclosing patcher",
    "expr~": "the expression", "mc.gen~": "the gen patcher",
}

# Objects whose dataset shape also holds with creation arguments. Each was
# checked against Max's own saved boxes: arguments set initial values here,
# never the number or type of inlets/outlets.
_ARGS_KEEP_SHAPE = frozenset({
    "abs~", "adsr~", "allpass~", "append", "average~", "biquad~", "buffer~",
    "change~", "clip", "clip~", "click~", "coll", "comb~", "count~", "counter",
    "cycle~", "delay", "delay~", "delta~", "deltaclip~", "dict", "edge~",
    "filtercoeff~", "info~", "line~", "listfunnel", "live.object",
    "live.observer", "live.path", "live.remote~", "loadmess", "lores~",
    "metro", "onepole~", "opendialog", "peek~", "phasor~", "pong~", "pow~",
    "prepend", "rampsmooth~", "random", "rate~", "reson~", "saw~",
    "scale", "scale~", "sig~", "slide~", "snapshot~", "speedlim", "svf~",
    "tapin~", "thresh~", "triangle~", "uzi", "zl", "zl.group",
    "zl.reg",
})

_INT_BINOPS = frozenset({"+", "-", "*", "/", "!-", "!/"})
_INT_ONLY_BINOPS = frozenset({
    "%", "==", "!=", ">", "<", ">=", "<=", "&&", "||", "&", "|", "<<", ">>",
})
_SIGNAL_BINOPS = frozenset({
    "+~", "-~", "*~", "/~", "%~", "!-~", "!/~", "==~", "!=~", ">~", "<~",
    ">=~", "<=~", "pow~", "minimum~", "maximum~",
})

_TRIGGER_TYPES = {"b": "bang", "i": "int", "f": "float", "l": "", "a": "", "s": ""}


def _numtype(token: str, default: str) -> str:
    if _INT.match(token):
        return "int"
    if _FLOAT.match(token):
        return "float"
    return default


def _underivable(text: str, why: str) -> UnknownObjectIO:
    return UnknownObjectIO(
        f"[{text}]: {why}; pass numinlets/numoutlets explicitly")


def _count(args: list[str], default: int, head: str) -> int:
    if not args:
        return default
    if not _INT.match(args[0]) or int(args[0]) < 1:
        raise UnknownObjectIO(
            f"[{head} {args[0]}]: the count argument is not a literal positive "
            "integer; pass numinlets/numoutlets explicitly")
    return int(args[0])


def _split(text: str) -> tuple[str, list[str], dict[str, list[str]]]:
    tokens = text.split()
    if not tokens:
        raise UnknownObjectIO("empty object text; pass numinlets/numoutlets explicitly")
    head, rest = tokens[0], tokens[1:]
    args: list[str] = []
    attrs: dict[str, list[str]] = {}
    current: list[str] | None = None
    for token in rest:
        if token.startswith("@") and len(token) > 1:
            current = attrs.setdefault(token[1:], [])
        elif current is None:
            args.append(token)
        else:
            current.append(token)
    return head, args, attrs


def _dollar_inlets(text: str, pattern: str) -> int:
    return max((int(n) for n in re.findall(pattern, text)), default=1)


def _rule(head: str, args: list[str], attrs: dict, text: str) -> ObjectIO | None:
    n = len(args)
    if head in ("pack", "pak"):
        return ObjectIO(n or 2, 1, [""])
    if head == "unpack":
        types = [_numtype(a, "int" if a == "i" else "float" if a == "f" else "")
                 for a in args] or ["int", "int"]
        return ObjectIO(1, len(types), types)
    if head in ("t", "trigger"):
        types = [_TRIGGER_TYPES.get(a, _numtype(a, "?")) for a in args] or ["", ""]
        if "?" in types:
            # Max's saved outlettype for a constant-symbol outlet isn't consistent
            raise _underivable(text, "a constant-symbol outlet's type isn't fixed")
        return ObjectIO(1, len(types), types)
    if head in ("route", "routepass"):
        k = n or 1
        return ObjectIO(k + 1, k + 1, [""] * (k + 1))
    if head in ("sel", "select"):
        k = n or 1
        return ObjectIO(k + 1, k + 1, ["bang"] * k + [""])
    if head == "gate":
        k = _count(args, 1, head)
        return ObjectIO(2, k, [""] * k)
    if head == "gate~":
        k = _count(args, 1, head)
        return ObjectIO(2, k, ["signal"] * k)
    if head == "switch":
        return ObjectIO(_count(args, 2, head) + 1, 1, [""])
    if head == "selector~":
        return ObjectIO(_count(args, 1, head) + 1, 1, ["signal"])
    if head == "join":
        return ObjectIO(_count(args, 2, head), 1, [""])
    if head == "unjoin":
        k = _count(args, 2, head) + 1
        return ObjectIO(1, k, [""] * k)
    if head == "spray":
        k = _count(args, 2, head)
        return ObjectIO(1, k, [""] * k)
    if head == "funnel":
        return ObjectIO(_count(args, 2, head), 1, ["list"])
    if head in ("plugin~", "plugout~"):
        if args:
            raise _underivable(text, "arguments are channel indices")
        k = _count(attrs.get("chans", []), 2, head)
        return ObjectIO(k, k, ["signal"] * k)
    if head == "mc.pack~":
        return ObjectIO(_count(args or attrs.get("chans", []), 2, head), 1,
                        ["multichannelsignal"])
    if head == "mc.unpack~":
        k = _count(args or attrs.get("chans", []), 2, head)
        return ObjectIO(1, k, ["signal"] * k)
    if head == "tapout~":
        k = n or 1
        return ObjectIO(k, k, ["signal"] * k)
    if head in _INT_BINOPS:
        kind = _numtype(args[0], "") if args else "int"
        if not kind:
            raise _underivable(text, "the output type follows a non-literal argument")
        return ObjectIO(2, 1, [kind])
    if head in _INT_ONLY_BINOPS:
        return ObjectIO(2, 1, ["int"])
    if head in _SIGNAL_BINOPS:
        return ObjectIO(2, 1, ["signal"])
    if head in ("f", "float"):
        return ObjectIO(2, 1, ["float"])
    if head in ("i", "int"):
        return ObjectIO(2, 1, ["int"])
    if head in ("s", "send", "s~", "send~"):
        if n != 1:
            raise _underivable(text, "it needs exactly one name argument")
        return ObjectIO(1, 0, [])
    if head in ("r", "receive"):
        return ObjectIO(0 if n else 1, 1, [""])
    if head in ("v", "value", "pv"):
        if not n:
            raise _underivable(text, "it needs a name argument")
        return ObjectIO(1, 1, [""])
    if head == "expr":
        if re.search(r"\bin\d", text):
            raise _underivable(text, "inN inputs aren't counted")
        return ObjectIO(_dollar_inlets(text, r"\$[ifs](\d+)"), 1, [""])
    if head == "if":
        outs = 2 if "out2" in text else 1
        return ObjectIO(_dollar_inlets(text, r"\$[ifs](\d+)"), outs, [""] * outs)
    if head == "sprintf":
        if attrs:
            raise _underivable(text, "attributes aren't parsed")
        conversions = len(re.findall(r"%[^%]", text.replace("%%", "")))
        return ObjectIO(max(conversions, 1), 1, [""])
    return None


def infer_object_io(text: str) -> ObjectIO:
    """The ``(numinlets, numoutlets, outlettype)`` of the Max object ``text``.

    Raises :class:`UnknownObjectIO` when the shape isn't known.
    """
    if not isinstance(text, str):
        raise UnknownObjectIO(f"object text must be a string, got {text!r}")
    head, args, attrs = _split(text.strip())
    if '"' in text:
        raise UnknownObjectIO(
            f"[{text}]: quoted arguments aren't parsed; pass "
            "numinlets/numoutlets explicitly")
    if head in _OPAQUE:
        raise UnknownObjectIO(
            f"[{text}]: {head}'s inlets and outlets are set by {_OPAQUE[head]}; "
            "pass numinlets/numoutlets explicitly")
    ruled = _rule(head, args, attrs, text)
    if ruled is not None:
        return ruled
    if head.startswith(("mc.", "mcs.")):
        # the dataset aliases mc.* to the mono object, whose outlet types differ
        raise UnknownObjectIO(
            f"[{text}]: multichannel shapes aren't tabled; pass "
            "numinlets/numoutlets explicitly")
    spec = known_object_spec(head)
    if spec is not None and spec.get("maxclass") != "newobj":
        raise UnknownObjectIO(
            f"[{text}]: {head} is a UI object (maxclass {spec['maxclass']!r}), "
            "not a newobj; pass numinlets/numoutlets explicitly")
    if spec is None or (spec.get("numinlets") == 0 and spec.get("numoutlets") == 0):
        raise UnknownObjectIO(
            f"[{text}]: no inlet/outlet data for {head!r}; pass "
            "numinlets/numoutlets (and outlettype) explicitly")
    if attrs or (args and (
            head not in _ARGS_KEEP_SHAPE
            # [prepend 0] grows a second inlet; a symbol argument doesn't
            or (head in ("prepend", "append") and _numtype(args[0], "") != "")
            # [scale minor] isn't the 6-inlet range mapper
            or (head in ("scale", "scale~")
                and any(_numtype(a, "") == "" for a in args)))):
        raise UnknownObjectIO(
            f"[{text}]: only bare {head!r} has known inlets/outlets and its "
            "arguments or attributes may change them; pass "
            "numinlets/numoutlets explicitly")
    outlettype = list(spec.get("outlettype") or [])
    return ObjectIO(int(spec["numinlets"]), int(spec["numoutlets"]), outlettype)


def resolve_newobj_io(text: str, numinlets: int | None, numoutlets: int | None,
                      outlettype: list | None) -> tuple[int, int, list | None]:
    """Fill in whichever of the three the caller left as ``None``.

    Explicit values always win. With both counts given nothing is inferred
    (``outlettype`` stays as passed), so existing calls are unchanged. An
    inferred ``outlettype`` is only used when it matches the final outlet count.
    """
    if numinlets is not None and numoutlets is not None:
        return numinlets, numoutlets, outlettype
    io = infer_object_io(text)
    ni = io.numinlets if numinlets is None else numinlets
    no = io.numoutlets if numoutlets is None else numoutlets
    if outlettype is None and no == io.numoutlets:
        outlettype = io.outlettype
    return ni, no, outlettype
