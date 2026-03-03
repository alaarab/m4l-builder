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

__all__ = [
    "filter_curve_js",
    "eq_curve_js",
    "envelope_display_js",
    "spectrum_analyzer_js",
    "waveform_display_js",
]
