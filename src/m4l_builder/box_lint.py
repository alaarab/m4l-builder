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


def lint_box(box: dict) -> list[str]:
    """Issues for one box dict (the ``{"box": {...}}`` inner dict)."""
    maxclass = box.get("maxclass", "")
    if maxclass == "newobj":
        text = str(box.get("text", "")).strip()
        if not text or " " in text:
            return []          # creation args -> arity may differ; skip
        key = text
    elif maxclass in ("message", "comment"):
        return []              # fixed shapes the kit already hard-codes
    else:
        key = maxclass
    if key in _SCRIPT_ARITY:
        return []
    spec = known_object_spec(key)
    if spec is None:
        return []
    issues = []
    bid = box.get("id", "?")
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
    """Issues across a device's box list (``device.boxes`` shape)."""
    issues: list[str] = []
    for box in iter_boxes(boxes):
        issues.extend(lint_box(box))
    return issues


def redundant_patcher_fields(patcher: dict) -> list[str]:
    """Top-level patcher fields equal to Max's default (safe to omit)."""
    return [key for key, default in default_patcher.items()
            if key != "boxes" and key in patcher and patcher[key] == default]
