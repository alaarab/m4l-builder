"""Integration tests — build all examples and validate the .amxd output.

Each example script is run exactly ONCE per pytest session (via the
session-scoped `built_examples` fixture in conftest.py). Individual tests
read from that cached result dict rather than re-running scripts.
"""

import json
import os
import struct

import pytest

from m4l_builder import (
    BRIDGE_RUNTIME_FILENAME,
    BRIDGE_SCHEMA_FILENAME,
    BRIDGE_SERVER_FILENAME,
)


EXAMPLES_DIR = os.path.join(os.path.dirname(__file__), "..", "examples")
EXAMPLE_SCRIPTS = [
    "simple_gain.py",
    "stereo_filter.py",
    "stereo_utility.py",
    "simple_compressor.py",
    "multiband_imager.py",
    "transient_shaper.py",
    "tape_degradation.py",
    "stereo_delay.py",
    "midside_suite.py",
    "multiband_saturator.py",
    "rhythmic_gate.py",
    "auto_filter.py",
    "comb_bank.py",
    "lofi_processor.py",
    "parametric_eq.py",
    "expression_control.py",
    "macro_randomizer.py",
    "step_sequencer.py",
    "drone_synth.py",
    "reverb.py",
    "midi_transpose.py",
    "midi_velocity.py",
    "xy_filter.py",
    "sidechain_compressor.py",
    "wavetable_synth.py",
    "midi_arpeggiator.py",
    "midi_chord.py",
    "midi_pitch_quantize.py",
    "granular_looper.py",
    "super_slicer.py",
    "fdn_reverb.py",
    "transport_lfo_demo.py",
    "expressive_synth.py",
    "convolution_reverb.py",
    "live_api_demo.py",
    "poly_synth.py",
    "preset_demo.py",
    "hardware_sync.py",
    "morphing_lfo_demo.py",
    "modulation_matrix_demo.py",
    "analog_supersaw.py",
    "probability_gate.py",
    "morphing_filter.py",
    "glue_compressor.py",
    "parallel_compressor.py",
    "livemcp_bridge_demo.py",
]

# Non-AudioEffect scripts
MIDI_EFFECT_SCRIPTS = {
    "expression_control.py", "step_sequencer.py",
    "midi_transpose.py", "midi_velocity.py",
    "midi_arpeggiator.py", "midi_chord.py", "midi_pitch_quantize.py",
    "probability_gate.py",
}
INSTRUMENT_SCRIPTS = {
    "drone_synth.py", "wavetable_synth.py", "granular_looper.py",
    "super_slicer.py",
    "expressive_synth.py", "poly_synth.py", "analog_supersaw.py",
}


def _parse_amxd(path):
    """Parse an .amxd file and return (header_info, patcher_dict)."""
    with open(path, "rb") as f:
        data = f.read()
    magic = data[:4]
    version = struct.unpack_from("<I", data, 4)[0]
    type_code = data[8:12]
    meta_tag = data[12:16]
    meta_len = struct.unpack_from("<I", data, 16)[0]
    ptch_tag = data[24:28]
    json_len = struct.unpack_from("<I", data, 28)[0]
    json_bytes = data[32:]
    json_str = json_bytes.rstrip(b"\x00").rstrip(b"\n").decode("utf-8")
    patcher = json.loads(json_str)

    header = {
        "magic": magic,
        "version": version,
        "type_code": type_code,
        "meta_tag": meta_tag,
        "meta_len": meta_len,
        "ptch_tag": ptch_tag,
        "json_len": json_len,
    }
    return header, patcher


def _get_box_ids(patcher):
    return {b["box"]["id"] for b in patcher["patcher"]["boxes"]}


def _get_box_texts(patcher):
    return {b["box"].get("text", "") for b in patcher["patcher"]["boxes"]}


def _has_patchline(patcher, src_id, src_outlet, dst_id, dst_inlet):
    for line in patcher["patcher"]["lines"]:
        patchline = line["patchline"]
        if (
            patchline["source"] == [src_id, src_outlet]
            and patchline["destination"] == [dst_id, dst_inlet]
        ):
            return True
    return False


class TestExampleBuilds:
    """Every example script should produce a valid .amxd file."""

    @pytest.fixture(autouse=True)
    def _load(self, built_examples):
        self.outputs = {s: r["path"] for s, r in built_examples.items() if r["ok"]}
        self.results = built_examples

    @pytest.mark.parametrize("script", EXAMPLE_SCRIPTS)
    def test_example_runs_successfully(self, script):
        r = self.results.get(script)
        if r is None:
            pytest.skip(f"{script} not found")
        assert r["ok"], f"stderr: {r['stderr']}"

    @pytest.mark.parametrize("script", EXAMPLE_SCRIPTS)
    def test_output_file_exists(self, script):
        if script not in self.outputs:
            pytest.skip(f"{script} did not produce output")
        assert os.path.exists(self.outputs[script])

    @pytest.mark.parametrize("script", EXAMPLE_SCRIPTS)
    def test_ampf_magic_bytes(self, script):
        if script not in self.outputs:
            pytest.skip(f"{script} did not produce output")
        header, _ = _parse_amxd(self.outputs[script])
        assert header["magic"] == b"ampf"

    @pytest.mark.parametrize("script", EXAMPLE_SCRIPTS)
    def test_format_version_is_4(self, script):
        if script not in self.outputs:
            pytest.skip(f"{script} did not produce output")
        header, _ = _parse_amxd(self.outputs[script])
        assert header["version"] == 4

    @pytest.mark.parametrize("script", EXAMPLE_SCRIPTS)
    def test_device_type_code(self, script):
        if script not in self.outputs:
            pytest.skip(f"{script} did not produce output")
        header, _ = _parse_amxd(self.outputs[script])
        if script in MIDI_EFFECT_SCRIPTS:
            assert header["type_code"] == b"mmmm"
        elif script in INSTRUMENT_SCRIPTS:
            assert header["type_code"] == b"iiii"
        else:
            assert header["type_code"] == b"aaaa"

    @pytest.mark.parametrize("script", EXAMPLE_SCRIPTS)
    def test_valid_json_payload(self, script):
        if script not in self.outputs:
            pytest.skip(f"{script} did not produce output")
        _, patcher = _parse_amxd(self.outputs[script])
        assert "patcher" in patcher
        assert "boxes" in patcher["patcher"]
        assert "lines" in patcher["patcher"]

    @pytest.mark.parametrize("script", EXAMPLE_SCRIPTS)
    def test_has_plugin_and_plugout(self, script):
        """Audio effects must have plugin~ and plugout~."""
        if script not in self.outputs:
            pytest.skip(f"{script} did not produce output")
        if script in MIDI_EFFECT_SCRIPTS:
            pytest.skip("MIDI effects don't use plugin~/plugout~")
        _, patcher = _parse_amxd(self.outputs[script])
        texts = _get_box_texts(patcher)
        if script in INSTRUMENT_SCRIPTS:
            assert "plugout~" in texts, "Missing plugout~ object"
        else:
            assert "plugin~" in texts, "Missing plugin~ object"
            assert "plugout~" in texts, "Missing plugout~ object"

    @pytest.mark.parametrize("script", EXAMPLE_SCRIPTS)
    def test_has_presentation_objects(self, script):
        """Should have at least one object with presentation mode."""
        if script not in self.outputs:
            pytest.skip(f"{script} did not produce output")
        _, patcher = _parse_amxd(self.outputs[script])
        has_presentation = any(
            b["box"].get("presentation") == 1
            for b in patcher["patcher"]["boxes"]
        )
        assert has_presentation, "No objects in presentation mode"

    @pytest.mark.parametrize("script", EXAMPLE_SCRIPTS)
    def test_patchlines_reference_existing_boxes(self, script):
        """Every patchline should reference box IDs that exist."""
        if script not in self.outputs:
            pytest.skip(f"{script} did not produce output")
        _, patcher = _parse_amxd(self.outputs[script])
        box_ids = _get_box_ids(patcher)
        for line in patcher["patcher"]["lines"]:
            src_id = line["patchline"]["source"][0]
            dst_id = line["patchline"]["destination"][0]
            assert src_id in box_ids, f"Patchline source {src_id} not in boxes"
            assert dst_id in box_ids, f"Patchline dest {dst_id} not in boxes"

    @pytest.mark.parametrize("script", EXAMPLE_SCRIPTS)
    def test_no_sig_tilde_objects(self, script):
        """sig~ starts at 0.0 on load and causes cold-start silence."""
        if script not in self.outputs:
            pytest.skip(f"{script} did not produce output")
        _, patcher = _parse_amxd(self.outputs[script])
        for b in patcher["patcher"]["boxes"]:
            text = b["box"].get("text", "")
            assert text != "sig~", f"Found sig~ object: {b['box']['id']}"

    @pytest.mark.parametrize("script", EXAMPLE_SCRIPTS)
    def test_no_dcblock_tilde_objects(self, script):
        """dcblock~ doesn't exist in Max 8."""
        if script not in self.outputs:
            pytest.skip(f"{script} did not produce output")
        _, patcher = _parse_amxd(self.outputs[script])
        for b in patcher["patcher"]["boxes"]:
            text = b["box"].get("text", "")
            assert "dcblock~" not in text, f"Found dcblock~ in: {b['box']['id']}"

    @pytest.mark.parametrize("script", EXAMPLE_SCRIPTS)
    def test_panel_has_background_1(self, script):
        """All panel objects must have background:1 to avoid covering UI."""
        if script not in self.outputs:
            pytest.skip(f"{script} did not produce output")
        _, patcher = _parse_amxd(self.outputs[script])
        for b in patcher["patcher"]["boxes"]:
            if b["box"].get("maxclass") == "panel":
                assert b["box"].get("background") == 1, \
                    f"Panel {b['box']['id']} missing background:1"

    @pytest.mark.parametrize("script", EXAMPLE_SCRIPTS)
    def test_selector_has_initial_arg(self, script):
        """All selector~ objects must have an initial arg (not just 'selector~ N')."""
        if script not in self.outputs:
            pytest.skip(f"{script} did not produce output")
        _, patcher = _parse_amxd(self.outputs[script])
        for b in patcher["patcher"]["boxes"]:
            text = b["box"].get("text", "")
            if text.startswith("selector~"):
                parts = text.split()
                assert len(parts) >= 3, \
                    f"selector~ missing initial arg: '{text}' (default 0 = silence)"

    def test_parametric_eq_delete_resets_do_not_reemit_deleted_band_state(self):
        script = "parametric_eq.py"
        if script not in self.outputs:
            pytest.skip(f"{script} did not produce output")
        _, patcher = _parse_amxd(self.outputs[script])
        forbidden_sources = (
            "msg_off_from_graph_b",
            "msg_motion_reset_b",
            "msg_dynamic_reset_b",
            "msg_dynamic_amt_reset_b",
            "msg_motion_rate_reset_b",
            "msg_motion_depth_reset_b",
            "msg_motion_direction_reset_b",
        )
        for line in patcher["patcher"]["lines"]:
            src_id = line["patchline"]["source"][0]
            dst_id = line["patchline"]["destination"][0]
            if src_id.startswith(forbidden_sources):
                assert not dst_id.startswith("pak_b"), (
                    f"Delete reset {src_id} should not feed {dst_id}; "
                    "that re-emits a deleted band back into the EQ graph state."
                )

    @pytest.mark.parametrize("script", EXAMPLE_SCRIPTS)
    def test_minimum_file_size(self, script):
        """Every .amxd should be at least 1KB."""
        if script not in self.outputs:
            pytest.skip(f"{script} did not produce output")
        size = os.path.getsize(self.outputs[script])
        assert size >= 1000, f"File too small: {size} bytes"

    def test_livemcp_bridge_demo_registers_support_files(self):
        script = "livemcp_bridge_demo.py"
        if script not in self.outputs:
            pytest.skip(f"{script} did not produce output")
        _, patcher = _parse_amxd(self.outputs[script])
        deps = {
            dep["name"]
            for dep in patcher["patcher"].get("dependency_cache", [])
        }

        assert BRIDGE_RUNTIME_FILENAME in deps
        assert BRIDGE_SERVER_FILENAME in deps
        assert BRIDGE_SCHEMA_FILENAME in deps

    def test_livemcp_bridge_demo_writes_sidecars(self):
        script = "livemcp_bridge_demo.py"
        if script not in self.outputs:
            pytest.skip(f"{script} did not produce output")
        output_path = self.outputs[script]
        output_dir = os.path.dirname(output_path)

        assert os.path.exists(os.path.join(output_dir, BRIDGE_RUNTIME_FILENAME))
        assert os.path.exists(os.path.join(output_dir, BRIDGE_SERVER_FILENAME))
        assert os.path.exists(os.path.join(output_dir, BRIDGE_SCHEMA_FILENAME))

    def test_super_slicer_uses_midiin_midiparse_for_clip_midi(self):
        script = "super_slicer.py"
        if script not in self.outputs:
            pytest.skip(f"{script} did not produce output")
        _, patcher = _parse_amxd(self.outputs[script])
        texts = _get_box_texts(patcher)

        assert "midiin" in texts
        assert "midiparse" in texts
        assert "notein" not in texts

    def test_super_slicer_retriggers_envelopes_on_main_steps(self):
        script = "super_slicer.py"
        if script not in self.outputs:
            pytest.skip(f"{script} did not produce output")
        _, patcher = _parse_amxd(self.outputs[script])

        assert _has_patchline(patcher, "index_fire_trig", 0, "startloop_msg", 0)

    def test_super_slicer_scales_mix_percent_before_dry_wet_stage(self):
        script = "super_slicer.py"
        if script not in self.outputs:
            pytest.skip(f"{script} did not produce output")
        _, patcher = _parse_amxd(self.outputs[script])
        texts = _get_box_texts(patcher)

        assert "scale 0. 100. 0. 1." in texts
        assert _has_patchline(patcher, "mix_dial", 0, "mix_scale", 0)
        assert _has_patchline(patcher, "mix_scale", 0, "mix_mix_in", 0)

    def test_super_slicer_avoids_parallel_raw_voice_bypass(self):
        script = "super_slicer.py"
        if script not in self.outputs:
            pytest.skip(f"{script} did not produce output")
        _, patcher = _parse_amxd(self.outputs[script])

        assert not _has_patchline(patcher, "groove", 0, "voice_gain_1", 0)
        assert not _has_patchline(patcher, "groove_2", 0, "voice_gain_2", 0)
        assert not _has_patchline(patcher, "groove_3", 0, "voice_gain_3", 0)
        assert not _has_patchline(patcher, "groove_4", 0, "voice_gain_4", 0)

    def test_super_slicer_routes_active_slice_window_to_surface(self):
        script = "super_slicer.py"
        if script not in self.outputs:
            pytest.skip(f"{script} did not produce output")
        _, patcher = _parse_amxd(self.outputs[script])

        assert _has_patchline(patcher, "active_slice_start_norm_expr", 0, "slice_surface", 5)
        assert _has_patchline(patcher, "active_slice_end_norm_expr", 0, "slice_surface", 6)
        assert _has_patchline(patcher, "slice_start_expr", 0, "active_slice_start_norm_expr", 0)
        assert _has_patchline(patcher, "slice_end_expr", 0, "active_slice_end_norm_expr", 0)

    def test_super_slicer_decay_control_scales_with_slice_length(self):
        script = "super_slicer.py"
        if script not in self.outputs:
            pytest.skip(f"{script} did not produce output")
        _, patcher = _parse_amxd(self.outputs[script])
        texts = _get_box_texts(patcher)

        assert "expr max(18.\\, min($f1 * 1.2\\, $f1 * (0.35 + ($f2 / 220.))))" in texts
        assert _has_patchline(patcher, "effective_slice_ms_expr", 0, "env_decay_expr", 0)
        assert _has_patchline(patcher, "decay_dial", 0, "env_decay_expr", 1)
