"""Visual engines for jsui — pre-built JavaScript displays.

Each engine module provides a function that returns JavaScript source code
for Max's jsui object (mgraphics/Cairo vector graphics). The code renders
interactive visualizations: filter curves, EQ nodes, envelopes, spectrums.

Usage:
    from m4l_builder.engines.filter_curve import filter_curve_js
    device.add_jsui("filter_display", [10, 30, 200, 80],
                    js_code=filter_curve_js(), numinlets=3)
"""

from .filter_curve import filter_curve_js
from .eq_curve import eq_curve_js
from .envelope_display import envelope_display_js
from .spectrum_analyzer import spectrum_analyzer_js
from .waveform_display import waveform_display_js
from .xy_pad import xy_pad_js
from .piano_roll import piano_roll_js
from .velocity_curve_display import velocity_curve_display_js
from .wavetable_display import wavetable_display_js
from .resonance_bank_display import resonance_bank_display_js
from .sidechain_display import sidechain_display_js
from .spectral_display import spectral_display_js
from .peaking_eq_display import peaking_eq_display_js
from .step_grid_display import step_grid_display_js
from .grain_display import grain_display_js
from .grid_sequencer_display import grid_sequencer_display_js
from .wavetable_editor import wavetable_editor_js
from .spectral_vocoder_display import spectral_vocoder_display_js

__all__ = [
    "filter_curve_js",
    "eq_curve_js",
    "envelope_display_js",
    "spectrum_analyzer_js",
    "waveform_display_js",
    "xy_pad_js",
    "piano_roll_js",
    "velocity_curve_display_js",
    "wavetable_display_js",
    "resonance_bank_display_js",
    "sidechain_display_js",
    "spectral_display_js",
    "peaking_eq_display_js",
    "step_grid_display_js",
    "grain_display_js",
    "grid_sequencer_display_js",
    "wavetable_editor_js",
    "spectral_vocoder_display_js",
]
