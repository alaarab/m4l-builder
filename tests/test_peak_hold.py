import math

import pytest

from m4l_builder.gen_sim import simulate
from m4l_builder.gen_snippets import peak_hold


@pytest.mark.parametrize("reference_rate", [44100.0, 48000.0])
@pytest.mark.parametrize("samplerate", [44100, 48000, 96000, 192000])
def test_peak_hold_duration_and_attack(reference_rate, samplerate):
    code = "History held(0);\n" + peak_hold("in1", "held", reference_rate=reference_rate)
    code += "\nout1 = held;"
    frames = samplerate // 10
    result = simulate(code, inputs=[1.0] + [0.0] * frames + [2.0],
                      samplerate=samplerate)["out1"]
    assert result[0] == 1.0
    assert result[frames] == pytest.approx(0.99997 ** (reference_rate * 0.1), abs=1e-11)
    assert result[-1] == 2.0


@pytest.mark.parametrize("coefficient", [0, 1, -1, math.nan, math.inf])
def test_peak_hold_rejects_invalid_decay(coefficient):
    with pytest.raises(ValueError, match="coefficient"):
        peak_hold("in1", "held", coefficient=coefficient)


@pytest.mark.parametrize("rate", [0, -1, math.nan, math.inf])
def test_peak_hold_rejects_invalid_reference_rate(rate):
    with pytest.raises(ValueError, match="reference_rate"):
        peak_hold("in1", "held", reference_rate=rate)
