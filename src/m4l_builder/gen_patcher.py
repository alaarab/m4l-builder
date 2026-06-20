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

import json

from .gen_lint import lint_genexpr

__all__ = ["build_gendsp"]


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
