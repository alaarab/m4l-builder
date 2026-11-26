"""The ``m4l`` command line: scaffold, build, watch, lint, preview, inspect and import
devices.

Installed as the ``m4l`` console script (also ``python -m m4l_builder``)::

    m4l new "My Gain" --type audio     # scaffold my_gain/build.py
    m4l build my_gain/build.py         # run it; --out redirects the .amxd
    m4l watch my_gain/build.py         # rebuild into the User Library on save
    m4l lint my_gain/build.py          # validation + box lint + GenExpr lint
    m4l preview my_gain/build.py       # render the presentation view to SVG
    m4l inspect "My Gain.amxd"         # type, size, parameters, box counts
    m4l import "Their Device.amxd"     # write a build.py that rebuilds it
    m4l render my_gain/build.py --in dry.wav --out wet.wav --param Gain=-6

A build script is any Python file that makes a :class:`~m4l_builder.Device` and
calls ``device.build(path)``, the way every example does. The CLI runs it as
``__main__`` with ``Device.build`` intercepted, so it sees each device the script
builds and can redirect, skip or summarise the write. Scripts that only define a
top-level ``device`` or a ``build_device()`` (the ``m4l_builder.guidelines``
convention) work too. Stdlib only, like the rest of the library.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import math
import os
import re
import runpy
import sys
import time
import traceback
from collections import Counter
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .device import Device

__all__ = ["main", "run_build_script", "device_summary", "lint_device", "ScriptBuild"]


# --------------------------------------------------------------------------- #
# Running build scripts
# --------------------------------------------------------------------------- #


@dataclass
class ScriptBuild:
    """One ``device.build(...)`` call seen while running a build script."""

    device: Device
    requested_path: str | None
    written_path: str | None = None
    bytes_written: int = 0


class ScriptError(Exception):
    """A build script could not be run or built no device."""


# Receives the build and the path the script asked for; returns where to write,
# or None to skip the write (lint only wants the device).
Redirect = Callable[[Device, "str | None"], "str | None"]


@contextlib.contextmanager
def _script_context(script: Path) -> Iterator[None]:
    """Run a script the way ``python script.py`` would: its own argv[0] and its
    directory first on sys.path (so it can import sibling helpers)."""
    old_argv = sys.argv[:]
    old_path = sys.path[:]
    sys.argv = [str(script)]
    sys.path.insert(0, str(script.parent))
    try:
        yield
    finally:
        sys.argv = old_argv
        sys.path[:] = old_path


@contextlib.contextmanager
def _silenced(enabled: bool) -> Iterator[None]:
    if not enabled:
        yield
        return
    with open(os.devnull, "w") as devnull, contextlib.redirect_stdout(devnull):
        yield


def run_build_script(script: str | os.PathLike, redirect: Redirect | None = None,
                     *, quiet: bool = False) -> list[ScriptBuild]:
    """Run ``script`` as ``__main__`` and return every device it built.

    ``redirect(device, requested_path)`` picks where each build is written;
    returning None captures the device without writing anything. With no
    ``redirect`` the script writes where it asked to. ``quiet`` swallows the
    script's own stdout.
    """
    path = Path(script).resolve()
    if not path.is_file():
        raise ScriptError(f"{script}: no such file")

    builds: list[ScriptBuild] = []
    original_build = Device.build

    def intercepted(self, output_path, *, validate=None, freeze=False):
        record = ScriptBuild(self, os.fspath(output_path))
        target = redirect(self, record.requested_path) if redirect else record.requested_path
        if target is not None:
            record.bytes_written = original_build(self, target, validate=validate,
                                                  freeze=freeze)
            record.written_path = str(target)
        builds.append(record)
        return record.bytes_written

    Device.build = intercepted  # type: ignore[method-assign]
    try:
        with _script_context(path), _silenced(quiet):
            namespace = runpy.run_path(str(path), run_name="__main__")
    except SystemExit as exc:
        if exc.code not in (None, 0):
            raise ScriptError(f"{script}: exited with status {exc.code}") from exc
        namespace = {}
    finally:
        Device.build = original_build  # type: ignore[method-assign]

    if builds:
        return builds

    # No build() call: fall back to the guidelines convention.
    device = namespace.get("device")
    if not isinstance(device, Device) and callable(namespace.get("build_device")):
        device = namespace["build_device"]()
    if not isinstance(device, Device):
        raise ScriptError(
            f"{script}: built no device (call device.build(path), or define a "
            f"top-level `device` or `build_device()`)"
        )
    record = ScriptBuild(device, None)
    target = redirect(device, None) if redirect else None
    if target is not None:
        record.bytes_written = device.build(target)
        record.written_path = str(target)
    return [record]


def _user_library_target(device: Device, _requested: str | None) -> str:
    from .paths import device_output_path

    return device_output_path(device.name, device.device_type, create_dirs=False)


def _out_redirect(out: str) -> Redirect:
    """--out FILE.amxd writes the single device there; any other --out is a
    directory that keeps each build's own file name."""
    out_path = Path(out)
    files_written = 0

    def redirect(device: Device, requested: str | None) -> str:
        nonlocal files_written
        if out_path.suffix.lower() == ".amxd":
            files_written += 1
            if files_written > 1:
                raise ScriptError(
                    f"--out {out} names one file but the script builds more than one "
                    f"device; pass a directory instead"
                )
            return str(out_path)
        name = Path(requested).name if requested else f"{device.name}.amxd"
        return str(out_path / name)

    return redirect


# --------------------------------------------------------------------------- #
# Summaries (inspect + watch diffs)
# --------------------------------------------------------------------------- #

_PARAM_TYPES = {0: "float", 1: "int", 2: "enum", 3: "blob"}


def _param_row(spec) -> dict:
    row: dict[str, Any] = {"name": spec.name,
                           "type": _PARAM_TYPES.get(spec.parameter_type, str(spec.parameter_type))}
    if spec.enum:
        row["values"] = list(spec.enum)
    else:
        if spec.minimum is not None:
            row["min"] = spec.minimum
        if spec.maximum is not None:
            row["max"] = spec.maximum
    initial = spec.initial
    if isinstance(initial, list) and len(initial) == 1:
        initial = initial[0]
    if isinstance(initial, (int, float, str)):
        row["initial"] = initial
    return row


def _walk_boxes(node: Any) -> Iterator[dict]:
    """Every box dict in a patcher tree, subpatchers and embedded gen~ included."""
    if isinstance(node, list):
        for item in node:
            yield from _walk_boxes(item)
        return
    if not isinstance(node, dict):
        return
    box = node.get("box", node)
    if not isinstance(box, dict):
        return
    if "maxclass" in box:
        yield box
    inner = box.get("patcher")
    if isinstance(inner, dict):
        yield from _walk_boxes(inner.get("boxes", []))


def device_summary(device: Device, path: str | os.PathLike | None = None) -> dict:
    """A JSON-ready summary: type, size, parameters, box and line counts."""
    top = [entry.get("box", entry) for entry in device.boxes]
    all_boxes = list(_walk_boxes(device.boxes))
    kinds = Counter(box.get("maxclass", "?") for box in top)
    objects = Counter(
        str(box.get("text", "")).split()[0]
        for box in top if box.get("maxclass") == "newobj" and box.get("text")
    )
    summary: dict[str, Any] = {
        "name": device.name,
        "type": device.device_type,
        "size": [device.width, device.height],
        "parameters": [_param_row(spec) for spec in device.parameters()],
        "boxes": len(top),
        "nested_boxes": len(all_boxes) - len(top),
        "presentation_boxes": sum(1 for box in top if box.get("presentation")),
        "lines": len(device.lines),
        "maxclasses": dict(sorted(kinds.items(), key=lambda kv: (-kv[1], kv[0]))),
        "objects": dict(sorted(objects.items(), key=lambda kv: (-kv[1], kv[0]))),
        "assets": sorted(asset.filename for asset in device.assets()),
        "box_ids": sorted(str(box.get("id")) for box in top),
    }
    if path is not None and Path(path).is_file():
        summary["file_bytes"] = Path(path).stat().st_size
    return summary


def _format_summary(summary: dict, *, path: str | None = None) -> str:
    width, height = summary["size"]
    lines = [
        f"{summary['name']}  ({summary['type']}, {width:g} x {height:g} px)",
    ]
    if path:
        size = summary.get("file_bytes")
        lines.append(f"  file        {path}" + (f"  ({size:,} bytes)" if size else ""))
    nested = f", {summary['nested_boxes']} nested" if summary["nested_boxes"] else ""
    lines.append(f"  boxes       {summary['boxes']} ({summary['presentation_boxes']} "
                 f"in presentation{nested}), {summary['lines']} patch lines")
    kinds = ", ".join(f"{name} {n}" for name, n in summary["maxclasses"].items())
    lines.append(f"  maxclasses  {kinds}")
    if summary["objects"]:
        top = list(summary["objects"].items())[:12]
        more = len(summary["objects"]) - len(top)
        text = ", ".join(f"{name} {n}" for name, n in top) + (f", +{more} more" if more > 0 else "")
        lines.append(f"  objects     {text}")
    params = summary["parameters"]
    lines.append(f"  parameters  {len(params)}")
    for row in params:
        if "values" in row:
            detail = " | ".join(str(v) for v in row["values"])
        else:
            detail = f"{row.get('min', '?')} .. {row.get('max', '?')}"
        initial = f", initial {row['initial']}" if "initial" in row else ""
        lines.append(f"    - {row['name']} ({row['type']}: {detail}{initial})")
    if summary["assets"]:
        lines.append(f"  assets      {', '.join(summary['assets'])}")
    return "\n".join(lines)


def diff_summaries(before: dict | None, after: dict) -> list[str]:
    """Human-readable changes between two device summaries (for ``watch``)."""
    if before is None:
        return [f"first build: {after['boxes']} boxes, {after['lines']} lines, "
                f"{len(after['parameters'])} parameter(s)"]
    changes: list[str] = []
    old_ids, new_ids = set(before["box_ids"]), set(after["box_ids"])
    if new_ids - old_ids:
        changes.append("+ boxes: " + ", ".join(sorted(new_ids - old_ids)))
    if old_ids - new_ids:
        changes.append("- boxes: " + ", ".join(sorted(old_ids - new_ids)))
    if before["lines"] != after["lines"]:
        changes.append(f"lines: {before['lines']} -> {after['lines']}")
    old_params = {row["name"]: row for row in before["parameters"]}
    new_params = {row["name"]: row for row in after["parameters"]}
    for name in sorted(new_params.keys() - old_params.keys()):
        changes.append(f"+ parameter: {name}")
    for name in sorted(old_params.keys() - new_params.keys()):
        changes.append(f"- parameter: {name}")
    for name in sorted(new_params.keys() & old_params.keys()):
        if new_params[name] != old_params[name]:
            changes.append(f"~ parameter: {name}")
    if before["size"] != after["size"]:
        changes.append("size: {:g}x{:g} -> {:g}x{:g}".format(*before["size"], *after["size"]))
    if before.get("file_bytes") != after.get("file_bytes") and after.get("file_bytes"):
        changes.append(f"bytes: {before.get('file_bytes', 0):,} -> {after['file_bytes']:,}")
    return changes or ["no structural change"]


# --------------------------------------------------------------------------- #
# Lint
# --------------------------------------------------------------------------- #


def _gen_sources(device: Device) -> Iterator[tuple[str, dict]]:
    """Every GenExpr codebox: in embedded gen~ boxes and in .gendsp assets."""
    for box in _walk_boxes(device.boxes):
        if box.get("maxclass") == "codebox" and isinstance(box.get("code"), str):
            yield str(box.get("id", "codebox")), box
    for asset in device.assets():
        if not asset.filename.endswith(".gendsp"):
            continue
        content = asset.content
        text = content.decode(asset.encoding) if isinstance(content, bytes) else content
        try:
            data = json.loads(text)
        except (TypeError, ValueError):
            continue
        for box in _walk_boxes(data):
            if box.get("maxclass") == "codebox" and isinstance(box.get("code"), str):
                yield f"{asset.filename}:{box.get('id', 'codebox')}", box


def lint_device(device: Device) -> list:
    """Build validation + box lint + GenExpr lint, as ``ValidationIssue`` rows."""
    from .amxd import WIRING_INTEGRITY_CODES, collect_build_issues
    from .gen_lint import lint_genexpr
    from .validation import ValidationIssue

    issues = []
    for issue in collect_build_issues(device):
        # A wiring-integrity rule blocks every default build, so report it as one.
        if issue.code in WIRING_INTEGRITY_CODES and issue.severity != "error":
            issue = ValidationIssue(issue.code, issue.message, "error", issue.box_id)
        issues.append(issue)
    for where, box in _gen_sources(device):
        for message in lint_genexpr(box["code"], int(box.get("numinlets", 0)),
                                    int(box.get("numoutlets", 0))):
            issues.append(ValidationIssue("genexpr", message, "error", where))
    return issues


# --------------------------------------------------------------------------- #
# Scaffolding
# --------------------------------------------------------------------------- #

_TYPES = {
    "audio": ("AudioEffect", "audio_effect", "WARM"),
    "midi": ("MidiEffect", "midi_effect", "COOL"),
    "instrument": ("Instrument", "instrument", "SYNTHWAVE"),
}

_BODIES = {
    "audio": '''\
    device = AudioEffect(NAME, width=70, height=110, theme=WARM)
    device.add_panel("bg", [0, 0, 70, 110])
    device.add_dial("gain", "Gain", [10, 6, 50, 90],
                    min_val=-70.0, max_val=6.0, initial=0.0,
                    unitstyle=4, annotation_name="Gain")

    # AudioEffect adds the stereo plugin~ / plugout~ (obj-plugin, obj-plugout).
    device.add_newobj("mul_l", "*~ 1.")
    device.add_newobj("mul_r", "*~ 1.")
    device.add_newobj("db2a", "dbtoa")
    device.add_newobj("pk", "pack f 20")
    device.add_newobj("ln", "line~")

    device.add_line("obj-plugin", 0, "mul_l", 0)   # stereo in
    device.add_line("obj-plugin", 1, "mul_r", 0)
    device.add_line("mul_l", 0, "obj-plugout", 0)  # stereo out
    device.add_line("mul_r", 0, "obj-plugout", 1)
    device.add_line("gain", 0, "db2a", 0)          # dial -> dB to gain -> smoothed
    device.add_line("db2a", 0, "pk", 0)
    device.add_line("pk", 0, "ln", 0)
    device.add_line("ln", 0, "mul_l", 1)
    device.add_line("ln", 0, "mul_r", 1)
    return device
''',
    "midi": '''\
    device = MidiEffect(NAME, width=150, height=110, theme=COOL)
    device.add_panel("bg", [0, 0, 150, 110])
    device.add_comment("title", [10, 10, 130, 20], "MIDI in -> out")

    # A pass-through to start from: put your note processing between the two.
    device.add_newobj("in", "midiin")
    device.add_newobj("out", "midiout")
    device.add_line("in", 0, "out", 0)
    return device
''',
    "instrument": '''\
    device = Instrument(NAME, width=70, height=110, theme=SYNTHWAVE)
    device.add_panel("bg", [0, 0, 70, 110])
    device.add_dial("level", "Level", [10, 6, 50, 90],
                    min_val=-70.0, max_val=0.0, initial=-12.0,
                    unitstyle=4, annotation_name="Level")

    # notein -> mtof -> cycle~ ; velocity / 127 -> adsr~ ; osc * env * level -> out
    device.add_newobj("notein", "notein")
    device.add_newobj("mtof", "mtof")
    device.add_newobj("osc", "cycle~")
    device.add_newobj("vel", "/ 127.")
    device.add_newobj("env", "adsr~ 10 80 0.6 300")
    device.add_newobj("amp", "*~")
    device.add_newobj("db2a", "dbtoa")
    device.add_newobj("pk", "pack f 20")
    device.add_newobj("ln", "line~")
    device.add_newobj("lvl", "*~")
    device.add_newobj("out", "plugout~")

    device.add_line("notein", 0, "mtof", 0)
    device.add_line("mtof", 0, "osc", 0)
    device.add_line("notein", 1, "vel", 0)
    device.add_line("vel", 0, "env", 0)
    device.add_line("osc", 0, "amp", 0)
    device.add_line("env", 0, "amp", 1)
    device.add_line("level", 0, "db2a", 0)
    device.add_line("db2a", 0, "pk", 0)
    device.add_line("pk", 0, "ln", 0)
    device.add_line("amp", 0, "lvl", 0)
    device.add_line("ln", 0, "lvl", 1)
    device.add_line("lvl", 0, "out", 0)            # mono voice to both channels
    device.add_line("lvl", 0, "out", 1)
    return device
''',
}

_TEMPLATE = '''\
"""{title} -- a {kind} built with m4l-builder.

    m4l build {script}     # write it to your Ableton User Library
    m4l watch {script}     # rebuild on every save
    m4l lint {script}      # check it without writing anything
"""

from m4l_builder import {theme}, {klass}, device_output_path

NAME = {name!r}


def build_device() -> {klass}:
{body}

if __name__ == "__main__":
    path = device_output_path(NAME, {device_type!r}, create_dirs=False)
    build_device().build(path)
    print("wrote", path)
'''


def slugify(name: str) -> str:
    """``"My Gain!"`` -> ``"my_gain"``: a safe directory name for a device."""
    slug = re.sub(r"[^0-9a-zA-Z]+", "_", name).strip("_").lower()
    return slug or "device"


def scaffold(name: str, device_type: str = "audio") -> str:
    """Source of a runnable build script for a new device of ``device_type``."""
    klass, live_type, theme = _TYPES[device_type]
    kind = {"audio": "audio effect", "midi": "MIDI effect",
            "instrument": "instrument"}[device_type]
    return _TEMPLATE.format(title=name, kind=kind, script="build.py", theme=theme,
                            klass=klass, name=name, body=_BODIES[device_type],
                            device_type=live_type)


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #


def _cmd_new(args) -> int:
    target = Path(args.out) if args.out else Path(slugify(args.name)) / "build.py"
    if target.exists() and not args.force:
        print(f"m4l new: {target} already exists (pass --force to overwrite)",
              file=sys.stderr)
        return 1
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(scaffold(args.name, args.type), encoding="utf-8")
    print(f"created {target}")
    print(f"next:   m4l build {target}    (or: m4l watch {target})")
    return 0


def _cmd_build(args) -> int:
    if args.out:
        redirect: Redirect = _out_redirect(args.out)
    else:
        def redirect(device: Device, requested: str | None) -> str:
            return requested or _user_library_target(device, requested)
    builds = run_build_script(args.script, redirect, quiet=True)
    for record in builds:
        print(f"built {record.device.name} -> {record.written_path} "
              f"({record.bytes_written:,} bytes)")
    return 0


def _load_devices(target: Path) -> list[Device]:
    """The device in a .amxd (named after the file), or every device a build
    script builds, captured without writing anything."""
    if target.suffix.lower() == ".amxd":
        from .amxd import device_from_amxd

        device = device_from_amxd(str(target))
        device.name = target.stem
        return [device]
    return [record.device for record in
            run_build_script(target, lambda _d, _p: None, quiet=True)]


def _cmd_lint(args) -> int:
    devices = _load_devices(Path(args.target))

    errors = warnings = 0
    for device in devices:
        issues = lint_device(device)
        dev_errors = sum(1 for issue in issues if issue.severity == "error")
        errors += dev_errors
        warnings += len(issues) - dev_errors
        if not issues:
            print(f"ok    {device.name}: clean")
            continue
        print(f"{'FAIL' if dev_errors else 'warn'}  {device.name}: {dev_errors} error(s), "
              f"{len(issues) - dev_errors} warning(s)")
        for issue in issues:
            mark = "E" if issue.severity == "error" else "w"
            where = f" [{issue.box_id}]" if issue.box_id else ""
            print(f"  {mark} {issue.code}{where}: {issue.message}")
    if errors or (args.strict and warnings):
        return 1
    return 0


def _cmd_preview(args) -> int:
    from .preview import render_svg

    devices = _load_devices(Path(args.target))
    out = Path(args.out) if args.out else Path(".")
    single_file = out.suffix.lower() == ".svg"
    if single_file and len(devices) > 1:
        raise ScriptError(f"--out {out} names one file but there are {len(devices)} devices; "
                          f"pass a directory instead")
    for device in devices:
        target = out if single_file else out / f"{slugify(device.name)}.svg"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_svg(device, scale=args.scale, frame=not args.no_frame),
                          encoding="utf-8")
        print(f"preview {device.name} -> {target}")
    return 0


def _cmd_inspect(args) -> int:
    from .amxd import device_from_amxd

    device = device_from_amxd(args.file)
    device.name = Path(args.file).stem
    summary = device_summary(device, args.file)
    if args.json:
        summary.pop("box_ids", None)
        print(json.dumps(summary, indent=2))
    else:
        print(_format_summary(summary, path=args.file))
    return 0


def _cmd_import(args) -> int:
    from .importer import check_import, import_amxd

    source = Path(args.file)
    target = Path(args.out) if args.out else Path(slugify(source.stem)) / "build.py"
    if target.suffix != ".py":
        target = target / "build.py"
    result = import_amxd(source, script_name=target.name)
    clashes = [path for path in [target, *(target.parent / name for name in result.files)]
               if path.exists()]
    if clashes and not args.force:
        print(f"m4l import: {clashes[0]} already exists (pass --force to overwrite)",
              file=sys.stderr)
        return 1
    written = result.write(target)
    print(f"created {target}")
    for path in written[1:]:
        print(f"        {path}  (support file)")
    theme = result.theme_name or "none recognised"
    print(f"{result.class_name}, theme {theme}: {result.box_count} boxes, "
          f"{result.line_count} patch lines")
    if result.raw_boxes:
        print(f"kept raw: {len(result.raw_boxes)} box(es) no m4l-builder call reproduces "
              "(marked TODO(m4l import) in the script)")
        for entry in result.raw_boxes:
            print(f"  - {entry}")
    if result.missing:
        print(f"missing support files: {', '.join(result.missing)} (not inside the device "
              "or next to it)")
    if result.source.unsafe:
        print(f"ignored support files pointing outside the device folder: "
              f"{', '.join(result.source.unsafe)}")
    if not args.no_check:
        try:
            diffs = check_import(result.source, target)
        except Exception as exc:  # the generated script itself failed to run
            print(f"round-trip check failed: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 1
        if diffs:
            print("round-trip: the script does NOT rebuild an identical device:")
            for diff in diffs:
                print(f"  - {diff}")
            return 1
        print("round-trip: the script rebuilds an identical device (box IDs aside)")
    print(f"next:   m4l build {target}    (or: m4l watch {target})")
    return 0


def _parse_params(pairs: list[str]) -> dict[str, str]:
    params: dict[str, str] = {}
    for pair in pairs:
        name, sep, value = pair.partition("=")
        if not sep or not name.strip():
            raise ScriptError(f"--param {pair!r}: expected NAME=VALUE")
        params[name.strip()] = value.strip()
    return params


def _render_source(target: Path, device_name: str | None):
    if target.suffix.lower() == ".amxd":
        return str(target)
    devices = [record.device for record in
               run_build_script(target, lambda _d, _p: None, quiet=True)]
    if device_name is not None:
        devices = [d for d in devices if d.name == device_name]
        if not devices:
            raise ScriptError(f"{target}: builds no device named {device_name!r}")
    if len(devices) > 1:
        names = ", ".join(repr(d.name) for d in devices)
        raise ScriptError(f"{target} builds {len(devices)} devices ({names}); pick one "
                          f"with --device NAME")
    return devices[0]


def _format_render(result, signal_label: str, dry_check) -> str:
    def cell(value: float) -> str:
        return f"{round(value, 1) + 0.0:8.1f}" if value != float("-inf") else "    -inf"

    summary = result.summary()
    labels = (["L", "R"] if len(result.output) == 2 else
              [str(i + 1) for i in range(len(result.output))])
    rows_in = summary["input"]
    if len(rows_in) < len(labels):  # mono input fed to every channel
        rows_in = rows_in + [rows_in[-1]] * (len(labels) - len(rows_in))
    columns = [(f"in {lab}", row) for lab, row in zip(labels, rows_in, strict=False)]
    columns += [(f"out {lab}", row) for lab, row in zip(labels, summary["output"], strict=True)]
    lines = [f"{result.device}: rendered {result.seconds:.2f} s of {signal_label} "
             f"at {result.samplerate:g} Hz through {len(result.path)} boxes"]
    if result.params:
        lines.append("  params      " + ", ".join(f"{k} = {v:g}" for k, v in result.params.items()))
    lines.append("  dBFS        " + "".join(f"{name:>8}" for name, _ in columns))
    lines.append("  rms         " + "".join(cell(row["rms_db"]) for _, row in columns))
    lines.append("  peak        " + "".join(cell(row["peak_db"]) for _, row in columns))
    for band in columns[0][1]["bands_db"]:
        lines.append(f"  {band:<12}" + "".join(cell(row["bands_db"][band]) for _, row in columns))
    if any(row["nonfinite"] for row in summary["output"]):
        bad = sum(row["nonfinite"] for row in summary["output"])
        lines.append(f"  WARNING     {bad} NaN/Inf output sample(s)")
    if dry_check is not None:
        verdict = "" if dry_check.ok else "  <- DRY: the output is the input, untouched"
        lines.append(f"  change      {dry_check.detail.split(': ', 1)[1]}{verdict}")
    for note in result.notes:
        lines.append(f"  note        {note}")
    return "\n".join(lines)


def _finite_json(value):
    """-inf dB (silence) and other non-finite floats become null: strict JSON."""
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {k: _finite_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_finite_json(v) for v in value]
    return value


def _cmd_render(args) -> int:
    from .render import check_finite, check_not_dry, render

    target = Path(args.target)
    source = _render_source(target, args.device)
    signal = args.input or args.signal
    result = render(source, signal, params=_parse_params(args.param),
                    samplerate=args.samplerate, seconds=args.seconds,
                    level_db=args.level, freq=args.freq, seed=args.seed,
                    strict=args.strict)
    silent_in = all(v == 0.0 for ch in result.input for v in ch)
    dry = None if silent_in else check_not_dry(result)
    clipped = result.write(args.out) if args.out else None
    if args.json:
        payload = {"device": result.device, "samplerate": result.samplerate,
                   "seconds": result.seconds, "params": result.params,
                   "notes": result.notes, "path": result.path, **result.summary()}
        if dry is not None:
            payload["not_dry"] = dry.ok
        print(json.dumps(_finite_json(payload), indent=2, allow_nan=False))
    else:
        label = args.input or args.signal
        print(_format_render(result, label, dry))
        if args.out:
            print(f"wrote {args.out} (24-bit PCM"
                  + (f", {clipped} sample(s) clipped to full scale)" if clipped else ")"))
    if args.check:
        sys.stdout.flush()
        failed = [c for c in (dry, check_finite(result)) if c is not None and not c]
        for check in failed:
            print(f"m4l render: check failed: {check}", file=sys.stderr)
        return 1 if failed else 0
    return 0


def watch(script: str | os.PathLike, *, out: str | None = None, interval: float = 0.5) -> int:
    """Rebuild ``script`` every time its mtime changes, until Ctrl-C.

    Each build goes to the User Library (``device_output_path``) unless ``out``
    names a directory or ``.amxd`` file, and prints what changed since the last
    build. A script that raises reports the error and keeps watching.
    """
    path = Path(script)
    previous: dict[str, dict] = {}
    last_mtime: float | None = None
    print(f"watching {path} (Ctrl-C to stop)", flush=True)
    try:
        while True:
            try:
                mtime: float | None = path.stat().st_mtime
            except FileNotFoundError:
                mtime = None
            if mtime is not None and mtime != last_mtime:
                last_mtime = mtime
                _rebuild(path, out, previous)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("stopped")
    return 0


def _rebuild(path: Path, out: str | None, previous: dict[str, dict]) -> None:
    stamp = time.strftime("%H:%M:%S")
    redirect = _out_redirect(out) if out else _user_library_target
    try:
        builds = run_build_script(path, redirect, quiet=True)
    except Exception as exc:  # keep watching through script errors
        detail = "".join(traceback.format_exception_only(type(exc), exc)).strip()
        print(f"[{stamp}] build failed: {detail}", flush=True)
        return
    for record in builds:
        summary = device_summary(record.device, record.written_path)
        key = record.written_path or record.device.name
        print(f"[{stamp}] built {record.device.name} -> {record.written_path}")
        for change in diff_summaries(previous.get(key), summary):
            print(f"           {change}")
        previous[key] = summary
    sys.stdout.flush()


def _cmd_watch(args) -> int:
    return watch(args.script, out=args.out, interval=args.interval)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="m4l", description="Build Max for Live devices from Python scripts.")
    sub = parser.add_subparsers(dest="command", metavar="<command>", required=True)

    p = sub.add_parser("new", help="scaffold a build script for a new device")
    p.add_argument("name", help='device name, e.g. "My Gain"')
    p.add_argument("--type", choices=sorted(_TYPES), default="audio",
                   help="device type (default: audio)")
    p.add_argument("--out", help="script path (default: <name>/build.py)")
    p.add_argument("--force", action="store_true", help="overwrite an existing file")
    p.set_defaults(func=_cmd_new)

    p = sub.add_parser("build", help="run a build script and write its .amxd")
    p.add_argument("script", help="build script (.py)")
    p.add_argument("--out", help="write here instead: a .amxd file or a directory")
    p.set_defaults(func=_cmd_build)

    p = sub.add_parser("watch", help="rebuild into the User Library on every save")
    p.add_argument("script", help="build script (.py)")
    p.add_argument("--out", help="write here instead of the User Library")
    p.add_argument("--interval", type=float, default=0.5,
                   help="seconds between checks (default: 0.5)")
    p.set_defaults(func=_cmd_watch)

    p = sub.add_parser("lint", help="validate a build script or .amxd without writing")
    p.add_argument("target", help="build script (.py) or device (.amxd)")
    p.add_argument("--strict", action="store_true", help="fail on warnings too")
    p.set_defaults(func=_cmd_lint)

    p = sub.add_parser("preview", help="render a device's presentation view to SVG")
    p.add_argument("target", help="build script (.py) or device (.amxd)")
    p.add_argument("--out", help="a .svg file or a directory (default: <name>.svg here)")
    p.add_argument("--scale", type=float, default=1.0,
                   help="display size multiplier (default: 1)")
    p.add_argument("--no-frame", action="store_true",
                   help="leave out the title strip with the device name")
    p.set_defaults(func=_cmd_preview)

    p = sub.add_parser("inspect", help="summarise a .amxd: type, size, parameters, boxes")
    p.add_argument("file", help="device (.amxd)")
    p.add_argument("--json", action="store_true", help="print the summary as JSON")
    p.set_defaults(func=_cmd_inspect)

    p = sub.add_parser("import", help="write a build script that rebuilds an existing .amxd")
    p.add_argument("file", help="device (.amxd), frozen or with its support files beside it")
    p.add_argument("--out", help="script path or folder (default: <name>/build.py)")
    p.add_argument("--force", action="store_true", help="overwrite existing files")
    p.add_argument("--no-check", action="store_true",
                   help="skip running the script to confirm it rebuilds the device")
    p.set_defaults(func=_cmd_import)

    from .render import SIGNAL_KINDS

    p = sub.add_parser("render", help="run a device's audio path offline: WAV in, WAV out")
    p.add_argument("target", help="build script (.py) or device (.amxd)")
    source = p.add_mutually_exclusive_group()
    source.add_argument("--in", dest="input", metavar="WAV", help="input WAV file")
    source.add_argument("--signal", choices=SIGNAL_KINDS, default="noise",
                        help="generated input when there is no --in (default: noise)")
    p.add_argument("--out", metavar="WAV", help="write the output here (24-bit PCM)")
    p.add_argument("--param", action="append", default=[], metavar="NAME=VALUE",
                   help="set a parameter by name (repeatable)")
    p.add_argument("--seconds", type=float, default=1.0,
                   help="length of a generated signal (default: 1)")
    p.add_argument("--samplerate", type=float, default=None,
                   help="sample rate of a generated signal (default: 48000)")
    p.add_argument("--level", type=float, default=-6.0,
                   help="peak level of a generated signal in dBFS (default: -6)")
    p.add_argument("--freq", type=float, default=440.0,
                   help="frequency of --signal sine in Hz (default: 440)")
    p.add_argument("--seed", type=int, default=0, help="seed for noise (default: 0)")
    p.add_argument("--device", help="which device, when the script builds several")
    p.add_argument("--strict", action="store_true",
                   help="refuse approximate gen constructs instead of noting them")
    p.add_argument("--check", action="store_true",
                   help="exit 1 if the output is a dry copy of the input or has NaN/Inf")
    p.add_argument("--json", action="store_true", help="print the summary as JSON")
    p.set_defaults(func=_cmd_render)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except (ScriptError, ValueError, OSError) as exc:
        print(f"m4l {args.command}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
