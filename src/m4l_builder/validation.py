"""Library-level validation and lint rules for Max for Live graphs."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class ValidationIssue:
    """Structured validation issue."""

    code: str
    message: str
    severity: str = "warning"
    box_id: str | None = None


def format_validation_issues(issues: Iterable[ValidationIssue]) -> str:
    """Format validation issues for warnings and exceptions."""
    issues = list(issues)
    if not issues:
        return "No validation issues."
    lines = ["Build validation issues:"]
    for issue in issues:
        location = f" [{issue.box_id}]" if issue.box_id else ""
        lines.append(f"- {issue.severity.upper()} {issue.code}{location}: {issue.message}")
    return "\n".join(lines)


class BuildValidationError(ValueError):
    """Raised when build-time validation fails."""

    def __init__(self, issues: Iterable[ValidationIssue], *, warnings: Iterable[ValidationIssue] = ()):
        self.issues = tuple(issues)
        self.warnings = tuple(warnings)
        combined = list(self.issues) + list(self.warnings)
        super().__init__(format_validation_issues(combined))


# Pure-decoration UI maxclasses: a background panel, a text label, a divider rule,
# an image. They carry no signal/data and are NEVER patched, so the orphan-box
# check must not flag them (they would ALWAYS be "orphans", burying a genuinely
# unwired DSP/message object). Grounded in the kit's own emitted maxclass strings
# (panel / live.comment / live.line / fpic) plus the reversed-device "comment".
_DECORATION_MAXCLASSES = frozenset(
    {"panel", "comment", "live.comment", "live.line", "fpic"}
)


def lint_graph(boxes: list, lines: list, *, device_type: str = None) -> list[ValidationIssue]:
    """Validate common structural and Max-specific graph rules."""
    issues = []
    seen_ids = {}
    texts = {}

    for box in boxes:
        payload = box.get("box", {})
        box_id = payload.get("id")
        if not box_id:
            continue
        if box_id in seen_ids:
            issues.append(
                ValidationIssue(
                    code="duplicate-box-id",
                    message=f"Duplicate box ID: {box_id}",
                    severity="error",
                    box_id=box_id,
                )
            )
        seen_ids[box_id] = payload
        texts[box_id] = payload.get("text", "")

        text = str(payload.get("text", "")).strip()
        head = text.split()[0] if text else ""
        if head == "sig~":
            issues.append(
                ValidationIssue(
                    code="disallowed-sig-tilde",
                    message=f"Found sig~ object: {box_id}",
                    severity="error",
                    box_id=box_id,
                )
            )
        if head == "dcblock~":
            issues.append(
                ValidationIssue(
                    code="disallowed-dcblock-tilde",
                    message=f"Found dcblock~ in: {box_id}",
                    severity="error",
                    box_id=box_id,
                )
            )
        if payload.get("maxclass") == "panel" and payload.get("background") != 1:
            # Foreground panels ARE legitimate (Live-proven on Shard's group
            # cards: a later background-layer panel never renders above an
            # existing full-face background panel, so hand-layout group cards
            # MUST be background=0, added after the controls they sit under).
            # Downgraded from error: the covered-controls failure mode is
            # instantly visible in QA; the warn keeps it on the radar.
            issues.append(
                ValidationIssue(
                    code="panel-background",
                    message=(f"Panel {box_id} is foreground (background=0) — "
                             "fine for group cards ADDED AFTER their controls; "
                             "verify nothing renders beneath it"),
                    severity="warning",
                    box_id=box_id,
                )
            )
        if text.startswith("selector~"):
            parts = text.split()
            if len(parts) < 3:
                issues.append(
                    ValidationIssue(
                        code="selector-missing-initial",
                        message=f"selector~ missing initial arg: '{text}' (default 0 = silence)",
                        severity="error",
                        box_id=box_id,
                    )
                )
            else:
                try:
                    n_in, init = int(parts[1]), int(parts[2])
                    if not 0 <= init <= n_in:
                        issues.append(
                            ValidationIssue(
                                code="selector-initial-out-of-range",
                                message=f"selector~ initial {init} out of range 0..{n_in}: '{text}'",
                                severity="error",
                                box_id=box_id,
                            )
                        )
                except ValueError:
                    pass

    connected = set()
    for line in lines:
        payload = line.get("patchline", {})
        src = payload.get("source", [None])[0]
        dst = payload.get("destination", [None])[0]
        if src is not None:
            connected.add(src)
        if dst is not None:
            connected.add(dst)
        if src not in seen_ids:
            issues.append(
                ValidationIssue(
                    code="unknown-source",
                    message=f"Patchline references unknown source: {src}",
                    severity="error",
                    box_id=src,
                )
            )
        if dst not in seen_ids:
            issues.append(
                ValidationIssue(
                    code="unknown-destination",
                    message=f"Patchline references unknown destination: {dst}",
                    severity="error",
                    box_id=dst,
                )
            )
        # Outlet/inlet index bounds — Max silently DROPS an out-of-range patchline
        # ("patchcord source not found: deleting"), a dead connection with no error.
        src_arr = payload.get("source", [])
        if src in seen_ids and len(src_arr) > 1 and isinstance(src_arr[1], int):
            nout = seen_ids[src].get("numoutlets")
            if isinstance(nout, int) and src_arr[1] >= nout:
                issues.append(
                    ValidationIssue(
                        code="outlet-index-out-of-range",
                        message=f"Patchline from {src} outlet {src_arr[1]} exceeds its numoutlets ({nout})",
                        severity="error",
                        box_id=src,
                    )
                )
        dst_arr = payload.get("destination", [])
        if dst in seen_ids and len(dst_arr) > 1 and isinstance(dst_arr[1], int):
            nin = seen_ids[dst].get("numinlets")
            if isinstance(nin, int) and dst_arr[1] >= nin:
                issues.append(
                    ValidationIssue(
                        code="inlet-index-out-of-range",
                        message=f"Patchline to {dst} inlet {dst_arr[1]} exceeds its numinlets ({nin})",
                        severity="error",
                        box_id=dst,
                    )
                )

    if device_type == "audio_effect":
        if "obj-plugin" not in seen_ids:
            issues.append(
                ValidationIssue(
                    code="missing-plugin",
                    message="AudioEffect missing obj-plugin",
                    severity="warning",
                )
            )
        if "obj-plugout" not in seen_ids:
            issues.append(
                ValidationIssue(
                    code="missing-plugout",
                    message="AudioEffect missing obj-plugout",
                    severity="warning",
                )
            )

    for box_id in seen_ids:
        if box_id in connected:
            continue
        # Skip pure-decoration UI objects — they are never patched, so flagging
        # them "orphan" is noise that hides a real unwired FUNCTIONAL box.
        if seen_ids[box_id].get("maxclass") in _DECORATION_MAXCLASSES:
            continue
        issues.append(
            ValidationIssue(
                code="orphan-box",
                message=f"Orphan box (no connections): {box_id}",
                severity="warning",
                box_id=box_id,
            )
        )

    return issues


_FORBIDDEN_OBJECTS = {"print", "dac~", "adc~"}
_SEND_RECEIVE_OBJECTS = {"send", "receive", "send~", "receive~", "s", "r"}


def final_checklist_issues(boxes: list) -> list[ValidationIssue]:
    """Official M4L *Final Checklist* checks beyond :func:`lint_graph` (additive).

    Mirrors items from Ableton's device-submission checklist not already covered:
      * no debug / hardware-IO objects (``print`` / ``dac~`` / ``adc~``) — error;
      * ``send``/``receive`` names should be LOCAL (``---``-prefixed) so device
        instances don't cross-talk — warning;
      * presentation rects should be whole-integer pixels — warning.

    Opt-in (call it from a device's own ``validate``); it does not run during a
    normal build, so existing devices are unaffected. Returns ``ValidationIssue``s.
    """
    issues: list[ValidationIssue] = []
    for box in boxes:
        payload = box.get("box", {})
        bid = payload.get("id")
        maxclass = payload.get("maxclass")
        text = (payload.get("text") or "").strip()
        parts = text.split()
        first = parts[0] if parts else maxclass

        if first in _FORBIDDEN_OBJECTS:
            issues.append(ValidationIssue(
                code="checklist/forbidden-object",
                message=f"'{first}' is not allowed in a shipped M4L device",
                severity="error", box_id=bid))

        if maxclass == "newobj" and first in _SEND_RECEIVE_OBJECTS and len(parts) >= 2:
            if not parts[1].startswith("---"):
                issues.append(ValidationIssue(
                    code="checklist/nonlocal-send",
                    message=f"send/receive name '{parts[1]}' should be local ('---'-prefixed)",
                    severity="warning", box_id=bid))

        if payload.get("presentation"):
            rect = payload.get("presentation_rect")
            if rect and any(float(v) != int(float(v)) for v in rect):
                issues.append(ValidationIssue(
                    code="checklist/fractional-rect",
                    message=f"presentation_rect {rect} should use whole-integer pixels",
                    severity="warning", box_id=bid))

    return issues


# ── Device-level LAYOUT lint (UI Foundations v2) ─────────────────────────────
# Interactive control classes for the overlap rule: two of THESE intersecting is
# almost always a real authoring bug. Displays (jsui/v8ui/scope~/…) are exempt —
# stacking a transparent display/overlay is a legitimate corpus pattern (P6), as
# is an alpha-0 "ghost" control (stacked_panels tabs, drop targets).
_INTERACTIVE_MAXCLASSES = frozenset({
    "live.dial", "live.menu", "live.numbox", "live.text", "live.toggle",
    "live.tab", "live.slider", "live.gain~", "live.button", "textbutton",
    "number", "flonum",
})
# A vertical band this wide with no content reads as DEAD SPACE (the stale-width
# / pressure-688 bug class). Section padding is ~8-16px; 40 clears it safely.
_DEAD_ZONE_MIN_W = 40.0
_LAYOUT_MARGIN = 8.0
_WIDTH_MISMATCH_TOL = 12.0
# The deliberate parking band (PARK_RECT / HIDDEN_RECT / retired-rail convention):
# boxes at x/y >= 900 are intentionally hidden. An interactive control past the
# device edge but BEFORE this band is STRANDED — authored as visible yet
# unreachable in Live. ``_onscreen_rect`` cannot tell the two apart (it treats
# ALL fully-offscreen boxes as parked), which is how stranded controls shipped.
_PARK_X = 900.0


def _alpha0_bg(payload: dict) -> bool:
    bg = payload.get("bgcolor")
    if not isinstance(bg, (list, tuple)) or len(bg) < 4:
        return False
    return float(bg[3]) == 0.0


def _onscreen_rect(payload: dict, width: float, height: float):
    if payload.get("presentation") != 1:
        return None
    rect = payload.get("presentation_rect")
    if not rect or len(rect) < 4:
        return None
    try:
        x, y, w, h = (float(v) for v in rect[:4])
    except (TypeError, ValueError):
        return None
    if x >= width or y >= height or x + w <= 0 or y + h <= 0:
        return None  # parked / fully off-canvas
    return x, y, w, h


def layout_issues(boxes: list, width: float, height: float) -> list[ValidationIssue]:
    """Device-level layout rules (all WARNING except ``setwidth-mismatch``):

    * ``control-overlap`` — two INTERACTIVE controls' rects intersect by more
      than 4px on both axes (alpha-0 "ghost" controls and ``ignoreclick`` boxes
      exempt — transparent-stack patterns are legitimate);
    * ``dead-zone`` — a vertical band >= 40px wide inside the content margins
      with no non-panel content (the stale-width / pressure-688 bug class);
    * ``width-mismatch`` — the rightmost content edge + margin disagrees with
      the authored device width by > 12px;
    * ``setwidth-mismatch`` — a ``setwidth N`` message wider than the device
      (ERROR: a width-collapse FULL wider than the layout re-creates the dead
      zone at runtime).

    Pure function over the box list so it can lint a live ``Device`` (via
    ``Device.lint()``) or a reverse-loaded .amxd alike.
    """
    issues: list[ValidationIssue] = []
    interactive: list[tuple[str, str, tuple[float, float, float, float]]] = []
    content_spans: list[tuple[float, float]] = []
    content_right = 0.0

    # A settings-sidebar / width-collapse can legitimately ``setwidth`` WIDER
    # than the authored (closed) width to reveal an extra column. The device's
    # true maximum reachable width is ``width`` or the largest setwidth target;
    # a control or setwidth into that revealed region is legitimate IFF the
    # region is actually POPULATED (non-panel content past the closed edge) —
    # otherwise it is the stale-FULL dead-zone bug (Pressure-688).
    max_setwidth = width
    for box in boxes:
        payload = box.get("box", {})
        if payload.get("maxclass") != "message":
            continue
        parts = (payload.get("text") or "").strip().split()
        if len(parts) == 2 and parts[0] == "setwidth":
            try:
                max_setwidth = max(max_setwidth, float(parts[1]))
            except ValueError:
                pass
    reveal_populated = False
    if max_setwidth > width + 0.5:
        for box in boxes:
            payload = box.get("box", {})
            if payload.get("presentation") != 1:
                continue
            if (payload.get("maxclass") or "") == "panel":
                continue  # a backdrop alone does not populate the reveal
            r = payload.get("presentation_rect")
            if not r or len(r) < 4:
                continue
            try:
                rx = float(r[0])
            except (TypeError, ValueError):
                continue
            if width - 0.5 <= rx < _PARK_X:
                reveal_populated = True
                break
        if not reveal_populated:
            # A LEFT settings_sidebar reveals by REFLOW (script sendbox ...
            # presentation_rect moves the whole layout into the widened region at
            # runtime), so the region is empty at rest yet fills on open — a
            # legitimate widen, not the stale-FULL dead zone.
            for box in boxes:
                payload = box.get("box", {})
                if payload.get("maxclass") != "message":
                    continue
                t = (payload.get("text") or "")
                if t.startswith("script sendbox") and "presentation_rect" in t:
                    reveal_populated = True
                    break

    for box in boxes:
        payload = box.get("box", {})
        rect = _onscreen_rect(payload, width, height)
        if rect is None:
            continue
        x, y, w, h = rect
        maxclass = payload.get("maxclass") or ""
        # Everything except the full-bleed device bg counts as content: hero
        # frames and section cards are DELIBERATE structure, so a "dead zone"
        # is a band with nothing at all (the pressure-688 signature).
        full_bleed_panel = (maxclass == "panel" and x <= 0.5 and w >= width - 1.0)
        if not full_bleed_panel:
            content_spans.append((x, x + w))
            content_right = max(content_right, x + w)
        if (maxclass in _INTERACTIVE_MAXCLASSES
                and not _alpha0_bg(payload)
                and not payload.get("ignoreclick")):
            interactive.append((payload.get("id") or "?", maxclass, rect))
        # dead-live-text: a VISIBLE live.text with parameter_enable=0 renders
        # but NEVER receives clicks in Live (proven on Para EQ's ANALYZER/
        # ACTIVE, Linear Phase EQ's ANALYZER, Spectrum Analyzer's mode chips).
        # A clickable live.text must be a real param; state-mirror displays
        # should set ignoreclick=1 to declare they are not click targets.
        if (maxclass == "live.text"
                and payload.get("parameter_enable") == 0
                and not payload.get("ignoreclick")):
            issues.append(ValidationIssue(
                code="dead-live-text",
                message=(f"visible live.text '{payload.get('id')}' has "
                         "parameter_enable=0 — it renders but never receives "
                         "clicks in Live (the dead-button class); make it a "
                         "real param, or set ignoreclick=1 if it is a "
                         "display-only mirror"),
                severity="error", box_id=payload.get("id")))

    # control-overlap
    for i, (id_a, cls_a, ra) in enumerate(interactive):
        ax, ay, aw, ah = ra
        for id_b, cls_b, rb in interactive[i + 1:]:
            bx, by, bw, bh = rb
            ox = min(ax + aw, bx + bw) - max(ax, bx)
            oy = min(ay + ah, by + bh) - max(ay, by)
            if ox > 4.0 and oy > 4.0:
                issues.append(ValidationIssue(
                    code="control-overlap",
                    message=(f"interactive controls overlap by {ox:g}x{oy:g}px: "
                             f"{id_a} ({cls_a}) vs {id_b} ({cls_b})"),
                    severity="warning", box_id=id_a))

    # dead-zone: gaps in the x-projection of non-panel content
    if content_spans:
        spans = sorted(content_spans)
        cursor = _LAYOUT_MARGIN
        gaps: list[tuple[float, float]] = []
        for x0, x1 in spans:
            if x0 - cursor >= _DEAD_ZONE_MIN_W:
                gaps.append((cursor, x0))
            cursor = max(cursor, x1)
        if (width - _LAYOUT_MARGIN) - cursor >= _DEAD_ZONE_MIN_W:
            gaps.append((cursor, width - _LAYOUT_MARGIN))
        for g0, g1 in gaps:
            issues.append(ValidationIssue(
                code="dead-zone",
                message=(f"no content between x={g0:g} and x={g1:g} "
                         f"({g1 - g0:g}px of dead space in a {width:g}px device)"),
                severity="warning"))

        # width-mismatch (only meaningful when there IS content)
        expected = content_right + _LAYOUT_MARGIN
        if abs(width - expected) > _WIDTH_MISMATCH_TOL and width > expected:
            issues.append(ValidationIssue(
                code="width-mismatch",
                message=(f"authored width {width:g} but content ends at "
                         f"x={content_right:g} (+{_LAYOUT_MARGIN:g} margin -> "
                         f"~{expected:g}); derive the width from content "
                         f"(Surface.finalize) or tighten it"),
                severity="warning"))

    # setwidth-mismatch
    for box in boxes:
        payload = box.get("box", {})
        if payload.get("maxclass") != "message":
            continue
        text = (payload.get("text") or "").strip()
        parts = text.split()
        if len(parts) == 2 and parts[0] == "setwidth":
            try:
                target = float(parts[1])
            except ValueError:
                continue
            if target > width + 0.5 and not reveal_populated:
                issues.append(ValidationIssue(
                    code="setwidth-mismatch",
                    message=(f"'{text}' exceeds the authored device width "
                             f"{width:g} with nothing in the revealed region — a "
                             f"width-collapse FULL wider than the layout "
                             f"re-creates the dead-zone bug at runtime (populate "
                             f"the reveal, e.g. a settings_sidebar column)"),
                    severity="error", box_id=payload.get("id")))

    # stranded-control: reads the RAW presentation_rect (NOT _onscreen_rect,
    # which treats every fully-offscreen box as parked) — an interactive
    # control between the device edge and the x/y>=900 parking band was
    # authored to be visible but is unreachable in Live (the stranded M/S
    # menu class).
    for box in boxes:
        payload = box.get("box", {})
        if payload.get("presentation") != 1:
            continue
        if (payload.get("maxclass") or "") not in _INTERACTIVE_MAXCLASSES:
            continue
        rect = payload.get("presentation_rect")
        if not rect or len(rect) < 4:
            continue
        try:
            x, y = float(rect[0]), float(rect[1])
        except (TypeError, ValueError):
            continue
        if x >= _PARK_X or y >= _PARK_X:
            continue  # deliberate parking
        # A control between the closed width and the widest setwidth target is
        # reachable — it is revealed when the sidebar/collapse expands. Only a
        # control beyond ANY reveal (or off the bottom) is truly stranded.
        if x >= max_setwidth or y >= height:
            issues.append(ValidationIssue(
                code="stranded-control",
                message=(f"interactive control '{payload.get('id')}' sits at "
                         f"[{x:g}, {y:g}] — past the {max_setwidth:g}x{height:g} "
                         f"reachable edge but below the x/y>=900 parking band: "
                         f"visible-intended yet unreachable in Live; move it "
                         f"on-canvas or park it at >=900"),
                severity="error", box_id=payload.get("id")))
    return issues
