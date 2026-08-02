"""Compressor transfer curve display engine for jsui.

Generates JavaScript code that renders a compression transfer curve with a
live gain reduction indicator inside Max's jsui object using mgraphics.

Inlets:
    0 -- Threshold in dB (float -60 to 0)
    1 -- Ratio (float 1 to 20)
    2 -- Gain reduction indicator (float 0-1, position riding the curve)
"""

COMPRESSOR_DISPLAY_INLETS = 3
COMPRESSOR_DISPLAY_OUTLETS = 0
