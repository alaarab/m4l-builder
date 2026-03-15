"""Library-level validation and lint rules for Max for Live graphs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional


@dataclass(frozen=True)
class ValidationIssue:
    """Structured validation issue."""

    code: str
    message: str
    severity: str = "warning"
    box_id: Optional[str] = None


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
        if box_id not in connected:
            issues.append(
                ValidationIssue(
                    code="orphan-box",
                    message=f"Orphan box (no connections): {box_id}",
                    severity="warning",
                    box_id=box_id,
                )
            )

    return issues
