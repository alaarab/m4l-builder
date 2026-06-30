"""Shared ES5 unit-style readout formatter (C3).

ONE premium value formatter for the jspainter controls (C1) and the
custom_knob/readout JS to share, so every control prints ms / Hz / dB / % / Pan /
semitone / MIDI the way Live's native LCD does — kHz and s roll-over, signed dB
with a ``-inf`` floor, L/C/R pan, ``+``/``-`` semitones, note names — instead of a
dumb ``value.toFixed(decimals) + unit``.

The ``unitstyle`` codes match :mod:`m4l_builder.constants` ``UNITSTYLE_*`` (Live's
``live.dial`` enum): 0 int, 1 float, 2 time(ms), 3 Hz, 4 dB, 5 %, 6 pan,
7 semitone, 8 MIDI note, 9 custom, 10 native.
"""

from __future__ import annotations

# ES5 (jsui/v8ui-safe). Include once, then call ``fmtUnit(value, unitstyle, dec)``.
UNITSTYLE_READOUT_JS = r"""function fmtUnit(v, us, dec) {
    if (dec === undefined) dec = 1;
    if (us === 0) return "" + Math.round(v);                 // INT
    if (us === 2) {                                          // TIME (ms -> s)
        if (Math.abs(v) >= 1000.) return (v / 1000.).toFixed(2) + " s";
        return v.toFixed(dec) + " ms";
    }
    if (us === 3) {                                          // HZ (-> kHz)
        if (Math.abs(v) >= 1000.) return (v / 1000.).toFixed(2) + " kHz";
        return v.toFixed(dec) + " Hz";
    }
    if (us === 4) {                                          // DB (signed, -inf)
        if (v <= -70.) return "-inf dB";
        return (v > 0. ? "+" : "") + v.toFixed(dec) + " dB";
    }
    if (us === 5) return v.toFixed(dec) + " %";              // PERCENT
    if (us === 6) {                                          // PAN (L/C/R)
        var p = Math.round(v);
        if (p === 0) return "C";
        return Math.abs(p) + (p < 0 ? "L" : "R");
    }
    if (us === 7) return (v > 0. ? "+" : "") + Math.round(v) + " st";  // SEMITONE
    if (us === 8) {                                          // MIDI (60 = C3)
        var names = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"];
        var n = Math.round(v);
        return names[((n % 12) + 12) % 12] + (Math.floor(n / 12) - 2);
    }
    return v.toFixed(dec);                                   // FLOAT / CUSTOM / NATIVE
}"""


def unitstyle_readout_js() -> str:
    """Return the shared ES5 ``fmtUnit(value, unitstyle, dec)`` formatter — the
    premium LCD-style value formatter (kHz/s roll-over, signed dB with a ``-inf``
    floor, L/C/R pan, ``+``/``-`` semitones, MIDI note names). ``unitstyle`` codes
    match :mod:`m4l_builder.constants` ``UNITSTYLE_*``. Include the string once in a
    jsui/v8ui painter, then call ``fmtUnit(v, us, dec)``.
    """
    return UNITSTYLE_READOUT_JS
