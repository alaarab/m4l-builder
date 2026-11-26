"""Offline render of a device's audio path (m4l_builder.render).

The renderer's job is to catch, without Live, the failure where a broken gen~
device passes its input through untouched. Expected values are computed from
the input with plain arithmetic, never by the renderer under test.
"""

import math
import struct
from pathlib import Path

import pytest

from m4l_builder import AudioEffect
from m4l_builder.cli import run_build_script
from m4l_builder.dsp import gen_codebox
from m4l_builder.gen_snippets import ms_width_equal_power
from m4l_builder.render import (
    Render,
    RenderError,
    audit,
    check_not_dry,
    generate_signal,
    read_wav,
    render,
    summarize,
    write_wav,
)

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"

# ms_width_equal_power: width 0 = mono, 0.5 = unchanged, 1 = all side.
WIDTH_KERNEL = "Param width(0.5);\n" + ms_width_equal_power("in1", "in2", "out1", "out2", "width")


def _gen_device(code: str = WIDTH_KERNEL, *, external: bool = False, bind: bool = True,
                lint: bool = True) -> AudioEffect:
    device = AudioEffect("Gen Width", 120, 100)
    device.add_dial("w", "Width", [10, 10, 40, 40], min_val=0.0, max_val=1.0, initial=0.5)
    if external:
        device.add_gendsp("core", "width", code, 2, 2, [100, 100, 200, 22], lint=lint)
    else:
        device.embed_gendsp("core", code, 2, 2, [100, 100, 200, 22], lint=lint)
    if bind:
        device.bind_gen_param("w", "core", "width", id="bind")
    device.add_line("obj-plugin", 0, "core", 0)
    device.add_line("obj-plugin", 1, "core", 1)
    device.add_line("core", 0, "obj-plugout", 0)
    device.add_line("core", 1, "obj-plugout", 1)
    return device


def _close(a, b, tol=1e-9):
    return len(a) == len(b) and all(abs(x - y) <= tol for x, y in zip(a, b, strict=True))


# -- example 03 ---------------------------------------------------------- #

def test_example_03_width_renders_mono_unity_and_double_side():
    device = run_build_script(EXAMPLES / "03_stereo_width.py", lambda _d, _p: None,
                              quiet=True)[0].device
    mono = render(device, "noise", params={"wid_width": 0.0}, seconds=0.05)
    left, right = mono.input
    mid = [(a + b) / 2 for a, b in zip(left, right, strict=True)]
    assert _close(mono.output[0], mid) and _close(mono.output[1], mid)

    unity = render(device, "noise", params={"wid_width": 1.0}, seconds=0.05)
    assert _close(unity.output[0], left) and _close(unity.output[1], right)

    wide = render(device, "noise", params={"wid_width": 2.0}, seconds=0.05)
    side_in = [a - b for a, b in zip(left, right, strict=True)]
    side_out = [a - b for a, b in zip(*wide.output, strict=True)]
    assert _close(side_out, [2 * s for s in side_in])
    assert any("held at its target" in note for note in wide.notes)


# -- gen~ devices and the dry-passthrough failure ------------------------- #

def test_working_gen_device_passes_the_audit():
    report = audit(_gen_device(), engaged={"Width": 1.0}, bypass={"Width": 0.5})
    assert report, str(report)


# What Live runs when a gen~ codebox fails to compile: the input, untouched.
PASSTHROUGH = "Param width(0.5);\nout1 = in1;\nout2 = in2;"
BLOWS_UP_AT_FULL_SCALE = ("Param width(0.5);\n"
                          "out1 = in1 > 0.99 ? in1 * 1e308 * 10. : in1 * 0.5;\nout2 = in2 * 0.5;")
DC_OFFSET = "Param width(0.5);\nout1 = in1 * 0.5 + 0.01;\nout2 = in2 * 0.5;"


@pytest.mark.parametrize("device, failing", [
    (lambda: _gen_device(PASSTHROUGH, lint=False), {"not dry (engaged)"}),
    (lambda: _gen_device(bind=False), {"not dry (engaged)"}),
    (lambda: _gen_device(BLOWS_UP_AT_FULL_SCALE), {"finite (full-scale noise)",
                                                    "finite (full-scale sine)",
                                                    "finite (full-scale impulse)"}),
    (lambda: _gen_device(DC_OFFSET), {"silent (silence in)"}),
], ids=["kernel-passes-dry", "param-not-wired", "blows-up", "dc-offset"])
def test_audit_catches_a_broken_device(device, failing):
    report = audit(device(), engaged={"Width": 1.0})
    assert {check.name for check in report.failures} == failing, str(report)


def test_unwired_parameter_is_reported():
    result = render(_gen_device(bind=False), "noise", params={"Width": 1.0}, seconds=0.02)
    assert not check_not_dry(result)
    assert any("'Width' does not reach the audio path" in note for note in result.notes)


def test_gen_param_set_directly_wins_over_the_bound_control():
    device = _gen_device()
    via_dial = render(device, "noise", params={"Width": 0.0}, seconds=0.02)
    direct = render(device, "noise", params={"Width": 0.0, "core.width": 0.5}, seconds=0.02)
    assert _close(via_dial.output[0], via_dial.output[1])           # mono
    assert _close(direct.output[0], direct.input[0])                 # unity
    with pytest.raises(RenderError, match="unknown parameter 'Depth'.*Width, core.width"):
        render(device, "noise", params={"Depth": 1.0}, seconds=0.01)


def test_built_and_frozen_amxd_render_the_same_as_the_device(tmp_path):
    device = _gen_device(external=True)
    expected = render(device, "noise", params={"Width": 0.0}, seconds=0.02).output
    loose = tmp_path / "loose" / "Gen Width.amxd"
    frozen = tmp_path / "frozen" / "Gen Width.amxd"
    device.build(str(loose))
    device.build(str(frozen), freeze=True)
    assert [p.suffix for p in frozen.parent.iterdir()] == [".amxd"]
    for path in (loose, frozen):
        assert render(path, "noise", params={"Width": 0.0}, seconds=0.02).output == expected

    for sidecar in loose.parent.glob("*.gendsp"):
        sidecar.unlink()
    with pytest.raises(RenderError, match=r"box 'core'.*\.gendsp was not found"):
        render(loose, "noise", seconds=0.02)


def _with_box(add) -> AudioEffect:
    device = AudioEffect("Odd", 100, 100)
    first = add(device)
    device.add_line("obj-plugin", 0, first, 0)
    device.add_line(first, 0, "obj-plugout", 0)
    device.add_line(first, 0, "obj-plugout", 1)
    return device


@pytest.mark.parametrize("add, message", [
    (lambda d: d.add_newobj("smooth", "slide~ 10 10", numinlets=3, numoutlets=1,
                            outlettype=["signal"]),
     r"box 'smooth' \[slide~ 10 10\]: not an object the renderer can run"),
    (lambda d: d.add_dsp(*gen_codebox("flat", "out1 = in1 * 0.5;")) or "flat_gen",
     r"box 'flat_gen' \[gen~\]: has a flat `code` attribute.*passes the audio through dry"),
    (lambda d: d.embed_gendsp("tbl", 'Buffer b("tbl");\nout1 = in1 * peek(b, 0);', 1, 1,
                              [0, 0, 80, 20]),
     r"box 'tbl' \[gen~\]: gen_sim cannot run its codebox: .*'Buffer'"),
], ids=["msp-object", "flat-code-gen", "buffer-kernel"])
def test_anything_the_renderer_cannot_run_raises_naming_the_box(add, message):
    with pytest.raises(RenderError, match=message):
        render(_with_box(add), "noise", seconds=0.01)


def test_a_wired_cold_inlet_on_a_bare_pack_is_refused():
    device = AudioEffect("Ramp", 100, 100)
    device.add_dial("g", "Gain", [10, 10, 40, 40], min_val=0.0, max_val=1.0, initial=0.5)
    device.add_newobj("ms", "loadmess 50", numinlets=1, numoutlets=1)
    device.add_newobj("pk", "pack", numinlets=2, numoutlets=1)
    device.add_newobj("ln", "line~", numinlets=2, numoutlets=2, outlettype=["signal", "bang"])
    device.add_newobj("vca", "*~", numinlets=2, numoutlets=1, outlettype=["signal"])
    device.add_line("g", 0, "pk", 0)
    device.add_line("ms", 0, "pk", 1)
    device.add_line("pk", 0, "ln", 0)
    device.add_line("ln", 0, "vca", 1)
    device.add_line("obj-plugin", 0, "vca", 0)
    device.add_line("vca", 0, "obj-plugout", 0)
    with pytest.raises(RenderError, match=r"box 'pk' \[pack\]: control inlet 1 is wired"):
        render(device, "noise", seconds=0.01)


def test_feedback_without_a_delay_is_refused():
    device = AudioEffect("Loop", 100, 100)
    device.add_newobj("a", "+~", numinlets=2, numoutlets=1, outlettype=["signal"])
    device.add_newobj("b", "*~ 0.5", numinlets=2, numoutlets=1, outlettype=["signal"])
    device.add_line("obj-plugin", 0, "a", 0)
    device.add_line("a", 0, "b", 0)
    device.add_line("b", 0, "a", 1)
    device.add_line("a", 0, "obj-plugout", 0)
    with pytest.raises(RenderError, match="feedback loop without a delay: a -> b -> a"):
        render(device, "noise", seconds=0.01)


def test_approximate_gen_constructs_are_noted_or_refused():
    dither = "Param width(0.5);\nout1 = in1 + noise() * 1e-5;\nout2 = in2;"
    result = render(_gen_device(dither), "noise", seconds=0.01)
    assert any("noise()" in note for note in result.notes)
    # gen noise() must be independent of the generated input noise
    added = [o - i for o, i in zip(result.output[0], result.input[0], strict=True)]
    dot = sum(a * b for a, b in zip(added, result.input[0], strict=True))
    norms = math.sqrt(sum(a * a for a in added) * sum(b * b for b in result.input[0]))
    assert abs(dot / norms) < 0.3
    with pytest.raises(RenderError, match="strict"):
        render(_gen_device(dither), "noise", seconds=0.01, strict=True)


def test_a_nan_output_is_not_reported_as_dry():
    result = Render("x", 48000.0, [[0.5, -0.5]], [[float("nan"), float("nan")]])
    check = check_not_dry(result)
    assert check and "2 NaN/Inf" in check.detail


# -- signals, WAV files and the summary ----------------------------------- #

def test_wav_round_trip_and_clipping(tmp_path):
    sig = [[0.5, -0.25, 1.5, float("nan")], [0.0, 0.125, -2.0, float("-inf")]]
    for bits, tol in ((16, 1 / 32768), (24, 1 / 8388608)):
        path = tmp_path / f"x{bits}.wav"
        assert write_wav(path, sig, 44100, bits=bits) == 4   # 1.5, -2.0, NaN, -inf
        channels, rate = read_wav(path)
        assert rate == 44100
        assert _close(channels[0], [0.5, -0.25, 1 - 1 / 2 ** (bits - 1), 0.0], tol)
        assert _close(channels[1], [0.0, 0.125, -1.0, -1.0], tol)


FLOAT_GUID = b"\x03\x00\x00\x00\x00\x00\x10\x00\x80\x00\x00\xaa\x00\x38\x9b\x71"


@pytest.mark.parametrize("fmt", [
    struct.pack("<HHIIHH", 3, 2, 48000, 48000 * 8, 8, 32),
    struct.pack("<HHIIHHHHI", 0xFFFE, 2, 48000, 48000 * 8, 8, 32, 22, 32, 3) + FLOAT_GUID,
], ids=["ieee-float", "extensible-float"])
def test_reads_32_bit_float_wav(tmp_path, fmt):
    samples = [0.5, -0.5, 0.25, -1.25]   # interleaved stereo, one over full scale
    data = struct.pack("<4f", *samples)
    riff = (b"WAVE" + b"fmt " + struct.pack("<I", len(fmt)) + fmt
            + b"data" + struct.pack("<I", len(data)) + data)
    path = tmp_path / "float.wav"
    path.write_bytes(b"RIFF" + struct.pack("<I", len(riff)) + riff)
    assert read_wav(path) == ([[0.5, 0.25], [-0.5, -1.25]], 48000)


def test_mono_wav_feeds_both_channels(tmp_path):
    path = tmp_path / "mono.wav"
    write_wav(path, [[0.5, -0.5, 0.25]], 48000)
    device = run_build_script(EXAMPLES / "03_stereo_width.py", lambda _d, _p: None,
                              quiet=True)[0].device
    result = render(device, path, params={"wid_width": 2.0})
    assert result.output[0] == result.output[1] == pytest.approx([0.5, -0.5, 0.25], abs=1e-6)


def test_summary_levels_and_bands_of_a_full_scale_sine():
    sine = generate_signal("sine", seconds=0.5, samplerate=48000, channels=1,
                           level_db=0.0, freq=1000.0)
    row = summarize(sine, 48000)[0]
    assert row["rms_db"] == pytest.approx(20 * math.log10(math.sqrt(0.5)), abs=0.01)
    assert row["peak_db"] == pytest.approx(0.0, abs=0.01)
    assert row["bands_db"]["500-2k Hz"] == pytest.approx(-3.01, abs=0.05)
    others = [v for name, v in row["bands_db"].items() if name != "500-2k Hz"]
    assert max(others) < -40.0
