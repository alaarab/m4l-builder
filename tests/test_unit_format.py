"""Tests for the shared ES5 unit-style readout formatter (C3)."""

from m4l_builder.engines.unit_format import UNITSTYLE_READOUT_JS, unitstyle_readout_js


def test_accessor_returns_the_constant():
    assert unitstyle_readout_js() == UNITSTYLE_READOUT_JS


def test_is_balanced_es5_function():
    js = unitstyle_readout_js()
    assert js.startswith("function fmtUnit(v, us, dec)")
    assert js.count("{") == js.count("}")
    assert js.count("(") == js.count(")")
    # ES5-safe: no const/let/arrow (jsui/v8ui run ES5)
    assert "const " not in js and "let " not in js and "=>" not in js


def test_covers_every_unitstyle_branch():
    js = unitstyle_readout_js()
    # the premium LCD behaviours, one assertion per unitstyle code
    assert "us === 0" in js                       # INT -> Math.round
    assert '(v / 1000.).toFixed(2) + " s"' in js  # TIME ms -> s rollover
    assert '(v / 1000.).toFixed(2) + " kHz"' in js  # HZ -> kHz rollover
    assert '"-inf dB"' in js                      # DB floor
    assert '(v > 0. ? "+" : "")' in js            # DB / semitone signed
    assert '+ " %"' in js                         # PERCENT
    assert 'if (p === 0) return "C"' in js        # PAN center
    assert '(p < 0 ? "L" : "R")' in js            # PAN L/R
    assert '+ " st"' in js                        # SEMITONE
    assert '"C","C#","D"' in js                   # MIDI note names
    assert "Math.floor(n / 12) - 2" in js         # MIDI octave (60 = C3)
