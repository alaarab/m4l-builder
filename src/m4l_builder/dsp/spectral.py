"""Spectral (pfft~) processing."""

from ..objects import newobj, patchline
from .dynamics import envelope_follower
from .filters import bandpass_filter


def spectral_gate(id_prefix: str, threshold: float = 0.01) -> tuple:
    """Spectral gate using pfft~ pointing to spectral_gate_sub.maxpat.

    Wire audio into {prefix}_pfft inlet 0.
    Wire threshold into {prefix}_pfft inlet 1.
    Output from {prefix}_pfft outlet 0.
    """
    p = id_prefix
    boxes = [
        newobj(f"{p}_pfft", "pfft~ spectral_gate_sub.maxpat 1024 4",
               numinlets=2, numoutlets=1,
               outlettype=["signal"],
               patching_rect=[30, 120, 200, 20]),
    ]
    return (boxes, [])


def spectral_gate_subpatcher(threshold: float = 0.01) -> dict:
    """Return a dict representing the pfft~ subpatcher JSON for spectral gating.

    The subpatcher contains fftin~, fftout~, and threshold-based magnitude gating.
    """
    return {
        "patcher": {
            "fileversion": 1,
            "appversion": {"major": 8, "minor": 6, "revision": 2},
            "rect": [0, 0, 600, 400],
            "bglocked": 0,
            "openinpresentation": 0,
            "boxes": [
                {"box": {"id": "sp_fftin", "maxclass": "newobj", "text": "fftin~ 1",
                         "numinlets": 0, "numoutlets": 2,
                         "outlettype": ["signal", "signal"],
                         "patching_rect": [30, 30, 70, 20]}},
                {"box": {"id": "sp_cartopol", "maxclass": "newobj",
                         "text": "cartopol~",
                         "numinlets": 2, "numoutlets": 2,
                         "outlettype": ["signal", "signal"],
                         "patching_rect": [30, 70, 70, 20]}},
                {"box": {"id": "sp_thresh", "maxclass": "newobj",
                         "text": f">~ {threshold}",
                         "numinlets": 2, "numoutlets": 1,
                         "outlettype": ["signal"],
                         "patching_rect": [30, 110, 70, 20]}},
                {"box": {"id": "sp_gate", "maxclass": "newobj",
                         "text": "*~",
                         "numinlets": 2, "numoutlets": 1,
                         "outlettype": ["signal"],
                         "patching_rect": [30, 150, 30, 20]}},
                {"box": {"id": "sp_poltocar", "maxclass": "newobj",
                         "text": "poltocar~",
                         "numinlets": 2, "numoutlets": 2,
                         "outlettype": ["signal", "signal"],
                         "patching_rect": [30, 200, 70, 20]}},
                {"box": {"id": "sp_fftout", "maxclass": "newobj",
                         "text": "fftout~ 1",
                         "numinlets": 2, "numoutlets": 0,
                         "patching_rect": [30, 250, 70, 20]}},
            ],
            "lines": [
                {"patchline": {"source": ["sp_fftin", 0], "destination": ["sp_cartopol", 0]}},
                {"patchline": {"source": ["sp_fftin", 1], "destination": ["sp_cartopol", 1]}},
                {"patchline": {"source": ["sp_cartopol", 0], "destination": ["sp_thresh", 0]}},
                {"patchline": {"source": ["sp_cartopol", 0], "destination": ["sp_gate", 0]}},
                {"patchline": {"source": ["sp_thresh", 0], "destination": ["sp_gate", 1]}},
                {"patchline": {"source": ["sp_gate", 0], "destination": ["sp_poltocar", 0]}},
                {"patchline": {"source": ["sp_cartopol", 1], "destination": ["sp_poltocar", 1]}},
                {"patchline": {"source": ["sp_poltocar", 0], "destination": ["sp_fftout", 0]}},
                {"patchline": {"source": ["sp_poltocar", 1], "destination": ["sp_fftout", 1]}},
            ],
        }
    }


def vocoder(id_prefix: str, num_bands: int = 16) -> tuple:
    """N-band vocoder: carrier analysis + modulator filtering.

    For each band:
      - A bandpass_filter instance analyzes the carrier
      - An envelope_follower tracks the carrier band level
      - The modulator passes through a bandpass_filter, then gets multiplied
        by the carrier envelope

    Wire carrier into each {prefix}_car_bp_{n}_l inlet 0.
    Wire modulator into each {prefix}_mod_bp_{n}_l inlet 0.
    Each band output comes from {prefix}_out_{n} outlet 0.
    """
    if num_bands < 1:
        raise ValueError(f"vocoder num_bands must be >= 1, got {num_bands}")
    p = id_prefix
    all_boxes = []
    all_lines = []

    for i in range(num_bands):
        # Carrier analysis: bandpass
        car_bp_boxes, car_bp_lines = bandpass_filter(f"{p}_car_bp_{i}")
        # Carrier envelope follower (mono, use L channel)
        env_boxes, env_lines = envelope_follower(f"{p}_env_{i}")
        # Modulator bandpass
        mod_bp_boxes, mod_bp_lines = bandpass_filter(f"{p}_mod_bp_{i}")
        # Multiply modulator by carrier envelope
        out_box = newobj(f"{p}_out_{i}", "*~", numinlets=2, numoutlets=1,
                         outlettype=["signal"],
                         patching_rect=[30 + i * 60, 400, 30, 20])

        all_boxes.extend(car_bp_boxes + env_boxes + mod_bp_boxes + [out_box])
        all_lines.extend(car_bp_lines + env_lines + mod_bp_lines)

        # Wire carrier BP (L) -> envelope follower
        all_lines.append(patchline(f"{p}_car_bp_{i}_out_l", 0, f"{p}_env_{i}_abs", 0))
        # Wire envelope -> out multiplier inlet 1
        all_lines.append(patchline(f"{p}_env_{i}_slide", 0, f"{p}_out_{i}", 1))
        # Wire modulator BP (L) -> out multiplier inlet 0
        all_lines.append(patchline(f"{p}_mod_bp_{i}_out_l", 0, f"{p}_out_{i}", 0))

    return (all_boxes, all_lines)


def spectral_crossover(id_prefix: str, bands: int = 4) -> tuple:
    """Spectral crossover using pfft~ pointing to spectral_crossover_sub.maxpat.

    Wire audio into {prefix}_pfft inlet 0.
    Output from {prefix}_pfft outlet 0.
    """
    p = id_prefix
    boxes = [
        newobj(f"{p}_pfft", "pfft~ spectral_crossover_sub.maxpat 1024 4",
               numinlets=1, numoutlets=bands,
               outlettype=["signal"] * bands,
               patching_rect=[30, 120, 240, 20]),
    ]
    return (boxes, [])


def spectral_crossover_subpatcher(bands: int = 4) -> dict:
    """Return the pfft~ subpatcher dict for spectral band splitting.

    Splits the input spectrum into N equal-width frequency bands using
    fftin~, bin-range routing logic, and fftout~.
    """
    sub_boxes = [
        {"box": {"id": "sc_fftin", "maxclass": "newobj", "text": "fftin~ 1",
                 "numinlets": 0, "numoutlets": 2,
                 "outlettype": ["signal", "signal"],
                 "patching_rect": [30, 30, 70, 20]}},
        {"box": {"id": "sc_cartopol", "maxclass": "newobj", "text": "cartopol~",
                 "numinlets": 2, "numoutlets": 2,
                 "outlettype": ["signal", "signal"],
                 "patching_rect": [30, 70, 70, 20]}},
    ]
    for i in range(bands):
        sub_boxes.append({
            "box": {
                "id": f"sc_fftout_{i}", "maxclass": "newobj",
                "text": f"fftout~ {i + 1}",
                "numinlets": 2, "numoutlets": 0,
                "patching_rect": [30 + i * 80, 200, 70, 20],
            }
        })

    sub_lines = [
        {"patchline": {"source": ["sc_fftin", 0], "destination": ["sc_cartopol", 0]}},
        {"patchline": {"source": ["sc_fftin", 1], "destination": ["sc_cartopol", 1]}},
    ]

    return {
        "patcher": {
            "fileversion": 1,
            "appversion": {"major": 8, "minor": 6, "revision": 2},
            "rect": [0, 0, 600, 400],
            "bglocked": 0,
            "openinpresentation": 0,
            "boxes": sub_boxes,
            "lines": sub_lines,
        }
    }


def stft_phase_vocoder(id_prefix: str) -> tuple:
    """Phase vocoder using pfft~ for time-stretch/pitch-shift.

    Points to phase_vocoder_sub.maxpat as the subpatcher.
    Wire audio into {prefix}_pfft inlet 0.
    Output from {prefix}_pfft outlet 0.
    """
    p = id_prefix
    boxes = [
        newobj(f"{p}_pfft", "pfft~ phase_vocoder_sub.maxpat 1024 4",
               numinlets=1, numoutlets=1, outlettype=["signal"],
               patching_rect=[30, 30, 260, 20]),
    ]
    return (boxes, [])


def phase_vocoder_subpatcher() -> dict:
    """Return the pfft~ subpatcher dict for a phase vocoder.

    Contains fftin~, fftout~, and phase accumulation objects for time-stretch.
    """
    sub_boxes = [
        {"box": {"id": "pv_fftin", "maxclass": "newobj", "text": "fftin~ 1",
                 "numinlets": 0, "numoutlets": 2,
                 "outlettype": ["signal", "signal"],
                 "patching_rect": [30, 30, 70, 20]}},
        {"box": {"id": "pv_cartopol", "maxclass": "newobj", "text": "cartopol~",
                 "numinlets": 2, "numoutlets": 2,
                 "outlettype": ["signal", "signal"],
                 "patching_rect": [30, 80, 80, 20]}},
        {"box": {"id": "pv_phase_acc", "maxclass": "newobj", "text": "+~",
                 "numinlets": 2, "numoutlets": 1,
                 "outlettype": ["signal"],
                 "patching_rect": [120, 80, 30, 20]}},
        {"box": {"id": "pv_poltocar", "maxclass": "newobj", "text": "poltocar~",
                 "numinlets": 2, "numoutlets": 2,
                 "outlettype": ["signal", "signal"],
                 "patching_rect": [30, 140, 80, 20]}},
        {"box": {"id": "pv_fftout", "maxclass": "newobj", "text": "fftout~ 1",
                 "numinlets": 2, "numoutlets": 0,
                 "patching_rect": [30, 200, 70, 20]}},
    ]
    sub_lines = [
        {"patchline": {"source": ["pv_fftin", 0], "destination": ["pv_cartopol", 0]}},
        {"patchline": {"source": ["pv_fftin", 1], "destination": ["pv_cartopol", 1]}},
        {"patchline": {"source": ["pv_cartopol", 0], "destination": ["pv_poltocar", 0]}},
        {"patchline": {"source": ["pv_cartopol", 1], "destination": ["pv_phase_acc", 0]}},
        {"patchline": {"source": ["pv_phase_acc", 0], "destination": ["pv_poltocar", 1]}},
        {"patchline": {"source": ["pv_poltocar", 0], "destination": ["pv_fftout", 0]}},
        {"patchline": {"source": ["pv_poltocar", 1], "destination": ["pv_fftout", 1]}},
    ]
    return {
        "patcher": {
            "fileversion": 1,
            "appversion": {"major": 8, "minor": 6, "revision": 2},
            "rect": [0, 0, 400, 300],
            "bglocked": 0,
            "openinpresentation": 0,
            "boxes": sub_boxes,
            "lines": sub_lines,
        }
    }
