"""Render a device's presentation view to SVG (stdlib only).

``render_svg`` draws what a device looks like in Live's device view, built from
the presentation boxes of its patcher: panels and labels in their theme
colours, and recognisable approximations of the native controls (``live.dial``,
``live.slider``, ``live.toggle``, ``live.text``, ``live.menu``, ``live.tab``,
``live.numbox``, meters and scopes) showing their initial values. jsui / v8ui
engines draw their pictures at runtime, so they appear as labelled
placeholders; any other object is drawn as a labelled outline.

It is an approximation for docs, reviews and diffs, not a pixel match with
Live::

    from m4l_builder.preview import render_svg
    svg = render_svg(device)              # a Device, a patcher dict or a .amxd path
    Path("my_gain.svg").write_text(svg)

From the shell: ``m4l preview build.py --out previews/``.
"""

from __future__ import annotations

import math
import os
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape, quoteattr

__all__ = ["render_svg", "format_value"]

FONT = "Arial, Helvetica, sans-serif"
TITLE_H = 18.0

# Fallbacks for boxes that carry no colour of their own (roughly Live's defaults).
DEFAULTS = {
    "device_bg": (0.18, 0.18, 0.18, 1.0),
    "text": (0.86, 0.86, 0.86, 1.0),
    "dim": (0.55, 0.55, 0.55, 1.0),
    "track": (0.33, 0.33, 0.33, 1.0),
    "accent": (0.95, 0.62, 0.22, 1.0),
    "control_bg": (0.24, 0.24, 0.24, 1.0),
    "outline": (0.42, 0.42, 0.42, 1.0),
}


# --------------------------------------------------------------------------- #
# Small SVG helpers
# --------------------------------------------------------------------------- #

def _n(value: float) -> str:
    """Compact, deterministic number formatting for SVG attributes."""
    text = f"{float(value):.2f}".rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


def _color(value: Any, fallback: str = "text") -> tuple[float, float, float, float]:
    if isinstance(value, dict):  # bgfillcolor-style {"color": [...]} / gradients
        value = value.get("color") or value.get("color1")
    if isinstance(value, (list, tuple)) and len(value) >= 3:
        rgba = [float(c) for c in value[:4]] + [1.0] * (4 - len(value[:4]))
        return (rgba[0], rgba[1], rgba[2], rgba[3])
    return DEFAULTS[fallback]


def _paint(attr: str, rgba: tuple[float, float, float, float]) -> str:
    """``fill="#rrggbb"`` plus an opacity attribute when alpha < 1."""
    r, g, b, a = (min(1.0, max(0.0, c)) for c in rgba)
    hexcode = "#{:02x}{:02x}{:02x}".format(*(round(c * 255) for c in (r, g, b)))
    out = f'{attr}="{hexcode}"'
    if a < 1.0:
        out += f' {attr}-opacity="{_n(a)}"'
    return out


def _rect(x, y, w, h, *, fill=None, stroke=None, rx=0.0, extra="") -> str:
    parts = [f'<rect x="{_n(x)}" y="{_n(y)}" width="{_n(max(w, 0))}" '
             f'height="{_n(max(h, 0))}"']
    if rx:
        parts.append(f' rx="{_n(rx)}"')
    parts.append(" " + (_paint("fill", fill) if fill else 'fill="none"'))
    if stroke:
        parts.append(" " + _paint("stroke", stroke))
    if extra:
        parts.append(" " + extra)
    parts.append("/>")
    return "".join(parts)


def _text(x, y, text, *, size=9.0, color=None, anchor="middle", weight=None) -> str:
    attrs = f'x="{_n(x)}" y="{_n(y)}" font-size="{_n(size)}"'
    if anchor != "start":
        attrs += f' text-anchor="{anchor}"'
    if weight:
        attrs += f' font-weight="{weight}"'
    return f'<text {attrs} {_paint("fill", color or DEFAULTS["text"])}>{escape(str(text))}</text>'


def _fit(text: str, width: float, size: float) -> str:
    """Trim ``text`` to roughly fit ``width`` px at ``size`` (no font metrics)."""
    max_chars = max(1, int(width / (size * 0.56)))
    return text if len(text) <= max_chars else text[: max(1, max_chars - 1)] + "…"


def _baseline(top: float, height: float, size: float) -> float:
    """Baseline that vertically centres one line of ``size`` text in a band."""
    return top + height / 2 + size * 0.35


# --------------------------------------------------------------------------- #
# Parameter values
# --------------------------------------------------------------------------- #

_NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def format_value(value: float, unitstyle: int | None, units: str | None = None) -> str:
    """Format a parameter value the way Live labels it for ``unitstyle``."""
    style = 1 if unitstyle is None else int(unitstyle)
    v = float(value)
    if style == 0:
        return str(int(round(v)))
    if style == 2:
        return f"{v / 1000:.2f} s" if abs(v) >= 1000 else f"{v:.0f} ms"
    if style == 3:
        return f"{v / 1000:.2f} kHz" if abs(v) >= 1000 else f"{v:.0f} Hz"
    if style == 4:
        return "-inf dB" if v <= -70 else f"{v:.1f} dB"
    if style == 5:
        return f"{v:.0f} %"
    if style == 6:
        return "C" if abs(v) < 0.5 else f"{abs(v):.0f}{'L' if v < 0 else 'R'}"
    if style == 7:
        return f"{v:+.0f} st"
    if style == 8:
        note = int(round(v))
        return f"{_NOTE_NAMES[note % 12]}{note // 12 - 2}"
    if style == 9 and units:
        try:
            return units % v
        except (TypeError, ValueError):
            return f"{v:.2f}"
    return f"{v:.2f}"


@dataclass
class _Param:
    name: str
    value: float
    minimum: float
    maximum: float
    exponent: float
    unitstyle: int | None
    units: str | None
    enum: list[str]

    @property
    def fraction(self) -> float:
        span = self.maximum - self.minimum
        if span == 0:
            return 0.0
        linear = min(1.0, max(0.0, (self.value - self.minimum) / span))
        return linear ** (1.0 / self.exponent) if self.exponent > 0 else linear

    @property
    def label(self) -> str:
        if self.enum:
            index = int(round(self.value))
            return self.enum[index] if 0 <= index < len(self.enum) else ""
        return format_value(self.value, self.unitstyle, self.units)


def _param(box: dict) -> _Param:
    valueof = (box.get("saved_attribute_attributes") or {}).get("valueof") or {}
    enum = [str(item) for item in valueof.get("parameter_enum") or []]
    lo = float(valueof.get("parameter_mmin", 0.0))
    hi = valueof.get("parameter_mmax")
    hi = float(hi) if hi is not None else (len(enum) - 1 if enum else 127.0)
    initial = valueof.get("parameter_initial")
    if isinstance(initial, list):
        initial = initial[0] if initial else None
    value = float(initial) if isinstance(initial, (int, float)) else lo
    name = (valueof.get("parameter_shortname") or valueof.get("parameter_longname")
            or box.get("varname") or "")
    return _Param(str(name), value, lo, hi, float(valueof.get("parameter_exponent", 1.0) or 1.0),
                  valueof.get("parameter_unitstyle"), valueof.get("parameter_units"), enum)


# --------------------------------------------------------------------------- #
# Control renderers: (box, x, y, w, h) -> SVG fragments
# --------------------------------------------------------------------------- #

Renderer = Callable[[dict, float, float, float, float], list[str]]


def _font_size(box: dict, default: float = 9.0) -> float:
    try:
        return float(box.get("fontsize", default))
    except (TypeError, ValueError):
        return default


def _panel(box, x, y, w, h):
    fill = _color(box.get("bgfillcolor") if box.get("mode") == 1 and box.get("bgfillcolor")
                  else box.get("bgcolor"), "device_bg")
    stroke = _color(box.get("bordercolor"), "outline") if box.get("border") else None
    extra = f'stroke-width="{_n(box["border"])}"' if stroke else ""
    return [_rect(x, y, w, h, fill=fill, stroke=stroke, rx=float(box.get("rounded") or 0),
                  extra=extra)]


def _arc_point(cx, cy, r, degrees):
    rad = math.radians(degrees)
    return cx + r * math.cos(rad), cy + r * math.sin(rad)


def _arc(cx, cy, r, start, end, color, width):
    if end - start < 0.5:
        return ""
    x1, y1 = _arc_point(cx, cy, r, start)
    x2, y2 = _arc_point(cx, cy, r, end)
    large = 1 if end - start > 180 else 0
    return (f'<path d="M{_n(x1)} {_n(y1)} A{_n(r)} {_n(r)} 0 {large} 1 {_n(x2)} {_n(y2)}" '
            f'fill="none" {_paint("stroke", color)} stroke-width="{_n(width)}" '
            f'stroke-linecap="round"/>')


def _dial(box, x, y, w, h):
    param = _param(box)
    size = _font_size(box, 9.0)
    show_name = box.get("showname", 1) and h >= 30
    show_number = box.get("shownumber", 1) and h >= 30
    tiny = box.get("appearance") == 1
    out: list[str] = []
    text_color = _color(box.get("textcolor"), "text")
    if tiny:  # small dial with the value beside it
        d = min(h, w * 0.45)
        cx, cy, top = x + d / 2, y + h / 2, y
        label_x = x + d + 3
        if show_number or not show_name:
            out.append(_text(label_x, _baseline(top, h, size), _fit(param.label, w - d - 3, size),
                             size=size, color=text_color, anchor="start"))
    else:
        name_h = size + 3 if show_name else 0.0
        number_h = size + 3 if show_number else 0.0
        d = max(6.0, min(w - 4, h - name_h - number_h - 2))
        cx, cy = x + w / 2, y + name_h + (h - name_h - number_h) / 2
        if show_name:
            out.append(_text(cx, y + size, _fit(param.name, w, size), size=size, color=text_color))
        if show_number:
            out.append(_text(cx, y + h - 2, _fit(param.label, w, size), size=size,
                             color=text_color))
    r = d / 2 - 1.5
    stroke = max(1.5, d * 0.09)
    start, end = 135.0, 405.0
    value_angle = start + (end - start) * param.fraction
    out.append(_arc(cx, cy, r, start, end, _color(box.get("dialcolor"), "track"), stroke))
    out.append(_arc(cx, cy, r, start, value_angle,
                    _color(box.get("activedialcolor"), "accent"), stroke))
    nx, ny = _arc_point(cx, cy, r, value_angle)
    ix, iy = _arc_point(cx, cy, r * 0.25, value_angle)
    needle = _color(box.get("activeneedlecolor") or box.get("needlecolor"), "text")
    out.append(f'<line x1="{_n(ix)}" y1="{_n(iy)}" x2="{_n(nx)}" y2="{_n(ny)}" '
               f'{_paint("stroke", needle)} stroke-width="{_n(max(1.0, stroke * 0.6))}" '
               f'stroke-linecap="round"/>')
    return [part for part in out if part]


def _slider(box, x, y, w, h):
    param = _param(box)
    size = _font_size(box, 9.0)
    text_color = _color(box.get("textcolor"), "text")
    fill = _color(box.get("slidercolor"), "accent")
    track = _color(box.get("trackcolor"), "track")
    out: list[str] = []
    horizontal = box.get("orientation") == 1 or (w > h * 2 and "orientation" not in box)
    if horizontal:
        bar_y, bar_h = y + h / 2 - 2, 4.0
        out.append(_rect(x, bar_y, w, bar_h, fill=track, rx=1))
        out.append(_rect(x, bar_y, w * param.fraction, bar_h, fill=fill, rx=1))
        return out
    show_text = h >= 40
    name_h = size + 3 if show_text and box.get("showname", 1) else 0.0
    number_h = size + 3 if show_text and box.get("shownumber", 1) else 0.0
    if name_h:
        out.append(_text(x + w / 2, y + size, _fit(param.name, w + 10, size), size=size,
                         color=text_color))
    if number_h:
        out.append(_text(x + w / 2, y + h - 2, _fit(param.label, w + 10, size), size=size,
                         color=text_color))
    top, bottom = y + name_h + 1, y + h - number_h - 1
    bar_w = min(6.0, w * 0.35)
    bx = x + (w - bar_w) / 2
    out.append(_rect(bx, top, bar_w, bottom - top, fill=track, rx=1))
    level = (bottom - top) * param.fraction
    out.append(_rect(bx, bottom - level, bar_w, level, fill=fill, rx=1))
    out.append(_rect(x + w * 0.15, bottom - level - 1.5, w * 0.7, 3, fill=text_color, rx=1))
    return out


def _is_on(box) -> bool:
    return _param(box).value >= 0.5


def _toggle(box, x, y, w, h):
    on = _is_on(box)
    fill = _color(box.get("activebgoncolor") or box.get("bgoncolor"), "accent") if on \
        else _color(box.get("bgcolor"), "control_bg")
    return [_rect(x + 0.5, y + 0.5, w - 1, h - 1, fill=fill,
                  stroke=_color(box.get("bordercolor"), "outline"), rx=2)]


def _live_text(box, x, y, w, h):
    on = box.get("mode", 1) == 1 and _is_on(box)
    if on:
        fill = _color(box.get("activebgoncolor") or box.get("bgoncolor"), "accent")
        color = _color(box.get("activetextoncolor") or box.get("textoncolor"), "text")
        label = box.get("texton", "")
    else:
        fill = _color(box.get("activebgcolor") or box.get("bgcolor"), "control_bg")
        color = _color(box.get("activetextcolor") or box.get("textcolor"), "text")
        label = box.get("text", "")
    size = _font_size(box, 9.5)
    return [
        _rect(x + 0.5, y + 0.5, w - 1, h - 1, fill=fill,
              stroke=_color(box.get("bordercolor"), "outline"), rx=2),
        _text(x + w / 2, _baseline(y, h, size), _fit(str(label), w - 4, size), size=size,
              color=color),
    ]


def _menu(box, x, y, w, h):
    param = _param(box)
    size = _font_size(box, 9.5)
    color = _color(box.get("textcolor"), "text")
    tri = min(6.0, h * 0.35)
    tx, ty = x + w - tri - 4, y + h / 2 - tri / 4
    return [
        _rect(x + 0.5, y + 0.5, w - 1, h - 1,
              fill=_color(box.get("activebgcolor") or box.get("bgcolor"), "control_bg"), rx=2),
        _text(x + 4, _baseline(y, h, size), _fit(param.label, w - tri - 10, size), size=size,
              color=color, anchor="start"),
        f'<path d="M{_n(tx)} {_n(ty)} h{_n(tri)} l{_n(-tri / 2)} {_n(tri / 2)} z" '
        f'{_paint("fill", color)}/>',
    ]


def _tab(box, x, y, w, h):
    param = _param(box)
    labels = param.enum or [str(i) for i in range(int(box.get("tabs", 2)))]
    if not labels:
        return []
    size = _font_size(box, 9.0)
    selected = int(round(param.value))
    vertical = h > w * 1.5 and len(labels) > 1
    count = len(labels)
    out: list[str] = []
    for index, label in enumerate(labels):
        if vertical:
            cell_h = (h - (count - 1)) / count
            cx, cy, cw, ch = x, y + index * (cell_h + 1), w, cell_h
        else:
            cell_w = (w - (count - 1)) / count
            cx, cy, cw, ch = x + index * (cell_w + 1), y, cell_w, h
        on = index == selected
        fill = (_color(box.get("activebgoncolor") or box.get("bgoncolor"), "accent") if on
                else _color(box.get("activebgcolor") or box.get("bgcolor"), "control_bg"))
        color = (_color(box.get("textoncolor"), "text") if on
                 else _color(box.get("textcolor"), "dim"))
        out.append(_rect(cx, cy, cw, ch, fill=fill, rx=1.5))
        out.append(_text(cx + cw / 2, _baseline(cy, ch, size), _fit(label, cw - 2, size),
                         size=size, color=color))
    return out


def _numbox(box, x, y, w, h):
    param = _param(box)
    size = _font_size(box, 9.5)
    return [
        _rect(x + 0.5, y + 0.5, w - 1, h - 1,
              fill=_color(box.get("activebgcolor") or box.get("bgcolor"), "control_bg"),
              stroke=_color(box.get("bordercolor"), "outline"), rx=2),
        _text(x + w / 2, _baseline(y, h, size), _fit(param.label, w - 4, size), size=size,
              color=_color(box.get("textcolor"), "text")),
    ]


def _comment(box, x, y, w, h):
    size = _font_size(box, 10.0)
    justify = int(box.get("textjustification", box.get("justification", 0)) or 0)
    anchor, tx = {1: ("middle", x + w / 2), 2: ("end", x + w)}.get(justify, ("start", x))
    color = _color(box.get("textcolor"), "text")
    lines = str(box.get("text", "")).split("\n")
    return [_text(tx, y + size * (1.05 + 1.2 * i), line, size=size, color=color, anchor=anchor)
            for i, line in enumerate(lines) if line]


def _meter(box, x, y, w, h):
    track = _color(box.get("slidercolor") or box.get("bgcolor"), "control_bg")
    cold = _color(box.get("inactivecoldcolor") or box.get("coldcolor"), "dim")
    out = [_rect(x, y, w, h, fill=track, rx=1)]
    horizontal = box.get("orientation") == 1 or w > h
    ticks = 8
    for i in range(1, ticks):
        if horizontal:
            tx = x + w * i / ticks
            out.append(f'<line x1="{_n(tx)}" y1="{_n(y + 1)}" x2="{_n(tx)}" y2="{_n(y + h - 1)}" '
                       f'{_paint("stroke", cold)} stroke-opacity="0.35" stroke-width="0.5"/>')
        else:
            ty = y + h * i / ticks
            out.append(f'<line x1="{_n(x + 1)}" y1="{_n(ty)}" x2="{_n(x + w - 1)}" y2="{_n(ty)}" '
                       f'{_paint("stroke", cold)} stroke-opacity="0.35" stroke-width="0.5"/>')
    return out


def _scope(box, x, y, w, h):
    grid = _color(box.get("gridcolor"), "dim")
    line = _color(box.get("linecolor"), "accent")
    mid = y + h / 2
    return [
        _rect(x, y, w, h, fill=_color(box.get("bgcolor"), "control_bg"), rx=1),
        f'<line x1="{_n(x)}" y1="{_n(mid)}" x2="{_n(x + w)}" y2="{_n(mid)}" '
        f'{_paint("stroke", grid)} stroke-width="0.5"/>',
        f'<line x1="{_n(x + 2)}" y1="{_n(mid)}" x2="{_n(x + w - 2)}" y2="{_n(mid)}" '
        f'{_paint("stroke", line)} stroke-width="1.2"/>',
    ]


def _live_line(box, x, y, w, h):
    color = _color(box.get("linecolor"), "outline")
    if w >= h:
        x1, y1, x2, y2 = x, y + h / 2, x + w, y + h / 2
    else:
        x1, y1, x2, y2 = x + w / 2, y, x + w / 2, y + h
    return [f'<line x1="{_n(x1)}" y1="{_n(y1)}" x2="{_n(x2)}" y2="{_n(y2)}" '
            f'{_paint("stroke", color)} stroke-width="1"/>']


def _button(box, x, y, w, h):
    r = min(w, h) / 2 - 1
    return [f'<circle cx="{_n(x + w / 2)}" cy="{_n(y + h / 2)}" r="{_n(max(r, 1))}" '
            f'{_paint("fill", _color(box.get("bgcolor"), "control_bg"))} '
            f'{_paint("stroke", _color(box.get("bordercolor"), "outline"))}/>']


def _placeholder(label: str, detail: str = "", *, dashed: bool = True) -> Renderer:
    def render(box, x, y, w, h):
        out = [_rect(x + 0.5, y + 0.5, w - 1, h - 1, fill=(1.0, 1.0, 1.0, 0.04),
                     stroke=DEFAULTS["dim"],
                     extra='stroke-dasharray="3 2"' if dashed else "")]
        size = 8.0 if h < 28 else 9.0
        name = label or str(box.get("maxclass", ""))
        sub = detail and box.get(detail)
        if h >= size * 2.6 and sub:
            out.append(_text(x + w / 2, y + h / 2 - 1, _fit(name, w - 4, size), size=size,
                             color=DEFAULTS["dim"]))
            out.append(_text(x + w / 2, y + h / 2 + size, _fit(str(sub), w - 4, size - 1),
                             size=size - 1, color=DEFAULTS["dim"]))
        elif h >= size + 2 and w >= size * 2:
            out.append(_text(x + w / 2, _baseline(y, h, size), _fit(name, w - 4, size),
                             size=size, color=DEFAULTS["dim"]))
        return out
    return render


RENDERERS: dict[str, Renderer] = {
    "panel": _panel,
    "live.dial": _dial,
    "live.slider": _slider,
    "live.gain~": _slider,
    "live.toggle": _toggle,
    "live.text": _live_text,
    "live.menu": _menu,
    "umenu": _menu,
    "live.tab": _tab,
    "live.numbox": _numbox,
    "live.comment": _comment,
    "comment": _comment,
    "live.meter~": _meter,
    "meter~": _meter,
    "live.scope~": _scope,
    "live.line": _live_line,
    "live.button": _button,
    "jsui": _placeholder("jsui", "filename"),
    "v8ui": _placeholder("v8ui", "filename"),
    "fpic": _placeholder("image", "pic"),
    "bpatcher": _placeholder("bpatcher", "name"),
}


# --------------------------------------------------------------------------- #
# Device -> SVG
# --------------------------------------------------------------------------- #

@dataclass
class _View:
    name: str
    width: float
    height: float
    boxes: list


def _view(source: Any) -> _View:
    from .device import Device

    if isinstance(source, Device):
        return _View(source.name, float(source.width), float(source.height), list(source.boxes))
    if isinstance(source, (str, os.PathLike)):
        from .amxd import device_from_amxd

        device = device_from_amxd(os.fspath(source))
        return _View(Path(source).stem, float(device.width), float(device.height),
                     list(device.boxes))
    if isinstance(source, dict):
        patcher = source.get("patcher", source)
        rect = patcher.get("openrect") or [0, 0, 400, 169]
        width = patcher.get("devicewidth") or rect[2]
        return _View(str(patcher.get("description") or "Device"), float(width),
                     float(rect[3]), list(patcher.get("boxes", [])))
    raise TypeError(f"render_svg: expected a Device, a patcher dict or a .amxd path, "
                    f"got {type(source).__name__}")


def _presentation_boxes(boxes: Iterable) -> list[dict]:
    """Presentation boxes in drawing order: background boxes first, then the
    rest, each group in patcher order (how Max layers them)."""
    shown = []
    for entry in boxes:
        box = entry.get("box", entry) if isinstance(entry, dict) else None
        if not isinstance(box, dict) or not box.get("presentation") or box.get("hidden"):
            continue
        rect = box.get("presentation_rect")
        if not isinstance(rect, (list, tuple)) or len(rect) < 4:
            continue
        shown.append(box)
    return ([b for b in shown if b.get("background")]
            + [b for b in shown if not b.get("background")])


def render_svg(source: Any, *, scale: float = 1.0, frame: bool = True,
               title: str | None = None) -> str:
    """Render a device's presentation view as an SVG document string.

    ``source`` is a :class:`~m4l_builder.Device`, a patcher dict or the path of
    a ``.amxd`` file. ``scale`` multiplies the displayed size (the drawing is
    vector, so 2 gives a crisp image at twice the size). ``frame`` adds a title
    strip with the device name, like Live's device header; ``title`` overrides
    the name shown there.
    """
    view = _view(source)
    width, height = view.width, view.height
    top = TITLE_H if frame else 0.0
    total_h = height + top
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{_n(width * scale)}" '
        f'height="{_n(total_h * scale)}" viewBox="0 0 {_n(width)} {_n(total_h)}" '
        f'font-family={quoteattr(FONT)}>',
        f"<title>{escape(title or view.name)}</title>",
        # In the coordinates of the translated group that uses it.
        f'<clipPath id="device"><rect width="{_n(width)}" height="{_n(height)}"/></clipPath>',
    ]
    if frame:
        out.append(_rect(0, 0, width, top, fill=(0.27, 0.27, 0.27, 1.0)))
        out.append(f'<circle cx="9" cy="{_n(top / 2)}" r="3.5" '
                   f'{_paint("fill", DEFAULTS["accent"])}/>')
        out.append(_text(18, _baseline(0, top, 9.5), _fit(title or view.name, width - 24, 9.5),
                         size=9.5, color=(0.9, 0.9, 0.9, 1.0), anchor="start", weight="bold"))
    out.append(f'<g clip-path="url(#device)" transform="translate(0 {_n(top)})">')
    out.append(_rect(0, 0, width, height, fill=DEFAULTS["device_bg"]))
    for box in _presentation_boxes(view.boxes):
        x, y, w, h = (float(v) for v in box["presentation_rect"][:4])
        if w <= 0 or h <= 0 or x >= width or y >= height or x + w <= 0 or y + h <= 0:
            continue
        maxclass = str(box.get("maxclass", ""))
        renderer = RENDERERS.get(maxclass) or _placeholder(maxclass, dashed=False)
        fragments = renderer(box, x, y, w, h)
        if fragments:
            out.append(f'<g data-id={quoteattr(str(box.get("id", "")))} '
                       f'data-maxclass={quoteattr(maxclass)}>')
            out.extend(fragments)
            out.append("</g>")
    out.append("</g>")
    out.append(_rect(0.5, 0.5, width - 1, total_h - 1, stroke=(0.08, 0.08, 0.08, 1.0)))
    out.append("</svg>")
    return "\n".join(out) + "\n"
