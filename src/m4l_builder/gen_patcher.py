"""Shared gen~ patcher (.gendsp) codegen.

The single canonical builder for a gen-namespace patcher (``classnamespace``
``dsp.gen``) holding one codebox wired to N signal ins/outs, serialized as a
``.gendsp`` support file and referenced from a patcher as ``gen~ <stem>``.

Why this and not a flat ``code`` attribute on a ``gen~`` box: a flat ``code``
attribute does NOT program the object — it loads as the default passthrough
template (silently). The working mechanism, proven live in Live 12, is exactly
this gen-namespace patcher shipped as a separate support file. See the runtime
pitfalls memory ("gen~ flat code box attributes do NOT program the gen~").

This was copy-pasted into every DSP plugin's ``build.py`` (pressure, ceiling,
heat, echotide, spectrum_analyzer); promoting it to the library makes it the one
shared codegen the flagships compose their gen DSP on top of.
"""

from __future__ import annotations

import hashlib
import json
import re

from .gen_lint import lint_genexpr

__all__ = ["build_gendsp", "embed_gendsp", "gendsp_support_name"]

_STATE_DECL = ("History ", "Delay ", "Data ")
# A gen function def opens as ``name(args){`` (NO ``function`` keyword) on one line.
_FUNC_DEF = re.compile(r"^\w+\s*\([^)]*\)\s*\{")


def _is_stmt(stripped: str) -> bool:
    """A depth-0 line that is an executable statement (not a decl/function/comment)."""
    if not stripped or stripped.startswith(_STATE_DECL):
        return False
    if stripped.startswith(("Param ", "Buffer ", "Const ", "//", "/*", "*")):
        return False
    if stripped.startswith("function ") or _FUNC_DEF.match(stripped):
        return False
    return True


def _hoist_history(code: str) -> str:
    """Hoist top-level History/Delay/Data decls above the first statement.

    gen REQUIRES every state declaration to precede the first executable statement.
    Splicing two-or-more self-contained stateful kernels (e.g. two ``tilt_shelf``
    blocks, an FDN's delay lines) interleaves a later kernel's ``History`` AFTER an
    earlier kernel's body, which SILENCES the whole codebox — Live-CONFIRMED: Tilt,
    Aurora, Mono Maker and Snap all shipped silent (output meter 0.0) from exactly
    this. This moves every **depth-0** ``History``/``Delay``/``Data`` line to just
    before the first depth-0 statement.

    SAFE: a true NO-OP unless a violation actually exists (a state decl after the
    first statement), so correct codeboxes are byte-identical; never touches decls
    inside function bodies (brace depth > 0).
    """
    lines = code.split("\n")
    depth = 0
    seen_stmt = False
    violation = False
    for ln in lines:
        s = ln.strip()
        if depth == 0:
            if s.startswith(_STATE_DECL):
                if seen_stmt:
                    violation = True
                    break
            elif _is_stmt(s):
                seen_stmt = True
        depth += ln.count("{") - ln.count("}")
    if not violation:
        return code
    hoist: list[str] = []
    keep: list[str] = []
    first_stmt: int | None = None
    depth = 0
    for ln in lines:
        s = ln.strip()
        if depth == 0 and s.startswith(_STATE_DECL):
            hoist.append(ln)
            depth += ln.count("{") - ln.count("}")
            continue
        if depth == 0 and first_stmt is None and _is_stmt(s):
            first_stmt = len(keep)
        keep.append(ln)
        depth += ln.count("{") - ln.count("}")
    if first_stmt is None:
        first_stmt = len(keep)
    return "\n".join(keep[:first_stmt] + hoist + keep[first_stmt:])


def gendsp_support_name(stem: str, code: str, *, hash_len: int = 8) -> str:
    """Content-addressed ``.gendsp`` filename: ``f"{stem}_{hash}.gendsp"``.

    Max caches a COMPILED ``gen~`` by its patcher *filename*, so editing the
    GenExpr without renaming the support file makes Live serve the STALE compile —
    Live-CONFIRMED: Tilt, Aurora, Mono Maker and Snap all shipped silent (output
    meter 0.0) until their ``.gendsp`` stem was bumped BY HAND (``heat_core_v23``
    etc.). Deriving the suffix from a hash of ``code`` automates that bump: the
    same source reuses the cache (byte-identical name), and ANY source change
    yields a new filename and a guaranteed fresh compile — eliminating the manual
    ``GEN_FILENAME`` version bump and the whole stale-gen-cache failure class.

    ``stem`` stays a stable, human-readable prefix (it is the display name in the
    gen editor); only the underscore-joined hash suffix moves. Underscore (not a
    dot) matches the proven ``<stem>_<suffix>.gendsp`` convention so ``gen~
    <stem>_<hash>`` resolves exactly the way the hand-versioned names did.

    Hash ``code`` (the GenExpr source — the DSP identity), NOT the full serialized
    patcher, so a cosmetic ``codebox_h``/``patcher_h`` editor-window tweak does not
    churn the filename while any real DSP edit does. ``blake2b`` keeps it a plain
    content fingerprint (no security-hash lint noise); ``hash_len`` hex chars
    (default 8 = 32 bits) make a collision between two live kernels negligible.
    """
    digest = hashlib.blake2b(
        code.encode("utf-8"), digest_size=(hash_len + 1) // 2
    ).hexdigest()
    return f"{stem}_{digest[:hash_len]}.gendsp"


def build_gendsp(
    code: str,
    numins: int,
    numouts: int,
    *,
    codebox_h: float = 560.0,
    patcher_h: float = 660.0,
    lint: bool = True,
) -> str:
    """Serialize a gen~ patcher (.gendsp) with one codebox wired to ins/outs.

    ``code`` is the GenExpr source; ``numins``/``numouts`` are the signal in/out
    counts (an ``in N`` / ``out N`` object per channel, wired to the codebox).

    With ``lint=True`` (default) the GenExpr is checked by
    :func:`m4l_builder.gen_lint.lint_genexpr` and a build-time ``ValueError`` is
    raised on a dead/passthrough signal out, an out-of-range ``in``/``out`` index,
    or a multi-line ternary — turning those silent-in-Live failures (the
    "advertised but unwired / dynamic-EQ-never-touches-audio" class) into a build
    error. Pass ``lint=False`` only for the rare intentional exception.

    ``codebox_h`` / ``patcher_h`` size the gen editor window only — purely
    cosmetic, no DSP effect. They default to the suite-wide 560/660 and are
    overridable so an existing plugin can reproduce its exact prior bytes (e.g.
    pressure historically shipped 540/640).
    """
    code = _hoist_history(code)  # state decls before first statement, or the codebox silences
    if lint:
        issues = lint_genexpr(code, numins, numouts)
        if issues:
            raise ValueError(
                "build_gendsp: GenExpr lint failed ("
                + str(len(issues)) + " issue(s); pass lint=False to bypass):\n  - "
                + "\n  - ".join(issues)
            )
    boxes = [{
        "box": {
            "id": "codebox",
            "maxclass": "codebox",
            "code": code,
            "numinlets": numins,
            "numoutlets": numouts,
            "patching_rect": [200.0, 40.0, 460.0, codebox_h],
        }
    }]
    lines = []
    for i in range(numins):
        boxes.append({"box": {
            "id": f"in_{i + 1}", "maxclass": "newobj", "text": f"in {i + 1}",
            "numinlets": 0, "numoutlets": 1, "outlettype": [""],
            "patching_rect": [40.0, 40.0 + i * 40.0, 40.0, 22.0]}})
        lines.append({"patchline": {"source": [f"in_{i + 1}", 0],
                                    "destination": ["codebox", i]}})
    for o in range(numouts):
        boxes.append({"box": {
            "id": f"out_{o + 1}", "maxclass": "newobj", "text": f"out {o + 1}",
            "numinlets": 1, "numoutlets": 0,
            "patching_rect": [700.0, 60.0 + o * 40.0, 50.0, 22.0]}})
        lines.append({"patchline": {"source": ["codebox", o],
                                    "destination": [f"out_{o + 1}", 0]}})
    return json.dumps({"patcher": {
        "fileversion": 1,
        "appversion": {"major": 8, "minor": 6, "revision": 0,
                       "architecture": "x64", "modernui": 1},
        "classnamespace": "dsp.gen",
        "rect": [40.0, 40.0, 820.0, patcher_h],
        "bglocked": 0, "openinpresentation": 0,
        "default_fontsize": 12.0, "default_fontname": "Arial",
        "gridonopen": 1, "gridsize": [15.0, 15.0],
        "boxes": boxes, "lines": lines,
    }}, indent=2)


def embed_gendsp(
    code: str,
    numins: int,
    numouts: int,
    *,
    box_id: str = "gen",
    patching_rect: list = None,
    lint: bool = True,
    codebox_h: float = 560.0,
    patcher_h: float = 660.0,
) -> dict:
    """Return a ``gen~`` BOX dict with the gen patcher EMBEDDED inline (the
    Particle-Reverb structure) instead of referenced as an external ``.gendsp``.

    LIVE-VERIFIED (ZZGenFuncEmbed, output meter 0.737 on an empty monitored track):
    an EMBEDDED gen~ codebox MAY define user functions and still compile + pass
    audio — whereas the EXTERNAL ``.gendsp`` path (``add_support_file`` + ``gen~
    <stem>``) silences a codebox that defines any ``name(args){...}`` function. So
    **embed** when your gen code uses the ``gen_stateful`` function primitives
    (``op`` / ``svf`` / ``allpass`` / ``lowpass_12`` / ``variable_sigmoid`` /
    ``modulated_allpass_reverb`` / …); use :func:`build_gendsp` + a support file
    only for fully inlined (function-free) code.

    Pass the result straight to ``device.add_box(...)``, then wire its inlets/outlets
    like any ``gen~`` (one signal inlet per ``in N``, one signal outlet per ``out N``).
    """
    patcher = json.loads(build_gendsp(
        code, numins, numouts, lint=lint,
        codebox_h=codebox_h, patcher_h=patcher_h,
    ))["patcher"]
    return {"box": {
        "id": box_id,
        "maxclass": "newobj",
        "text": "gen~",
        "numinlets": max(1, numins),
        "numoutlets": numouts,
        "outlettype": ["signal"] * numouts,
        "patching_rect": patching_rect or [80.0, 240.0, 200.0, 22.0],
        "patcher": patcher,
    }}
