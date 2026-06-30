"""Real FFT spectrum-analysis backend (``pfft~`` + ``buffer~``).

This is the analysis half of the spectrum feature; the *display* half lives in
``spectrum_analyzer.py`` (standalone) and ``eq_curve.py`` (EQ overlay).

Contract: the kernel writes ``fft_size/2`` linear magnitudes (~2/N-normalized
so a full-scale sine lands near 0 dB) into a named ``buffer~`` every spectral
frame, indexed by ``fftin~``'s sync outlet. The consumer is told where to look:

    set_analyzer_buffer <name> <bins>     poll this buffer~ (display-side Task
                                          or setInterval reads peek(1,0,bins))
    set_samplerate <hz>                   so the consumer can map bin -> Hz.

Kernel topology (the classic "Forbidden Planet" spectral-buffer pattern)::

    fftin~ 1 blackman ─┬─ cartopol~ ─ *~ 2/N ─ poke~ <buf> (value)
                       │       fftin~ idx ────────┘ (index, samples)
                       └─ fftout~ 1 blackman    (spectral passthrough)

Why not message frames? An earlier framesnap~/vectral~ design emitted
zero-filled 256-sample vector chunks in Live (framesnap~ snapshots the MSP
vector, not the spectral frame) — the buffer~ handoff is sample-accurate,
scheduler-free, and survives FFT-size changes.
"""

from __future__ import annotations

import json

from ..objects import newobj, patchline

FFT_ANALYZER_DEFAULT_SIZE = 2048
FFT_ANALYZER_DEFAULT_OVERLAP = 4

__all__ = [
    "FFT_ANALYZER_DEFAULT_SIZE",
    "FFT_ANALYZER_DEFAULT_OVERLAP",
    "fft_analyzer_kernel",
    "fft_analyzer_dsp",
]


def _support_patcher(boxes, lines, width=520.0, height=280.0):
    return {
        "patcher": {
            "fileversion": 1,
            "appversion": {
                "major": 8,
                "minor": 6,
                "revision": 0,
                "architecture": "x64",
                "modernui": 1,
            },
            "classnamespace": "box",
            "rect": [50.0, 50.0, width, height],
            "bglocked": 0,
            "openinpresentation": 0,
            "default_fontface": 0,
            "default_fontname": "Arial",
            "default_fontsize": 10.0,
            "gridonopen": 1,
            "gridsize": [15.0, 15.0],
            "boxes": boxes,
            "lines": lines,
        }
    }


def fft_analyzer_kernel(
    *,
    buffer_name: str,
    fft_size: int = FFT_ANALYZER_DEFAULT_SIZE,
    window: str = "blackman",
) -> str:
    """Return the ``pfft~`` kernel as a JSON ``.maxpat`` string.

    Writes 2/N-normalized magnitudes into ``buffer_name`` at the bin index
    given by ``fftin~``'s sync outlet, every spectral frame.
    """
    boxes: list = []
    lines: list = []

    def add(box):
        boxes.append(box)

    def wire(src, so, dst, di):
        lines.append(patchline(src, so, dst, di))

    add(newobj("fft_in", f"fftin~ 1 {window}", numinlets=1, numoutlets=3,
               outlettype=["signal", "signal", "signal"],
               patching_rect=[34.0, 34.0, 110.0, 22.0]))
    add(newobj("fft_out", f"fftout~ 1 {window}", numinlets=2, numoutlets=0,
               patching_rect=[34.0, 220.0, 110.0, 22.0]))
    add(newobj("cartopol", "cartopol~", numinlets=2, numoutlets=2,
               outlettype=["signal", "signal"],
               patching_rect=[34.0, 78.0, 72.0, 22.0]))
    # ~2/N normalization so a full-scale sine reads near 0 dB.
    add(newobj("mag_scale", f"*~ {2.0 / fft_size}", numinlets=2, numoutlets=1,
               outlettype=["signal"], patching_rect=[34.0, 118.0, 96.0, 22.0]))
    add(newobj("spec_poke", f"poke~ {buffer_name}", numinlets=3, numoutlets=0,
               patching_rect=[34.0, 162.0, 120.0, 22.0]))

    wire("fft_in", 0, "cartopol", 0)
    wire("fft_in", 1, "cartopol", 1)
    wire("fft_in", 0, "fft_out", 0)
    wire("fft_in", 1, "fft_out", 1)
    wire("cartopol", 0, "mag_scale", 0)
    wire("mag_scale", 0, "spec_poke", 0)
    # fftin~ outlet 2 = bin index (samples) -> poke~ index inlet.
    wire("fft_in", 2, "spec_poke", 1)

    return json.dumps(_support_patcher(boxes, lines), indent=2)


def fft_analyzer_dsp(
    device,
    target_id: str,
    source_id: str,
    *,
    source_outlet: int = 0,
    target_inlet: int = 2,
    fft_size: int = FFT_ANALYZER_DEFAULT_SIZE,
    overlap: int = FFT_ANALYZER_DEFAULT_OVERLAP,
    window: str = "blackman",
    id_prefix: str = "fft",
    kernel_filename: str | None = None,
    samplerate_handshake: bool = True,
    announce_selector: str = "set_analyzer_buffer",
    loadbang_id: str | None = None,
    gate_src: tuple | None = None,
    patch_x: int = 80,
    patch_y: int = 560,
) -> dict[str, str]:
    """Wire a ``pfft~`` analyzer from ``source_id`` for ``target_id`` to poll.

    Emits the kernel support file, instantiates ``pfft~`` writing magnitudes
    into a named ``buffer~`` (see the ⚠️ collision caveat at ``buffer_name`` below),
    and tells the consumer where to look via
    ``<announce_selector> <name> <bins>`` at load (default
    ``set_analyzer_buffer``; pass ``announce_selector="set_dyn_buffer"`` for a
    second, detector-only analyzer that drives a dynamic detector instead of the
    spectrum display). When ``samplerate_handshake`` is set, also wires
    ``dspstate~ -> prepend set_samplerate`` into the same inlet so the consumer
    can map bins to Hz.

    When ``gate_src=(toggle_id, outlet)`` is given, the source is routed through a
    ``selector~ 1 1`` whose control is the toggle (1 = pass, 0 = silence) before
    ``pfft~``, so the FFT processes silence when the analyzer is off (the CPU
    gate). Default ``None`` keeps existing devices byte-identical. Returns the
    created object ids.
    """
    kernel_filename = kernel_filename or f"{id_prefix}_analyzer_core.maxpat"
    stem = kernel_filename[:-len(".maxpat")] if kernel_filename.endswith(".maxpat") else kernel_filename
    bins = fft_size // 2
    # ⚠️ COLLISION CAVEAT (Live-verified 2026-06): this is a FIXED, GLOBAL buffer~
    # name — NOT per-instance-unique. buffer~ names are global across the Max app,
    # so TWO instances of the same device (e.g. after duplicate_track, or two copies
    # in a Set) both bind "<id_prefix>_specbuf"; deleting one leaves the survivor's
    # analyzer DEAD (spectrum draws empty though audio is loud). Reload fixes it.
    # PROPER FIX (tracked): make this per-instance-unique like Rainbow's
    # DEVICE_UNIQUE_ID+name — a "#0" patcher-instance prefix, or a live.thisdevice/
    # LOM-derived suffix set at load. Needs grounding (#0 in an M4L root) + a
    # duplication Live-verify across ALL devices that call this (Para EQ, Linear
    # Phase EQ, Strip), so it's a focused task, not an in-line change.
    buffer_name = f"{id_prefix}_specbuf"
    device.add_support_file(
        kernel_filename,
        fft_analyzer_kernel(
            buffer_name=buffer_name, fft_size=fft_size, window=window,
        ),
        file_type="JSON",
    )

    pfft_id = f"{id_prefix}_pfft"
    buf_id = f"{id_prefix}_buf"
    bufsize_id = f"{id_prefix}_bufsize"
    bufmsg_id = f"{id_prefix}_bufannounce"
    lb_id = loadbang_id
    ids = {"pfft": pfft_id, "buffer": buf_id}

    if lb_id is None:
        lb_id = f"{id_prefix}_lb"
        device.add_newobj(
            lb_id, "loadbang", numinlets=0, numoutlets=1, outlettype=["bang"],
            patching_rect=[patch_x + 240, patch_y - 40, 70, 22],
        )
        ids["loadbang"] = lb_id

    # buffer~ sized in samples (fft_size covers the full frame; the consumer
    # reads the first fft_size/2 bins).
    device.add_newobj(
        buf_id, f"buffer~ {buffer_name}",
        numinlets=1, numoutlets=2, outlettype=["float", "bang"],
        patching_rect=[patch_x, patch_y - 40, 160, 22],
    )
    device.add_box({
        "box": {
            "id": bufsize_id,
            "maxclass": "message",
            "text": f"sizeinsamps {fft_size}",
            "numinlets": 2,
            "numoutlets": 1,
            "outlettype": [""],
            "patching_rect": [patch_x + 180, patch_y - 70, 130, 20],
        }
    })
    device.add_line(lb_id, 0, bufsize_id, 0)
    device.add_line(bufsize_id, 0, buf_id, 0)

    device.add_newobj(
        pfft_id, f"pfft~ {stem} {fft_size} {overlap}",
        numinlets=1, numoutlets=1, outlettype=["signal"],
        patching_rect=[patch_x, patch_y, 220, 22],
    )
    if gate_src is not None:
        gate_id = f"{id_prefix}_gate"
        device.add_newobj(
            gate_id, "selector~ 1 1", numinlets=2, numoutlets=1,
            outlettype=["signal"],
            patching_rect=[patch_x, patch_y - 70, 90, 22],
        )
        device.add_line(source_id, source_outlet, gate_id, 1)
        device.add_line(gate_src[0], gate_src[1], gate_id, 0)
        device.add_line(gate_id, 0, pfft_id, 0)
        ids["gate"] = gate_id
    else:
        device.add_line(source_id, source_outlet, pfft_id, 0)

    # Tell the consumer where the spectrum lives.
    device.add_box({
        "box": {
            "id": bufmsg_id,
            "maxclass": "message",
            "text": f"{announce_selector} {buffer_name} {bins}",
            "numinlets": 2,
            "numoutlets": 1,
            "outlettype": [""],
            "patching_rect": [patch_x, patch_y + 40, 240, 20],
        }
    })
    device.add_line(lb_id, 0, bufmsg_id, 0)
    device.add_line(bufmsg_id, 0, target_id, target_inlet)
    ids["buffer_announce"] = bufmsg_id

    if samplerate_handshake:
        dspstate_id = f"{id_prefix}_dspstate"
        sr_prepend = f"{id_prefix}_sr_prepend"
        device.add_newobj(
            dspstate_id, "dspstate~",
            numinlets=1, numoutlets=4, outlettype=["int", "float", "int", "int"],
            patching_rect=[patch_x + 240, patch_y, 80, 22],
        )
        device.add_newobj(
            sr_prepend, "prepend set_samplerate",
            numinlets=1, numoutlets=1, outlettype=[""],
            patching_rect=[patch_x + 240, patch_y + 30, 140, 22],
        )
        device.add_line(dspstate_id, 1, sr_prepend, 0)
        device.add_line(sr_prepend, 0, target_id, target_inlet)
        device.add_line(lb_id, 0, dspstate_id, 0)
        ids["dspstate"] = dspstate_id
        ids["sr_prepend"] = sr_prepend

    return ids
