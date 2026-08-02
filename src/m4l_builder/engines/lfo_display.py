"""LFO waveform display engine for jsui.

Generates JavaScript code that renders a live LFO waveform shape with a
sweeping playhead inside Max's jsui object using mgraphics.

Inlets:
    0 -- Shape index (int 0-4: sine, triangle, square, sawtooth, ramp)
    1 -- Phase position (float 0-1, sweeping playhead)
    2 -- Depth (float 0-1, amplitude scale)
"""

LFO_DISPLAY_INLETS = 3
LFO_DISPLAY_OUTLETS = 0
