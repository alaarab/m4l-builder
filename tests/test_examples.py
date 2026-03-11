"""Integration tests — build all examples and validate the .amxd output.

Each example script is run exactly ONCE per pytest session (via the
session-scoped `built_examples` fixture in conftest.py). Individual tests
read from that cached result dict rather than re-running scripts.
"""

import json
import os
import struct

import pytest


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
    "linear_phase_eq.py",
    "linear_phase_splitter.py",
    "sidechain_eq_compressor.py",
    "ducking_delay.py",
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

    @pytest.mark.parametrize("script", EXAMPLE_SCRIPTS)
    def test_minimum_file_size(self, script):
        """Every .amxd should be at least 1KB."""
        if script not in self.outputs:
            pytest.skip(f"{script} did not produce output")
        size = os.path.getsize(self.outputs[script])
        assert size >= 1000, f"File too small: {size} bytes"


class TestLinearPhaseEqExample:
    @pytest.fixture(autouse=True)
    def _load(self, built_examples):
        result = built_examples.get("linear_phase_eq.py")
        if result is None or not result["ok"] or not result["path"]:
            pytest.skip("linear_phase_eq.py did not build successfully in built_examples")
        self.path = result["path"]
        self.output_dir = os.path.dirname(self.path)
        _, self.patcher = _parse_amxd(self.path)

    def test_writes_sidecar_support_files(self):
        expected = [
            "linear_phase_eq_state_v2.js",
            "linear_phase_eq_chips_v2.js",
            "linear_phase_eq_short_core.maxpat",
            "linear_phase_eq_medium_core.maxpat",
            "linear_phase_eq_high_core.maxpat",
            "lpeq_eqcurve_display_v2.js",
        ]
        for filename in expected:
            assert os.path.exists(os.path.join(self.output_dir, filename)), filename

        deps = {d["name"] for d in self.patcher["patcher"]["dependency_cache"]}
        for filename in expected:
            assert filename in deps

    def test_contains_major_ui_regions(self):
        ids = _get_box_ids(self.patcher)
        for required in {
            "lpeq_display",
            "lpeq_spectroscope",
            "band_chip_row",
            "quality_tab",
            "analyzer_tab",
            "range_tab",
            "collision_tab",
            "selected_type",
            "selected_freq",
            "selected_gain",
            "selected_q",
            "selected_slope",
            "selected_enable",
            "selected_solo",
            "state_js",
        }:
            assert required in ids

    def test_excludes_placeholder_controls(self):
        texts = " ".join(_get_box_texts(self.patcher))
        assert "AUTO GAIN" not in texts
        assert "M/S" not in texts
        assert "L/R" not in texts

    def test_uses_listen_style_solo_workflow(self):
        state_js_path = os.path.join(self.output_dir, "linear_phase_eq_state_v2.js")
        with open(state_js_path, encoding="utf-8") as f:
            state_js = f.read()

        assert "function audition_mask_db_at" in state_js
        assert "Listen isolates the marked band region" in state_js

        selected_solo = next(
            b["box"] for b in self.patcher["patcher"]["boxes"]
            if b["box"]["id"] == "selected_solo"
        )
        selected_enable = next(
            b["box"] for b in self.patcher["patcher"]["boxes"]
            if b["box"]["id"] == "selected_enable"
        )
        spectroscope = next(
            b["box"] for b in self.patcher["patcher"]["boxes"]
            if b["box"]["id"] == "lpeq_spectroscope"
        )
        overlay_group = next(
            b["box"] for b in self.patcher["patcher"]["boxes"]
            if b["box"]["id"] == "lpeq_overlay_spec_group"
        )
        assert selected_solo["texton"] == "LISTEN"
        assert selected_solo["text"] == "LISTEN"
        assert selected_enable["texton"] == "ON"
        assert selected_enable["text"] == "BYP"
        assert spectroscope["maxclass"] == "spectroscope~"
        assert spectroscope["background"] == 1
        assert spectroscope["ignoreclick"] == 1
        assert spectroscope["logfreq"] == 1
        assert spectroscope["interval"] == 20
        assert spectroscope["scroll"] == 0
        assert spectroscope["sono"] == 0
        assert spectroscope["logamp"] == 1
        assert spectroscope["domain"] == [20.0, 20000.0]
        assert spectroscope["fgcolor"][3] >= 0.60
        assert spectroscope["presentation"] == 1
        assert spectroscope["presentation_rect"] == [12, 10, 728, 130]
        assert overlay_group["text"] == "zl.group 40"

        analyzer_tab = next(
            b["box"] for b in self.patcher["patcher"]["boxes"]
            if b["box"]["id"] == "analyzer_tab"
        )
        analyzer_post = next(
            b["box"] for b in self.patcher["patcher"]["boxes"]
            if b["box"]["id"] == "msg_analyzer_post"
        )
        assert analyzer_tab["saved_attribute_attributes"]["valueof"]["parameter_initial"] == [2]
        assert analyzer_post["text"] == "2"

    def test_chart_owns_band_creation_and_chip_row_has_no_add_button(self):
        chips_js_path = os.path.join(self.output_dir, "linear_phase_eq_chips_v2.js")
        display_js_path = os.path.join(self.output_dir, "lpeq_eqcurve_display_v2.js")
        state_js_path = os.path.join(self.output_dir, "linear_phase_eq_state_v2.js")

        with open(chips_js_path, encoding="utf-8") as f:
            chips_js = f.read()
        with open(display_js_path, encoding="utf-8") as f:
            display_js = f.read()
        with open(state_js_path, encoding="utf-8") as f:
            state_js = f.read()

        assert "+ ADD BAND" not in chips_js
        assert "Click empty graph" in display_js
        assert "function draw_nodes()" in display_js
        assert "function set_display_range(v)" in display_js
        assert "function set_analyzer_enabled(v)" in display_js
        assert '"add_band"' in display_js
        assert '"delete_band"' in display_js
        assert "var analyzer_display = [];" in display_js
        assert "function display_type_for_band(type)" in state_js
        assert "function state_type_from_display(type)" in state_js

    def test_quality_switch_only_flushes_other_buffers_when_dirty(self):
        state_js_path = os.path.join(self.output_dir, "linear_phase_eq_state_v2.js")
        with open(state_js_path, encoding="utf-8") as f:
            state_js = f.read()

        quality_section = state_js.split("function set_quality(idx) {", 1)[1].split(
            "function set_sample_rate(v) {", 1
        )[0]
        assert "if (response_tables_dirty) rebuild_response_tables();" in quality_section
        assert "response_tables_dirty = 1;" in state_js

    def test_default_state_starts_with_four_flat_bands_and_no_selection(self):
        state_js_path = os.path.join(self.output_dir, "linear_phase_eq_state_v2.js")
        with open(state_js_path, encoding="utf-8") as f:
            state_js = f.read()

        assert "var DEFAULT_FREQS = [30.0, 200.0, 1000.0, 5000.0" in state_js
        assert "var DEFAULT_TYPES = [TYPE_LOSHELF, TYPE_PEAK, TYPE_PEAK, TYPE_HISHELF" in state_js
        assert "var DEFAULT_ENABLED = [1, 1, 1, 1, 0, 0, 0, 0];" in state_js
        assert "selected_band = -1;" in state_js
        assert "Select a node or click the graph to add one." in state_js

    def test_layout_prioritizes_graph_width_over_rails(self):
        boxes = {b["box"]["id"]: b["box"] for b in self.patcher["patcher"]["boxes"]}
        hero = boxes["hero_frame"]
        display = boxes["lpeq_display"]
        chips = boxes["band_chip_row"]
        selected_type = boxes["selected_type"]

        assert display["maxclass"] == "jsui"
        assert hero["presentation_rect"][2] >= 730
        assert hero["presentation_rect"][3] >= 135
        assert display["presentation_rect"][2] >= 720
        assert display["presentation_rect"][3] >= 129
        assert display["presentation_rect"][0] <= 14
        assert chips["presentation_rect"][2] <= 140
        assert selected_type["presentation_rect"][0] >= 900
