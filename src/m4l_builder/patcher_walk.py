"""Shared traversal helpers for Max patcher box/line graphs.

Max devices are represented as ``{"boxes": [...], "lines": [...]}`` where each
box entry is a wrapper ``{"box": {...}}`` around the real box dict (which
carries the ``"id"``) and each line entry is a wrapper ``{"patchline": {...}}``
around the real connection dict (``"source"``/``"destination"`` pairs). Before
this module existed, ~16 modules across the library hand-rolled this
unwrap-and-iterate dance independently (~40+ call sites), and the derived
``{id: box}`` index got rebuilt as a local variable 23 separate times. These
four functions are the one shared implementation of that dance.

``iter_boxes``/``boxes_by_id``/``iter_patchlines`` accept either a live
``Device``/``GraphContainer`` instance (read via its ``.boxes``/``.lines``
attributes) or a raw patcher-JSON dict/list (a normalized "snapshot" dict with
top-level ``"boxes"``/``"lines"`` keys, or an already-extracted list of
wrapper entries) — both shapes use the identical wrapper convention, so one
implementation serves live authoring code and reverse-engineering/corpus code
alike.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import Any

__all__ = ["iter_boxes", "boxes_by_id", "iter_patchlines", "unwrap_box"]


def _raw_entries(container: Any, key: str) -> Iterable:
    """The raw wrapper-entry list for ``key`` ("boxes"/"lines") on ``container``."""
    if hasattr(container, key):
        return getattr(container, key)
    if isinstance(container, dict):
        return container.get(key, [])
    if isinstance(container, (list, tuple)):
        return container
    return []


def unwrap_box(entry: Any) -> Any:
    """Return the bare box dict from ``entry``.

    Idempotent: works whether ``entry`` is a ``{"box": {...}}`` wrapper (the
    on-disk/patcher-JSON shape) or an already-bare box dict.
    """
    if isinstance(entry, dict) and "box" in entry:
        return entry["box"]
    return entry


def _unwrap_patchline(entry: Any) -> Any:
    if isinstance(entry, dict) and "patchline" in entry:
        return entry["patchline"]
    return entry


def iter_boxes(container: Any) -> Iterator[dict]:
    """Yield bare (unwrapped) box dicts from ``container``.

    ``container`` may be a ``Device``/``GraphContainer`` instance, a raw
    patcher/snapshot dict with a ``"boxes"`` key, or a plain list of
    ``{"box": {...}}`` wrapper entries (already-bare dicts pass through
    unchanged, per :func:`unwrap_box`).
    """
    for entry in _raw_entries(container, "boxes"):
        yield unwrap_box(entry)


def boxes_by_id(container: Any) -> dict[str, dict]:
    """Return ``{id: box}`` for every box in ``container``.

    Built on :func:`iter_boxes`, so it accepts the same three container
    shapes. This is the index that used to get hand-rebuilt as a local
    variable throughout the library.
    """
    return {box["id"]: box for box in iter_boxes(container)}


def iter_patchlines(container: Any) -> Iterator[dict]:
    """Yield bare (unwrapped) patchline dicts from ``container``.

    Each yielded dict has ``"source"``/``"destination"`` ``[box_id, index]``
    pairs plus any other saved patchline attributes (color, midpoints, ...).
    ``container`` may be a ``Device``/``GraphContainer`` instance, a raw
    patcher/snapshot dict with a ``"lines"`` key, or a plain list of
    ``{"patchline": {...}}`` wrapper entries.
    """
    for entry in _raw_entries(container, "lines"):
        yield _unwrap_patchline(entry)
