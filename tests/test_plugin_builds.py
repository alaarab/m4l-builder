"""Structural tests for flagship plugin build scripts."""

import importlib.util
import uuid
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


def _load_build_module(relative_path: str):
    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(
        f"test_plugin_{path.stem}_{uuid.uuid4().hex}",
        path,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    with patch("m4l_builder.device.Device.build", return_value=0):
        spec.loader.exec_module(module)
    return module


def _boxes_by_id(device):
    return {box["box"]["id"]: box["box"] for box in device.boxes}


class TestLinearPhaseEqBuild:
    def test_exposes_per_band_parameters_and_disables_selected_proxies(self):
        module = _load_build_module("plugins/linear_phase_eq/build.py")
        boxes = _boxes_by_id(module.device)

        for proxy_id in (
            "selected_freq",
            "selected_gain",
            "selected_q",
            "selected_type",
            "selected_slope",
            "selected_enable",
            "selected_solo",
            "output_gain_compact",
        ):
            assert boxes[proxy_id]["parameter_enable"] == 0

        for i in range(module.NUM_BANDS):
            for prefix in (
                "band_freq_p",
                "band_gain_p",
                "band_q_p",
                "band_type_p",
                "band_enable_p",
                "band_slope_p",
                "band_solo_p",
            ):
                assert boxes[f"{prefix}{i}"]["parameter_enable"] == 1

        assert "route_param_band" in boxes
        assert "route_param_band_idx" in boxes
        assert "band_chip_row" in boxes
        assert "selected_core_rail" in boxes
        assert boxes["lpeq_display"]["maxclass"] == "v8ui"
        assert boxes["selected_band_column"]["presentation_rect"] == [
            module.SELECTED_EDITOR_X + 8,
            module.SELECTED_EDITOR_Y + 8,
            module.SELECTED_EDITOR_W - 16,
            module.SELECTED_EDITOR_H - 16,
        ]

    def test_groups_parameter_banks_by_global_then_band(self):
        module = _load_build_module("plugins/linear_phase_eq/build.py")
        banks = module.device.to_patcher()["patcher"]["parameters"]["parameterbanks"]

        assert banks["0"]["name"] == "Global"
        assert [param["name"] for param in banks["0"]["parameters"]] == [
            "Output Gain",
            "Analyzer",
            "Quality",
            "Collision",
            "Range",
        ]
        assert banks["1"]["name"] == "B1"
        assert [param["name"] for param in banks["1"]["parameters"]] == [
            "Band 1 Enable",
            "Band 1 Freq",
            "Band 1 Gain",
            "Band 1 Q",
            "Band 1 Type",
            "Band 1 Slope",
            "Band 1 Listen",
        ]

    def test_state_js_distinguishes_display_type_from_parameter_type(self):
        module = _load_build_module("plugins/linear_phase_eq/build.py")
        state_js = module.device._support_files[module.STATE_FILENAME]["content"]

        assert "function state_type_from_param(type)" in state_js
        assert '"param_band"' in state_js
        assert 'case "band_type":' in state_js
        assert 'case "context_type":' in state_js
        assert 'set_selected_param("type", args[1], 1);' in state_js


class TestParametricEqBuild:
    def test_keeps_per_band_controls_canonical_and_disables_hidden_duplicates(self):
        module = _load_build_module("plugins/parametric_eq/build.py")
        boxes = _boxes_by_id(module.device)

        assert boxes["out_gain_compact"]["parameter_enable"] == 0
        assert boxes["bypass_compact"]["parameter_enable"] == 0
        assert boxes["out_gain"]["parameter_enable"] == 1
        assert boxes["bypass_toggle"]["parameter_enable"] == 1

        for i in range(module.NUM_BANDS):
            for prefix in (
                "freq_b",
                "gain_b",
                "q_b",
                "type_b",
                "on_b",
                "motion_b",
                "dynamic_b",
                "dynamic_amt_b",
                "motion_rate_b",
                "motion_depth_b",
                "motion_direction_b",
            ):
                assert boxes[f"{prefix}{i}"]["parameter_enable"] == 1

        assert "band_nav" in boxes
        assert "selected_core_rail" not in boxes
        assert boxes["eq_display"]["maxclass"] == "v8ui"
        assert boxes["band_nav"]["presentation_rect"] == [module.HIDDEN_X, 148, 1, 1]
        assert boxes["selected_band_column"]["presentation_rect"] == [
            module.HIDDEN_X,
            148,
            1,
            1,
        ]
        assert boxes["selected_freq"]["presentation_rect"] == [
            module.CORE_X + 4,
            module.CORE_Y + 10,
            module.CORE_W - 8,
            22,
        ]
        assert boxes["selected_gain"]["presentation_rect"] == [
            module.CORE_X + 4,
            module.CORE_Y + 33,
            module.CORE_W - 8,
            22,
        ]
        assert boxes["selected_q"]["presentation_rect"] == [
            module.CORE_X + 4,
            module.CORE_Y + 56,
            module.CORE_W - 8,
            22,
        ]
        assert boxes["selected_type_label"]["presentation_rect"] == [
            module.CORE_X + 6,
            module.CORE_Y + 87,
            module.CORE_W - 12,
            7,
        ]
        assert boxes["selected_type_chip_bg"]["presentation_rect"] == [
            module.CORE_X + 7,
            module.CORE_Y + 86,
            module.CORE_W - 14,
            8,
        ]
        assert boxes["selected_band_label"]["presentation_rect"] == [
            module.CORE_X + 7,
            module.CORE_Y + 95,
            module.CORE_W - 14,
            8,
        ]
        assert boxes["selected_band_chip_bg"]["presentation_rect"] == [
            module.CORE_X + 11,
            module.CORE_Y + 95,
            module.CORE_W - 22,
            8,
        ]
        assert boxes["selected_band_name_sel"]["text"] == "select -1 0 1 2 3 4 5 6 7"
        assert boxes["msg_selected_band_label_0"]["text"] == "-"
        assert boxes["msg_selected_band_label_1"]["text"] == "1"
        assert boxes["msg_selected_band_label_8"]["text"] == "8"
        assert boxes["selected_type_name_route"]["text"] == "route selected_type"
        assert boxes["selected_type_name_sel"]["text"] == "select 0 1 2 3 4 5 6 7"
        assert boxes["selected_type_clear_sel"]["text"] == "select -1"
        assert boxes["selected_type_clear_delay"]["text"] == "del 1"
        assert boxes["msg_selected_type_label_clear"]["text"] == "-"
        assert boxes["msg_selected_type_label_0"]["text"] == "PK"
        assert boxes["msg_selected_type_label_7"]["text"] == "AP"
        assert boxes["analyzer_mode_tab"]["maxclass"] == "live.tab"
        assert boxes["range_tab"]["maxclass"] == "live.tab"
        assert boxes["bypass_toggle"]["text"] == "ON"
        assert boxes["bypass_toggle"]["texton"] == "OFF"
        assert module.GRAPH_W > module.CORE_W * 6
        assert module.GLOBAL_W <= 60
        for suffix in (
            "freq_store_b0",
            "gain_recalc_trig_b0",
            "gain_dbtoa_ctrl_b0",
            "q_recalc_trig_b0",
        ):
            assert suffix in boxes

    def test_starts_with_visible_bands_and_explicit_selected_band_store(self):
        module = _load_build_module("plugins/parametric_eq/build.py")
        boxes = _boxes_by_id(module.device)

        assert module.BAND_DEFAULT_ENABLED == [1, 1, 1, 1, 0, 0, 0, 0]
        assert boxes["msg_focus_default"]["text"] == "0"
        assert boxes["selected_band_store"]["text"] == "int -1"
        assert boxes["on_b0"]["saved_attribute_attributes"]["valueof"]["parameter_initial"] == [1]
        assert boxes["on_b4"]["saved_attribute_attributes"]["valueof"]["parameter_initial"] == [0]

    def test_groups_parameter_banks_by_global_core_and_motion(self):
        module = _load_build_module("plugins/parametric_eq/build.py")
        banks = module.device.to_patcher()["patcher"]["parameters"]["parameterbanks"]

        assert banks["0"]["name"] == "Global"
        assert [param["name"] for param in banks["0"]["parameters"]] == [
            "Out Gain",
            "Bypass",
            "Analyzer Mode",
            "Display Range",
            "Focus Band",
        ]
        assert banks["1"]["name"] == "B1 Core"
        assert [param["name"] for param in banks["1"]["parameters"]] == [
            "Freq B1",
            "Gain B1",
            "Q B1",
            "Type B1",
            "On B1",
            "Motion B1",
            "Dynamic B1",
            "Dynamic Amt B1",
        ]
        assert banks["9"]["name"] == "B1 Motion"
        assert [param["name"] for param in banks["9"]["parameters"]] == [
            "Motion Rate B1",
            "Motion Depth B1",
            "Motion Direction B1",
        ]
