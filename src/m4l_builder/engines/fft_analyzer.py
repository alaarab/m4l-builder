"""Real FFT spectrum-analysis backend (``pfft~``-based).

This is the analysis half of the spectrum feature; the *display* half lives in
``spectrum_analyzer.py`` (standalone) and ``eq_curve.py`` (EQ overlay). Both
consume the same wire contract:

    fft_frame <m0> <m1> ... <m_{N-1}>     N = fft_size/2 linear magnitudes,
                                          ~2/N-normalized so a full-scale sine
                                          lands near 0 dB, emitted every
                                          ``frame_interval_ms``.
    set_samplerate <hz>                   so the consumer can map bin -> Hz.

The kernel is emitted as a JSON ``.maxpat`` support file and instantiated with
``pfft~ <stem> <fft_size> <overlap>``. Topology (proven in the standalone
Spectrum Analyzer product)::

    fftin~ 1 blackman ─┬─ cartopol~ ─ *~ 2/N ─ vectral~ N ─ framesnap~ <ms> ─ out 1
                       └─ fftout~ 1 blackman                 (audio passthrough)
    in 1 ─ route interval slide ─┬─ framesnap~ (right inlet)
                                 └─ prepend slide ─ vectral~ (left inlet)

The ``fftin~ -> fftout~`` passthrough keeps ``pfft~`` happy (it expects a
spectral path to the output); the analysis tap is a side branch.
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
    fft_size: int = FFT_ANALYZER_DEFAULT_SIZE,
    window: str = "blackman",
    frame_interval_ms: int = 33,
    slide_up: float = 3.0,
    slide_down: float = 11.0,
) -> str:
    """Return the ``pfft~`` kernel as a JSON ``.maxpat`` string.

    ``slide_up``/``slide_down`` set the ``vectral~`` spectral smoothing (fast
    rise, slow fall). ``frame_interval_ms`` sets how often a full frame is
    emitted on ``out 1``.
    """
    bins = fft_size // 2
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
               patching_rect=[34.0, 250.0, 110.0, 22.0]))
    add(newobj("cartopol", "cartopol~", numinlets=2, numoutlets=2,
               outlettype=["signal", "signal"],
               patching_rect=[34.0, 78.0, 72.0, 22.0]))
    # ~2/N normalization so a full-scale sine reads near 0 dB.
    add(newobj("mag_scale", f"*~ {2.0 / fft_size}", numinlets=2, numoutlets=1,
               outlettype=["signal"], patching_rect=[34.0, 118.0, 96.0, 22.0]))
    add(newobj("mag_smooth", f"vectral~ {bins}", numinlets=2, numoutlets=1,
               outlettype=["signal"], patching_rect=[34.0, 158.0, 100.0, 22.0]))
    add(newobj("smooth_default", f"loadmess slide {slide_up} {slide_down}",
               numinlets=1, numoutlets=1, outlettype=[""],
               patching_rect=[150.0, 158.0, 150.0, 20.0]))
    add(newobj("frame_snap", f"framesnap~ {frame_interval_ms}",
               numinlets=2, numoutlets=1, outlettype=["list"],
               patching_rect=[34.0, 198.0, 100.0, 22.0]))
    add(newobj("frame_start", "loadmess 1", numinlets=1, numoutlets=1,
               outlettype=[""], patching_rect=[150.0, 198.0, 80.0, 20.0]))
    add(newobj("ctrl_in", "in 1", numinlets=1, numoutlets=1, outlettype=[""],
               patching_rect=[320.0, 34.0, 40.0, 22.0]))
    add(newobj("ctrl_route", "route interval slide", numinlets=1, numoutlets=3,
               outlettype=["", "", ""], patching_rect=[320.0, 78.0, 120.0, 22.0]))
    add(newobj("smooth_prepend", "prepend slide", numinlets=1, numoutlets=1,
               outlettype=[""], patching_rect=[320.0, 118.0, 92.0, 22.0]))
    add(newobj("frame_out", "out 1", numinlets=1, numoutlets=0,
               patching_rect=[160.0, 250.0, 48.0, 22.0]))

    wire("fft_in", 0, "cartopol", 0)
    wire("fft_in", 1, "cartopol", 1)
    wire("fft_in", 0, "fft_out", 0)
    wire("fft_in", 1, "fft_out", 1)
    wire("cartopol", 0, "mag_scale", 0)
    wire("mag_scale", 0, "mag_smooth", 1)
    wire("smooth_default", 0, "mag_smooth", 0)
    wire("frame_start", 0, "frame_snap", 0)
    wire("mag_smooth", 0, "frame_snap", 0)
    wire("frame_snap", 0, "frame_out", 0)
    wire("ctrl_in", 0, "ctrl_route", 0)
    wire("ctrl_route", 0, "frame_snap", 1)
    wire("ctrl_route", 1, "smooth_prepend", 0)
    wire("smooth_prepend", 0, "mag_smooth", 0)

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
    frame_interval_ms: int = 33,
    slide_up: float = 3.0,
    slide_down: float = 11.0,
    id_prefix: str = "fft",
    kernel_filename: str | None = None,
    samplerate_handshake: bool = True,
    loadbang_id: str | None = None,
    patch_x: int = 80,
    patch_y: int = 560,
) -> dict[str, str]:
    """Wire a ``pfft~`` analyzer from ``source_id`` into ``target_id``'s inlet.

    Emits the kernel support file, instantiates ``pfft~``, taps the mono signal
    at ``source_id[source_outlet]``, and feeds ``fft_frame <mags...>`` into
    ``target_id`` at ``target_inlet``. When ``samplerate_handshake`` is set,
    also wires ``dspstate~ -> prepend set_samplerate`` into the same inlet so
    the consumer can map bins to Hz. Returns the created object ids.
    """
    kernel_filename = kernel_filename or f"{id_prefix}_analyzer_core.maxpat"
    stem = kernel_filename[:-len(".maxpat")] if kernel_filename.endswith(".maxpat") else kernel_filename
    device.add_support_file(
        kernel_filename,
        fft_analyzer_kernel(
            fft_size=fft_size, window=window,
            frame_interval_ms=frame_interval_ms,
            slide_up=slide_up, slide_down=slide_down,
        ),
        file_type="JSON",
    )

    pfft_id = f"{id_prefix}_pfft"
    frame_prepend = f"{id_prefix}_frame_prepend"
    device.add_newobj(
        pfft_id, f"pfft~ {stem} {fft_size} {overlap}",
        numinlets=1, numoutlets=2, outlettype=["signal", ""],
        patching_rect=[patch_x, patch_y, 220, 22],
    )
    device.add_newobj(
        frame_prepend, "prepend fft_frame",
        numinlets=1, numoutlets=1, outlettype=[""],
        patching_rect=[patch_x, patch_y + 30, 140, 22],
    )
    device.add_line(source_id, source_outlet, pfft_id, 0)
    device.add_line(pfft_id, 1, frame_prepend, 0)
    device.add_line(frame_prepend, 0, target_id, target_inlet)

    ids = {"pfft": pfft_id, "frame_prepend": frame_prepend}

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
        if loadbang_id is not None:
            device.add_line(loadbang_id, 0, dspstate_id, 0)
        else:
            lb_id = f"{id_prefix}_lb"
            device.add_newobj(
                lb_id, "loadbang", numinlets=0, numoutlets=1, outlettype=["bang"],
                patching_rect=[patch_x + 240, patch_y - 30, 70, 22],
            )
            device.add_line(lb_id, 0, dspstate_id, 0)
            ids["loadbang"] = lb_id
        ids["dspstate"] = dspstate_id
        ids["sr_prepend"] = sr_prepend

    return ids
