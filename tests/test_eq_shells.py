"""Tests for shared EQ routing shells."""

from m4l_builder import AudioEffect
from m4l_builder.eq_shells import (
    add_band_message_routers,
    add_selected_band_focus_shell,
    add_selected_band_proxy_shell,
)


def _boxes(device):
    return {entry["box"]["id"]: entry["box"] for entry in device.boxes}


def _line_pairs(device):
    return {
        (
            line["patchline"]["source"][0],
            line["patchline"]["source"][1],
            line["patchline"]["destination"][0],
            line["patchline"]["destination"][1],
        )
        for line in device.lines
    }


class TestSelectedBandFocusShell:
    def test_adds_focus_store_and_graph_route_shell(self):
        device = AudioEffect("T", width=200, height=100)

        add_selected_band_focus_shell(
            device,
            loadbang_id="lb_init",
            focus_control_id="focus_tab",
            graph_source_id="eq_display",
            nav_source_id="band_nav",
            focus_target_ids=["eq_display", "band_nav", "selected_band_column"],
            default_band=2,
            patch_x=30,
            patch_y=40,
        )

        boxes = _boxes(device)
        lines = _line_pairs(device)

        assert boxes["msg_focus_default"]["text"] == "2"
        assert boxes["selected_band_store"]["text"] == "int -1"
        assert boxes["route_graph_events"]["text"] == "route selected_band add_band delete_band"
        assert ("lb_init", 0, "focus_init_delay", 0) in lines
        assert ("route_graph_events", 0, "focus_tab", 0) in lines
        assert ("prepend_focus", 0, "selected_band_column", 0) in lines

    def test_nav_source_is_optional(self):
        device = AudioEffect("T", width=200, height=100)

        add_selected_band_focus_shell(
            device,
            loadbang_id="lb_init",
            focus_control_id="focus_tab",
            graph_source_id="eq_display",
            focus_target_ids=["eq_display", "selected_band_column"],
            default_band=3,
            patch_x=30,
            patch_y=40,
        )

        lines = _line_pairs(device)

        assert ("focus_tab", 0, "selected_band_store", 0) in lines
        assert ("selected_band_store", 0, "prepend_focus", 0) in lines


class TestBandMessageRouters:
    def test_adds_indexed_band_routes_with_multiple_targets(self):
        device = AudioEffect("T", width=200, height=100)

        add_band_message_routers(
            device,
            num_bands=3,
            route_specs=[
                {
                    "name": "freq",
                    "message": "band_freq",
                    "sources": [("eq_display", 1), ("selected_band_column", 0)],
                    "targets": [{"prefix": "freq_b"}, {"prefix": "pak_b", "inlet": 1}],
                    "patch_x": 10,
                    "patch_y": 20,
                }
            ],
        )

        boxes = _boxes(device)
        lines = _line_pairs(device)

        assert boxes["route_freq"]["text"] == "route band_freq"
        assert boxes["route_freq_idx"]["text"] == "route 0 1 2"
        assert ("eq_display", 1, "route_freq", 0) in lines
        assert ("selected_band_column", 0, "route_freq", 0) in lines
        assert ("route_freq_idx", 0, "freq_b0", 0) in lines
        assert ("route_freq_idx", 0, "pak_b0", 1) in lines
        assert ("route_freq_idx", 2, "freq_b2", 0) in lines


class TestSelectedBandProxyShell:
    def test_adds_selected_ui_router_and_control_fanout(self):
        device = AudioEffect("T", width=200, height=100)

        add_selected_band_proxy_shell(
            device,
            num_bands=2,
            source_id="selected_band_column",
            selected_band_store_id="selected_band_store",
            route_fields=[
                {
                    "route_name": "selected_label",
                    "prepend_id": "set_selected_label",
                    "target_id": "selected_band_label",
                    "patch_x": 100,
                },
                {
                    "route_name": "selected_freq",
                    "prepend_id": "set_selected_freq",
                    "target_id": "selected_freq",
                    "patch_x": 180,
                },
            ],
            control_routes=[
                {
                    "control_id": "selected_freq",
                    "pack_text": "pack f i",
                    "target_prefix": "freq_b",
                    "patch_y": 140,
                }
            ],
            patch_x=100,
            patch_y=80,
        )

        boxes = _boxes(device)
        lines = _line_pairs(device)

        assert boxes["route_selected_ui"]["text"] == "route selected_label selected_freq"
        assert boxes["selected_freq_pack"]["text"] == "pack f i"
        assert boxes["selected_freq_swap"]["text"] == "$2 $1"
        assert boxes["selected_freq_route_idx"]["text"] == "route 0 1"
        assert ("selected_band_column", 0, "route_selected_ui", 0) in lines
        assert ("route_selected_ui", 0, "set_selected_label", 0) in lines
        assert ("selected_band_store", 0, "selected_freq_pack", 1) in lines
        assert ("selected_freq_route_idx", 1, "freq_b1", 0) in lines
