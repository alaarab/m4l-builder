"""Ableton production-standards linter — the *static* subset of Ableton's
published Max for Live device conventions (parameter naming, presentation
geometry, forbidden objects, JavaScript style) decidable from the patcher JSON.

This is the pre-Live complement to the live ``console_audit`` harness: the audit
loads a device in Live and catches load-time console errors, while this checks
the built ``Device`` statically — before it is ever loaded — against the parts
of Ableton's checklist that are decidable from the patcher JSON alone.

**Advisory by design.** Everything here returns :class:`ValidationIssue`s for a
report; nothing gates a build. Run it via :meth:`Device.check_guidelines`, the
``python -m m4l_builder.guidelines`` CLI, or ``tests/test_guidelines.py``.

Checks implemented (all statically decidable):
  * unknown/misspelled object names (typo detection vs the maxdiff roster);
  * duplicate parameter Long Names / Scripting Names (Ableton requires both
    unique within a device);
  * auto-indexed default parameter names (``live.numbox[1]`` / trailing ``[N]``);
  * non-integer ``patching_rect`` positions (the whole-pixel grid convention) —
    ``final_checklist_issues`` already covers ``presentation_rect``;
  * plus the existing ``final_checklist_issues`` set (forbidden print/dac~/adc~,
    non-local send/receive, fractional presentation rects).

Deliberately NOT here (need Live or human judgement, or an attribute whose
semantics aren't safe to assume yet): CPU load, audio clicks, render/sample-rate
consistency, Push display, presets/demo, external testing, per-param modulation
mode (Live already applies a correct default so "unset" is not a defect),
live.text Mouse-Up mode, and MPE flags. See the module TODO for the follow-ups.
"""
from __future__ import annotations

import re

from .box_lint import known_object_names
from .patcher_walk import iter_boxes
from .validation import ValidationIssue, final_checklist_issues

# Legit Max/Live object names that postdate the vendored maxdiff dataset, so the
# arity roster doesn't know them. Harvested from the (console-clean) fleet's
# actual usage — every name here is a confirmed-valid object, not a guess.
_EXTRA_KNOWN = frozenset({
    "live.miditool.in", "live.miditool.out",   # Live 12 MIDI Tools I/O
    "loudness~",                                # Max 9 / Live 12 loudness meter
})

# maxclasses whose arity/identity comes from a script or embedded patcher, so
# the "is this a real object name" question doesn't apply.
_SCRIPT_LIKE = frozenset({
    "jsui", "v8ui", "js", "v8", "gen~", "bpatcher", "poly~", "pfft~",
})

_AUTO_INDEX_RE = re.compile(r"\[\d+\]$")


def _all_known_names() -> frozenset[str]:
    return known_object_names() | _EXTRA_KNOWN | _SCRIPT_LIKE


def _edit_distance_le_1(a: str, b: str) -> bool:
    """True iff Levenshtein(a, b) <= 1 (one insert/delete/substitute). Bounded
    and allocation-free — the hot path for typo detection."""
    if a == b:
        return True
    la, lb = len(a), len(b)
    if abs(la - lb) > 1:
        return False
    if la > lb:              # make `a` the shorter (or equal-length) string
        a, b, la, lb = b, a, lb, la
    i = 0
    while i < la and a[i] == b[i]:
        i += 1
    if la == lb:             # substitution: the tails after i must be identical
        return a[i + 1:] == b[i + 1:]
    return a[i:] == b[i + 1:]  # insertion in b: skip b[i], tails must match


def _suggest(name: str, known: frozenset[str]) -> str | None:
    """The best known name within edit distance 1, else None. Ties (both
    ``cycle`` and ``cycle~`` sit one edit from ``cycl~``) are broken toward the
    candidate that matches the typo's ``~`` suffix (signal vs control), then
    nearest length, then alphabetically — deterministic and sensible."""
    tilde = name.endswith("~")
    cands = [c for c in known if _edit_distance_le_1(name, c)]
    if not cands:
        return None
    cands.sort(key=lambda c: (c.endswith("~") != tilde, abs(len(c) - len(name)), c))
    return cands[0]


def unknown_object_issues(boxes) -> list[ValidationIssue]:
    """Flag ``newobj`` boxes whose (argless) object name is unknown but is one
    edit away from a real object name — i.e. a probable typo that would ship as
    a Max ``newobj: no such object`` load failure. Names close to nothing known
    are left alone (they may be legit rare objects), so false positives are
    near zero. Advisory."""
    known = _all_known_names()
    issues: list[ValidationIssue] = []
    for box in iter_boxes(boxes):
        if box.get("maxclass") != "newobj":
            continue
        text = str(box.get("text", "")).strip()
        if not text or " " in text:      # creation args -> not a bare name; skip
            continue
        name = text
        if name in known or name in _SCRIPT_LIKE:
            continue
        suggestion = _suggest(name, known)
        if suggestion is not None:
            issues.append(ValidationIssue(
                code="guidelines/unknown-object",
                message=(f"'{name}' is not a known Max object "
                         f"(did you mean '{suggestion}'?)"),
                severity="error", box_id=box.get("id")))
    return issues


def _valueof(box: dict) -> dict:
    return box.get("saved_attribute_attributes", {}).get("valueof", {}) or {}


def parameter_name_issues(boxes) -> list[ValidationIssue]:
    """Ableton: every parameter's Long Name and Scripting Name must be unique
    within the device, and default auto-indexed names (``live.numbox[1]``,
    trailing ``[N]``) must be renamed. Advisory."""
    issues: list[ValidationIssue] = []
    longnames: dict[str, object] = {}     # longname -> first box id seen
    scripts: dict[str, object] = {}       # scripting/varname -> first box id
    for box in iter_boxes(boxes):
        vo = _valueof(box)
        longname = vo.get("parameter_longname")
        if not longname:
            continue                    # not a bound parameter
        bid = box.get("id")
        if _AUTO_INDEX_RE.search(longname):
            issues.append(ValidationIssue(
                code="guidelines/auto-indexed-name",
                message=(f"parameter Long Name '{longname}' is an auto-indexed "
                         "default; give it a meaningful name"),
                severity="warning", box_id=bid))
        if longname in longnames:
            issues.append(ValidationIssue(
                code="guidelines/duplicate-longname",
                message=(f"parameter Long Name '{longname}' is also used by box "
                         f"'{longnames[longname]}' (must be unique)"),
                severity="error", box_id=bid))
        else:
            longnames[longname] = bid
        scripting = box.get("varname")
        if scripting:
            if scripting in scripts:
                issues.append(ValidationIssue(
                    code="guidelines/duplicate-scripting-name",
                    message=(f"Scripting Name '{scripting}' is also used by box "
                             f"'{scripts[scripting]}' (must be unique)"),
                    severity="error", box_id=bid))
            else:
                scripts[scripting] = bid
    return issues


def patching_rect_issues(boxes) -> list[ValidationIssue]:
    """Ableton convention: objects have integer positions. ``final_checklist``
    already covers presentation_rect; this covers ``patching_rect``. Advisory."""
    issues: list[ValidationIssue] = []
    for box in iter_boxes(boxes):
        rect = box.get("patching_rect")
        if rect and any(float(v) != int(float(v)) for v in rect):
            issues.append(ValidationIssue(
                code="guidelines/fractional-patching-rect",
                message=f"patching_rect {rect} should use whole-integer pixels",
                severity="warning", box_id=box.get("id")))
    return issues


def js_style_issues(js: str, source: str = "<js>") -> list[ValidationIssue]:
    """Ableton JavaScript style rules for a generated engine string:
    ``'use strict'``, a trailing newline, and no trailing whitespace. Advisory.
    (Two-space indentation is not machine-checked here — mixed literal/generated
    indentation makes it noisy.)"""
    issues: list[ValidationIssue] = []

    def _issue(code: str, msg: str) -> None:
        issues.append(ValidationIssue(code=code, message=f"{source}: {msg}",
                                      severity="warning", box_id=None))

    if "use strict" not in js[:400]:
        _issue("guidelines/js-no-use-strict",
               "generated JS should open with \"use strict\"")
    if js and not js.endswith("\n"):
        _issue("guidelines/js-no-trailing-newline",
               "generated JS should end with a newline")
    if any(ln != ln.rstrip() for ln in js.splitlines()):
        _issue("guidelines/js-trailing-space",
               "generated JS has trailing whitespace")
    return issues


def check_guidelines(device) -> list[ValidationIssue]:
    """Full static Ableton-standards report for a built ``Device`` (advisory).

    Combines the unknown-object typo pass, the parameter-name conventions, the
    patching_rect grid rule, and the existing ``final_checklist_issues`` set.
    Returns a flat list of :class:`ValidationIssue`, most-severe orderable by
    ``.severity``. Does not raise and does not gate the build."""
    boxes = device.boxes
    out: list[ValidationIssue] = []
    out += unknown_object_issues(boxes)
    out += parameter_name_issues(boxes)
    out += patching_rect_issues(boxes)
    out += final_checklist_issues(boxes)
    return out


def _load_device_from_build(build_py: str):
    """Import a device ``build.py`` with ``Device.build`` mocked (no .amxd
    write) and return the built ``Device``. Used by the CLI."""
    import contextlib
    import importlib.util
    import io
    from pathlib import Path
    from unittest.mock import patch

    path = Path(build_py)
    spec = importlib.util.spec_from_file_location(f"guidelines_{path.parent.name}", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"{build_py}: not an importable Python module")
    module = importlib.util.module_from_spec(spec)
    with patch("m4l_builder.device.Device.build", return_value=0), \
            contextlib.redirect_stdout(io.StringIO()):
        spec.loader.exec_module(module)
    if hasattr(module, "device"):
        return module.device
    if hasattr(module, "build_device"):
        return module.build_device()
    raise SystemExit(f"{build_py}: no top-level `device` or `build_device()` found")


def _main(argv: list[str] | None = None) -> int:
    """CLI: ``python -m m4l_builder.guidelines <build.py> [<build.py> ...]``.

    Prints the advisory Ableton-standards report for each device. Exit 0 always
    (advisory) unless ``--strict`` is passed, which exits 1 if any ERROR-severity
    issue is found."""
    import argparse

    ap = argparse.ArgumentParser(
        prog="python -m m4l_builder.guidelines",
        description="Static Ableton production-standards linter for built M4L devices.")
    ap.add_argument("build_scripts", nargs="+", help="device build.py path(s)")
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 if any error-severity issue is found")
    args = ap.parse_args(argv)

    total_err = 0
    total_warn = 0
    for bp in args.build_scripts:
        device = _load_device_from_build(bp)
        issues = check_guidelines(device)
        errs = [i for i in issues if i.severity == "error"]
        warns = [i for i in issues if i.severity != "error"]
        total_err += len(errs)
        total_warn += len(warns)
        name = getattr(device, "name", bp)
        if not issues:
            print(f"✓ {name}: clean")
            continue
        print(f"✗ {name}: {len(errs)} error(s), {len(warns)} warning(s)")
        for i in issues:
            mark = "E" if i.severity == "error" else "w"
            loc = f" [{i.box_id}]" if i.box_id else ""
            print(f"    {mark} {i.code}{loc}: {i.message}")
    print(f"\nTotal: {total_err} error(s), {total_warn} warning(s) "
          f"across {len(args.build_scripts)} device(s).")
    return 1 if (args.strict and total_err) else 0


if __name__ == "__main__":
    raise SystemExit(_main())
