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
            issues.append(
                ValidationIssue(
                    code="panel-background",
                    message=f"Panel {box_id} missing background:1",
                    severity="error",
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
