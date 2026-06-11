"""Visual engines for jsui: pre-built JavaScript displays.

Each engine module provides a function that returns JavaScript source code
for Max's jsui object (mgraphics/Cairo vector graphics). The code renders
interactive visualizations: filter curves, EQ nodes, envelopes, spectrums.

Usage:
    from m4l_builder.engines.filter_curve import filter_curve_js
    device.add_jsui("filter_display", [10, 30, 200, 80],
                    js_code=filter_curve_js(), numinlets=3)
"""

from .compressor_display import compressor_display_js
from .crossover_display import crossover_display_js
from .delay_trail import (
    DELAY_TRAIL_INLETS,
    DELAY_TRAIL_OUTLETS,
    delay_trail_js,
)
from .envelope_display import envelope_display_js
from .eq_band_column import eq_band_column_js
from .eq_curve import eq_curve_js
from .fft_analyzer import (
    FFT_ANALYZER_DEFAULT_OVERLAP,
    FFT_ANALYZER_DEFAULT_SIZE,
    fft_analyzer_dsp,
    fft_analyzer_kernel,
)
from .filter_curve import filter_curve_js
from .grain_display import grain_display_js
from .grid_sequencer_display import grid_sequencer_display_js
from .level_history import (
    LEVEL_HISTORY_INLETS,
    LEVEL_HISTORY_OUTLETS,
    level_history_js,
)
from .lfo_display import lfo_display_js
from .linear_phase_eq_display import linear_phase_eq_display_js
from .peaking_eq_display import peaking_eq_display_js
from .piano_roll import piano_roll_js
from .resonance_bank_display import resonance_bank_display_js
from .sidechain_display import sidechain_display_js
from .slice_overview import slice_overview_js
from .slice_pattern_display import slice_pattern_display_js
from .spectral_display import spectral_display_js
from .spectral_vocoder_display import spectral_vocoder_display_js
from .spectrum_analyzer import spectrum_analyzer_js
from .step_grid_display import step_grid_display_js
from .transfer_curve import (
    TRANSFER_CURVE_INLETS,
    TRANSFER_CURVE_OUTLETS,
    transfer_curve_js,
)
from .velocity_curve_display import velocity_curve_display_js
from .waveform_display import waveform_display_js
from .waveshape_curve import (
    WAVESHAPE_CURVE_INLETS,
    WAVESHAPE_CURVE_OUTLETS,
    waveshape_curve_js,
)
from .wavetable_display import wavetable_display_js
from .wavetable_editor import wavetable_editor_js
from .xy_pad import xy_pad_js
from .xy_trail_display import xy_trail_display_js

__all__ = [
    "filter_curve_js",
    "crossover_display_js",
    "eq_curve_js",
    "eq_band_column_js",
    "fft_analyzer_dsp",
    "fft_analyzer_kernel",
    "transfer_curve_js",
    "TRANSFER_CURVE_INLETS",
    "TRANSFER_CURVE_OUTLETS",
    "waveshape_curve_js",
    "delay_trail_js",
    "DELAY_TRAIL_INLETS",
    "DELAY_TRAIL_OUTLETS",
    "level_history_js",
    "LEVEL_HISTORY_INLETS",
    "LEVEL_HISTORY_OUTLETS",
    "WAVESHAPE_CURVE_INLETS",
    "WAVESHAPE_CURVE_OUTLETS",
    "FFT_ANALYZER_DEFAULT_SIZE",
    "FFT_ANALYZER_DEFAULT_OVERLAP",
    "linear_phase_eq_display_js",
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
    "lfo_display_js",
    "compressor_display_js",
    "xy_trail_display_js",
    "slice_overview_js",
    "slice_pattern_display_js",
]
