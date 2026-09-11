"""Dataset-backed box lint (T35/Q15): validate emitted boxes against
Ableton's maxdiff ``known_objects`` dataset (vendored, MIT).

The dataset carries one authoritative instance per object — maxclass,
``numinlets`` / ``numoutlets`` / ``outlettype`` — measured from Max itself.
The lint compares every box the kit emits against it:

- UI maxclasses (``live.dial``, ``waveform~`` …) always compare — they take
  no creation args, so their I/O shape is fixed.
- ``newobj`` boxes compare only when the box text is the BARE object name
  (alias-resolved): creation args change the I/O arity of many objects
  (``t b b``, ``pak``, ``sprintf`` …), so argful boxes are skipped rather
  than false-positived.

``redundant_patcher_fields`` flags top-level patcher fields that equal the
``default_patcher`` value — safe to omit from emitted patchers (smaller
diffs, maxdiff-friendly).
"""

from __future__ import annotations

from .patcher_walk import iter_boxes
from .vendor.maxdiff import default_patcher, known_objects, object_aliases

_SPEC_BY_KEY: dict[str, dict] = {}


def _index() -> dict[str, dict]:
    if _SPEC_BY_KEY:
        return _SPEC_BY_KEY
    for box in iter_boxes(dict(known_objects)):
        maxclass = box.get("maxclass", "")
        if maxclass == "newobj":
            key = str(box.get("text", "")).split()[0] if box.get("text") else ""
        else:
            key = maxclass
        if not key or key in _SPEC_BY_KEY:
            continue
        _SPEC_BY_KEY[key] = {
            "numinlets": box.get("numinlets"),
            "numoutlets": box.get("numoutlets"),
            "outlettype": box.get("outlettype"),
            "maxclass": maxclass,
        }
    return _SPEC_BY_KEY


def known_object_spec(name: str) -> dict | None:
    """The dataset spec for ``name`` (alias-resolved), or None."""
    index = _index()
    if name in index:
        return index[name]
    alias = object_aliases.get(name)
    if alias and alias in index:
        return index[alias]
    return None


def known_object_names() -> frozenset[str]:
    """Every object NAME the vendored maxdiff dataset knows, including aliases.

    The arity dataset is measured from real Max, so its keys are a
    high-confidence roster of valid object names. Used by
    :func:`m4l_builder.guidelines.unknown_object_issues` as the base allowlist
    for typo detection (it is only an *arity* reference elsewhere, never a
    name check)."""
    return (frozenset(_index())
            | frozenset(object_aliases)
            | frozenset(object_aliases.values()))


# arity is defined by the script / embedded patcher / creation context,
# not the object name — the dataset's single instance is not authoritative
_SCRIPT_ARITY = frozenset({
    "jsui", "v8ui", "js", "v8", "gen~", "bpatcher", "poly~", "pfft~",
})

# Objects whose inlet/outlet COUNT is set by their creation arguments, so the
# dataset's bare instance says nothing about an argument-carrying box: [unpack]
# has 2 outlets, [unpack f f f] has 3. Everything NOT listed keeps a fixed arity
# regardless of arguments — [maximum 40] has the same two outlets as bare
# [maximum] — so argument-carrying boxes of those ARE checkable. Skipping every
# box with a space (the previous rule) left 462 of the fleet's calls unchecked
# and hid four real wrong declarations.
_ARGS_VARY_ARITY = frozenset({
    "unpack", "pack", "unpackjoin", "packjoin",
    "t", "trigger", "route", "routepass", "sel", "select",
    "gate", "switch", "ggate", "gswitch", "spray",
    "matrix~", "mc.unpack~", "mc.pack~", "mc.gen~", "mc.target~",
    "gate~", "selector~", "gswitch~", "ggate~",
})


def lint_box(box: dict, *, with_args: bool = False) -> list[str]:
    """Issues for one box dict (the ``{"box": {...}}`` inner dict).

    ``with_args=False`` (the default) keeps the long-standing BLOCKING contract:
    only argument-free boxes are checked, where the dataset's bare instance is
    authoritative. ``with_args=True`` instead returns ONLY the advisory
    under-declared-outlet findings for argument-carrying boxes — reported as a
    non-blocking warning, because the fleet has pre-existing instances in
    protected devices (Shard) and in a SHA-pinned verification candidate
    (Foundry) whose source must not change to satisfy a lint.
    """
    maxclass = box.get("maxclass", "")
    has_args = False
    if maxclass == "newobj":
        text = str(box.get("text", "")).strip()
        if not text:
            return []
        key = text.split()[0]
        has_args = " " in text
        if has_args and key in _ARGS_VARY_ARITY:
            return []          # creation args change OUTLET count here; skip
    elif maxclass in ("message", "comment"):
        return []              # fixed shapes the kit already hard-codes
    else:
        key = maxclass
    if key in _SCRIPT_ARITY:
        return []
    spec = known_object_spec(key)
    if spec is None:
        return []
    # A 0-inlet/0-outlet dataset entry means that object FAILED TO INSTANTIATE
    # bare when the dataset was captured (bare [expr] is invalid, so Max made a
    # dead 0/0 box). That is an absence of information, not a claim of zero
    # outlets — treating it as a spec would "fix" 21 correct expr declarations
    # into broken ones.
    if spec.get("numinlets") == 0 and spec.get("numoutlets") == 0:
        return []
    if has_args != with_args:
        return []
    issues = []
    bid = box.get("id", "?")
    if has_args:
        # An argument-carrying box can only be checked on OUTLET COUNT, and only
        # for UNDER-declaration. Measured across the fleet: numinlets produces
        # 206 false positives (an argument CONSUMES the matching inlet — [pak
        # 1 2 3 4] has 4 inlets, bare [pak] has 2; [r name] has 0, bare [r] has
        # 1) and outlettype produces 127 (output TYPE follows argument type —
        # [+ 1.] is float where bare [+] is int). Over-declaring outlets
        # relative to a Max-8.6 dataset usually means Max 9 ADDED outlets
        # (live.adsr~, info~), not a mistake, so only a shortfall is reported.
        want = spec.get("numoutlets")
        got = box.get("numoutlets")
        if want is not None and got is not None and got < want:
            issues.append(
                f"{bid} ({key}): numoutlets={got}, dataset says {want}")
        return issues
    for field in ("numinlets", "numoutlets"):
        want = spec.get(field)
        got = box.get(field)
        if want is not None and got is not None and got != want:
            issues.append(
                f"{bid} ({key}): {field}={got}, dataset says {want}")
    want_ot = spec.get("outlettype")
    got_ot = box.get("outlettype")
    if want_ot is not None and got_ot is not None and list(got_ot) != list(want_ot):
        issues.append(
            f"{bid} ({key}): outlettype={got_ot}, dataset says {want_ot}")
    return issues


def lint_boxes(boxes: list[dict]) -> list[str]:
    """Blocking issues across a device's box list (``device.boxes`` shape)."""
    issues: list[str] = []
    for box in iter_boxes(boxes):
        issues.extend(lint_box(box))
    return issues


def lint_boxes_with_args(boxes: list[dict]) -> list[str]:
    """Advisory under-declared-outlet findings for argument-carrying boxes.

    Separate from :func:`lint_boxes` because these are reported as warnings, not
    build errors: Max uses its own object definition at load, so a short outlet
    declaration mis-wires nothing as long as the patch only cords the outlets it
    declared. Real instances found in the fleet: maximum, minimum, change,
    buffer~, opendialog.
    """
    issues: list[str] = []
    for box in iter_boxes(boxes):
        issues.extend(lint_box(box, with_args=True))
    return issues


def redundant_patcher_fields(patcher: dict) -> list[str]:
    """Top-level patcher fields equal to Max's default (safe to omit)."""
    return [key for key, default in default_patcher.items()
            if key != "boxes" and key in patcher and patcher[key] == default]
