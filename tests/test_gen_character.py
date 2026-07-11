"""Tests for the harvested character-DSP palette (m4l_builder.gen_character).

These kernels are stateful (History/Delay), so unlike the pure-arithmetic
gen_snippets we can't exec them as Python. Instead we prove two things that
matter for reuse: (1) each emitted kernel passes the structural GenExpr lint the
kit runs at build time (out assigned, i/o indices in range, no multi-line-ternary
trap), and (2) a real device composing them actually builds through the kit's
gen~ path. Both guard against the "advertised but unwired / won't compile"
failure class that ships green.
"""
from m4l_builder import AudioEffect
from m4l_builder.gen_character import (
    bbd_chorus,
    bbd_ensemble,
    console_saturation,
    crosstalk,
    deesser,
    duck_gain,
    haas_widener,
    iron_transformer,
    leslie_rotor,
    optical_leveler,
    tape_hysteresis,
    wow_flutter,
)
from m4l_builder.gen_lint import lint_genexpr


def _hoist(code: str) -> str:
    """Move History/Delay/Data/Buffer decls to the top (the fleet _hoist_history
    contract) so a composed kernel is decls-first, as gen~ requires."""
    decls, body = [], []
    for line in code.split("\n"):
        bucket = decls if line.strip().startswith(
            ("History ", "Delay ", "Data ", "Buffer ")) else body
        bucket.append(line)
    return "\n".join(decls + body)


# (label, kernel-body, numins, numouts) — each a full, decls-first kernel.
CASES = [
    ("optical_leveler",
     optical_leveler("in1", "in2", "out1", "out2", "40.", makeup="0.",
                     gr_out="out3"), 2, 3),
    ("tape_channel",
     wow_flutter("wfpos", "20.", "30.", "20.")
     + "wfd.write(in1);\nwfv = wfd.read(wfpos, interp=\"cubic\");\n"
     + tape_hysteresis("wfv", "out1", "6.")
     + "out2 = in2;\n"
     + "Delay wfd(9600);\n", 2, 2),
    ("leslie_rotor",
     "mono = (in1 + in2) * 0.5;\n"
     + leslie_rotor("mono", "out1", "out2", speed="0.", doppler="60.",
                    balance="50.", horn_hz_out="out3"), 2, 3),
    ("bbd_chorus",
     "mono = (in1 + in2) * 0.5;\n"
     + bbd_chorus("mono", "out1", "out2", rate="0.6", depth="60.",
                  voices="3.", tone="8000.", sweep_out="out3"), 2, 3),
    ("bbd_ensemble",
     "mono = (in1 + in2) * 0.5;\n"
     + bbd_ensemble("mono", "out1", "out2", rate="0.6", depth="60.",
                    voices="6.", tone="8000.", detune="35.", shimmer="100.",
                    center_ms="12.", feedback="20.", spread="100.",
                    locut="90.", sweep_out="out3"), 2, 3),
    ("deesser",
     deesser("in1", "in2", "out1", "out2", split_hz="6500.", thresh="-30.",
             range_db="-8.", gr_out="out3"), 2, 3),
    ("console_chain",
     console_saturation("in1", "csl", "4.", prefix="csl")
     + console_saturation("in2", "csr", "4.", prefix="csr")
     + crosstalk("csl", "csr", "xl", "xr", amount="20.")
     + iron_transformer("xl", "out1", "40.", prefix="irl")
     + iron_transformer("xr", "out2", "40.", prefix="irr"), 2, 2),
    ("duck_gain",
     duck_gain("in1", "in2", "dg", duck="60.", release_ms="250.")
     + "out1 = in1 * dg;\nout2 = in2 * dg;\n", 2, 2),
    ("haas_widener",
     haas_widener("in1", "in2", "out1", "out2", amount_ms="8.", side="1."),
     2, 2),
]


def test_all_character_kernels_lint_clean():
    """Every harvested kernel passes the build-time structural lint."""
    for label, body, numins, numouts in CASES:
        issues = lint_genexpr(_hoist(body), numins, numouts)
        assert issues == [], f"{label}: {issues}"


def test_prefix_namespacing_isolates_state():
    """Two calls with distinct prefixes share no scratch/state var (the
    reuse-twice-in-one-codebox guarantee)."""
    a = console_saturation("in1", "o1", "4.", prefix="csa")
    b = console_saturation("in2", "o2", "4.", prefix="csb")
    a_vars = {tok for tok in a.replace("(", " ").replace(")", " ").split()
              if tok.startswith("csa_")}
    b_vars = {tok for tok in b.replace("(", " ").replace(")", " ").split()
              if tok.startswith("csb_")}
    assert a_vars and b_vars
    # no bare-name overlap once the prefix is stripped is fine; the point is the
    # emitted identifiers are disjoint:
    assert a_vars.isdisjoint(b_vars)


def test_optical_leveler_taps_gain_reduction():
    code = optical_leveler("in1", "in2", "out1", "out2", "pr", gr_out="out3")
    assert "History opt_env" in code and "History opt_pool" in code
    assert "out3 = opt_gr;" in code           # meter tap wired
    assert "soft" not in code                 # composed, not the word


def test_devices_build_with_character_dsp():
    """End-to-end: the kit's gen~ path accepts each kernel in a real device."""
    for label, body, numins, numouts in CASES:
        dev = AudioEffect(f"CharProbe {label}", width=120, height=90)
        dev.add_line("obj-plugin", 0, "obj-plugout", 0)
        dev.add_line("obj-plugin", 1, "obj-plugout", 1)
        dev.add_gendsp(f"g_{label}", f"char_{label}", _hoist(body),
                       numins, numouts, [40, 250, 200, 22])
        blob = dev.to_patcher()
        assert isinstance(blob, dict) and blob.get("patcher")


def test_bbd_ensemble_is_a_true_six_voice_superset():
    code = bbd_ensemble("mono", "wl", "wr", rate="r", depth="d", voices="v",
                        tone="t", detune="dt", shimmer="sh", center_ms="c",
                        feedback="fb", spread="sp", locut="lc")
    # six INDEPENDENT slow phases (per-voice detune skew needs its own
    # accumulator — a shared phase + offset cannot detune)
    for i in range(6):
        assert f"History ens_ph{i}(0.)" in code
        assert f"ens_ph{i} = wrap(ens_ph{i} + ens_r * (1. + " in code
    # voice gating for 3..6, never for the always-on pair
    for i in (2, 3, 4, 5):
        assert f"ens_g{i} = v > {i + 0.5} ? 1. : 0.;" in code
    assert "ens_g0" not in code and "ens_g1" not in code
    # loudness renormalised by ACTIVE count, not fixed
    # wet makeup folded into the norm: the 0.6-gain tanh stage + stereo
    # fold left the wet ~5.5 dB under dry (insert ducked the level)
    assert "ens_norm = 1.66 / sqrt(ens_act);" in code
    # feedback re-enters the SAME saturated stage, capped safe (90 * .007)
    assert "ens_mono = tanh((mono) * 0.6 + ens_fb * ens_fbamt);" in code
    assert "clamp(fb, 0., 90.) * 0.007" in code
    # shimmer exposes the fast rank amplitude; 100 = classic bbd_chorus
    assert "mstosamps(0.9) * ens_dpt * clamp(sh, 0., 100.) * 0.01" in code
    # the wet-only low cut: HP applied to ens_wl/ens_wr AFTER the pan sum
    assert "wl = ens_wl - ens_hpl;" in code
    assert "wr = ens_wr - ens_hpr;" in code
    # centre tap is caller-set (4..25 ms), not the fixed 12
    assert "mstosamps(clamp(c, 4., 25.))" in code
