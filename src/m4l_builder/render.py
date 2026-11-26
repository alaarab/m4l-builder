"""Offline audio render of a device's audio path: WAV in, WAV out, no Live.

A gen~ device that fails to compile in Live does not error: it passes the audio
through untouched, so a broken effect looks like a working one until someone
listens closely. :func:`render` runs a built device's audio path in pure Python
so a test (or ``m4l render``) can hear and measure what the DSP does, and the
checks below turn "is it actually processing?" into an assertion.

What it runs, traced backwards from ``plugout~``:

* ``plugin~`` (the input signal) and ``plugout~`` (the rendered output).
* ``gen~`` boxes, embedded or loaded from a ``.gendsp`` support file, whose
  gen patcher is one codebox wired to ``in N`` / ``out N`` (what
  :func:`~m4l_builder.gen_patcher.build_gendsp` writes), run by
  :mod:`m4l_builder.gen_sim`. Direct ``in`` to ``out`` wires pass through.
* MSP arithmetic between them: ``*~ +~ -~ /~ !-~ !/~`` with an argument, a
  signal or a control value on the right inlet.
* Control chains feeding those inlets, evaluated once with the parameter
  values you pass (or each parameter's initial value): Live parameter boxes
  (``live.dial``, ``live.numbox``, ``live.slider``, ``live.toggle``,
  ``live.tab``, ``live.menu``, ``live.text``), ``pack``/``pak``,
  ``prepend``/``append``, ``t f``/``trigger f``/``f``/``float``, ``dbtoa``,
  ``atodb``, ``+ - * / !- !/`` with an argument, ``scale`` (linear, four
  arguments), ``loadmess``, and ``line~``/``sig~`` to turn the result into a
  signal. A ``prepend NAME`` reaching a ``gen~`` sets that gen ``Param``.

Anything else on the path raises :class:`RenderError` naming the box, so an
unsupported device is never reported as passing. Two things are approximate
and are listed in :attr:`Render.notes` when they apply: ``line~`` is held at
its target from the first sample (the smoothing ramp a parameter change
starts in Live is not rendered), and any gen construct the simulator marks
approximate (``noise()``, cubic delay reads; see :mod:`m4l_builder.gen_sim`).

Stdlib only: WAV files go through :mod:`wave` (PCM) or a small RIFF reader for
32/64-bit float input, and the band summary uses a plain radix-2 FFT.
"""

from __future__ import annotations

import cmath
import hashlib
import json
import math
import os
import random
import re
import struct
import sys
import wave
from array import array
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .gen_sim import GenKernel, UnsupportedKernel
from .patcher_walk import iter_boxes, iter_patchlines

__all__ = [
    "RenderError",
    "Render",
    "Check",
    "render",
    "generate_signal",
    "read_wav",
    "write_wav",
    "summarize",
    "check_not_dry",
    "check_identity",
    "check_silent",
    "check_finite",
    "audit",
    "SIGNAL_KINDS",
]

Channels = list[list[float]]


class RenderError(ValueError):
    """The device's audio path contains something the renderer cannot run."""


# --------------------------------------------------------------------------- #
# Test signals and WAV files
# --------------------------------------------------------------------------- #

SIGNAL_KINDS = ("sine", "noise", "impulse", "silence")


def generate_signal(kind: str = "noise", *, seconds: float = 1.0,
                    samplerate: float = 48000.0, channels: int = 2,
                    level_db: float = -6.0, freq: float = 440.0,
                    seed: int = 0) -> Channels:
    """A deterministic test signal, ``channels`` lists of floats.

    ``level_db`` is the peak level in dBFS. ``sine`` puts each channel a
    quarter cycle after the previous one, and ``noise`` (uniform white) is
    independent per channel, so both carry stereo (side) content a width or
    panning effect can act on. ``impulse`` is one sample at full ``level_db``
    on every channel at time zero; ``silence`` is all zeros.
    """
    if kind not in SIGNAL_KINDS:
        raise ValueError(f"unknown signal {kind!r}; choose one of {', '.join(SIGNAL_KINDS)}")
    n = max(1, int(round(seconds * samplerate)))
    amp = 10.0 ** (level_db / 20.0)
    out: Channels = []
    for ch in range(channels):
        if kind == "sine":
            step = 2.0 * math.pi * freq / samplerate
            phase = ch * math.pi / 2.0
            out.append([amp * math.sin(phase + step * i) for i in range(n)])
        elif kind == "noise":
            rng = random.Random(seed * 1000 + ch)
            out.append([amp * rng.uniform(-1.0, 1.0) for _ in range(n)])
        elif kind == "impulse":
            out.append([amp] + [0.0] * (n - 1))
        else:
            out.append([0.0] * n)
    return out


_FLOAT_GUID_TAIL = b"\x00\x00\x00\x00\x10\x00\x80\x00\x00\xaa\x00\x38\x9b\x71"


def _read_float_wav(path: Path) -> tuple[Channels, int]:
    """Read an IEEE-float WAV (format 3, or extensible with a float subformat)."""
    data = path.read_bytes()
    if data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise ValueError(f"{path}: not a WAV file")
    pos, fmt, frames = 12, None, None
    while pos + 8 <= len(data):
        tag, size = data[pos:pos + 4], struct.unpack_from("<I", data, pos + 4)[0]
        body = data[pos + 8:pos + 8 + size]
        if tag == b"fmt ":
            fmt = body
        elif tag == b"data":
            frames = body
        pos += 8 + size + (size & 1)
    if fmt is None or frames is None:
        raise ValueError(f"{path}: WAV has no fmt or data chunk")
    tag_id, nch, rate = struct.unpack_from("<HHI", fmt, 0)
    bits = struct.unpack_from("<H", fmt, 14)[0]
    if tag_id == 0xFFFE and len(fmt) >= 40 and fmt[26:40] == _FLOAT_GUID_TAIL:
        tag_id = struct.unpack_from("<H", fmt, 24)[0]
    if tag_id != 3 or bits not in (32, 64):
        raise ValueError(f"{path}: unsupported WAV encoding (format {tag_id}, {bits}-bit); "
                         f"use PCM or 32/64-bit float")
    samples = array("f" if bits == 32 else "d")
    samples.frombytes(frames[:len(frames) - len(frames) % samples.itemsize])
    if sys.byteorder == "big":
        samples.byteswap()
    return [list(samples[c::nch]) for c in range(nch)], rate


def read_wav(path: str | os.PathLike) -> tuple[Channels, int]:
    """Read a WAV file into ``(channels, samplerate)`` with samples in [-1, 1].

    PCM 8/16/24/32-bit and 32/64-bit float are supported.
    """
    path = Path(path)
    try:
        handle = wave.open(str(path), "rb")
    except wave.Error:
        # wave reads PCM only; float (plain or extensible) goes through our reader,
        # which raises a clear error for anything else.
        return _read_float_wav(path)
    with handle:
        nch, width = handle.getnchannels(), handle.getsampwidth()
        rate, raw = handle.getframerate(), handle.readframes(handle.getnframes())
    if width == 1:
        values = [(b - 128) / 128.0 for b in raw]
    elif width == 3:
        values = [int.from_bytes(raw[i:i + 3], "little", signed=True) / 8388608.0
                  for i in range(0, len(raw) - 2, 3)]
    elif width in (2, 4):
        ints = array("h" if width == 2 else "i")
        ints.frombytes(raw)
        if sys.byteorder == "big":
            ints.byteswap()
        scale = 32768.0 if width == 2 else 2147483648.0
        values = [v / scale for v in ints]
    else:
        raise ValueError(f"{path}: unsupported {8 * width}-bit PCM")
    return [values[c::nch] for c in range(nch)], rate


def write_wav(path: str | os.PathLike, channels: Sequence[Sequence[float]],
              samplerate: float, *, bits: int = 24) -> int:
    """Write ``channels`` as PCM (16 or 24-bit). Returns how many samples had to
    be clipped to full scale (NaN and infinity count, and are written as 0 and
    full scale)."""
    if bits not in (16, 24):
        raise ValueError("bits must be 16 or 24")
    full = float(2 ** (bits - 1))
    top, width = full - 1, bits // 8
    clipped = 0
    frames = bytearray()
    length = max((len(ch) for ch in channels), default=0)
    for i in range(length):
        for ch in channels:
            v = ch[i] if i < len(ch) else 0.0
            if math.isnan(v):
                v, clipped = 0.0, clipped + 1
            elif math.isinf(v):
                v = 2.0 if v > 0 else -2.0   # counted below as clipped
            q = round(v * full)
            if q > top or q < -full:
                clipped += 1
                q = int(top) if q > top else int(-full)
            frames += int(q).to_bytes(width, "little", signed=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(len(channels))
        handle.setsampwidth(width)
        handle.setframerate(int(round(samplerate)))
        handle.writeframes(bytes(frames))
    return clipped


# --------------------------------------------------------------------------- #
# Level and spectrum summary
# --------------------------------------------------------------------------- #

def _db(power_or_amp: float, *, power: bool = False) -> float:
    if power_or_amp <= 0.0 or math.isnan(power_or_amp):
        return -math.inf
    return (10.0 if power else 20.0) * math.log10(power_or_amp)


def _fft(values: list[complex]) -> list[complex]:
    """Iterative radix-2 FFT (len must be a power of two)."""
    n = len(values)
    out = list(values)
    j = 0
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j |= bit
        if i < j:
            out[i], out[j] = out[j], out[i]
    size = 2
    while size <= n:
        step = cmath.exp(-2j * math.pi / size)
        half = size // 2
        for start in range(0, n, size):
            w = 1 + 0j
            for k in range(start, start + half):
                t = w * out[k + half]
                out[k + half] = out[k] - t
                out[k] = out[k] + t
                w *= step
        size *= 2
    return out


_BAND_EDGES = (20.0, 120.0, 500.0, 2000.0, 6000.0, 12000.0)


def _band_names(samplerate: float) -> list[tuple[str, float, float]]:
    def hz(f: float) -> str:
        return f"{f / 1000:g}k" if f >= 1000 else f"{f:g}"
    edges = list(_BAND_EDGES) + [samplerate / 2.0]
    return [(f"{hz(lo)}-{hz(hi)} Hz", lo, hi) for lo, hi in zip(edges, edges[1:], strict=False)
            if hi > lo]


def _bands(samples: Sequence[float], samplerate: float, frame: int,
           max_frames: int) -> dict[str, float]:
    """Mean power per coarse band (dBFS, a full-scale sine reads -3) from
    Hann-windowed frames spread evenly over the signal."""
    names = _band_names(samplerate)
    n = len(samples)
    if n < 4:
        return {name: -math.inf for name, _lo, _hi in names}
    if n < frame:
        frame = 1 << max(1, (n.bit_length() - 1))
    window = [0.5 - 0.5 * math.cos(2 * math.pi * i / frame) for i in range(frame)]
    norm = 2.0 / (frame * frame * (sum(w * w for w in window) / frame))
    count = max(1, min(max_frames, n // frame))
    hop = (n - frame) // max(1, count - 1) if count > 1 else 0
    totals = [0.0] * len(names)
    for f in range(count):
        start = f * hop
        chunk = [complex(samples[start + i] * window[i]) for i in range(frame)]
        spectrum = _fft(chunk)
        for k in range(1, frame // 2):
            freq = k * samplerate / frame
            power = abs(spectrum[k]) ** 2 * norm
            for b, (_name, lo, hi) in enumerate(names):
                if lo <= freq < hi or (b == len(names) - 1 and freq >= lo):
                    totals[b] += power
                    break
    return {name: round(_db(total / count, power=True), 2)
            for (name, _lo, _hi), total in zip(names, totals, strict=True)}


def summarize(channels: Sequence[Sequence[float]], samplerate: float, *,
              frame: int = 1024, max_frames: int = 16) -> list[dict]:
    """Per-channel level summary: RMS and peak in dBFS, NaN/Inf counts, and
    the mean power of six coarse bands (dBFS) from a stdlib FFT."""
    rows = []
    for ch in channels:
        finite = [v for v in ch if math.isfinite(v)]
        bad = len(ch) - len(finite)
        rms = math.sqrt(sum(v * v for v in finite) / len(finite)) if finite else 0.0
        peak = max((abs(v) for v in finite), default=0.0)
        row: dict[str, Any] = {"rms_db": round(_db(rms), 2), "peak_db": round(_db(peak), 2),
                               "nonfinite": bad}
        row["bands_db"] = _bands([v if math.isfinite(v) else 0.0 for v in ch],
                                 samplerate, frame, max_frames)
        rows.append(row)
    return rows


# --------------------------------------------------------------------------- #
# Loading a device's patcher
# --------------------------------------------------------------------------- #

@dataclass
class _Patch:
    name: str
    boxes: dict[str, dict]
    lines: list[tuple[str, int, str, int]]
    files: dict[str, bytes | str]
    search_dir: Path | None = None

    def file(self, filename: str) -> str | None:
        content = self.files.get(filename)
        if content is None and self.search_dir is not None:
            candidate = self.search_dir / filename
            if candidate.is_file():
                content = candidate.read_bytes()
        if isinstance(content, bytes):
            return content.decode("utf-8", "replace")
        return content


def _patch_from_container(name: str, container: Any, files: dict,
                          search_dir: Path | None = None) -> _Patch:
    boxes = {str(box["id"]): box for box in iter_boxes(container) if "id" in box}
    lines = []
    for line in iter_patchlines(container):
        (src, so), (dst, di) = line["source"], line["destination"]
        lines.append((str(src), int(so), str(dst), int(di)))
    return _Patch(name, boxes, lines, files, search_dir)


def _load(source: Any) -> _Patch:
    from .device import Device

    if isinstance(source, Device):
        assets = {asset.filename: asset.content for asset in source.assets()}
        return _patch_from_container(source.name, source, assets)
    path = Path(source)
    if path.suffix.lower() != ".amxd":
        raise RenderError(f"{path}: render takes a Device or an .amxd file")
    from .freeze import _patcher_dict_from_payload, _read_amxd, extract_frozen_amxd

    _code, payload, frozen = _read_amxd(str(path))
    files: dict[str, bytes | str] = {}
    if frozen:
        bundled = extract_frozen_amxd(path.read_bytes())
        device_json = next(iter(bundled.values()))
        files = dict(list(bundled.items())[1:])
        patcher = _patcher_dict_from_payload(device_json)
    else:
        patcher = _patcher_dict_from_payload(payload)
    return _patch_from_container(path.stem, patcher.get("patcher", patcher), files,
                                 search_dir=path.parent)


# --------------------------------------------------------------------------- #
# Parameters
# --------------------------------------------------------------------------- #

_PARAM_CLASSES = {"live.dial", "live.numbox", "live.slider", "live.toggle", "live.tab",
                  "live.menu", "live.text"}


@dataclass
class _LiveParam:
    box_id: str
    names: list[str]
    value: float
    minimum: float | None
    maximum: float | None
    enum: list[str] | None


def _live_params(patch: _Patch) -> dict[str, _LiveParam]:
    params = {}
    for box_id, box in patch.boxes.items():
        if box.get("maxclass") not in _PARAM_CLASSES:
            continue
        valueof = box.get("saved_attribute_attributes", {}).get("valueof", {})
        names = [valueof.get("parameter_longname"), valueof.get("parameter_shortname"),
                 box.get("varname"), box_id]
        enum = valueof.get("parameter_enum")
        lo, hi = valueof.get("parameter_mmin"), valueof.get("parameter_mmax")
        if box.get("maxclass") == "live.toggle":
            lo, hi = 0, 1
        if enum:
            lo, hi = 0, len(enum) - 1
        initial = valueof.get("parameter_initial")
        if isinstance(initial, list):
            initial = initial[0] if initial else None
        if not valueof.get("parameter_initial_enable", initial is not None) or initial is None:
            initial = lo if lo is not None else 0.0
        params[box_id] = _LiveParam(box_id, [str(n) for n in names if n], float(initial),
                                    None if lo is None else float(lo),
                                    None if hi is None else float(hi),
                                    [str(e) for e in enum] if enum else None)
    return params


def _parse_value(raw: Any, param: _LiveParam | None) -> float:
    if isinstance(raw, (int, float)):
        return float(raw)
    text = str(raw).strip()
    if param is not None and param.enum and text in param.enum:
        return float(param.enum.index(text))
    try:
        return float(text)
    except ValueError:
        choices = f" (choices: {', '.join(param.enum)})" if param and param.enum else ""
        raise RenderError(f"parameter value {raw!r} is not a number{choices}") from None


# --------------------------------------------------------------------------- #
# The renderer
# --------------------------------------------------------------------------- #

_BINOPS = {
    "*": lambda a, b: a * b,
    "+": lambda a, b: a + b,
    "-": lambda a, b: a - b,
    "/": lambda a, b: a / b if b != 0 else 0.0,
    "!-": lambda a, b: b - a,
    "!/": lambda a, b: b / a if a != 0 else 0.0,
}
_CONTROL_OPS = {
    "dbtoa": lambda x: 10.0 ** (x / 20.0),
    "atodb": lambda x: 20.0 * math.log10(x) if x > 0 else -math.inf,
}
_NUMBER = re.compile(r"^[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?$")


def _gen_seed(seed: int, box_id: str) -> int:
    """A noise() seed per gen~ box, unrelated to the generated input's seeds."""
    digest = hashlib.blake2b(f"gen~:{seed}:{box_id}".encode(), digest_size=8).digest()
    return int.from_bytes(digest, "little")


def _number(atom: str) -> float | None:
    return float(atom) if _NUMBER.match(atom) else None


def _words(box: dict) -> list[str]:
    return str(box.get("text", "")).split()


@dataclass
class _Gen:
    kernel: GenKernel
    params: dict[str, float]
    # gen~ inlet index -> codebox input names it feeds
    inputs: dict[int, list[str]]
    # gen~ outlet index -> list of ("out", k) codebox outs or ("in", i) passthroughs
    outputs: dict[int, list[tuple[str, int]]]


class _Renderer:
    def __init__(self, patch: _Patch, params: Mapping[str, Any], samplerate: float,
                 inputs: Channels, seed: int, strict: bool):
        self.patch = patch
        self.sr = samplerate
        self.inputs = inputs
        self.n = max((len(ch) for ch in inputs), default=0)
        self.seed = seed
        self.strict = strict
        self.notes: list[str] = []
        self.into: dict[tuple[str, int], list[tuple[str, int]]] = defaultdict(list)
        for src, so, dst, di in patch.lines:
            self.into[(dst, di)].append((src, so))
        self.live = _live_params(patch)
        self.gen_overrides: dict[str, dict[str, float]] = defaultdict(dict)
        self.applied: dict[str, float] = {}
        self._applied_by: dict[str, str] = {}  # applied name -> param box or gen~ id
        self._reached: set[str] = set()        # param boxes and gen~ boxes on the path
        self._signals: dict[tuple[str, int], list[float]] = {}
        self._gen_out: dict[str, dict[int, list[float]]] = {}
        self._gens: dict[str, _Gen] = {}
        self._active: list[str] = []
        self.order: list[str] = []
        self._bind_params(params)

    # -- parameters -------------------------------------------------------- #

    def _bind_params(self, params: Mapping[str, Any]) -> None:
        by_name: dict[str, _LiveParam] = {}
        for live in self.live.values():
            for alias in live.names:
                by_name.setdefault(alias, live)
        folded = {alias.lower(): live for alias, live in reversed(list(by_name.items()))}
        for name, raw in params.items():
            param = by_name.get(name) or folded.get(name.lower())
            if param is not None:
                value = _parse_value(raw, param)
                lo, hi = param.minimum, param.maximum
                if lo is not None and hi is not None and not lo <= value <= hi:
                    clamped = min(max(value, lo), hi)
                    self.notes.append(f"parameter {name!r} = {value:g} is outside "
                                      f"{lo:g}..{hi:g}; Live clamps it to {clamped:g}")
                    value = clamped
                param.value = value
                self.applied[param.names[0]] = value
                self._applied_by[param.names[0]] = param.box_id
                continue
            self._bind_gen_param(name, raw)

    def _gen_param_names(self) -> dict[str, list[str]]:
        found: dict[str, list[str]] = defaultdict(list)
        for box_id, box in self.patch.boxes.items():
            if _words(box)[:1] == ["gen~"]:
                try:
                    gen = self._gen(box_id)
                except RenderError:
                    continue
                for pname in gen.kernel.params:
                    found[pname].append(box_id)
        return found

    def _bind_gen_param(self, name: str, raw: Any) -> None:
        value = _parse_value(raw, None)
        owners = self._gen_param_names()
        box_id, _, pname = name.rpartition(".")
        if box_id and box_id in self.patch.boxes and box_id in owners.get(pname, []):
            self.gen_overrides[box_id][pname] = value
            self.applied[name] = value
            self._applied_by[name] = box_id
            return
        if len(owners.get(name, [])) == 1:
            self.gen_overrides[owners[name][0]][name] = value
            self.applied[name] = value
            self._applied_by[name] = owners[name][0]
            return
        if len(owners.get(name, [])) > 1:
            raise RenderError(f"gen Param {name!r} exists in several gen~ boxes "
                              f"({', '.join(owners[name])}); name one as BOX.{name}")
        available = sorted({p.names[0] for p in self.live.values()}
                           | {f"{b}.{p}" for p, boxes in owners.items() for b in boxes})
        raise RenderError(f"unknown parameter {name!r}; this device has: "
                          + (", ".join(available) or "no parameters"))

    # -- helpers ----------------------------------------------------------- #

    def _box(self, box_id: str) -> dict:
        box = self.patch.boxes.get(box_id)
        if box is None:
            raise RenderError(f"a patch line refers to missing box {box_id!r}")
        return box

    def _describe(self, box_id: str) -> str:
        box = self.patch.boxes.get(box_id, {})
        text = box.get("text") or box.get("maxclass", "?")
        return f"{box_id!r} [{text}]"

    def _unsupported(self, box_id: str, why: str) -> RenderError:
        return RenderError(f"box {self._describe(box_id)}: {why}")

    def _is_signal_source(self, box_id: str, outlet: int) -> bool:
        """True for a signal object the renderer runs, False for a control
        object; raises for any other signal object."""
        box = self._box(box_id)
        words = _words(box)
        head = words[0] if words else ""
        if box.get("maxclass") in _PARAM_CLASSES or box.get("maxclass") == "message":
            return False
        if head in ("plugin~", "gen~", "sig~") or (head.endswith("~") and head[:-1] in _BINOPS):
            return True
        if head == "line~":
            if outlet != 0:
                raise self._unsupported(box_id, f"line~ outlet {outlet} is not rendered")
            return True
        outlettypes = box.get("outlettype") or []
        kind = outlettypes[outlet] if outlet < len(outlettypes) else ""
        if head.endswith("~") or kind == "signal" or box.get("maxclass") != "newobj":
            raise self._unsupported(box_id, "not an object the renderer can run")
        return False

    # -- control chains ---------------------------------------------------- #

    def _control_in(self, box_id: str, inlet: int) -> list[Any] | None:
        sources = self.into.get((box_id, inlet), [])
        if not sources:
            return None
        if len(sources) > 1:
            raise self._unsupported(box_id, f"inlet {inlet} has {len(sources)} control "
                                            f"sources; only one is rendered")
        return self._control(*sources[0])

    def _require_cold_inlets_free(self, box_id: str, numinlets: int) -> None:
        for inlet in range(1, numinlets):
            if self.into.get((box_id, inlet)):
                raise self._unsupported(box_id, f"control inlet {inlet} is wired; only "
                                                f"left-inlet control chains are rendered")

    def _control(self, box_id: str, outlet: int) -> list[Any]:
        """The message a control box sends, evaluated once at its steady state."""
        box = self._box(box_id)
        self._enter(box_id)
        try:
            return self._control_eval(box_id, box, outlet)
        finally:
            self._leave(box_id)

    def _control_eval(self, box_id: str, box: dict, outlet: int) -> list[Any]:
        maxclass = box.get("maxclass")
        if maxclass in _PARAM_CLASSES:
            if outlet != 0:
                raise self._unsupported(box_id, f"outlet {outlet} of {maxclass} is not "
                                                f"rendered (use outlet 0, its value)")
            if any(key[0] == box_id for key in self.into):
                self.notes.append(f"{self._describe(box_id)} holds its parameter value; "
                                  f"messages wired into it are not rendered")
            self._reached.add(box_id)
            return [self.live[box_id].value]
        words = _words(box)
        if maxclass != "newobj" or not words:
            raise self._unsupported(box_id, "not a control object the renderer evaluates")
        head, args = words[0], words[1:]
        if head == "loadmess":
            return [_number(a) if _number(a) is not None else a for a in args]
        if head in ("pack", "pak"):
            atoms = args or ["0", "0"]   # a bare pack has two int inlets
            self._require_cold_inlets_free(box_id, len(atoms))
            first = self._needed(box_id, 0)
            rest = [_number(a) if _number(a) is not None else 0.0 for a in atoms[1:]]
            return [first[0], *rest]
        if head in ("prepend", "append"):
            msg = self._needed(box_id, 0)
            extra = [_number(a) if _number(a) is not None else a for a in args]
            return extra + msg if head == "prepend" else msg + extra
        if head in ("t", "trigger") and args and all(a in ("f", "l") for a in args):
            return self._needed(box_id, 0)
        if head in ("f", "float"):
            self._require_cold_inlets_free(box_id, 2)
            return [float(self._needed(box_id, 0)[0])]
        if head in _CONTROL_OPS and not args:
            return [_CONTROL_OPS[head](float(self._needed(box_id, 0)[0]))]
        if head in _BINOPS and len(args) == 1 and _number(args[0]) is not None:
            self._require_cold_inlets_free(box_id, 2)
            value = _BINOPS[head](float(self._needed(box_id, 0)[0]), float(args[0]))
            return [value]
        if head == "scale" and len(args) == 4 and all(_number(a) is not None for a in args):
            self._require_cold_inlets_free(box_id, 6)
            in_lo, in_hi, out_lo, out_hi = (float(a) for a in args)
            x = float(self._needed(box_id, 0)[0])
            if in_hi == in_lo:
                raise self._unsupported(box_id, "scale with an empty input range")
            return [out_lo + (x - in_lo) * (out_hi - out_lo) / (in_hi - in_lo)]
        raise self._unsupported(box_id, "not a control object the renderer evaluates")

    def _needed(self, box_id: str, inlet: int) -> list[Any]:
        msg = self._control_in(box_id, inlet)
        if msg is None:
            raise self._unsupported(box_id, f"inlet {inlet} has no input, so it never "
                                            f"sends anything")
        if not msg:
            raise self._unsupported(box_id, "receives an empty message")
        return msg

    # -- signals ----------------------------------------------------------- #

    def _enter(self, box_id: str) -> None:
        if box_id in self._active:
            loop = " -> ".join(self._active[self._active.index(box_id):] + [box_id])
            raise RenderError(f"feedback loop without a delay: {loop}")
        self._active.append(box_id)

    def _leave(self, box_id: str) -> None:
        self._active.pop()

    def _inlet_signal(self, box_id: str, inlet: int) -> list[float] | None:
        """Sum of the signals wired into an inlet, or None if no signal is."""
        total: list[float] | None = None
        for src, so in self.into.get((box_id, inlet), []):
            if not self._is_signal_source(src, so):
                continue
            sig = self.signal(src, so)
            total = list(sig) if total is None else [a + b for a, b in zip(total, sig, strict=True)]
        return total

    def _control_sources(self, box_id: str, inlet: int) -> list[tuple[str, int]]:
        return [(src, so) for src, so in self.into.get((box_id, inlet), [])
                if not self._is_signal_source(src, so)]

    def signal(self, box_id: str, outlet: int) -> list[float]:
        key = (box_id, outlet)
        if key not in self._signals:
            self._enter(box_id)
            try:
                self._signals[key] = self._signal_eval(box_id, outlet)
            finally:
                self._leave(box_id)
            if box_id not in self.order:
                self.order.append(box_id)
        return self._signals[key]

    def _constant(self, value: float) -> list[float]:
        return [float(value)] * self.n

    def _signal_eval(self, box_id: str, outlet: int) -> list[float]:
        box = self._box(box_id)
        words = _words(box)
        head, args = (words[0], words[1:]) if words else ("", [])
        if head == "plugin~":
            chans = [int(a) for a in args if a.isdigit()] or [1, 2]
            if outlet >= len(chans):
                raise self._unsupported(box_id, f"outlet {outlet} is not an audio input")
            channel = chans[outlet] - 1
            if channel < len(self.inputs):
                return list(self.inputs[channel])
            return list(self.inputs[-1]) if self.inputs else self._constant(0.0)
        if head == "gen~":
            return self._gen_outlet(box_id, outlet)
        if head in ("line~", "sig~"):
            sources = self._control_sources(box_id, 0)
            if self._inlet_signal(box_id, 0) is not None:
                raise self._unsupported(box_id, "a signal into it is not rendered")
            if not sources:
                arg = _number(args[0]) if args and head == "sig~" else None
                return self._constant(arg or 0.0)
            msg = self._control_in(box_id, 0)
            assert msg is not None
            if head == "line~":
                self.notes.append(f"{self._describe(box_id)} is held at its target "
                                  f"{float(msg[0]):g} from the first sample (the ramp is "
                                  f"not rendered)")
            return self._constant(float(msg[0]))
        if head.endswith("~") and head[:-1] in _BINOPS:
            return self._binop(box_id, head[:-1], args)
        raise self._unsupported(box_id, "not an object the renderer can run")

    def _binop(self, box_id: str, op: str, args: list[str]) -> list[float]:
        if len(args) > 1 or (args and _number(args[0]) is None):
            raise self._unsupported(box_id, "arguments other than one number are not rendered")
        left = self._inlet_signal(box_id, 0)
        if left is None:
            msg = self._control_in(box_id, 0)
            if msg is None:
                left = self._constant(0.0)
            else:
                left = self._constant(float(msg[0]))
        right = self._inlet_signal(box_id, 1)
        if right is None:
            controls = self._control_sources(box_id, 1)
            if controls:
                right = self._constant(float(self._needed(box_id, 1)[0]))
            else:
                right = self._constant(float(args[0]) if args else 0.0)
        fn = _BINOPS[op]
        return [fn(a, b) for a, b in zip(left, right, strict=True)]

    # -- gen~ -------------------------------------------------------------- #

    def _gen_patcher(self, box_id: str, box: dict) -> dict:
        patcher = box.get("patcher")
        if isinstance(patcher, dict):
            return patcher
        words = _words(box)
        name = next((w for w in words[1:] if not w.startswith("@")), None)
        if name is None:
            if isinstance(box.get("code"), str):
                raise self._unsupported(
                    box_id, "has a flat `code` attribute and no gen patcher. Max ignores "
                            "`code` and loads its default patcher, so in Live this box "
                            "passes the audio through dry. Build it with "
                            "Device.embed_gendsp or Device.add_gendsp")
            raise self._unsupported(box_id, "has no gen patcher (embedded or .gendsp)")
        filename = name if name.endswith(".gendsp") else f"{name}.gendsp"
        text = self.patch.file(filename)
        if text is None:
            raise self._unsupported(box_id, f"its gen patcher {filename} was not found "
                                            f"(not registered, bundled or next to the device)")
        try:
            data = json.loads(text)
        except ValueError as exc:
            raise self._unsupported(box_id, f"{filename} is not valid JSON: {exc}") from exc
        return data.get("patcher", data)

    def _gen(self, box_id: str) -> _Gen:
        if box_id in self._gens:
            return self._gens[box_id]
        box = self._box(box_id)
        patcher = self._gen_patcher(box_id, box)
        inner = {str(b["id"]): b for b in iter_boxes(patcher) if "id" in b}
        codeboxes = [bid for bid, b in inner.items() if b.get("maxclass") == "codebox"]
        ins: dict[str, int] = {}
        outs: dict[str, int] = {}
        for bid, b in inner.items():
            words = _words(b)
            if b.get("maxclass") in ("codebox", "comment"):
                continue
            if b.get("maxclass") == "newobj" and len(words) == 2 and words[0] in ("in", "out") \
                    and words[1].isdigit():
                (ins if words[0] == "in" else outs)[bid] = int(words[1]) - 1
                continue
            raise self._unsupported(box_id, f"its gen patcher holds {b.get('text') or b.get('maxclass')!r} "
                                            f"({bid}); only one codebox wired to in/out "
                                            f"objects is simulated")
        if len(codeboxes) > 1:
            raise self._unsupported(box_id, f"its gen patcher has {len(codeboxes)} "
                                            f"codeboxes; only one is simulated")
        code = inner[codeboxes[0]].get("code", "") if codeboxes else "out1 = 0.;"
        try:
            kernel = GenKernel(code, strict=self.strict)
        except UnsupportedKernel as exc:
            raise self._unsupported(box_id, f"gen_sim cannot run its codebox: {exc}") from exc
        gen = _Gen(kernel, dict(kernel.params), defaultdict(list), defaultdict(list))
        for line in iter_patchlines(patcher):
            (src, so), (dst, di) = line["source"], line["destination"]
            src, dst = str(src), str(dst)
            if src in ins and dst in codeboxes:
                gen.inputs[ins[src]].append(f"in{int(di) + 1}")
            elif src in codeboxes and dst in outs:
                gen.outputs[outs[dst]].append(("out", int(so) + 1))
            elif src in ins and dst in outs:
                gen.outputs[outs[dst]].append(("in", ins[src]))
            else:
                raise self._unsupported(box_id, f"its gen patcher wires {src} -> {dst}, "
                                                f"which is not simulated")
        self._gens[box_id] = gen
        return gen

    def _gen_messages(self, box_id: str, gen: _Gen) -> None:
        numinlets = int(self._box(box_id).get("numinlets", 1) or 1)
        for inlet in range(max(numinlets, 1)):
            for src, so in self._control_sources(box_id, inlet):
                msg = self._control(src, so)
                if len(msg) != 2 or not isinstance(msg[0], str) or msg[0] not in gen.params:
                    raise self._unsupported(src, f"sends {msg!r} to gen~ {box_id!r}; only "
                                                 f"'PARAM value' messages for its declared "
                                                 f"Params are rendered")
                gen.params[msg[0]] = float(msg[1])

    def _gen_outlet(self, box_id: str, outlet: int) -> list[float]:
        gen = self._gen(box_id)
        if box_id not in self._gen_out:
            self._reached.add(box_id)
            for note in gen.kernel.approximations:
                self.notes.append(f"gen~ {box_id!r}: {note}")
            self._gen_messages(box_id, gen)
            gen.params.update(self.gen_overrides.get(box_id, {}))
            inlet_signals: dict[int, list[float]] = {}
            kernel_in: dict[str, list[float]] = {}
            for inlet, names in gen.inputs.items():
                sig = self._inlet_signal(box_id, inlet)
                inlet_signals[inlet] = sig if sig is not None else self._constant(0.0)
                for name in names:
                    kernel_in[name] = inlet_signals[inlet]
            try:
                result = gen.kernel.run(kernel_in, gen.params, self.sr, self.n,
                                        seed=_gen_seed(self.seed, box_id))
            except UnsupportedKernel as exc:
                raise self._unsupported(box_id, f"gen_sim cannot run its codebox: {exc}") from exc
            outputs: dict[int, list[float]] = {}
            for out_idx, sources in gen.outputs.items():
                total = self._constant(0.0)
                for kind, k in sources:
                    if kind == "out":
                        part = result.get(f"out{k}") or self._constant(0.0)
                    else:
                        part = inlet_signals.get(k)
                        if part is None:
                            part = self._inlet_signal(box_id, k) or self._constant(0.0)
                    total = [a + b for a, b in zip(total, part, strict=True)]
                outputs[out_idx] = total
            self._gen_out[box_id] = outputs
        return self._gen_out[box_id].get(outlet) or self._constant(0.0)

    # -- top level --------------------------------------------------------- #

    def run(self) -> Channels:
        outs = [bid for bid, box in self.patch.boxes.items() if _words(box)[:1] == ["plugout~"]]
        if not outs:
            raise RenderError(f"{self.patch.name}: no plugout~, so there is no audio output "
                              f"to render")
        if len(outs) > 1:
            raise RenderError(f"{self.patch.name}: {len(outs)} plugout~ boxes "
                              f"({', '.join(outs)}); only one is rendered")
        out_id = outs[0]
        chans = [int(a) for a in _words(self.patch.boxes[out_id])[1:] if a.isdigit()] or [1, 2]
        result = []
        for inlet in range(len(chans)):
            if self._control_sources(out_id, inlet):
                src = self._control_sources(out_id, inlet)[0][0]
                raise self._unsupported(src, "is wired into plugout~ but is not a signal "
                                             "object the renderer can run")
            sig = self._inlet_signal(out_id, inlet)
            result.append(sig if sig is not None else self._constant(0.0))
        self.order.append(out_id)
        for name, owner in self._applied_by.items():
            if owner not in self._reached:
                self.notes.append(f"parameter {name!r} does not reach the audio path, so "
                                  f"setting it changed nothing")
        return result


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

@dataclass
class Render:
    """The result of :func:`render`: input and output audio plus what was applied."""

    device: str
    samplerate: float
    input: Channels
    output: Channels
    #: Parameter values set by name (Live parameters and gen Params).
    params: dict[str, float] = field(default_factory=dict)
    #: Approximations and held values that apply to this render.
    notes: list[str] = field(default_factory=list)
    #: Box ids on the audio path, in the order they were evaluated.
    path: list[str] = field(default_factory=list)

    @property
    def seconds(self) -> float:
        return len(self.output[0]) / self.samplerate if self.output else 0.0

    def summary(self) -> dict:
        """``{"input": [...], "output": [...]}`` per-channel :func:`summarize` rows."""
        return {"input": summarize(self.input, self.samplerate),
                "output": summarize(self.output, self.samplerate)}

    def write(self, path: str | os.PathLike, *, bits: int = 24) -> int:
        """Write the output as a WAV; returns the number of clipped samples."""
        return write_wav(path, self.output, self.samplerate, bits=bits)


def render(source: Any, signal: str | os.PathLike | Sequence[Sequence[float]] = "noise",
           *, params: Mapping[str, Any] | None = None, samplerate: float | None = None,
           seconds: float = 0.5, level_db: float = -6.0, freq: float = 440.0,
           seed: int = 0, strict: bool = False,
           out: str | os.PathLike | None = None) -> Render:
    """Render ``source`` (a :class:`~m4l_builder.Device` or ``.amxd`` path).

    ``signal`` is a WAV path, one of :data:`SIGNAL_KINDS` (generated with
    ``seconds``, ``level_db``, ``freq`` and ``seed``; see
    :func:`generate_signal`), or channel lists you made yourself. A mono
    input feeds every ``plugin~`` channel.

    ``params`` sets parameters by name: a Live parameter's long name, short
    name, varname or box id (enum parameters also take their labels), or a
    gen ``Param`` as ``BOX.param`` (or just ``param`` when one gen~ declares
    it). A Live parameter flows through the patch to whatever it controls; a
    gen Param set directly wins over the message the patch would send it.
    Unset parameters keep their initial values.

    ``strict`` refuses approximate gen constructs instead of noting them.
    ``out`` writes the output WAV (24-bit PCM). Raises :class:`RenderError`
    naming the box when the path holds anything the renderer cannot run.
    """
    patch = _load(source)
    rate = float(samplerate or 48000.0)
    if isinstance(signal, (str, os.PathLike)) and str(signal) in SIGNAL_KINDS:
        audio = generate_signal(str(signal), seconds=seconds, samplerate=rate,
                                level_db=level_db, freq=freq, seed=seed)
    elif isinstance(signal, (str, os.PathLike)):
        audio, file_rate = read_wav(signal)
        if samplerate is not None and float(file_rate) != rate:
            raise RenderError(f"{signal} is {file_rate} Hz but samplerate={rate:g} was "
                              f"asked for; resampling is not supported")
        rate = float(file_rate)
    else:
        audio = [list(map(float, ch)) for ch in signal]
    length = max((len(ch) for ch in audio), default=0)
    if not length:
        raise RenderError("the input signal is empty")
    audio = [ch + [0.0] * (length - len(ch)) for ch in audio]
    renderer = _Renderer(patch, params or {}, rate, audio, seed, strict)
    output = renderer.run()
    result = Render(patch.name, rate, audio, output, dict(renderer.applied),
                    list(dict.fromkeys(renderer.notes)), renderer.order)
    if out is not None:
        result.write(out)
    return result


# --------------------------------------------------------------------------- #
# Checks
# --------------------------------------------------------------------------- #

@dataclass
class Check:
    """One check's outcome; truthy when it passed."""

    name: str
    ok: bool
    detail: str

    def __bool__(self) -> bool:
        return self.ok

    def __str__(self) -> str:
        return f"{'ok  ' if self.ok else 'FAIL'} {self.name}: {self.detail}"


def _pairs(result: Render) -> Iterable[tuple[int, list[float], list[float]]]:
    for c, out in enumerate(result.output):
        src = result.input[c] if c < len(result.input) else result.input[-1]
        yield c, src, out


def _rms(values: Iterable[float]) -> float:
    vals = list(values)
    return math.sqrt(sum(v * v for v in vals) / len(vals)) if vals else 0.0


def check_not_dry(result: Render, *, min_change_db: float = -60.0) -> Check:
    """The output differs from the input: the effect is actually processing.

    Passes when, on at least one channel, the difference between output and
    input is no more than ``-min_change_db`` dB below the input level. A gen~
    that failed to compile passes audio through untouched and fails this.
    """
    parts, changed = [], False
    for c, src, out in _pairs(result):
        level = _rms(src)
        if level == 0.0:
            parts.append(f"ch{c + 1} input is silent")
            continue
        bad = sum(1 for v in out if not math.isfinite(v))
        if bad:   # NaN/Inf is a change, just not a healthy one (see check_finite)
            changed = True
            parts.append(f"ch{c + 1} has {bad} NaN/Inf sample(s)")
            continue
        rel = _db(_rms(a - b for a, b in zip(out, src, strict=True)) / level)
        changed = changed or rel >= min_change_db
        parts.append(f"ch{c + 1} {rel:.1f} dB")
    return Check("not dry", changed,
                 "output minus input, relative to the input: " + ", ".join(parts))


def check_identity(result: Render, *, tolerance: float = 1e-6) -> Check:
    """The output equals the input within ``tolerance`` on every sample (a
    bypass or neutral setting really is transparent)."""
    worst = 0.0
    for _c, src, out in _pairs(result):
        for a, b in zip(out, src, strict=True):
            worst = max(worst, abs(a - b) if math.isfinite(a) else math.inf)
    return Check("identity", worst <= tolerance,
                 f"largest sample difference {worst:.3g} (tolerance {tolerance:g})")


def check_silent(result: Render, *, floor_db: float = -120.0) -> Check:
    """The output peak stays below ``floor_db`` dBFS (feed it silence)."""
    peak = max((abs(v) if math.isfinite(v) else math.inf
                for ch in result.output for v in ch), default=0.0)
    return Check("silent", _db(peak) <= floor_db,
                 f"output peak {_db(peak):.1f} dBFS (floor {floor_db:g})")


def check_finite(result: Render) -> Check:
    """No NaN or infinity anywhere in the output."""
    bad = sum(1 for ch in result.output for v in ch if not math.isfinite(v))
    return Check("finite", bad == 0, f"{bad} NaN/Inf sample(s)")


class Audit(list):
    """A list of :class:`Check` results; truthy when every check passed."""

    def __bool__(self) -> bool:
        return all(self)

    @property
    def failures(self) -> list[Check]:
        return [check for check in self if not check]

    def __str__(self) -> str:
        return "\n".join(str(check) for check in self)


def audit(source: Any, *, engaged: Mapping[str, Any] | None = None,
          bypass: Mapping[str, Any] | None = None, seconds: float = 0.25,
          samplerate: float = 48000.0) -> Audit:
    """The standard battery, for tests: ``assert audit(device, ...), str(...)``.

    * with ``engaged`` params, noise at -6 dBFS: the output is not dry;
    * with ``engaged`` params, silence in: silence out;
    * with ``engaged`` params, full-scale noise, sine and impulse: no NaN/Inf;
    * with ``bypass`` params (when given), noise: output == input.
    """
    engaged = dict(engaged or {})
    checks = Audit()

    def run(kind: str, chosen: Mapping[str, Any], level: float) -> Render:
        return render(source, kind, params=chosen, seconds=seconds,
                      samplerate=samplerate, level_db=level)

    checks.append(_named(check_not_dry(run("noise", engaged, -6.0)), "engaged"))
    checks.append(_named(check_silent(run("silence", engaged, 0.0)), "silence in"))
    for kind in ("noise", "sine", "impulse"):
        checks.append(_named(check_finite(run(kind, engaged, 0.0)), f"full-scale {kind}"))
    if bypass is not None:
        checks.append(_named(check_identity(run("noise", bypass, -6.0)), "bypass"))
    return checks


def _named(check: Check, context: str) -> Check:
    return Check(f"{check.name} ({context})", check.ok, check.detail)
