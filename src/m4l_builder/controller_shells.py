"""Reverse-oriented controller shell helpers."""

from __future__ import annotations

import copy


def _normalize_box(box: dict | None) -> dict | None:
    if box is None:
        return None
    if "box" in box:
        return {"box": copy.deepcopy(box["box"])}
    return {"box": copy.deepcopy(box)}


def _normalize_line(line: dict | None) -> dict | None:
    if line is None:
        return None
    if "patchline" in line:
        return {"patchline": copy.deepcopy(line["patchline"])}
    return {"patchline": copy.deepcopy(line)}


def _collect_boxes(*groups) -> list[dict]:
    boxes = []
    for group in groups:
        if not group:
            continue
        if isinstance(group, list):
            items = group
        else:
            items = [group]
        for item in items:
            normalized = _normalize_box(item)
            if normalized is not None:
                boxes.append(normalized)
    return boxes


def _collect_lines(lines: list[dict] | None) -> list[dict]:
    normalized = []
    for line in lines or []:
        wrapped = _normalize_line(line)
        if wrapped is not None:
            normalized.append(wrapped)
    return normalized


def controller_surface_shell(
    *,
    boxes: list[dict] | None = None,
    message_box: dict | None = None,
    route_box: dict | None = None,
    trigger_box: dict | None = None,
    prepend_box: dict | None = None,
    device_box: dict | None = None,
    extra_boxes: list[dict] | None = None,
    lines: list[dict] | None = None,
) -> tuple[list[dict], list[dict]]:
    """Build a controller-surface shell from exact wrapped box/line specs.

    This helper is intentionally reverse-oriented: it preserves the supplied
    wrapped boxes and internal lines exactly so semantic reverse code can group
    recurring controller shells without losing fidelity.
    """
    if boxes is not None:
        return _collect_boxes(boxes), _collect_lines(lines)
    boxes = _collect_boxes(message_box, route_box, trigger_box, prepend_box, device_box, extra_boxes)
    return boxes, _collect_lines(lines)


def sequencer_dispatch_shell(
    *,
    boxes: list[dict] | None = None,
    selector_box: dict | None = None,
    gate_box: dict | None = None,
    scheduler_boxes: list[dict] | None = None,
    bus_boxes: list[dict] | None = None,
    extra_boxes: list[dict] | None = None,
    lines: list[dict] | None = None,
) -> tuple[list[dict], list[dict]]:
    """Build a sequencer-dispatch shell from exact wrapped box/line specs."""
    if boxes is not None:
        return _collect_boxes(boxes), _collect_lines(lines)
    boxes = _collect_boxes(selector_box, gate_box, scheduler_boxes, bus_boxes, extra_boxes)
    return boxes, _collect_lines(lines)


def embedded_ui_shell(
    *,
    boxes: list[dict] | None = None,
    host_box: dict | None = None,
    extra_boxes: list[dict] | None = None,
    lines: list[dict] | None = None,
) -> tuple[list[dict], list[dict]]:
    """Build an embedded-UI shell from exact wrapped box/line specs."""
    if boxes is not None:
        return _collect_boxes(boxes), _collect_lines(lines)
    boxes = _collect_boxes(host_box, extra_boxes)
    return boxes, _collect_lines(lines)


def embedded_ui_shell_v2(
    *,
    boxes: list[dict] | None = None,
    host_box: dict | None = None,
    bus_boxes: list[dict] | None = None,
    control_boxes: list[dict] | None = None,
    init_boxes: list[dict] | None = None,
    extra_boxes: list[dict] | None = None,
    lines: list[dict] | None = None,
) -> tuple[list[dict], list[dict]]:
    """Build an embedded-host shell with attached routing and init structure."""
    if boxes is not None:
        return _collect_boxes(boxes), _collect_lines(lines)
    boxes = _collect_boxes(host_box, bus_boxes, control_boxes, init_boxes, extra_boxes)
    return boxes, _collect_lines(lines)


def named_bus_router(
    *,
    boxes: list[dict] | None = None,
    bus_boxes: list[dict] | None = None,
    message_boxes: list[dict] | None = None,
    extra_boxes: list[dict] | None = None,
    lines: list[dict] | None = None,
) -> tuple[list[dict], list[dict]]:
    """Build an exact named-bus router shell from wrapped boxes and lines."""
    if boxes is not None:
        return _collect_boxes(boxes), _collect_lines(lines)
    boxes = _collect_boxes(bus_boxes, message_boxes, extra_boxes)
    return boxes, _collect_lines(lines)


def init_dispatch_chain(
    *,
    boxes: list[dict] | None = None,
    scheduler_boxes: list[dict] | None = None,
    message_boxes: list[dict] | None = None,
    target_boxes: list[dict] | None = None,
    extra_boxes: list[dict] | None = None,
    lines: list[dict] | None = None,
) -> tuple[list[dict], list[dict]]:
    """Build an exact init/scheduler dispatch chain from wrapped boxes and lines."""
    if boxes is not None:
        return _collect_boxes(boxes), _collect_lines(lines)
    boxes = _collect_boxes(scheduler_boxes, message_boxes, target_boxes, extra_boxes)
    return boxes, _collect_lines(lines)


def poly_shell(
    *,
    boxes: list[dict] | None = None,
    host_box: dict | None = None,
    bus_boxes: list[dict] | None = None,
    control_boxes: list[dict] | None = None,
    init_boxes: list[dict] | None = None,
    extra_boxes: list[dict] | None = None,
    lines: list[dict] | None = None,
) -> tuple[list[dict], list[dict]]:
    """Build an exact `poly~` host shell with attached control and routing layers."""
    if boxes is not None:
        return _collect_boxes(boxes), _collect_lines(lines)
    boxes = _collect_boxes(host_box, bus_boxes, control_boxes, init_boxes, extra_boxes)
    return boxes, _collect_lines(lines)


def poly_shell_bank(
    *,
    boxes: list[dict] | None = None,
    shell_boxes: list[dict] | None = None,
    shared_boxes: list[dict] | None = None,
    extra_boxes: list[dict] | None = None,
    lines: list[dict] | None = None,
) -> tuple[list[dict], list[dict]]:
    """Build an exact grouped bank of repeated `poly~` editor shells."""
    if boxes is not None:
        return _collect_boxes(boxes), _collect_lines(lines)
    boxes = _collect_boxes(shell_boxes, shared_boxes, extra_boxes)
    return boxes, _collect_lines(lines)


__all__ = [
    "controller_surface_shell",
    "sequencer_dispatch_shell",
    "embedded_ui_shell",
    "embedded_ui_shell_v2",
    "named_bus_router",
    "init_dispatch_chain",
    "poly_shell",
    "poly_shell_bank",
]
