"""Turn an existing ``.amxd`` into a readable m4l-builder build script.

:func:`import_amxd` reads a device (frozen or not, plus the sidecar files next
to it) and writes the source of a ``build.py`` that rebuilds an equivalent
device: the right device class, its size and theme, UI controls as
``add_dial`` / ``add_menu`` / ... calls, objects as ``add_newobj``, patchlines
as ``add_line``, and gen~ code, scripts and subpatchers carried across.

Every call is checked before it is written: the importer builds the box with
the call it is about to emit and keeps only the arguments that make the result
match the source box exactly. Attributes the source leaves unset but a helper
fills in are dropped again by a small ``_unset`` call in the script. A box no
helper can reproduce is written as a raw ``add_box`` with a TODO comment, so
nothing is dropped. :func:`check_import` runs the written script and compares
the rebuilt patcher with the source (:func:`patcher_differences`).
"""

from __future__ import annotations

import copy
import inspect
import json
import keyword
import math
import re
import runpy
import textwrap
import warnings
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import objects, theme, ui
from .constants import DEVICE_TYPE_CODES
from .device import Device
from .dsp import stereo_io
from .freeze import _patcher_dict_from_payload, _read_amxd, extract_frozen_amxd
from .gen_patcher import gendsp_support_name
from .native_sizes import DEVICE_H
from .patcher_walk import unwrap_box
from .profiles import DEFAULT_PATCHER_PROFILE
from .subpatcher import Subpatcher

__all__ = [
    "ImportedDevice",
    "SourceDevice",
    "check_import",
    "import_amxd",
    "patcher_differences",
    "read_device",
    "rebuild_from_script",
]

WIDTH = 100
TODO = "TODO(m4l import)"

_CLASSES = {
    "audio_effect": "AudioEffect",
    "instrument": "Instrument",
    "midi_effect": "MidiEffect",
    "note_transformation": "MidiTransformation",
    "note_generator": "MidiGenerator",
}
_TYPE_BY_CODE = {code: name for name, code in DEVICE_TYPE_CODES.items()}


# --------------------------------------------------------------------------- #
# Reading the source device
# --------------------------------------------------------------------------- #


@dataclass
class SourceDevice:
    """An ``.amxd`` as read from disk: its patcher and the files it depends on."""

    path: Path
    name: str
    device_type: str
    patcher: dict
    assets: dict[str, bytes]
    missing: list[str]
    frozen: bool

    @property
    def width(self) -> Any:
        return self.patcher.get("devicewidth", self.patcher.get("openrect", [0, 0, 400, 170])[2])

    @property
    def height(self) -> Any:
        return self.patcher.get("openrect", [0, 0, 400, 170])[3]


def read_device(path: str | Path) -> SourceDevice:
    """Read an ``.amxd`` (frozen or not) and the dependency files it lists.

    A frozen device carries its dependencies inside; an unfrozen one finds them
    next to the ``.amxd``. Dependencies found in neither place are ``missing``.
    """
    path = Path(path)
    try:
        type_code, payload, frozen = _read_amxd(str(path))
    except Exception as exc:
        raise ValueError(f"{path}: not a readable .amxd ({exc})") from exc
    if type_code not in _TYPE_BY_CODE:
        raise ValueError(f"{path}: unknown device type code {type_code!r}")
    assets: dict[str, bytes] = {}
    try:
        if frozen:
            contents = extract_frozen_amxd(path.read_bytes())
            names = list(contents)
            if not names:
                raise ValueError("frozen device has no patcher")
            top = _patcher_dict_from_payload(contents[names[0]])
            assets = {name: contents[name] for name in names[1:]}
        else:
            top = _patcher_dict_from_payload(payload)
    except ValueError as exc:
        raise ValueError(f"{path}: patcher JSON could not be read ({exc})") from exc
    patcher = top.get("patcher") if isinstance(top, dict) else None
    if not isinstance(patcher, dict):
        raise ValueError(f"{path}: no patcher in the device")

    missing = []
    for name in _dependency_names(patcher):
        if name in assets:
            continue
        sidecar = path.parent / name
        if sidecar.is_file():
            assets[name] = sidecar.read_bytes()
        else:
            missing.append(name)
    return SourceDevice(path=path, name=path.stem, device_type=_TYPE_BY_CODE[type_code],
                        patcher=patcher, assets=assets, missing=missing, frozen=frozen)


def _dependency_names(patcher: dict) -> list[str]:
    names = []
    for dep in patcher.get("dependency_cache", []):
        name = dep.get("name") if isinstance(dep, dict) else None
        if isinstance(name, str) and name and name not in names:
            names.append(name)
    return names


# --------------------------------------------------------------------------- #
# Writing Python source
# --------------------------------------------------------------------------- #


@dataclass
class Code:
    """A value written into the script as ``text`` and simulated as ``value``."""

    text: str
    value: Any


def _values(obj: Any) -> Any:
    """``obj`` with every :class:`Code` replaced by its value (deep-copied)."""
    if isinstance(obj, Code):
        return copy.deepcopy(obj.value)
    if isinstance(obj, dict):
        return {key: _values(val) for key, val in obj.items()}
    if isinstance(obj, list):
        return [_values(val) for val in obj]
    if isinstance(obj, tuple):
        return tuple(_values(val) for val in obj)
    return copy.deepcopy(obj)


def _py(value: Any) -> str:
    """One-line Python source for a JSON-like value."""
    if isinstance(value, Code):
        return value.text
    if value is None or isinstance(value, bool):
        return repr(value)
    if isinstance(value, int):
        return repr(value)
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return f'float("{value}")'
        return repr(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, tuple):
        inner = ", ".join(_py(val) for val in value)
        return f"({inner},)" if len(value) == 1 else f"({inner})"
    if isinstance(value, list):
        return "[" + ", ".join(_py(val) for val in value) + "]"
    if isinstance(value, dict):
        return "{" + ", ".join(f"{_py(key)}: {_py(val)}" for key, val in value.items()) + "}"
    raise TypeError(f"cannot write {type(value).__name__} as Python source")


def _py_block(value: Any, indent: int) -> str:
    """Python source for ``value``; containers break over lines when too long.

    The first line is not indented (it follows whatever precedes it); nested
    lines are indented from ``indent`` and the closing bracket sits at it.
    """
    flat = _py(value)
    if indent + len(flat) <= WIDTH or not isinstance(value, (dict, list)) or not value:
        return flat
    pad = " " * (indent + 4)
    if isinstance(value, dict):
        items = [f"{pad}{_py(key)}: {_py_block(val, indent + 4)}," for key, val in value.items()]
        return "{\n" + "\n".join(items) + "\n" + " " * indent + "}"
    items = [f"{pad}{_py_block(val, indent + 4)}," for val in value]
    return "[\n" + "\n".join(items) + "\n" + " " * indent + "]"


def _kwarg_parts(kwargs: dict[str, Any]) -> list[tuple[str, Any]]:
    parts: list[tuple[str, Any]] = []
    extra: dict[str, Any] = {}
    for key, val in kwargs.items():
        if key.isidentifier() and not keyword.iskeyword(key):
            parts.append((f"{key}=", val))
        else:
            extra[key] = val
    if extra:
        parts.append(("**", extra))
    return parts


def _render_call(callee: str, args: list[Any], kwargs: dict[str, Any], indent: int = 4) -> str:
    """``callee(args, kwargs)`` wrapped to WIDTH with a hanging indent."""
    parts: list[tuple[str, Any]] = [("", arg) for arg in args] + _kwarg_parts(kwargs)
    head = " " * indent + callee + "("
    flat = head + ", ".join(prefix + _py(val) for prefix, val in parts) + ")"
    if len(flat) <= WIDTH:
        return flat
    col = len(head)
    lines: list[str] = []
    cur = head
    fresh = True  # nothing on ``cur`` yet but indentation / the call head
    for index, (prefix, val) in enumerate(parts):
        end = ")" if index == len(parts) - 1 else ","
        piece = prefix + _py(val) + end
        sep = "" if fresh else " "
        if len(cur) + len(sep) + len(piece) <= WIDTH:
            cur += sep + piece
            fresh = False
            continue
        if not fresh:
            lines.append(cur)
            cur = " " * col
        if len(cur) + len(piece) > WIDTH:
            piece = prefix + _py_block(val, col) + end
        cur += piece
        fresh = False
    lines.append(cur)
    return "\n".join(lines)


def _str_constant(text: str) -> str:
    """A readable literal for a multi-line string (GenExpr code)."""
    lines = text.split("\n")
    safe = (
        '"""' not in text and "\\" not in text and "\t" not in text and "\r" not in text
        and not text.endswith('"')
        and all(line == line.rstrip() for line in lines)
        and all(ch.isprintable() or ch == "\n" for ch in text)
    )
    if safe:
        return '"""\\\n' + text + '"""'
    chunks = [json.dumps(line + "\n", ensure_ascii=False) for line in lines[:-1]]
    if lines[-1]:
        chunks.append(json.dumps(lines[-1], ensure_ascii=False))
    if not chunks:
        return '""'
    return "(\n" + "\n".join("    " + chunk for chunk in chunks) + "\n)"


def _slug(text: str) -> str:
    return re.sub(r"[^0-9a-zA-Z]+", "_", text).strip("_").lower()


def _const_name(base: str) -> str:
    name = re.sub(r"[^0-9A-Za-z]+", "_", base).strip("_").upper() or "CODE"
    return f"_{name}" if name[0].isdigit() else name


# --------------------------------------------------------------------------- #
# Readable box IDs
# --------------------------------------------------------------------------- #

_MAX_ID = re.compile(r"obj-\d+$")
_OPERATOR_WORDS = {
    "+": "add", "-": "sub", "*": "mul", "/": "div", "%": "mod", "!-": "rsub",
    "!/": "rdiv", "!%": "rmod", ">": "gt", "<": "lt", ">=": "gte", "<=": "lte",
    "==": "eq", "!=": "neq", "&&": "and", "||": "or", "&": "bitand", "|": "bitor",
    "<<": "shl", ">>": "shr", "t": "trig", "trigger": "trig", "b": "bang",
}


def _valueof(box: dict) -> dict:
    saved = box.get("saved_attribute_attributes")
    valueof = saved.get("valueof") if isinstance(saved, dict) else None
    return valueof if isinstance(valueof, dict) else {}


def _id_hint(box: dict) -> str:
    """A readable ID stem from what the box is: its object text, parameter or kind."""
    maxclass = str(box.get("maxclass", ""))
    text = str(box.get("text", ""))
    tokens = text.split()
    if maxclass == "newobj":
        head = tokens[0] if tokens else "obj"
        if head in ("p", "patcher") and len(tokens) > 1:
            return _slug(tokens[1]) or "sub"
        if head in ("js", "v8") and len(tokens) > 1:
            return _slug(Path(tokens[1]).stem) or head
        if head == "gen~" and len(tokens) > 1:
            return _slug(tokens[1]) or "gen"
        if head.endswith("~") and len(head) > 1:
            head = head[:-1]
        return _OPERATOR_WORDS.get(head) or _slug(head.removeprefix("live.")) or "obj"
    if maxclass == "message":
        return "msg_" + _slug(tokens[0]) if tokens and _slug(tokens[0]) else "msg"
    if maxclass in ("comment", "live.comment"):
        words = _slug(" ".join(tokens[:3]))
        return f"{words}_label" if words else "label"
    name = _valueof(box).get("parameter_longname") or box.get("varname")
    if isinstance(name, str) and _slug(name):
        return _slug(name)
    if maxclass in ("jsui", "v8ui") and isinstance(box.get("filename"), str):
        return _slug(Path(box["filename"]).stem) or maxclass
    if maxclass == "panel":
        rect = box.get("presentation_rect") or [1, 1]
        return "bg" if list(rect[:2]) == [0, 0] else "panel"
    return _slug(maxclass.replace("live.", "")) or "box"


def _plan_ids(boxes: list[dict], taken: dict[str, str] | None = None) -> dict[str, str]:
    """Map each source ID to a readable, unique one.

    Max's own ``obj-N`` IDs are replaced by a name derived from the box; IDs
    someone already chose are kept. ``taken`` pins IDs decided beforehand.
    """
    mapping = dict(taken or {})
    used = set(mapping.values())
    for box in boxes:
        box_id = str(box.get("id"))
        if box_id in mapping or _MAX_ID.match(box_id) or box_id in used:
            continue
        mapping[box_id] = box_id
        used.add(box_id)
    for box in boxes:
        box_id = str(box.get("id"))
        if box_id in mapping:
            continue
        base = _id_hint(box)
        candidate, n = base, 2
        while candidate in used:
            candidate, n = f"{base}_{n}", n + 1
        mapping[box_id] = candidate
        used.add(candidate)
    return mapping


def _renamed(patcher: dict, mapping: dict[str, str]) -> tuple[list[dict], list[dict]]:
    """The patcher's boxes and patchlines with IDs replaced through ``mapping``."""
    boxes = []
    for entry in patcher.get("boxes", []):
        box = copy.deepcopy(unwrap_box(entry))
        box["id"] = mapping.get(str(box.get("id")), box.get("id"))
        boxes.append(box)
    lines = []
    for entry in patcher.get("lines", []):
        line = copy.deepcopy(entry.get("patchline", entry))
        try:
            line["source"][0] = mapping.get(line["source"][0], line["source"][0])
            line["destination"][0] = mapping.get(line["destination"][0],
                                                 line["destination"][0])
        except (KeyError, IndexError, TypeError):
            pass
        lines.append(line)
    return boxes, lines


# --------------------------------------------------------------------------- #
# Matching one box with a library call
# --------------------------------------------------------------------------- #

def _same(a: Any, b: Any) -> bool:
    """Equal including JSON type (1 vs 1.0 vs True all differ)."""
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def _extra_paths(made: Any, want: Any, prefix: str) -> list[str] | None:
    """Dotted paths of keys ``made`` has and ``want`` lacks, or None if they
    differ in any other way."""
    if isinstance(made, dict) and isinstance(want, dict):
        paths: list[str] = []
        for key in made:
            if key not in want:
                paths.append(f"{prefix}.{key}")
                continue
            nested = _extra_paths(made[key], want[key], f"{prefix}.{key}")
            if nested is None:
                return None
            paths.extend(nested)
        if any(key not in made for key in want):
            return None
        return paths
    return [] if _same(made, want) else None


def _residual(made: dict, want: dict) -> tuple[dict[str, Any], list[str]]:
    """What separates a built box from the wanted one: top-level values to
    override, and dotted paths of attributes to drop again."""
    overrides: dict[str, Any] = {}
    unsets: list[str] = []
    for key in want:
        if key not in made:
            overrides[key] = want[key]
        elif not _same(made[key], want[key]):
            nested = _extra_paths(made[key], want[key], key)
            if nested is None:
                overrides[key] = want[key]
            else:
                unsets.extend(nested)
    unsets.extend(key for key in made if key not in want)
    return overrides, unsets


@dataclass
class _Ctx:
    """What a box conversion needs to know about the device being imported."""

    source: SourceDevice
    theme: Any = None
    theme_name: str | None = None
    constants: set[str] = field(default_factory=set)

    def constant(self, base: str, *, reserve: bool = True) -> str:
        """A module-level constant name, unique across the whole script."""
        stem = _const_name(base)
        name, n = stem, 2
        while name in self.constants:
            name, n = f"{stem}_{n}", n + 1
        if reserve:
            self.constants.add(name)
        return name


def _scratch(ctx: _Ctx, scope: str) -> Any:
    if scope == "device":
        return Device("scratch", ctx.source.width, ctx.source.height,
                      device_type=ctx.source.device_type, theme=ctx.theme)
    return Subpatcher("scratch")


def _invoke(container: Any, method: str, args: list[Any], kwargs: dict[str, Any]) -> None:
    if method == "add_message":
        container.add_box(objects.message(*args, **kwargs))
    else:
        getattr(container, method)(*args, **kwargs)


def _simulate(ctx: _Ctx, scope: str, method: str, args: list[Any],
              kwargs: dict[str, Any]) -> tuple[dict, dict[str, bytes]] | None:
    """Run the call on a scratch container: the box it adds and its assets."""
    container = _scratch(ctx, scope)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            _invoke(container, method, _values(args), _values(kwargs))
    except Exception:
        return None
    if not container.boxes:
        return None
    assets = {}
    for asset in container.assets():
        content = asset.content
        assets[asset.filename] = (content if isinstance(content, bytes)
                                  else content.encode(asset.encoding))
    return unwrap_box(container.boxes[-1]), assets


@dataclass
class _Fit:
    kwargs: dict[str, Any]
    unsets: list[str]


def _fit(ctx: _Ctx, scope: str, method: str, args: list[Any], kwargs: dict[str, Any],
         want: dict, *, fixed: set[str],
         keep: frozenset[str] | set[str] = frozenset(),
         assets: dict[str, bytes] | None = None,
         locked: frozenset[str] | set[str] = frozenset()) -> _Fit | str:
    """Find the smallest kwargs for which ``method(*args, **kwargs)`` rebuilds
    ``want`` exactly (after dropping unset attributes). Returns a reason
    string when no kwargs can.

    Box attributes that differ are passed as kwargs (every factory applies
    extra kwargs to the box last) until the box matches. ``fixed`` names box
    keys the positional args set (cannot be overridden); ``keep`` kwargs are
    never minimised away; ``locked`` box keys may not be overridden
    by a kwarg (they would need the whole value written out); ``assets`` must
    come out byte-identical.
    """
    kwargs = dict(kwargs)

    def attempt(trial: dict[str, Any]) -> tuple[dict[str, Any], list[str]] | None:
        result = _simulate(ctx, scope, method, args, trial)
        if result is None:
            return None
        made, made_assets = result
        for name, content in (assets or {}).items():
            if made_assets.get(name) != content:
                return None
        return _residual(made, want)

    for _ in range(10):
        outcome = attempt(kwargs)
        if outcome is None:
            return f"{_callee_name(method)}() rejects this box"
        overrides, _unsets = outcome
        if not overrides:
            break
        progressed = False
        for key, value in overrides.items():
            if key in fixed or key in locked:
                continue
            if key not in kwargs or not _same(_values(kwargs[key]), value):
                kwargs[key] = copy.deepcopy(value)
                progressed = True
        if not progressed:
            break

    outcome = attempt(kwargs)
    if outcome is None:
        return f"{_callee_name(method)}() rejects this box"
    overrides, unsets = outcome
    if overrides:
        keys = ", ".join(sorted(overrides))
        return f"{_callee_name(method)}() can't reproduce: {keys}"

    for name in list(kwargs):
        if name in keep:
            continue
        trial = {key: val for key, val in kwargs.items() if key != name}
        retry = attempt(trial)
        if retry is not None and not retry[0] and sorted(retry[1]) == sorted(unsets):
            kwargs = trial
    return _Fit(kwargs=kwargs, unsets=unsets)


def _callee_name(method: str) -> str:
    return "message" if method == "add_message" else method


def _ordered(kwargs: dict[str, Any], order: list[str], want: dict) -> dict[str, Any]:
    """Signature parameters first (in signature order), then box attributes in
    the source box's order."""
    rank = {name: i for i, name in enumerate(order)}
    box_rank = {name: i for i, name in enumerate(want)}
    return dict(sorted(kwargs.items(), key=lambda item: (
        0 if item[0] in rank else 1, rank.get(item[0], box_rank.get(item[0], 10_000)))))


# --------------------------------------------------------------------------- #
# Box converters
# --------------------------------------------------------------------------- #


@dataclass
class _Emit:
    """The statement(s) written for one box, plus what they need."""

    code: list[str]
    box_id: str
    unsets: list[str] = field(default_factory=list)
    raw_reason: str | None = None
    raw_inside: list[str] = field(default_factory=list)  # raw boxes in a subpatcher
    imports: set[tuple[str, str]] = field(default_factory=set)
    constants: dict[str, str] = field(default_factory=dict)
    files: dict[str, bytes] = field(default_factory=dict)
    consumed: set[str] = field(default_factory=set)
    helpers: set[str] = field(default_factory=set)
    cost: int = 0


def _signature(fn: Callable) -> list[str]:
    return [name for name in inspect.signature(fn).parameters if name not in ("self",)]


def _initial(value: Any) -> Any:
    if isinstance(value, list) and len(value) == 1:
        return value[0]
    return value


def _setter(name: str) -> Callable[[Any], tuple[str, Any]]:
    return lambda value: (name, copy.deepcopy(value))


def _param_map(fn: Callable) -> dict[str, Callable[[Any], tuple[str, Any]]]:
    """Parameter attributes (``valueof`` keys) a widget factory sets via a kwarg."""
    params = set(_signature(fn))
    table: dict[str, Callable[[Any], tuple[str, Any]]] = {}
    simple = {
        "parameter_shortname": "shortname",
        "parameter_mmin": "min_val",
        "parameter_mmax": "max_val",
        "parameter_unitstyle": "unitstyle",
        "parameter_exponent": "parameter_exponent",
        "parameter_annotation_name": "annotation_name",
        "parameter_info": "info",
        "parameter_units": "units",
        "parameter_steps": "steps",
        "parameter_invisible": "invisible",
    }
    for attr, name in simple.items():
        if name in params:
            table[attr] = _setter(name)
    if "initial" in params:
        table["parameter_initial"] = lambda v: ("initial", _initial(copy.deepcopy(v)))
    if "options" in params:
        table["parameter_enum"] = lambda v: ("options", list(v))
    elif "labels" in params:
        table["parameter_enum"] = lambda v: ("labels", tuple(v))
    return table


@dataclass(frozen=True)
class _Widget:
    method: str
    factory: Callable
    positional: tuple[str, ...]


_WIDGETS = {
    "panel": _Widget("add_panel", ui.panel, ("rect",)),
    "live.dial": _Widget("add_dial", ui.dial, ("varname", "rect")),
    "live.tab": _Widget("add_tab", ui.tab, ("varname", "rect")),
    "live.toggle": _Widget("add_toggle", ui.toggle, ("varname", "rect")),
    "live.menu": _Widget("add_menu", ui.menu, ("varname", "rect")),
    "live.numbox": _Widget("add_number_box", ui.number_box, ("varname", "rect")),
    "live.slider": _Widget("add_slider", ui.slider, ("varname", "rect")),
    "live.button": _Widget("add_button", ui.button, ("varname", "rect")),
    "live.text": _Widget("add_live_text", ui.live_text, ("varname", "rect")),
    "live.gain~": _Widget("add_live_gain", ui.live_gain, ("varname", "rect")),
    "live.comment": _Widget("add_comment", ui.comment, ("rect", "text")),
    "live.meter~": _Widget("add_meter", ui.meter, ("rect",)),
    "live.scope~": _Widget("add_scope", ui.scope, ("rect",)),
    "live.line": _Widget("add_live_line", ui.live_line, ("rect",)),
}
# The box keys each positional argument sets.
_POSITIONAL_KEYS = {"varname": {"varname"}, "rect": {"presentation_rect"}, "text": {"text"}}


def _emit_call(target: str, method: str, args: list[Any], kwargs: dict[str, Any],
               box_id: str, fit: _Fit, *, comment: str | None = None) -> _Emit:
    callee = f"{target}.add_box(message" if method == "add_message" else f"{target}.{method}"
    code = _render_call(callee, args, kwargs)
    if method == "add_message":
        code += ")"
    lines = [f"    # {comment}"] if comment else []
    lines.append(code)
    emit = _Emit(code=lines, box_id=box_id, unsets=fit.unsets,
                 cost=len(fit.kwargs) + len(fit.unsets))
    if method == "add_message":
        emit.imports.add(("m4l_builder", "message"))
    if fit.unsets:
        emit.helpers.add("unset")
    return emit


def _convert_widget(ctx: _Ctx, box: dict, target: str, scope: str) -> _Emit | str:
    rule = _WIDGETS[box["maxclass"]]
    valueof = _valueof(box)
    args: list[Any] = [box["id"]]
    for name in rule.positional:
        if name == "varname":
            longname = valueof.get("parameter_longname") or box.get("varname")
            if not isinstance(longname, str) or not longname.strip():
                return f"{rule.method}() needs a parameter name"
            args.append(longname)
        elif name == "rect":
            rect = box.get("presentation_rect") or box.get("patching_rect")
            if not isinstance(rect, list) or len(rect) != 4:
                return f"{rule.method}() needs a rect"
            args.append(copy.deepcopy(rect))
        elif name == "text":
            args.append(box.get("text", ""))
    kwargs: dict[str, Any] = {}
    keep: set[str] = set()
    params = _signature(rule.factory)
    if "options" in params:
        if "parameter_enum" not in valueof:
            return f"{rule.method}() needs the parameter's options"
        kwargs["options"] = list(valueof["parameter_enum"])
        keep.add("options")
    if rule.method == "add_panel":
        kwargs["bgcolor"] = copy.deepcopy(box.get("bgcolor"))
    for attr, to_kwarg in _param_map(rule.factory).items():
        if attr in valueof:
            name, value = to_kwarg(valueof[attr])
            kwargs.setdefault(name, value)
    kwargs.update(_initial_in_range(rule.factory, kwargs, valueof))
    fixed = {"id", "maxclass"}.union(*(_POSITIONAL_KEYS[name] for name in rule.positional))
    if "rect" in rule.positional and "presentation_rect" not in box:
        fixed.discard("presentation_rect")
    fit = _fit(ctx, scope, rule.method, args, kwargs, box, fixed=fixed, keep=keep)
    if isinstance(fit, str):
        return fit
    ordered = _ordered(fit.kwargs, params, box)
    return _emit_call(target, rule.method, args, ordered, box["id"], fit)


def _initial_in_range(factory: Callable, kwargs: dict[str, Any],
                      valueof: dict) -> dict[str, Any]:
    """An ``initial`` inside the range when the source stores none.

    Max leaves ``parameter_initial`` out unless it is enabled, but a factory's
    default initial (50.0 for a dial) can fall outside a source range like
    0..24, which the parameter spec rejects. The attribute is dropped again
    afterwards, so any in-range value will do; the minimum reads best.
    """
    params = inspect.signature(factory).parameters
    if "initial" not in params or "initial" in kwargs or "parameter_initial" in valueof:
        return {}
    def default(name: str) -> Any:
        return params[name].default if name in params else None
    low = kwargs.get("min_val", default("min_val"))
    high = kwargs.get("max_val", default("max_val"))
    initial = default("initial")
    numbers = all(isinstance(v, (int, float)) for v in (low, high, initial))
    if numbers and not low <= initial <= high:
        return {"initial": low}
    return {}


def _io_kwargs(box: dict) -> dict[str, Any]:
    kwargs = {key: copy.deepcopy(box[key]) for key in ("numinlets", "numoutlets", "outlettype")
              if key in box}
    if "patching_rect" in box:
        kwargs["patching_rect"] = copy.deepcopy(box["patching_rect"])
    return kwargs


def _convert_newobj(ctx: _Ctx, box: dict, target: str, scope: str) -> _Emit | str:
    args: list[Any] = [box["id"], box.get("text", "")]
    fit = _fit(ctx, scope, "add_newobj", args, _io_kwargs(box), box,
               fixed={"id", "maxclass", "text"}, locked={"patcher"})
    if isinstance(fit, str):
        return fit
    ordered = _ordered(fit.kwargs, _signature(objects.newobj), box)
    return _emit_call(target, "add_newobj", args, ordered, box["id"], fit)


def _convert_message(ctx: _Ctx, box: dict, target: str, scope: str) -> _Emit | str:
    args: list[Any] = [box["id"], box.get("text", "")]
    fit = _fit(ctx, scope, "add_message", args, _io_kwargs(box), box,
               fixed={"id", "maxclass", "text"})
    if isinstance(fit, str):
        return fit
    ordered = _ordered(fit.kwargs, _signature(objects.message), box)
    return _emit_call(target, "add_message", args, ordered, box["id"], fit)


def _gen_parts(patcher: dict) -> tuple[str, int, int, float, float] | None:
    """(code, numins, numouts, codebox_h, patcher_h) of a one-codebox gen patcher."""
    boxes = [unwrap_box(entry) for entry in patcher.get("boxes", [])]
    codeboxes = [box for box in boxes if box.get("maxclass") == "codebox"]
    if len(codeboxes) != 1 or not isinstance(codeboxes[0].get("code"), str):
        return None
    texts = [str(box.get("text", "")) for box in boxes if box.get("maxclass") == "newobj"]
    numins = sum(1 for text in texts if re.fullmatch(r"in \d+", text))
    numouts = sum(1 for text in texts if re.fullmatch(r"out \d+", text))
    try:
        codebox_h = codeboxes[0]["patching_rect"][3]
        patcher_h = patcher["rect"][3]
    except (KeyError, IndexError, TypeError):
        return None
    return codeboxes[0]["code"], numins, numouts, codebox_h, patcher_h


def _code_const(ctx: _Ctx, box_id: str, code: str) -> tuple[str, str]:
    """The constant a gen~ call will name; reserved only once the call is kept."""
    return ctx.constant(f"{box_id}_code", reserve=False), _str_constant(code)


def _convert_embedded_gen(ctx: _Ctx, box: dict, target: str, scope: str) -> _Emit | str:
    if scope != "device":
        return "embedded gen~ inside a subpatcher"
    parts = _gen_parts(box["patcher"])
    if parts is None:
        return "gen~ patcher is not a single codebox"
    code, numins, numouts, codebox_h, patcher_h = parts
    const, literal = _code_const(ctx, box["id"], code)
    args: list[Any] = [box["id"], Code(const, code), numins, numouts,
                       copy.deepcopy(box.get("patching_rect"))]
    kwargs = {"lint": False, "codebox_h": codebox_h, "patcher_h": patcher_h}
    fit = _fit(ctx, scope, "embed_gendsp", args, kwargs, box,
               fixed={"id", "maxclass", "text", "patching_rect"},
               locked={"patcher"})
    if isinstance(fit, str):
        if fit.endswith(": patcher"):
            return (f"gen~ patcher saved by Max (embed_gendsp() writes other patcher "
                    f"settings); its code is {const}")
        return fit
    ordered = _ordered(fit.kwargs, ["lint", "codebox_h", "patcher_h"], box)
    emit = _emit_call(target, "embed_gendsp", args, ordered, box["id"], fit)
    ctx.constants.add(const)
    emit.constants[const] = literal
    return emit


def _convert_external_gen(ctx: _Ctx, box: dict, target: str, scope: str,
                          filename: str) -> _Emit | str:
    if scope != "device":
        return "add_gendsp() inside a subpatcher"
    content = ctx.source.assets[filename]
    try:
        patcher = json.loads(content.decode("utf-8"))["patcher"]
    except (ValueError, KeyError, TypeError):
        return f"{filename} is not a gen patcher"
    parts = _gen_parts(patcher)
    if parts is None:
        return f"{filename} is not a single codebox"
    code, numins, numouts, codebox_h, patcher_h = parts
    stem = filename[: -len(".gendsp")].rsplit("_", 1)[0]
    if gendsp_support_name(stem, code) != filename:
        return f"{filename} is not content-addressed"
    const, literal = _code_const(ctx, box["id"], code)
    args: list[Any] = [box["id"], stem, Code(const, code), numins, numouts,
                       copy.deepcopy(box.get("patching_rect"))]
    kwargs = {"lint": False, "codebox_h": codebox_h, "patcher_h": patcher_h}
    fit = _fit(ctx, scope, "add_gendsp", args, kwargs, box,
               fixed={"id", "maxclass", "text"},
               assets={filename: content})
    if isinstance(fit, str):
        return fit
    ordered = _ordered(fit.kwargs, ["lint", "codebox_h", "patcher_h"], box)
    emit = _emit_call(target, "add_gendsp", args, ordered, box["id"], fit)
    ctx.constants.add(const)
    emit.constants[const] = literal
    emit.consumed.add(filename)
    return emit


def _convert_script_ui(ctx: _Ctx, box: dict, target: str, scope: str) -> _Emit | str:
    method = "add_jsui" if box["maxclass"] == "jsui" else "add_v8ui"
    if scope != "device":
        return f"{method}() inside a subpatcher"
    filename = box.get("filename")
    if not isinstance(filename, str) or filename not in ctx.source.assets:
        return f"script {filename!r} not found"
    content = ctx.source.assets[filename]
    try:
        js_code = content.decode("utf-8")
    except UnicodeDecodeError:
        return f"script {filename!r} is not UTF-8"
    rect = box.get("presentation_rect") or box.get("patching_rect")
    args: list[Any] = [box["id"], copy.deepcopy(rect)]
    kwargs: dict[str, Any] = {
        "js_code": Code(f"_asset({_py(filename)})", js_code),
        "js_filename": filename,
        "validate_contract": False,
    }
    kwargs.update({key: copy.deepcopy(box[key]) for key in ("numinlets", "numoutlets")
                   if key in box})
    factory = ui.jsui if method == "add_jsui" else ui.v8ui
    fixed = {"id", "maxclass", "filename"}
    if "presentation_rect" in box:
        fixed.add("presentation_rect")
    fit = _fit(ctx, scope, method, args, kwargs, box, fixed=fixed,
               keep={"js_code"}, assets={filename: content})
    if isinstance(fit, str):
        return fit
    order = ["js_code", "js_filename", "numinlets", "numoutlets", "validate_contract"]
    order += _signature(factory)
    emit = _emit_call(target, method, args, _ordered(fit.kwargs, order, box), box["id"], fit)
    emit.files[filename] = content
    emit.consumed.add(filename)
    emit.helpers.add("asset")
    return emit


def _subpatcher_header() -> dict:
    header = DEFAULT_PATCHER_PROFILE.build_subpatcher_patcher([], [])
    header.pop("boxes")
    header.pop("lines")
    return header


def _convert_subpatcher(ctx: _Ctx, box: dict, target: str, scope: str,
                        var_names: set[str]) -> _Emit | str:
    if scope != "device":
        return "nested subpatcher"
    inner = box["patcher"]
    header = {key: val for key, val in inner.items() if key not in ("boxes", "lines")}
    if not _same(header, _subpatcher_header()):
        return "Max-saved subpatcher (its patcher settings have no Subpatcher equivalent)"
    name = str(box.get("text", "")).split(None, 1)[1] if " " in str(box.get("text", "")) else ""
    if not name:
        return "unnamed subpatcher"
    base = f"sub_{_slug(name) or 'patch'}"
    var, n = base, 2
    while var in var_names:
        var, n = f"{base}_{n}", n + 1
    var_names.add(var)

    mapping = _plan_ids([unwrap_box(entry) for entry in inner.get("boxes", [])])
    boxes, lines = _renamed(inner, mapping)
    body = _convert_scope(ctx, boxes, lines, var, "sub", var_names)

    # Rebuild the wrapper the way the script will: a Subpatcher holding exactly
    # the (verified) inner boxes, then add_subpatcher.
    want = copy.deepcopy(box)
    want["patcher"] = {**header, "boxes": [{"box": b} for b in boxes],
                       "lines": [{"patchline": line} for line in lines]}
    sub = Subpatcher(name)
    sub.boxes = copy.deepcopy(want["patcher"]["boxes"])
    sub.lines = copy.deepcopy(want["patcher"]["lines"])
    args: list[Any] = [Code(var, sub), box["id"], copy.deepcopy(box.get("patching_rect"))]
    kwargs = {key: copy.deepcopy(box[key]) for key in ("numinlets", "numoutlets", "outlettype")
              if key in box}
    fit = _fit(ctx, scope, "add_subpatcher", args, kwargs, want,
               fixed={"id", "maxclass", "text", "patcher", "patching_rect"},
               locked=set(want) - {"numinlets", "numoutlets", "outlettype"})
    if isinstance(fit, str):
        return fit
    code = [f"    {var} = Subpatcher({_py(name)})"] + body.code
    emit = _emit_call(target, "add_subpatcher", args,
                      _ordered(fit.kwargs, ["numinlets", "numoutlets", "outlettype"], box),
                      box["id"], fit)
    emit.code = code + emit.code
    emit.imports |= body.imports | {("m4l_builder", "Subpatcher")}
    emit.constants.update(body.constants)
    emit.files.update(body.files)
    emit.consumed |= body.consumed
    emit.helpers |= body.helpers
    emit.cost += body.cost
    emit.raw_inside = [f"{box['id']}/{entry}" for entry in body.raw]
    return emit


def _hoist_code(ctx: _Ctx, value: Any, box_id: str, constants: dict[str, str]) -> Any:
    """Replace codebox ``code`` strings inside a raw box with module constants."""
    if isinstance(value, dict):
        out = {}
        for key, val in value.items():
            if key == "code" and value.get("maxclass") == "codebox" and isinstance(val, str):
                name = ctx.constant(f"{box_id}_code")
                constants[name] = _str_constant(val)
                out[key] = Code(name, val)
            else:
                out[key] = _hoist_code(ctx, val, box_id, constants)
        return out
    if isinstance(value, list):
        return [_hoist_code(ctx, val, box_id, constants) for val in value]
    return value


def _convert_raw(ctx: _Ctx, box: dict, target: str, reason: str) -> _Emit:
    constants: dict[str, str] = {}
    literal = _hoist_code(ctx, copy.deepcopy(box), box["id"], constants)
    head = f"    {target}.add_box({{\"box\": "
    body = _py_block(literal, 4)
    lines = [f"    # {TODO}: kept raw -- {reason}", head + body + "})"]
    return _Emit(code=lines, box_id=box["id"], raw_reason=reason, constants=constants,
                 cost=1000)


def _convert_box(ctx: _Ctx, box: dict, target: str, scope: str,
                 var_names: set[str]) -> _Emit:
    maxclass = box.get("maxclass")
    text = str(box.get("text", ""))
    head = text.split()[0] if text.split() else ""
    result: _Emit | str
    if maxclass == "newobj" and head == "gen~" and isinstance(box.get("patcher"), dict):
        result = _convert_embedded_gen(ctx, box, target, scope)
    elif (maxclass == "newobj" and head == "gen~" and len(text.split()) == 2
          and f"{text.split()[1]}.gendsp" in ctx.source.assets):
        result = _convert_external_gen(ctx, box, target, scope, f"{text.split()[1]}.gendsp")
        if isinstance(result, str):
            result = _convert_newobj(ctx, box, target, scope)
    elif maxclass == "newobj" and head in ("p", "patcher") and isinstance(box.get("patcher"),
                                                                         dict):
        result = _convert_subpatcher(ctx, box, target, scope, var_names)
    elif maxclass == "newobj":
        result = _convert_newobj(ctx, box, target, scope)
    elif maxclass == "message":
        result = _convert_message(ctx, box, target, scope)
    elif maxclass in ("jsui", "v8ui"):
        result = _convert_script_ui(ctx, box, target, scope)
    elif maxclass in _WIDGETS and scope == "device":
        result = _convert_widget(ctx, box, target, scope)
    else:
        result = f"no add_* helper for {maxclass!r}"
    if isinstance(result, str):
        return _convert_raw(ctx, box, target, result)
    return result


def _line_code(target: str, line: dict, ids: set[str]) -> str:
    try:
        (src, outlet), (dst, inlet) = line["source"], line["destination"]
    except (KeyError, TypeError, ValueError):
        return f"    # {TODO}: skipped a malformed patchline: {_py(line)}"
    if src not in ids or dst not in ids:
        return f"    # {TODO}: skipped a patchline to a missing box: {src} -> {dst}"
    extra = {key: val for key, val in line.items() if key not in ("source", "destination")}
    return _render_call(f"{target}.add_line", [src, outlet, dst, inlet], extra)


def _unset_code(target: str, unsets: dict[str, list[str]]) -> list[str]:
    """``_unset(target, [paths], ids...)`` calls, grouping boxes with the same paths."""
    groups: dict[tuple[str, ...], list[str]] = {}
    for box_id, paths in unsets.items():
        if paths:
            groups.setdefault(tuple(sorted(paths)), []).append(box_id)
    if not groups:
        return []
    code = ["", "    # The source leaves these attributes unset; drop the values add_* fills in."]
    for group, box_ids in groups.items():
        code.append(_render_call("_unset", [Code(target, None), list(group), *box_ids], {}))
    return code


@dataclass
class _Body:
    code: list[str]
    imports: set[tuple[str, str]] = field(default_factory=set)
    constants: dict[str, str] = field(default_factory=dict)
    files: dict[str, bytes] = field(default_factory=dict)
    consumed: set[str] = field(default_factory=set)
    helpers: set[str] = field(default_factory=set)
    raw: list[str] = field(default_factory=list)
    cost: int = 0


def _convert_scope(ctx: _Ctx, boxes: list[dict], lines: list[dict], target: str,
                   scope: str, var_names: set[str], known_ids: set[str] | None = None) -> _Body:
    """Statements for every box and patchline of one patcher (device or subpatcher).

    Boxes keep their source order (it is the z-order); a blank line separates
    UI from patching objects and sets off raw boxes and subpatchers.
    """
    body = _Body(code=[])
    unsets: dict[str, list[str]] = {}
    previous: str | None = None
    for box in boxes:
        emit = _convert_box(ctx, box, target, scope, var_names)
        if emit.raw_reason or "Subpatcher(" in emit.code[0]:
            kind = "block"
        else:
            kind = "ui" if box.get("presentation") == 1 else "object"
        if previous is not None and (kind != previous or kind == "block"):
            body.code.append("")
        previous = kind
        body.code.extend(emit.code)
        body.imports |= emit.imports
        body.constants.update(emit.constants)
        body.files.update(emit.files)
        body.consumed |= emit.consumed
        body.helpers |= emit.helpers
        body.cost += emit.cost
        if emit.raw_reason:
            body.raw.append(f"{box['id']} ({box.get('maxclass')}): {emit.raw_reason}")
        body.raw.extend(emit.raw_inside)
        if emit.unsets:
            unsets[box["id"]] = emit.unsets
    ids = {str(box["id"]) for box in boxes} | (known_ids or set())
    if lines:
        body.code.append("")
        body.code.extend(_line_code(target, line, ids) for line in lines)
    body.code.extend(_unset_code(target, unsets))
    if unsets:
        body.helpers.add("unset")
    return body


# --------------------------------------------------------------------------- #
# Whole devices
# --------------------------------------------------------------------------- #


@dataclass
class ImportedDevice:
    """The result of :func:`import_amxd`: the script and the files it reads."""

    source: SourceDevice
    script: str
    files: dict[str, bytes]
    class_name: str
    theme_name: str | None
    raw_boxes: list[str]
    missing: list[str]
    box_count: int
    line_count: int

    def write(self, script_path: str | Path) -> list[Path]:
        """Write the script and its support files; returns every path written."""
        script_path = Path(script_path)
        script_path.parent.mkdir(parents=True, exist_ok=True)
        script_path.write_text(self.script, encoding="utf-8")
        written = [script_path]
        for name, content in self.files.items():
            target = script_path.parent / name
            if not target.resolve().is_relative_to(script_path.parent.resolve()):
                raise ValueError(f"support file would land outside {script_path.parent}: {name}")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            written.append(target)
        return written


def _named_themes() -> dict[str, Any]:
    return {name: value for name, value in vars(theme).items()
            if isinstance(value, theme.Theme) and name.isupper()}


def _theme_candidates(boxes: list[dict]) -> dict[str, Any]:
    """Named themes whose colours appear on at least one UI box."""
    colours = set()
    for box in boxes:
        for val in box.values():
            if isinstance(val, list) and len(val) == 4 and all(
                    isinstance(v, (int, float)) for v in val):
                colours.add(json.dumps(val))
    found = {}
    for name, value in _named_themes().items():
        for attr in vars(value).values():
            if isinstance(attr, list) and json.dumps(attr) in colours:
                found[name] = value
                break
    return found


def _audio_io(source: SourceDevice, boxes: list[dict]) -> dict[str, str] | None:
    """Source IDs of a plugin~/plugout~ pair identical to the one AudioEffect adds."""
    io_boxes, _ = stereo_io()
    pinned: dict[str, str] = {}
    for entry in io_boxes:
        auto = unwrap_box(entry)
        for box in boxes:
            if str(box.get("id")) in pinned:
                continue
            candidate = dict(box, id=auto["id"])
            if _same(candidate, auto):
                pinned[str(box["id"])] = auto["id"]
                break
        else:
            return None
    return pinned


def _bank_code(patcher: dict) -> list[str]:
    banks = patcher.get("parameters", {}).get("parameterbanks", {})
    code: list[str] = []
    if not isinstance(banks, dict):
        return code
    for bank_key, bank in banks.items():
        try:
            index = int(bank_key)
        except ValueError:
            continue
        bank_name = bank.get("name") or None
        assigned = False
        for position, entry in enumerate(bank.get("parameters", [])):
            if isinstance(entry, dict):
                name = entry.get("name")
                position = entry.get("index", position)
            else:
                name = entry
            if not name or name == "-":
                continue
            kwargs: dict[str, Any] = {"bank": index, "position": position}
            if bank_name and not assigned:
                kwargs["bank_name"] = bank_name
            code.append(_render_call("device.assign_parameter_bank", [name], kwargs))
            assigned = True
        if bank_name and not assigned:
            code.append(_render_call("device.set_parameter_bank_name", [index, bank_name], {}))
    return code


_HELPERS = {
    "asset": '''\
def _asset(name: str) -> str:
    """A support file `m4l import` copied next to this script."""
    return (HERE / name).read_bytes().decode("utf-8")
''',
    "asset_bytes": '''\
def _asset_bytes(name: str) -> bytes:
    """A binary support file `m4l import` copied next to this script."""
    return (HERE / name).read_bytes()
''',
    "unset": '''\
def _unset(graph, keys: list[str], *box_ids: str) -> None:
    """Remove attributes (dotted paths) the source device leaves unset."""
    for entry in graph.boxes:
        box = entry["box"]
        if box["id"] not in box_ids:
            continue
        for key in keys:
            *parents, last = key.split(".")
            target = box
            for part in parents:
                target = target[part]
            target.pop(last, None)
''',
}


def _asset_code(source: SourceDevice, consumed: set[str]) -> tuple[list[str], dict[str, bytes],
                                                                   set[str], list[str]]:
    """Register the dependencies no high-level call registered itself."""
    code: list[str] = []
    files: dict[str, bytes] = {}
    helpers: set[str] = set()
    types = {dep.get("name"): dep.get("type", "TEXT")
             for dep in source.patcher.get("dependency_cache", []) if isinstance(dep, dict)}
    missing = []
    for name in _dependency_names(source.patcher):
        if name in consumed:
            continue
        if name not in source.assets:
            missing.append(name)
            code.append(f"    # {TODO}: {name!r} was neither inside the device nor next to it;")
            code.append("    # copy it next to this script and register it with add_support_file().")
            continue
        content = source.assets[name]
        files[name] = content
        try:
            content.decode("utf-8")
            loader = Code(f"_asset({_py(name)})", None)
            helpers.add("asset")
        except UnicodeDecodeError:
            loader = Code(f"_asset_bytes({_py(name)})", None)
            helpers.add("asset_bytes")
        asset_type = types.get(name) or "TEXT"
        kwargs: dict[str, Any] = {}
        if asset_type != "TEXT":
            kwargs["asset_type"] = asset_type
        if name.endswith(".js"):
            kwargs["category"] = "js"
            code.append(_render_call("device.register_asset", [name, loader], kwargs))
        else:
            if "asset_type" in kwargs:
                kwargs = {"file_type": kwargs["asset_type"]}
            code.append(_render_call("device.add_support_file", [name, loader], kwargs))
    return code, files, helpers, missing


def import_amxd(path: str | Path, *, script_name: str = "build.py") -> ImportedDevice:
    """Read ``path`` and write the source of a build script that rebuilds it."""
    source = read_device(path)
    patcher = source.patcher
    boxes = [unwrap_box(entry) for entry in patcher.get("boxes", [])]
    class_name = _CLASSES[source.device_type]

    pinned: dict[str, str] = {}
    keep_io = False
    if source.device_type == "audio_effect":
        found = _audio_io(source, boxes)
        if found is not None:
            pinned, keep_io = found, True
        else:
            # Its own pair: keep the IDs AudioEffect (and its lint) expect.
            for text, io_id in (("plugin~", "obj-plugin"), ("plugout~", "obj-plugout")):
                for box in boxes:
                    if box.get("maxclass") == "newobj" and box.get("text") == text:
                        pinned[str(box["id"])] = io_id
                        break
    mapping = _plan_ids(boxes, pinned)
    renamed_boxes, renamed_lines = _renamed(patcher, mapping)
    auto_ids = set(pinned.values()) if keep_io else set()
    own_boxes = [box for box in renamed_boxes if box["id"] not in auto_ids]

    # Pick the theme that lets the UI calls carry the fewest explicit arguments.
    ui_boxes = [box for box in own_boxes if box.get("maxclass") in _WIDGETS]
    best_name: str | None = None
    best_cost: int | None = None
    candidates: dict[str | None, Any] = {None: None}
    candidates.update(_theme_candidates(ui_boxes))
    for name, value in candidates.items():
        ctx = _Ctx(source=source, theme=value, theme_name=name)
        cost = sum(_convert_box(ctx, box, "device", "device", set()).cost for box in ui_boxes)
        if best_cost is None or cost < best_cost:
            best_name, best_cost = name, cost
    ctx = _Ctx(source=source, theme=candidates[best_name], theme_name=best_name)

    body = _convert_scope(ctx, own_boxes, renamed_lines, "device", "device", {"device"},
                          known_ids=auto_ids)
    asset_lines, asset_files, asset_helpers, missing = _asset_code(source, body.consumed)

    imports = {("m4l_builder", class_name), ("m4l_builder", "device_output_path")} | body.imports
    if best_name:
        module = "m4l_builder" if _exported(best_name) else "m4l_builder.theme"
        imports.add((module, best_name))
    helpers = body.helpers | asset_helpers

    ctor_kwargs: dict[str, Any] = {"width": source.width, "height": source.height}
    if best_name:
        ctor_kwargs["theme"] = Code(best_name, None)
    tall = (source.device_type in ("audio_effect", "instrument", "midi_effect")
            and isinstance(source.height, (int, float)) and source.height > DEVICE_H)
    if tall:
        ctor_kwargs["allow_tall"] = True
    build: list[str] = [_render_call(f"device = {class_name}", [Code("NAME", None)], ctor_kwargs)]
    if source.device_type == "audio_effect" and not keep_io:
        build.append("    # This device wires its own plugin~ / plugout~: drop the pair "
                     "AudioEffect adds.")
        build.append("    device.boxes.clear()")
    latency = patcher.get("latency", 0)
    if latency:
        build.append(f"    device.latency = {_py(latency)}")
    if patcher.get("is_mpe"):
        build.append("    device.is_mpe = True")
    if asset_lines:
        build += [""] + asset_lines
    build += [""] + body.code
    banks = _bank_code(patcher)
    if banks:
        build += ["", "    # Push parameter banks"] + banks
    build.append("    return device")

    script = _assemble(source, script_name, class_name, imports, body.constants, helpers, build,
                       len(body.raw), missing)
    files = {**asset_files, **body.files}
    return ImportedDevice(source=source, script=script, files=files, class_name=class_name,
                          theme_name=best_name, raw_boxes=body.raw, missing=missing,
                          box_count=len(boxes), line_count=len(renamed_lines))


def _exported(name: str) -> bool:
    import m4l_builder

    return hasattr(m4l_builder, name)


def _import_lines(imports: set[tuple[str, str]], helpers: set[str]) -> list[str]:
    def order(name: str) -> tuple[int, str]:
        kind = 0 if name.isupper() else 1 if name[:1].isupper() else 2
        return kind, name

    out = []
    if {"asset", "asset_bytes"} & helpers:
        out += ["from pathlib import Path", ""]
    modules: dict[str, list[str]] = {}
    for module, name in imports:
        modules.setdefault(module, []).append(name)
    for module in sorted(modules):
        names = sorted(modules[module], key=order)
        line = f"from {module} import {', '.join(names)}"
        if len(line) > WIDTH:
            line = f"from {module} import (\n" + "".join(f"    {n},\n" for n in names) + ")"
        out.append(line)
    return out


def _assemble(source: SourceDevice, script_name: str, class_name: str,
              imports: set[tuple[str, str]], constants: dict[str, str], helpers: set[str],
              build: list[str], raw_count: int, missing: list[str]) -> str:
    notes = []
    if raw_count:
        notes.append(f"{raw_count} box(es) have no matching m4l-builder call and are kept as raw "
                     f"add_box() dicts; search for {TODO}.")
    if missing:
        notes.append(f"Missing support files: {', '.join(missing)}.")
    note_text = "".join("\n" + textwrap.fill(note, 79) + "\n" for note in notes)
    out = [
        f'"""{source.name} -- imported from {source.path.name} by `m4l import`.',
        "",
        "Rebuilds an equivalent device with m4l-builder. Edit it like any build script:",
        "",
        f"    m4l build {script_name}     # write it to your Ableton User Library",
        f"    m4l watch {script_name}     # rebuild on every save",
        f"    m4l lint {script_name}      # check it without writing anything",
        note_text + '"""',
        "",
    ]
    out += _import_lines(imports, helpers)
    out += ["", f"NAME = {_py(source.name)}"]
    if {"asset", "asset_bytes"} & helpers:
        out.append("HERE = Path(__file__).resolve().parent")
    for name, literal in constants.items():
        out += ["", f"{name} = {literal}"]
    for helper in ("asset", "asset_bytes", "unset"):
        if helper in helpers:
            out += ["", ""] + _HELPERS[helper].rstrip("\n").split("\n")
    out += ["", "", f"def build_device() -> {class_name}:"]
    out += build
    out += [
        "",
        "",
        'if __name__ == "__main__":',
        f"    path = device_output_path(NAME, {_py(source.device_type)})",
        "    build_device().build(path)",
        '    print("wrote", path)',
    ]
    return "\n".join(out) + "\n"


# --------------------------------------------------------------------------- #
# Checking an import
# --------------------------------------------------------------------------- #


def rebuild_from_script(script_path: str | Path) -> Device:
    """Run a build script's ``build_device()`` and return the device."""
    namespace = runpy.run_path(str(script_path), run_name="__m4l_import__")
    factory = namespace.get("build_device")
    if not callable(factory):
        raise ValueError(f"{script_path}: no build_device() function")
    device = factory()
    if not isinstance(device, Device):
        raise ValueError(f"{script_path}: build_device() did not return a Device")
    return device


def _box_label(box: dict) -> str:
    what = box.get("text") or _valueof(box).get("parameter_longname") or box.get("varname")
    label = f"{box.get('maxclass')} {what!r}" if what else str(box.get("maxclass"))
    return f"{label} [{box.get('id')}]"


def _patcher_signature(patcher: dict) -> tuple[Counter, Counter, dict[str, str], dict]:
    boxes = [unwrap_box(entry) for entry in patcher.get("boxes", [])]
    sigs: dict[str, str] = {}
    labels: dict[str, str] = {}
    for box in boxes:
        body = {key: val for key, val in box.items() if key != "id"}
        if isinstance(body.get("patcher"), dict):
            body["patcher"] = _nested_signature(body["patcher"])
        sig = json.dumps(body, sort_keys=True)
        sigs[str(box.get("id"))] = sig
        labels.setdefault(sig, _box_label(box))
    line_sigs: Counter = Counter()
    line_labels: dict[str, str] = {}
    for entry in patcher.get("lines", []):
        line = entry.get("patchline", entry)
        try:
            (src, outlet), (dst, inlet) = line["source"], line["destination"]
        except (KeyError, TypeError, ValueError):
            continue
        extra = {key: val for key, val in line.items() if key not in ("source", "destination")}
        sig = json.dumps([sigs.get(src), outlet, sigs.get(dst), inlet, extra], sort_keys=True)
        line_sigs[sig] += 1
        line_labels.setdefault(sig, f"{src}:{outlet} -> {dst}:{inlet}")
    header = {key: val for key, val in patcher.items() if key not in ("boxes", "lines")}
    return Counter(sigs.values()), line_sigs, {**labels, **line_labels}, header


def _nested_signature(patcher: dict) -> dict:
    box_sigs, line_sigs, _labels, header = _patcher_signature(patcher)
    return {"header": header, "boxes": sorted(box_sigs.elements()),
            "lines": sorted(line_sigs.elements())}


def patcher_differences(source: dict, rebuilt: dict) -> list[str]:
    """How two device patchers differ, ignoring box IDs (empty = equivalent).

    Compares every box (all attributes, embedded patchers included), every
    patchline by the boxes it joins, the device size, latency, MPE flag,
    parameter banks and the dependency list. Patcher-level settings Max
    regenerates (timestamps, window rects, the parameter index) are ignored.
    """
    diffs: list[str] = []
    for key in ("devicewidth", "latency"):
        if not _same(source.get(key, 0), rebuilt.get(key, 0)):
            diffs.append(f"{key}: {source.get(key)!r} != {rebuilt.get(key)!r}")
    if not _same(source.get("openrect", [0, 0, 0, 0])[2:4], rebuilt.get("openrect",
                                                                       [0, 0, 0, 0])[2:4]):
        diffs.append(f"size: {source.get('openrect')} != {rebuilt.get('openrect')}")
    if bool(source.get("is_mpe")) != bool(rebuilt.get("is_mpe")):
        diffs.append("is_mpe differs")
    banks = [p.get("parameters", {}).get("parameterbanks", {}) for p in (source, rebuilt)]
    if not _same(*banks):
        diffs.append(f"parameter banks: {banks[0]} != {banks[1]}")
    deps = [sorted((d.get("name"), d.get("type")) for d in p.get("dependency_cache", [])
                   if isinstance(d, dict)) for p in (source, rebuilt)]
    if deps[0] != deps[1]:
        diffs.append(f"dependencies: {deps[0]} != {deps[1]}")
    src_boxes, src_lines, src_labels, _ = _patcher_signature(source)
    new_boxes, new_lines, new_labels, _ = _patcher_signature(rebuilt)
    for sig in (src_boxes - new_boxes).elements():
        diffs.append(f"box not rebuilt: {src_labels[sig]}")
    for sig in (new_boxes - src_boxes).elements():
        diffs.append(f"box not in source: {new_labels[sig]}")
    for sig in (src_lines - new_lines).elements():
        diffs.append(f"patchline not rebuilt: {src_labels[sig]}")
    for sig in (new_lines - src_lines).elements():
        diffs.append(f"patchline not in source: {new_labels[sig]}")
    return diffs


def check_import(source: SourceDevice, script_path: str | Path) -> list[str]:
    """Run the written script and list how its device differs from ``source``."""
    from .amxd import device_to_patcher

    device = rebuild_from_script(script_path)
    diffs = []
    if device.device_type != source.device_type:
        diffs.append(f"device type: {source.device_type} != {device.device_type}")
    diffs += patcher_differences(source.patcher, device_to_patcher(device)["patcher"])
    rebuilt_assets = {}
    for asset in device.assets():
        content = asset.content
        rebuilt_assets[asset.filename] = (content if isinstance(content, bytes)
                                          else content.encode(asset.encoding))
    for name, content in source.assets.items():
        if name in rebuilt_assets and rebuilt_assets[name] != content:
            diffs.append(f"support file differs: {name}")
    return diffs
