"""Tests for the high-level Device API (device.py)."""

import json
import os

from m4l_builder.device import (
    AudioEffect,
    Device,
    Instrument,
    MidiEffect,
    MidiTransformation,
)
from m4l_builder.theme import MIDNIGHT, WARM


def _parse_amxd_json(data: bytes) -> dict:
    """Extract and parse the JSON payload from an .amxd binary."""
    json_payload = data[32:].rstrip(b"\x00").rstrip(b"\n").decode("utf-8")
    return json.loads(json_payload)


class TestDevice:
    """Tests for the Device base class."""

    def _make(self, **kwargs):
        defaults = dict(name="TestDevice", width=400, height=168,
                        device_type="audio_effect")
        defaults.update(kwargs)
        return Device(**defaults)

    def test_init_name(self):
        d = self._make(name="MyDevice")
        assert d.name == "MyDevice"

    def test_init_width(self):
        d = self._make(width=600)
        assert d.width == 600

    def test_init_height(self):
        d = self._make(height=200)
        assert d.height == 200

    def test_init_device_type(self):
        d = self._make(device_type="midi_effect")
        assert d.device_type == "midi_effect"

    def test_add_compiled_ui_spectroscope(self):
        # The compiled-UI helper: layer a built-in C++ Max UI object (here a
        # spectroscope~) in presentation, with object attrs merged in and an
        # optional signal feed wired to inlet 0. Generalised from Parametric EQ
        # V2's "compiled spectrum behind a transparent jsui" pattern.
        d = self._make()
        d.add_newobj("sig_src", "selector~ 2 1", numinlets=3, numoutlets=1,
                     outlettype=["signal"], patching_rect=[0, 0, 80, 20])
        d.add_compiled_ui(
            "spec", "spectroscope~", [10, 20, 300, 100],
            varname="spec", outlettype=["signal"],
            attrs={"sono": 0, "logfreq": 1, "domain": [10.0, 22000.0],
                   "fgcolor": [0.6, 0.6, 0.6, 0.8], "bgcolor": [0.0, 0.0, 0.0, 0.0]},
            signal_src=("sig_src", 0),
        )
        boxes = {b["box"]["id"]: b["box"] for b in d.boxes}
        assert "spec" in boxes
        spec = boxes["spec"]
        assert spec["maxclass"] == "spectroscope~"
        assert spec["presentation"] == 1
        assert spec["presentation_rect"] == [10, 20, 300, 100]
        assert spec["patching_rect"] == [10, 20, 300, 100]   # defaults to presentation rect
        assert spec["varname"] == "spec"
        assert spec["logfreq"] == 1 and spec["domain"] == [10.0, 22000.0]  # attrs merged
        lines = {
            (ln["patchline"]["source"][0], ln["patchline"]["source"][1],
             ln["patchline"]["destination"][0], ln["patchline"]["destination"][1])
            for ln in d.lines
        }
        assert ("sig_src", 0, "spec", 0) in lines   # signal feed wired to inlet 0

    def _compiled_lines(self, d):
        return {
            (ln["patchline"]["source"][0], ln["patchline"]["source"][1],
             ln["patchline"]["destination"][0], ln["patchline"]["destination"][1])
            for ln in d.lines
        }

    def test_add_compiled_ui_multi_signal_feeds(self):
        # A LIST of feeds wires successive inlets — the scope~ X-Y goniometer
        # pattern (Mid -> inlet 0, Side -> inlet 1). The old single-tuple form
        # only ever reached inlet 0, silently dropping inlet 1.
        d = self._make()
        d.add_newobj("mid", "+~ 0.", numinlets=2, numoutlets=1, outlettype=["signal"])
        d.add_newobj("side", "-~ 0.", numinlets=2, numoutlets=1, outlettype=["signal"])
        d.add_compiled_ui(
            "gonio", "scope~", [10, 20, 200, 200], numinlets=2,
            signal_src=[("mid", 0), ("side", 0)],
        )
        lines = self._compiled_lines(d)
        assert ("mid", 0, "gonio", 0) in lines
        assert ("side", 0, "gonio", 1) in lines

    def test_add_compiled_ui_explicit_inlet_triples(self):
        d = self._make()
        d.add_newobj("a", "sig~ 0", numinlets=1, numoutlets=1, outlettype=["signal"])
        d.add_compiled_ui(
            "obj", "scope~", [0, 0, 100, 100], numinlets=3,
            signal_src=[("a", 0, 2)],
        )
        assert ("a", 0, "obj", 2) in self._compiled_lines(d)

    def test_add_compiled_ui_gate_inserts_selector(self):
        # gate_src routes the primary feed through a selector~ 1 1: live signal on
        # inlet 1, the toggle on the control inlet, gated output to the object.
        d = self._make()
        d.add_newobj("src", "selector~ 2 1", numinlets=3, numoutlets=1,
                     outlettype=["signal"])
        d.add_live_text("an_tog", "Tog", [0, 0, 40, 16], mode=1)
        d.add_compiled_ui(
            "spec", "spectroscope~", [10, 20, 300, 100],
            signal_src=("src", 0), gate_src=("an_tog", 0),
        )
        boxes = {b["box"]["id"]: b["box"] for b in d.boxes}
        assert boxes["spec_gate"]["text"] == "selector~ 1 1"
        lines = self._compiled_lines(d)
        assert ("src", 0, "spec_gate", 1) in lines      # live signal -> selector inlet 1
        assert ("an_tog", 0, "spec_gate", 0) in lines   # toggle -> control inlet
        assert ("spec_gate", 0, "spec", 0) in lines     # gated signal -> object
        assert ("src", 0, "spec", 0) not in lines       # NOT wired directly

    def test_add_compiled_ui_no_gate_byte_identical(self):
        # Default (no gate_src) keeps the direct inlet-0 wire — existing devices
        # must stay byte-identical.
        d = self._make()
        d.add_newobj("src", "sig~ 0", numinlets=1, numoutlets=1, outlettype=["signal"])
        d.add_compiled_ui("spec", "spectroscope~", [0, 0, 100, 50], signal_src=("src", 0))
        ids = {b["box"]["id"] for b in d.boxes}
        assert "spec_gate" not in ids
        assert ("src", 0, "spec", 0) in self._compiled_lines(d)

    def test_add_compiled_display_layers_overlay_in_front(self):
        # The keystone recipe: compiled box added BEFORE the transparent overlay
        # (so it sits behind), overlay rect = full, compiled rect = inset.
        d = self._make()
        d.add_newobj("src", "sig~ 0", numinlets=1, numoutlets=1, outlettype=["signal"])
        overlay_js = (
            "function paint(){} function init(){} function redraw(){}\n"
            "var mgraphics = {}; sketch;"
        )
        compiled, overlay = d.add_compiled_display(
            "disp", "spectroscope~", [0, 0, 300, 120],
            overlay_js=overlay_js, overlay_filename="disp_ov_v1.js",
            attrs={"sono": 0}, signal_src=("src", 0),
            inset=(20, 6, 8, 12), validate_contract=False,
        )
        ids = [b["box"]["id"] for b in d.boxes]
        assert ids.index("disp_scope") < ids.index("disp")   # compiled is behind
        boxes = {b["box"]["id"]: b["box"] for b in d.boxes}
        assert boxes["disp_scope"]["presentation_rect"] == [20, 6, 300 - 28, 120 - 18]
        assert boxes["disp"]["presentation_rect"] == [0, 0, 300, 120]
        assert boxes["disp"]["bgcolor"] == [0.0, 0.0, 0.0, 0.0]   # transparent overlay
        assert ("src", 0, "disp_scope", 0) in self._compiled_lines(d)

    def test_theme_compiled_display_kwargs(self):
        sk = MIDNIGHT.scope_kwargs()
        assert sk["bgcolor"][3] == 1.0          # scope~ needs an opaque bg
        assert sk["fgcolor"] == list(MIDNIGHT.scope_color)
        spk = MIDNIGHT.spectrum_kwargs()
        assert spk["logfreq"] == 1 and spk["logamp"] == 1
        assert MIDNIGHT.spectrum_kwargs(transparent_bg=True)["bgcolor"] == [0.0, 0.0, 0.0, 0.0]
        fk = MIDNIGHT.filtergraph_kwargs()
        assert "bgcolor" in fk and "gridcolor" in fk

    def test_add_compiled_ui_theme_under_explicit_attrs(self):
        # theme supplies maxclass-appropriate color DEFAULTS; explicit attrs win.
        d = self._make(theme=MIDNIGHT)
        d.add_newobj("src", "sig~ 0", numinlets=1, numoutlets=1, outlettype=["signal"])
        d.add_compiled_ui(
            "spec", "spectroscope~", [0, 0, 100, 50],
            attrs={"sono": 1, "fgcolor": [1.0, 0.0, 0.0, 1.0]},
            theme=MIDNIGHT, signal_src=("src", 0),
        )
        spec = {b["box"]["id"]: b["box"] for b in d.boxes}["spec"]
        assert spec["logfreq"] == 1 and spec["logamp"] == 1   # from theme
        assert spec["fgcolor"] == [1.0, 0.0, 0.0, 1.0]        # explicit wins
        assert spec["sono"] == 1

    def test_add_filtergraph_and_plot_device_widgets(self):
        d = self._make(theme=MIDNIGHT)
        d.add_filtergraph("fg", [0, 0, 100, 60])
        d.add_plot("pl", [0, 60, 100, 60])
        boxes = {b["box"]["id"]: b["box"] for b in d.boxes}
        assert boxes["fg"]["maxclass"] == "filtergraph~"
        assert boxes["pl"]["maxclass"] == "plot~"
        assert boxes["fg"]["bgcolor"] == list(MIDNIGHT.scope_bgcolor)   # theme injected

    def test_init_empty_boxes(self):
        d = self._make()
        assert d.boxes == []

    def test_init_empty_lines(self):
        d = self._make()
        assert d.lines == []

    def test_add_box_appends(self):
        d = self._make()
        box = {"box": {"id": "obj-1", "maxclass": "newobj"}}
        d.add_box(box)
        assert len(d.boxes) == 1

    def test_add_box_returns_id(self):
        d = self._make()
        box = {"box": {"id": "obj-42", "maxclass": "newobj"}}
        returned_id = d.add_box(box)
        assert returned_id == "obj-42"

    def test_add_box_stores_exact_dict(self):
        d = self._make()
        box = {"box": {"id": "obj-1", "maxclass": "newobj"}}
        d.add_box(box)
        assert d.boxes[0] is box

    def test_add_line_appends(self):
        d = self._make()
        d.add_line("obj-1", 0, "obj-2", 0)
        assert len(d.lines) == 1

    def test_add_line_patchline_structure(self):
        d = self._make()
        d.add_line("obj-src", 1, "obj-dst", 2)
        line = d.lines[0]
        assert "patchline" in line
        assert line["patchline"]["source"] == ["obj-src", 1]
        assert line["patchline"]["destination"] == ["obj-dst", 2]

    def test_add_support_file_stores_metadata(self):
        d = self._make()
        returned = d.add_support_file("kernel.maxpat", '{"patcher": {}}',
                                      file_type="JSON")
        assert returned == "kernel.maxpat"
        assert d._support_files["kernel.maxpat"]["content"] == '{"patcher": {}}'
        assert d._support_files["kernel.maxpat"]["type"] == "JSON"

    def _height_codes(self, d):
        return [i.code for i in d.lint() if i.code == "device-height-over-ceiling"]

    def test_tall_chain_device_lints_height_ceiling_warning(self):
        # an audio_effect taller than Live's ~168px view clips its bottom rows
        d = self._make(height=190)
        codes = self._height_codes(d)
        assert codes == ["device-height-over-ceiling"]
        issue = next(i for i in d.lint() if i.code == "device-height-over-ceiling")
        assert issue.severity == "warning"          # NOT an error (a default build stays quiet)

    def test_at_or_below_ceiling_no_height_warning(self):
        assert self._height_codes(self._make(height=168)) == []
        assert self._height_codes(self._make(height=120)) == []

    def test_allow_tall_opts_out_of_height_warning(self):
        # a faithful clone of a taller original (SEAR=190) suppresses the rule
        d = AudioEffect("Clone", width=280, height=190, allow_tall=True)
        assert self._height_codes(d) == []

    def test_midi_tool_exempt_from_height_ceiling(self):
        # MIDI Tools render in a different UI, not the 168px device chain row
        d = MidiTransformation("Tool", width=300, height=300)
        assert self._height_codes(d) == []

    def test_default_build_does_not_raise_on_tall_device(self):
        # height is a WARNING, not a wiring error -> validate=None build is silent
        d = self._make(height=190)
        d.to_bytes()                                # must not raise

    def test_validate_warn_surfaces_height_ceiling(self):
        import warnings as _w
        d = self._make(height=190)
        with _w.catch_warnings(record=True) as caught:
            _w.simplefilter("always")
            d.to_bytes(validate="warn")
        assert any("device-height-over-ceiling" in str(w.message) for w in caught)

    def _clip_ids(self, d):
        return {i.box_id for i in d.lint() if i.code == "control-clipped"}

    def test_control_straddling_bottom_edge_is_flagged(self):
        # a 168-tall device with a dial at y=150,h=30 → bottom 180, half-cut
        d = self._make(height=168)
        d.add_dial("k", "Knob", [10, 150, 40, 30])
        assert "k" in self._clip_ids(d)

    def test_control_past_right_edge_is_flagged(self):
        d = self._make(width=300, height=168)
        d.add_dial("k", "Knob", [280, 60, 40, 30])   # right = 320 > 300
        assert "k" in self._clip_ids(d)

    def test_control_fully_inside_not_flagged(self):
        d = self._make(width=300, height=168)
        d.add_dial("k", "Knob", [10, 60, 40, 30])
        assert self._clip_ids(d) == set()

    def test_parked_offcanvas_control_not_flagged(self):
        # the corpus idiom: a functional dial parked far off-canvas to hide it
        d = self._make(width=300, height=168)
        d.add_dial("probe", "Probe", [900, 900, 40, 30])
        assert self._clip_ids(d) == set()

    def test_full_bleed_background_panel_not_flagged(self):
        # a background panel routinely bleeds past the bottom edge by design
        d = self._make(width=300, height=168)
        d.add_panel("bg", [0, 0, 300, 188], bgcolor=[0, 0, 0, 1])   # bottom 188 > 168
        assert self._clip_ids(d) == set()

    def test_add_v8ui_content_address_hashes_js_into_filename(self):
        js = "function paint(){ mgraphics.init(); }\nfunction onpointermove(){}\n"
        d = self._make()
        d.add_v8ui("k", [0, 0, 40, 40], js_code=js, js_filename="k_knob.js",
                   content_address=True, validate_contract=False)
        names = [n for n in d._js_files if n.startswith("k_knob_")]
        assert len(names) == 1 and names[0].endswith(".js")
        # the v8ui box references the SAME hashed sidecar (no desync)
        box = {b["box"]["id"]: b["box"] for b in d.boxes}["k"]
        assert box["filename"] == names[0]
        # editing the JS changes the hashed filename (auto cache-bust)
        d2 = self._make()
        d2.add_v8ui("k", [0, 0, 40, 40], js_code=js + "// edit\n", js_filename="k_knob.js",
                    content_address=True, validate_contract=False)
        n2 = next(n for n in d2._js_files if n.startswith("k_knob_"))
        assert n2 != names[0]

    def test_add_v8ui_without_content_address_keeps_filename(self):
        d = self._make()
        d.add_v8ui("k", [0, 0, 40, 40], js_code="function paint(){ mgraphics.init(); }",
                   js_filename="stable.js", validate_contract=False)
        assert "stable.js" in d._js_files          # exact name preserved (default off)

    def test_add_gendsp_registers_content_addressed_file_and_wires_gen(self):
        d = self._make()
        code = "out1 = in1; out2 = in2;"
        ref = d.add_gendsp("core", "heat_core", code, 2, 2, [80, 240, 200, 22])
        # exactly one support file, registered under a <stem>_<hash>.gendsp name
        names = [n for n in d._support_files if n.startswith("heat_core_")]
        assert len(names) == 1
        fname = names[0]
        assert fname.endswith(".gendsp")
        # the gen~ object references the SAME stem (no desync possible)
        box = {b["box"]["id"]: b["box"] for b in d.boxes}[ref.id]
        assert box["text"] == f"gen~ {fname[:-len('.gendsp')]}"
        assert box["numinlets"] == 2 and box["numoutlets"] == 2
        assert box["outlettype"] == ["signal", "signal"]
        assert box["patching_rect"] == [80, 240, 200, 22]
        # the file body is the full serialized gen patcher
        assert json.loads(d._support_files[fname]["content"])["patcher"]["classnamespace"] == "dsp.gen"

    def test_add_gendsp_recompiles_on_code_change_without_manual_bump(self):
        # editing the DSP renames the support file AND the gen~ ref together — the
        # whole point: Max sees a new filename and recompiles fresh (no _vNN bump).
        d1 = self._make()
        r1 = d1.add_gendsp("core", "k", "out1 = in1 * 0.5; out2 = in2;", 2, 2, [0, 0, 200, 22])
        d2 = self._make()
        r2 = d2.add_gendsp("core", "k", "out1 = in1 * 0.6; out2 = in2;", 2, 2, [0, 0, 200, 22])
        f1 = next(n for n in d1._support_files if n.startswith("k_"))
        f2 = next(n for n in d2._support_files if n.startswith("k_"))
        assert f1 != f2                                       # new code -> new filename
        t1 = {b["box"]["id"]: b["box"] for b in d1.boxes}[r1.id]["text"]
        t2 = {b["box"]["id"]: b["box"] for b in d2.boxes}[r2.id]["text"]
        assert t1 != t2                                       # gen~ ref tracks it

    def test_add_panel_returns_id(self):
        d = self._make()
        returned_id = d.add_panel("panel-bg", [0, 0, 400, 170],
                                  bgcolor=[0.1, 0.1, 0.1, 1.0])
        assert returned_id == "panel-bg"

    def test_add_panel_appends_box(self):
        d = self._make()
        d.add_panel("panel-bg", [0, 0, 400, 170], bgcolor=[0.1, 0.1, 0.1, 1.0])
        assert len(d.boxes) == 1
        assert d.boxes[0]["box"]["id"] == "panel-bg"

    def test_add_panel_maxclass(self):
        d = self._make()
        d.add_panel("p1", [0, 0, 200, 100], bgcolor=[0, 0, 0, 1])
        assert d.boxes[0]["box"]["maxclass"] == "panel"

    def test_add_dial_returns_id(self):
        d = self._make()
        returned_id = d.add_dial("dial-gain", "Gain", [10, 10, 40, 40])
        assert returned_id == "dial-gain"

    def test_add_dial_appends_box(self):
        d = self._make()
        d.add_dial("dial-gain", "Gain", [10, 10, 40, 40])
        assert len(d.boxes) == 1
        assert d.boxes[0]["box"]["maxclass"] == "live.dial"

    def test_add_dial_varname(self):
        d = self._make()
        d.add_dial("d1", "MyParam", [0, 0, 40, 40])
        assert d.boxes[0]["box"]["varname"] == "MyParam"

    def test_add_tab_returns_id(self):
        d = self._make()
        returned_id = d.add_tab("tab-mode", "Mode", [0, 0, 120, 24],
                                options=["A", "B", "C"])
        assert returned_id == "tab-mode"

    def test_add_tab_appends_box(self):
        d = self._make()
        d.add_tab("t1", "Mode", [0, 0, 120, 24], options=["X", "Y"])
        assert len(d.boxes) == 1
        assert d.boxes[0]["box"]["maxclass"] == "live.tab"

    def test_add_tab_options_stored(self):
        d = self._make()
        d.add_tab("t1", "Mode", [0, 0, 120, 24], options=["Low", "Mid", "High"])
        attrs = d.boxes[0]["box"]["saved_attribute_attributes"]["valueof"]
        assert attrs["parameter_enum"] == ["Low", "Mid", "High"]

    def test_add_toggle_returns_id(self):
        d = self._make()
        returned_id = d.add_toggle("tog-bypass", "Bypass", [0, 0, 24, 24])
        assert returned_id == "tog-bypass"

    def test_add_toggle_appends_box(self):
        d = self._make()
        d.add_toggle("tog-bypass", "Bypass", [0, 0, 24, 24])
        assert len(d.boxes) == 1
        assert d.boxes[0]["box"]["maxclass"] == "live.toggle"

    def test_add_comment_returns_id(self):
        d = self._make()
        returned_id = d.add_comment("lbl-1", [0, 0, 80, 16], "Hello")
        assert returned_id == "lbl-1"

    def test_add_comment_appends_box(self):
        d = self._make()
        d.add_comment("lbl-1", [0, 0, 80, 16], "Hello")
        assert len(d.boxes) == 1
        assert d.boxes[0]["box"]["maxclass"] == "live.comment"

    def test_add_comment_text(self):
        d = self._make()
        d.add_comment("lbl-1", [0, 0, 80, 16], "Label Text")
        assert d.boxes[0]["box"]["text"] == "Label Text"

    def test_add_scope_returns_id(self):
        d = self._make()
        returned_id = d.add_scope("scope-1", [0, 0, 120, 60])
        assert returned_id == "scope-1"

    def test_add_scope_appends_box(self):
        d = self._make()
        d.add_scope("scope-1", [0, 0, 120, 60])
        assert len(d.boxes) == 1
        assert d.boxes[0]["box"]["maxclass"] == "live.scope~"

    def test_add_meter_returns_id(self):
        d = self._make()
        returned_id = d.add_meter("meter-1", [0, 0, 20, 100])
        assert returned_id == "meter-1"

    def test_add_meter_appends_box(self):
        d = self._make()
        d.add_meter("meter-1", [0, 0, 20, 100])
        assert len(d.boxes) == 1
        assert d.boxes[0]["box"]["maxclass"] == "live.meter~"

    def test_add_meter_with_theme_injects_colors(self):
        d = Device("Test", 200, 100, device_type="audio_effect", theme=MIDNIGHT)
        d.add_meter("m1", [0, 0, 20, 100])
        box = d.boxes[0]["box"]
        assert box["coldcolor"] == MIDNIGHT.meter_cold
        assert box["warmcolor"] == MIDNIGHT.meter_warm
        assert box["hotcolor"] == MIDNIGHT.meter_hot
        assert box["overloadcolor"] == MIDNIGHT.meter_over
        # slidercolor = the recessed background rail (live.gain~ maxref); corpus sets it
        # dark (~surface), so the channel matches the panel, not Live-default grey.
        assert box["slidercolor"] == MIDNIGHT.surface

    def test_add_meter_without_theme_no_color_injection(self):
        d = self._make()
        d.add_meter("m1", [0, 0, 20, 100])
        box = d.boxes[0]["box"]
        assert "coldcolor" not in box
        assert "warmcolor" not in box
        assert "hotcolor" not in box
        assert "overloadcolor" not in box

    def test_add_meter_explicit_color_overrides_theme(self):
        custom = [0.0, 1.0, 0.0, 1.0]
        d = Device("Test", 200, 100, device_type="audio_effect", theme=WARM)
        d.add_meter("m1", [0, 0, 20, 100], coldcolor=custom)
        box = d.boxes[0]["box"]
        assert box["coldcolor"] == custom
        assert box["warmcolor"] == WARM.meter_warm

    def test_add_live_line_themes_linecolor(self):
        # live.line divider: only linecolor; theme it to the subtle panel border.
        d = Device("Test", 200, 120, device_type="audio_effect", theme=MIDNIGHT)
        d.add_live_line("ln1", [0, 0, 174, 6])
        box = d.boxes[0]["box"]
        assert box["linecolor"] == MIDNIGHT.panel_border

    def test_add_live_text_themes_and_mirrors_active_twins(self):
        # live.text colors must mirror to active* (active=1 is the visible state).
        d = Device("Test", 200, 120, device_type="audio_effect", theme=MIDNIGHT)
        d.add_live_text("t1", "Bypass", [0, 0, 40, 15])
        box = d.boxes[0]["box"]
        assert box["bgcolor"] == MIDNIGHT.surface
        assert box["activebgcolor"] == MIDNIGHT.surface       # mirrored
        assert box["bgoncolor"] == MIDNIGHT.accent
        assert box["activebgoncolor"] == MIDNIGHT.accent      # mirrored
        assert box["activetextcolor"] == MIDNIGHT.text        # mirrored

    def test_add_slider_themes_bare_slidercolor_not_active(self):
        # live.slider has NO activeslidercolor — its fill is the bare slidercolor.
        d = Device("Test", 200, 120, device_type="audio_effect", theme=MIDNIGHT)
        d.add_slider("s1", "Level", [0, 0, 18, 80])
        box = d.boxes[0]["box"]
        assert box["slidercolor"] == MIDNIGHT.dial_color
        assert "activeslidercolor" not in box

    def test_add_number_box_themes_active_slidercolor(self):
        # live.numbox DOES have activeslidercolor (follows the active* rule).
        d = Device("Test", 200, 120, device_type="audio_effect", theme=MIDNIGHT)
        d.add_number_box("n1", "Num", [0, 0, 44, 15])
        box = d.boxes[0]["box"]
        assert box["activeslidercolor"] == MIDNIGHT.dial_color

    def test_add_lcd_numbox_themes_lcd_colors(self):
        # appearance=4 LCD numbox auto-themes its lcd colors from the theme.
        d = Device("Test", 200, 120, device_type="audio_effect", theme=MIDNIGHT)
        d.add_number_box("n1", "Freq", [0, 0, 44, 15], appearance=4)
        box = d.boxes[0]["box"]
        assert box["appearance"] == 4
        assert box["lcdcolor"] == MIDNIGHT.lcd_on
        assert box["lcdbgcolor"] == MIDNIGHT.lcd_bg
        assert box["inactivelcdcolor"] == MIDNIGHT.lcd_off

    def test_add_dial_with_theme_themes_ring_needle_and_triangle(self):
        # The reset-triangle marker (tricolor) is now themed to the needle color
        # so it isn't an off-theme Live-default dot on every knob.
        d = Device("Test", 200, 120, device_type="audio_effect", theme=MIDNIGHT)
        d.add_dial("k1", "Amount", [0, 0, 44, 47])
        box = d.boxes[0]["box"]
        assert box["activedialcolor"] == MIDNIGHT.dial_color
        assert box["activeneedlecolor"] == MIDNIGHT.needle_color
        assert box["tricolor"] == MIDNIGHT.needle_color

    def test_add_live_gain_with_theme_injects_meter_and_handle_colors(self):
        # Meter segments use the BARE attrs (inverted rule); the drag-triangle
        # handle (tricolor/trioncolor) themes to the accent so it isn't Live-grey.
        d = Device("Test", 200, 120, device_type="audio_effect", theme=MIDNIGHT)
        d.add_live_gain("lg1", "Output", [0, 0, 30, 100])
        box = d.boxes[0]["box"]
        assert box["coldcolor"] == MIDNIGHT.meter_cold
        assert box["overloadcolor"] == MIDNIGHT.meter_over
        assert box["tricolor"] == MIDNIGHT.dial_color
        assert box["trioncolor"] == MIDNIGHT.dial_color

    def test_add_bpatcher_module_embeds_presentation_subpatch(self):
        from m4l_builder.subpatcher import Subpatcher
        sub = Subpatcher("dsp_mod")
        sub.add_newobj("in0", "inlet", numinlets=0, numoutlets=1)
        sub.add_newobj("gain", "*~ 0.5", numinlets=2, numoutlets=1)
        d = self._make()
        d.add_bpatcher_module(sub, "bp1", [0, 0, 174, 167], name="dsp.maxpat",
                              numinlets=2, numoutlets=2, outlettype=["signal", "signal"])
        box = d.boxes[-1]["box"]
        assert box["maxclass"] == "bpatcher"
        assert box["embed"] == 1
        assert box["presentation"] == 1
        assert box["presentation_rect"] == [0, 0, 174, 167]
        assert box["viewvisibility"] == 1
        assert box["name"] == "dsp.maxpat"
        assert box["outlettype"] == ["signal", "signal"]
        # the embedded sub-patch is in presentation mode and carries its boxes
        assert box["patcher"]["openinpresentation"] == 1
        assert len(box["patcher"]["boxes"]) == 2

    def test_add_theme_bus_distributor_and_receivers(self):
        d = self._make()
        d.add_newobj("mydial", "live.dial", numinlets=1, numoutlets=1)
        res = d.add_theme_bus(
            [("lcd_control_fg", "activedialcolor", "dialcol"),
             ("lcd_bg", "bgcolor", "bgcol")],
            targets={"dialcol": ["mydial"]},
        )
        texts = {b["box"].get("text") for b in d.boxes if b["box"].get("text")}
        # ONE shared live.thisdevice + live.colors distributor
        assert "live.thisdevice" in texts and "live.colors" in texts
        # per-spec broadcast (route + prepend + send), and the control's receiver
        assert "s ---dialcol" in texts and "s ---bgcol" in texts
        assert "prepend activedialcolor" in texts
        assert "r ---dialcol" in texts
        # the receiver is wired into the control
        pairs = {
            (ln["patchline"]["source"][0], ln["patchline"]["destination"][0])
            for ln in d.lines
        }
        assert any(s.startswith("ltheme_rxdialcol") and dst == "mydial"
                   for s, dst in pairs)
        # the follow-live flag + the returned bus names
        assert d.theme_follow_live is True
        assert res["buses"] == ["dialcol", "bgcol"]

    def test_add_theme_bus_no_targets_is_just_the_distributor(self):
        d = self._make()
        res = d.add_theme_bus([("surface_bg", "bgcolor", "bg")], follow_live=False)
        texts = {b["box"].get("text") for b in d.boxes if b["box"].get("text")}
        assert "live.colors" in texts and "s ---bg" in texts
        assert "r ---bg" not in texts          # no receivers without targets
        assert d.theme_follow_live is False
        assert res["colors"] == "ltheme_colors"

    def test_paint_control_sets_jspainterfile_and_bundles_asset(self):
        from m4l_builder.engines.painters import lcd_panel_painter_js
        d = self._make()
        d.add_dial("vol", "Volume", [10, 10, 40, 40])
        js = lcd_panel_painter_js(40, 40, bg=[0.1, 0.12, 0.1, 1.0],
                                  border=[0.3, 0.8, 0.84, 1.0])
        ret = d.paint_control("vol", "lcd_vol.js", painter_js=js)
        assert ret == "lcd_vol.js"
        # the native control keeps parameter storage; the .js only paints it
        box = next(b["box"] for b in d.boxes if b["box"]["id"] == "vol")
        assert box["jspainterfile"] == "lcd_vol.js"
        assert box["parameter_enable"] == 1
        # the painter is bundled as a TEXT sidecar asset
        asset = d.asset("lcd_vol.js")
        assert asset is not None and asset.asset_type == "TEXT"
        assert "function paint()" in asset.content

    def test_paint_control_unknown_box_raises(self):
        import pytest
        d = self._make()
        with pytest.raises(KeyError):
            d.paint_control("nope", "x.js")

    def test_paint_control_without_js_only_sets_attr(self):
        d = self._make()
        d.add_dial("cut", "Cutoff", [0, 0, 40, 40])
        d.paint_control("cut", "shared_painter.js")   # asset bundled elsewhere
        box = next(b["box"] for b in d.boxes if b["box"]["id"] == "cut")
        assert box["jspainterfile"] == "shared_painter.js"
        assert d.asset("shared_painter.js") is None

    def test_add_init_ring_deferred_staged_broadcast(self):
        d = self._make()
        res = d.add_init_ring(stages=("dspInit", "uiInit", "startBang"))
        texts = {b["box"].get("text") for b in d.boxes if b["box"].get("text")}
        # live.thisdevice -> deferlow -> t b b b -> one ---<stage> send each
        assert "live.thisdevice" in texts
        assert "deferlow" in texts
        assert "t b b b" in texts
        assert "s ---dspInit" in texts and "s ---startBang" in texts
        pairs = {
            (ln["patchline"]["source"][0], ln["patchline"]["source"][1],
             ln["patchline"]["destination"][0])
            for ln in d.lines
        }
        assert ("initring_thisdev", 0, "initring_defer") in pairs
        # stages[0] (dspInit, s0) hangs off the RIGHTMOST t outlet (fires first)
        assert ("initring_seq", 2, "initring_s0") in pairs
        assert ("initring_seq", 0, "initring_s2") in pairs
        assert res["stages"] == ["dspInit", "uiInit", "startBang"]

    def test_add_init_ring_without_defer_skips_deferlow(self):
        d = self._make()
        res = d.add_init_ring(stages=("go",), defer=False)
        texts = {b["box"].get("text") for b in d.boxes if b["box"].get("text")}
        assert "deferlow" not in texts
        assert "s ---go" in texts
        assert res["deferlow"] is None

    def test_add_newobj_returns_id(self):
        d = self._make()
        returned_id = d.add_newobj("obj-1", "gain~", numinlets=2, numoutlets=1)
        assert returned_id == "obj-1"

    def test_add_newobj_appends_box(self):
        d = self._make()
        d.add_newobj("obj-1", "gain~", numinlets=2, numoutlets=1)
        assert len(d.boxes) == 1
        assert d.boxes[0]["box"]["maxclass"] == "newobj"

    def test_add_newobj_text(self):
        d = self._make()
        d.add_newobj("obj-1", "gain~", numinlets=2, numoutlets=1)
        assert d.boxes[0]["box"]["text"] == "gain~"

    def test_add_newobj_numinlets_numoutlets(self):
        d = self._make()
        d.add_newobj("obj-1", "gain~", numinlets=3, numoutlets=2)
        box = d.boxes[0]["box"]
        assert box["numinlets"] == 3
        assert box["numoutlets"] == 2

    def test_to_patcher_returns_dict(self):
        d = self._make()
        result = d.to_patcher()
        assert isinstance(result, dict)
        assert "patcher" in result

    def test_to_patcher_name(self):
        d = self._make(name="MyFX")
        result = d.to_patcher()
        assert result["patcher"]["project"]["amxdtype"] == 1633771873

    def test_to_patcher_rect(self):
        d = self._make(width=500, height=250)
        result = d.to_patcher()
        assert result["patcher"]["openrect"] == [0.0, 0.0, 500, 250]

    def test_to_patcher_boxes_included(self):
        d = self._make()
        d.add_panel("p1", [0, 0, 200, 100], bgcolor=[0, 0, 0, 1])
        result = d.to_patcher()
        assert len(result["patcher"]["boxes"]) == 1

    def test_to_patcher_lines_included(self):
        d = self._make()
        d.add_newobj("obj-1", "gain~", numinlets=2, numoutlets=1)
        d.add_newobj("obj-2", "dac~", numinlets=2, numoutlets=0)
        d.add_line("obj-1", 0, "obj-2", 0)
        result = d.to_patcher()
        assert len(result["patcher"]["lines"]) == 1

    def test_to_bytes_returns_bytes(self):
        d = self._make()
        result = d.to_bytes()
        assert isinstance(result, bytes)

    def test_to_bytes_magic_header(self):
        d = self._make()
        result = d.to_bytes()
        assert result[:4] == b"ampf"

    def test_to_bytes_device_type_audio_effect(self):
        d = self._make(device_type="audio_effect")
        result = d.to_bytes()
        assert result[8:12] == b"aaaa"

    def test_to_bytes_device_type_instrument(self):
        d = self._make(device_type="instrument")
        result = d.to_bytes()
        assert result[8:12] == b"iiii"

    def test_to_bytes_device_type_midi_effect(self):
        d = self._make(device_type="midi_effect")
        result = d.to_bytes()
        assert result[8:12] == b"mmmm"

    def test_to_bytes_null_terminated(self):
        d = self._make()
        result = d.to_bytes()
        assert result[-1:] == b"\x00"

    def test_to_bytes_json_recoverable(self):
        d = self._make(name="RoundTrip")
        result = d.to_bytes()
        recovered = _parse_amxd_json(result)
        assert recovered["patcher"]["project"]["amxdtype"] == 1633771873

    def test_build_writes_file(self, tmp_path):
        d = self._make(name="WriteTest")
        output = str(tmp_path / "test.amxd")
        d.build(output)
        assert os.path.exists(output)

    def test_build_returns_byte_count(self, tmp_path):
        d = self._make()
        output = str(tmp_path / "test.amxd")
        count = d.build(output)
        assert count == os.path.getsize(output)

    def test_build_file_starts_with_ampf(self, tmp_path):
        d = self._make()
        output = str(tmp_path / "test.amxd")
        d.build(output)
        with open(output, "rb") as f:
            header = f.read(4)
        assert header == b"ampf"

    def test_build_file_valid_json_payload(self, tmp_path):
        d = self._make(name="FileTest")
        output = str(tmp_path / "test.amxd")
        d.build(output)
        with open(output, "rb") as f:
            data = f.read()
        recovered = _parse_amxd_json(data)
        assert recovered["patcher"]["project"]["amxdtype"] == 1633771873

    def test_to_patcher_includes_support_file_dependency(self):
        d = self._make()
        d.add_support_file("kernel.maxpat", '{"patcher": {}}', file_type="JSON")
        patcher = d.to_patcher()
        deps = patcher["patcher"]["dependency_cache"]
        assert any(dep["name"] == "kernel.maxpat" for dep in deps)
        dep = next(dep for dep in deps if dep["name"] == "kernel.maxpat")
        assert dep["type"] == "JSON"

    def test_build_writes_support_file(self, tmp_path):
        d = self._make()
        d.add_support_file("kernel.maxpat", '{"patcher": {}}', file_type="JSON")
        output = str(tmp_path / "test.amxd")
        d.build(output)
        support_path = tmp_path / "kernel.maxpat"
        assert support_path.exists()
        assert support_path.read_text() == '{"patcher": {}}'


class TestAudioEffect:
    """Tests for the AudioEffect subclass."""

    def test_device_type(self):
        fx = AudioEffect("FX", 400, 170)
        assert fx.device_type == "audio_effect"

    def test_auto_adds_two_boxes(self):
        fx = AudioEffect("FX", 400, 170)
        assert len(fx.boxes) == 2

    def test_auto_adds_no_lines(self):
        """stereo_io() returns an empty lines list."""
        fx = AudioEffect("FX", 400, 170)
        assert len(fx.lines) == 0

    def test_first_box_is_plugin_tilde(self):
        fx = AudioEffect("FX", 400, 170)
        assert fx.boxes[0]["box"]["text"] == "plugin~"

    def test_second_box_is_plugout_tilde(self):
        fx = AudioEffect("FX", 400, 170)
        assert fx.boxes[1]["box"]["text"] == "plugout~"

    def test_plugin_tilde_has_two_outlets(self):
        fx = AudioEffect("FX", 400, 170)
        plugin_box = fx.boxes[0]["box"]
        assert plugin_box["numoutlets"] == 2

    def test_plugin_tilde_outlet_types_are_signal(self):
        fx = AudioEffect("FX", 400, 170)
        plugin_box = fx.boxes[0]["box"]
        assert plugin_box["outlettype"] == ["signal", "signal"]

    def test_plugout_tilde_has_two_inlets(self):
        fx = AudioEffect("FX", 400, 170)
        plugout_box = fx.boxes[1]["box"]
        assert plugout_box["numinlets"] == 2

    def test_plugout_tilde_has_zero_outlets(self):
        fx = AudioEffect("FX", 400, 170)
        plugout_box = fx.boxes[1]["box"]
        assert plugout_box["numoutlets"] == 0

    def test_to_bytes_magic_bytes(self):
        fx = AudioEffect("FX", 400, 170)
        data = fx.to_bytes()
        assert data[:4] == b"ampf"

    def test_to_bytes_type_code_audio_effect(self):
        fx = AudioEffect("FX", 400, 170)
        data = fx.to_bytes()
        assert data[8:12] == b"aaaa"

    def test_add_box_after_init_increments_count(self):
        fx = AudioEffect("FX", 400, 170)
        fx.add_panel("bg", [0, 0, 400, 170], bgcolor=[0, 0, 0, 1])
        assert len(fx.boxes) == 3

    def test_patcher_contains_auto_boxes(self):
        fx = AudioEffect("FX", 400, 170)
        patcher = fx.to_patcher()
        assert len(patcher["patcher"]["boxes"]) == 2

    def test_build_writes_valid_file(self, tmp_path):
        fx = AudioEffect("FX", 400, 170)
        output = str(tmp_path / "fx.amxd")
        count = fx.build(output)
        assert count > 0
        assert os.path.exists(output)


class TestInstrument:
    """Tests for the Instrument subclass."""

    def test_device_type(self):
        inst = Instrument("Synth", 400, 170)
        assert inst.device_type == "instrument"

    def test_no_auto_boxes(self):
        inst = Instrument("Synth", 400, 170)
        assert len(inst.boxes) == 0

    def test_no_auto_lines(self):
        inst = Instrument("Synth", 400, 170)
        assert len(inst.lines) == 0

    def test_to_bytes_type_code_instrument(self):
        inst = Instrument("Synth", 400, 170)
        data = inst.to_bytes()
        assert data[8:12] == b"iiii"

    def test_to_bytes_magic_bytes(self):
        inst = Instrument("Synth", 400, 170)
        data = inst.to_bytes()
        assert data[:4] == b"ampf"

    def test_patcher_amxdtype(self):
        inst = Instrument("Synth", 400, 170)
        patcher = inst.to_patcher()
        # iiii as uint32 LE = 1768515945
        assert patcher["patcher"]["project"]["amxdtype"] == 1768515945

    def test_build_writes_file(self, tmp_path):
        inst = Instrument("Synth", 400, 170)
        output = str(tmp_path / "synth.amxd")
        count = inst.build(output)
        assert count > 0
        assert os.path.exists(output)


class TestMidiEffect:
    """Tests for the MidiEffect subclass."""

    def test_device_type(self):
        midi = MidiEffect("Arp", 400, 170)
        assert midi.device_type == "midi_effect"

    def test_no_auto_boxes(self):
        midi = MidiEffect("Arp", 400, 170)
        assert len(midi.boxes) == 0

    def test_no_auto_lines(self):
        midi = MidiEffect("Arp", 400, 170)
        assert len(midi.lines) == 0

    def test_to_bytes_type_code_midi_effect(self):
        midi = MidiEffect("Arp", 400, 170)
        data = midi.to_bytes()
        assert data[8:12] == b"mmmm"

    def test_to_bytes_magic_bytes(self):
        midi = MidiEffect("Arp", 400, 170)
        data = midi.to_bytes()
        assert data[:4] == b"ampf"

    def test_patcher_amxdtype(self):
        midi = MidiEffect("Arp", 400, 170)
        patcher = midi.to_patcher()
        # mmmm as uint32 LE = 1835887981
        assert patcher["patcher"]["project"]["amxdtype"] == 1835887981

    def test_build_writes_file(self, tmp_path):
        midi = MidiEffect("Arp", 400, 170)
        output = str(tmp_path / "arp.amxd")
        count = midi.build(output)
        assert count > 0
        assert os.path.exists(output)


class TestDeviceIntegration:
    """Integration tests building more complete devices."""

    def test_audio_effect_with_panel_and_dial(self, tmp_path):
        fx = AudioEffect("TestFX", 400, 170)
        fx.add_panel("bg", [0, 0, 400, 170], bgcolor=[0.15, 0.15, 0.17, 1.0])
        fx.add_dial("gain-dial", "Gain", [20, 20, 40, 40],
                    min_val=0.0, max_val=100.0, initial=75.0)
        data = fx.to_bytes()
        assert data[:4] == b"ampf"
        # 2 auto + 1 panel + 1 dial
        recovered = _parse_amxd_json(data)
        assert len(recovered["patcher"]["boxes"]) == 4

    def test_audio_effect_json_boxes_count(self):
        fx = AudioEffect("CountFX", 400, 170)
        fx.add_newobj("obj-gain-l", "*~ 1.", numinlets=2, numoutlets=1)
        # 2 auto + 1 newobj
        patcher = fx.to_patcher()
        assert len(patcher["patcher"]["boxes"]) == 3

    def test_audio_effect_wired_connection(self):
        fx = AudioEffect("WiredFX", 400, 170)
        # Wire plugin~ outlet 0 to plugout~ inlet 0
        fx.add_line("obj-plugin", 0, "obj-plugout", 0)
        fx.add_line("obj-plugin", 1, "obj-plugout", 1)
        patcher = fx.to_patcher()
        assert len(patcher["patcher"]["lines"]) == 2

    def test_instrument_with_multiple_ui_elements(self, tmp_path):
        inst = Instrument("MySynth", 500, 200)
        inst.add_panel("bg", [0, 0, 500, 200], bgcolor=[0.1, 0.1, 0.1, 1.0])
        inst.add_dial("osc-tune", "Tune", [10, 10, 40, 40],
                      min_val=-24.0, max_val=24.0, initial=0.0)
        inst.add_toggle("tog-mono", "Mono", [60, 10, 24, 24])
        inst.add_tab("tab-wave", "Waveform", [90, 10, 120, 24],
                     options=["Sine", "Saw", "Square"])
        output = str(tmp_path / "synth.amxd")
        count = inst.build(output)
        assert count > 0
        with open(output, "rb") as f:
            data = f.read()
        recovered = _parse_amxd_json(data)
        # 1 panel + 1 dial + 1 toggle + 1 tab
        assert len(recovered["patcher"]["boxes"]) == 4

    def test_midi_effect_build_round_trip(self, tmp_path):
        midi = MidiEffect("Randomizer", 300, 120)
        midi.add_comment("lbl-title", [10, 10, 150, 16], "MIDI Randomizer")
        midi.add_dial("d-chance", "Chance", [10, 40, 40, 40],
                      min_val=0.0, max_val=100.0, initial=50.0)
        output = str(tmp_path / "midi.amxd")
        midi.build(output)
        with open(output, "rb") as f:
            data = f.read()
        assert data[:4] == b"ampf"
        assert data[8:12] == b"mmmm"
        recovered = _parse_amxd_json(data)
        assert recovered["patcher"]["project"]["amxdtype"] == 1835887981  # mmmm
        assert len(recovered["patcher"]["boxes"]) == 2

    def test_build_byte_count_matches_to_bytes(self, tmp_path):
        fx = AudioEffect("ByteCount", 400, 170)
        output = str(tmp_path / "fx.amxd")
        written = fx.build(output)
        in_memory = fx.to_bytes()
        assert written == len(in_memory)


class TestToJson:
    """Tests for Device.to_json()."""

    def test_returns_valid_json(self):
        d = Device("Test", 400, 170)
        result = json.loads(d.to_json())
        assert isinstance(result, dict)

    def test_contains_patcher_key(self):
        d = Device("Test", 400, 170)
        result = json.loads(d.to_json())
        assert "patcher" in result

    def test_contains_boxes_key(self):
        d = Device("Test", 400, 170)
        result = json.loads(d.to_json())
        assert "boxes" in result["patcher"]

    def test_custom_indent(self):
        d = Device("Test", 400, 170)
        output = d.to_json(indent=4)
        # 4-space indent should produce lines starting with 4 spaces
        assert "\n    " in output

    def test_default_indent(self):
        d = Device("Test", 400, 170)
        output = d.to_json()
        # Default indent=2 should produce lines starting with 2 spaces
        assert "\n  " in output


class TestWireChain:
    """Tests for Device.wire_chain()."""

    def test_wires_three_ids(self):
        d = Device("Test", 400, 170)
        d.wire_chain(["obj-1", "obj-2", "obj-3"])
        assert len(d.lines) == 2

    def test_first_connection(self):
        d = Device("Test", 400, 170)
        d.wire_chain(["obj-1", "obj-2", "obj-3"])
        line = d.lines[0]["patchline"]
        assert line["source"] == ["obj-1", 0]
        assert line["destination"] == ["obj-2", 0]

    def test_second_connection(self):
        d = Device("Test", 400, 170)
        d.wire_chain(["obj-1", "obj-2", "obj-3"])
        line = d.lines[1]["patchline"]
        assert line["source"] == ["obj-2", 0]
        assert line["destination"] == ["obj-3", 0]

    def test_custom_outlet_inlet(self):
        d = Device("Test", 400, 170)
        d.wire_chain(["obj-a", "obj-b"], outlet=1, inlet=2)
        line = d.lines[0]["patchline"]
        assert line["source"] == ["obj-a", 1]
        assert line["destination"] == ["obj-b", 2]

    def test_single_id_no_lines(self):
        d = Device("Test", 400, 170)
        d.wire_chain(["obj-1"])
        assert len(d.lines) == 0

    def test_empty_list_no_lines(self):
        d = Device("Test", 400, 170)
        d.wire_chain([])
        assert len(d.lines) == 0


class TestValidate:
    """Tests for Device.validate()."""

    def test_clean_device_returns_empty(self):
        fx = AudioEffect("FX", 400, 168)
        # Wire plugin to plugout so nothing is orphaned
        fx.add_line("obj-plugin", 0, "obj-plugout", 0)
        fx.add_line("obj-plugin", 1, "obj-plugout", 1)
        assert fx.validate() == []

    def test_duplicate_id_warning(self):
        d = Device("Test", 400, 170)
        d.boxes.append({"box": {"id": "obj-1", "maxclass": "newobj"}})
        d.boxes.append({"box": {"id": "obj-1", "maxclass": "newobj"}})
        # Wire them so they aren't flagged as orphans too
        d.add_line("obj-1", 0, "obj-1", 0)
        warnings = d.validate()
        assert any("Duplicate box ID: obj-1" in w for w in warnings)

    def test_bad_patchline_source(self):
        d = Device("Test", 400, 170)
        d.boxes.append({"box": {"id": "obj-1", "maxclass": "newobj"}})
        d.add_line("obj-missing", 0, "obj-1", 0)
        warnings = d.validate()
        assert any("unknown source: obj-missing" in w for w in warnings)

    def test_bad_patchline_destination(self):
        d = Device("Test", 400, 170)
        d.boxes.append({"box": {"id": "obj-1", "maxclass": "newobj"}})
        d.add_line("obj-1", 0, "obj-missing", 0)
        warnings = d.validate()
        assert any("unknown destination: obj-missing" in w for w in warnings)

    def test_audio_effect_missing_plugin(self):
        d = Device("Test", 400, 170, device_type="audio_effect")
        warnings = d.validate()
        assert any("missing obj-plugin" in w for w in warnings)

    def test_orphan_box_warning(self):
        d = Device("Test", 400, 170)
        d.boxes.append({"box": {"id": "obj-lonely", "maxclass": "newobj"}})
        warnings = d.validate()
        assert any("Orphan" in w and "obj-lonely" in w for w in warnings)

    def test_decoration_boxes_not_flagged_as_orphans(self):
        # panels/comments/dividers/images are pure decoration — never patched — so
        # they must NOT be reported as orphans (that noise buries a real unwired box)
        d = Device("Test", 400, 168)
        d.add_panel("bg", [0, 0, 400, 168], bgcolor=[0, 0, 0, 1])
        d.add_comment("title", "Hello", [10, 6, 80, 12])
        d.boxes.append({"box": {"id": "rule", "maxclass": "live.line"}})
        d.boxes.append({"box": {"id": "logo", "maxclass": "fpic"}})
        orphan_ids = {i.box_id for i in d.lint() if i.code == "orphan-box"}
        assert orphan_ids.isdisjoint({"bg", "title", "rule", "logo"})
        # but a genuinely unwired FUNCTIONAL object IS still caught
        d.boxes.append({"box": {"id": "dead", "maxclass": "newobj", "text": "+ 1"}})
        assert "dead" in {i.box_id for i in d.lint() if i.code == "orphan-box"}

    def test_instrument_no_plugin_warning(self):
        inst = Instrument("Synth", 400, 170)
        warnings = inst.validate()
        # Instrument should NOT warn about missing obj-plugin
        assert not any("obj-plugin" in w for w in warnings)


class TestParameterBanks:
    """Tests for Device.assign_parameter_bank()."""

    def test_bank_shows_in_patcher(self):
        d = Device("Test", 400, 170)
        d.assign_parameter_bank("Gain", bank=0, position=0)
        patcher = d.to_patcher()
        banks = patcher["patcher"]["parameters"]["parameterbanks"]
        assert "0" in banks
        params = banks["0"]["parameters"]
        # Live shape: flat 8-slot longname list, "-" for empty slots.
        assert params == ["Gain", "-", "-", "-", "-", "-", "-", "-"]

    def test_multiple_params_same_bank(self):
        d = Device("Test", 400, 170)
        d.assign_parameter_bank("Gain", bank=0, position=0)
        d.assign_parameter_bank("Pan", bank=0, position=1)
        patcher = d.to_patcher()
        params = patcher["patcher"]["parameters"]["parameterbanks"]["0"]["parameters"]
        assert len(params) == 8
        assert params[0] == "Gain"
        assert params[1] == "Pan"

    def test_different_banks(self):
        d = Device("Test", 400, 170)
        d.assign_parameter_bank("Gain", bank=0, position=0)
        d.assign_parameter_bank("Filter", bank=1, position=0)
        patcher = d.to_patcher()
        banks = patcher["patcher"]["parameters"]["parameterbanks"]
        assert "0" in banks
        assert "1" in banks

    def test_no_banks_omits_parameterbanks(self):
        # An empty-bank stub crashes Live 12.4.5b's bank parser under any
        # active control surface — no registered banks means NO key at all.
        d = Device("Test", 400, 170)
        patcher = d.to_patcher()
        assert "parameterbanks" not in patcher["patcher"]["parameters"]

    def test_bank_in_json_output(self):
        d = Device("Test", 400, 170)
        d.assign_parameter_bank("Mix", bank=0, position=0)
        output = json.loads(d.to_json())
        params = output["patcher"]["parameters"]["parameterbanks"]["0"]["parameters"]
        assert "Mix" in params

    def test_bank_name_can_be_assigned_inline(self):
        d = Device("Test", 400, 170)
        d.assign_parameter_bank("Gain", bank=2, position=0, bank_name="Band 1")
        patcher = d.to_patcher()
        assert patcher["patcher"]["parameters"]["parameterbanks"]["2"]["name"] == "Band 1"

    def test_bank_name_can_be_set_separately(self):
        d = Device("Test", 400, 170)
        d.assign_parameter_bank("Gain", bank=2, position=0)
        d.set_parameter_bank_name(2, "Band 1")
        patcher = d.to_patcher()
        assert patcher["patcher"]["parameters"]["parameterbanks"]["2"]["name"] == "Band 1"


class TestFromAmxd:
    """Tests for Device.from_amxd() classmethod."""

    def test_round_trip_audio_effect(self, tmp_path):
        fx = AudioEffect("MyFX", 400, 170)
        fx.add_panel("bg", [0, 0, 400, 170], bgcolor=[0.1, 0.1, 0.1, 1.0])
        path = str(tmp_path / "fx.amxd")
        fx.build(path)

        loaded = Device.from_amxd(path)
        assert isinstance(loaded, AudioEffect)
        assert len(loaded.boxes) == 3  # plugin~ + plugout~ + panel

    def test_round_trip_instrument(self, tmp_path):
        inst = Instrument("Synth", 500, 200)
        inst.add_dial("d1", "Freq", [10, 10, 40, 40])
        path = str(tmp_path / "synth.amxd")
        inst.build(path)

        loaded = Device.from_amxd(path)
        assert isinstance(loaded, Instrument)
        assert len(loaded.boxes) == 1

    def test_round_trip_midi_effect(self, tmp_path):
        midi = MidiEffect("Arp", 300, 120)
        path = str(tmp_path / "arp.amxd")
        midi.build(path)

        loaded = Device.from_amxd(path)
        assert isinstance(loaded, MidiEffect)

    def test_boxes_match(self, tmp_path):
        fx = AudioEffect("RoundTrip", 400, 170)
        path = str(tmp_path / "rt.amxd")
        fx.build(path)

        loaded = Device.from_amxd(path)
        original_ids = {b["box"]["id"] for b in fx.boxes}
        loaded_ids = {b["box"]["id"] for b in loaded.boxes}
        assert original_ids == loaded_ids

    def test_device_type_preserved(self, tmp_path):
        inst = Instrument("Synth", 400, 170)
        path = str(tmp_path / "synth.amxd")
        inst.build(path)

        loaded = Device.from_amxd(path)
        assert loaded.device_type == "instrument"


class TestLcdPanelPainter:
    """C1 render-only jspainterfile painter (engines.painters.lcd_panel_painter_js)."""

    def test_is_balanced_es5_render_only(self):
        from m4l_builder.engines.painters import lcd_panel_painter_js
        js = lcd_panel_painter_js(60, 24, bg=[0.1, 0.1, 0.12, 1.0])
        assert js.count("{") == js.count("}")
        assert "mgraphics.init();" in js and "function paint()" in js
        assert "const " not in js and "let " not in js and "=>" not in js
        # dimensions baked in (no runtime size query)
        assert "rectangle_rounded(0, 0, 60, 24" in js

    def test_border_is_optional(self):
        from m4l_builder.engines.painters import lcd_panel_painter_js
        assert "stroke();" not in lcd_panel_painter_js(40, 40, bg=[0, 0, 0, 1])
        assert "stroke();" in lcd_panel_painter_js(40, 40, bg=[0, 0, 0, 1],
                                                   border=[1, 1, 1, 1])


class TestLcdDialPainter:
    """Original jspainterfile dial painter (engines.painters.lcd_dial_painter_js)."""

    def test_is_balanced_es5_value_reader(self):
        from m4l_builder.engines.painters import lcd_dial_painter_js
        js = lcd_dial_painter_js()
        assert js.count("{") == js.count("}")
        assert js.count("(") == js.count(")")
        assert "function paint()" in js and "mgraphics.init();" in js
        # ES5-safe (jsui runs ES5)
        assert "const " not in js and "let " not in js and "=>" not in js
        # reads the host control's live value + range (the reusable technique)
        assert "box.getvalueof()" in js
        assert 'box.getattr("_parameter_range")' in js
        assert "mgraphics.arc(" in js   # the swept value arc

    def test_themes_from_active_dial_color(self):
        from m4l_builder.engines.painters import lcd_dial_painter_js
        js = lcd_dial_painter_js()
        assert 'box.getattr("activedialcolor")' in js


class TestLcdSliderPainter:
    """Original jspainterfile slider painter (engines.painters.lcd_slider_painter_js)."""

    def test_is_balanced_es5_value_reader(self):
        from m4l_builder.engines.painters import lcd_slider_painter_js
        js = lcd_slider_painter_js()
        assert js.count("{") == js.count("}")
        assert js.count("(") == js.count(")")
        assert "function paint()" in js and "box.getvalueof()" in js
        assert "const " not in js and "let " not in js and "=>" not in js
        # auto-orients vertical/horizontal + draws a groove + fill + handle
        assert "var vert = h >= w" in js
        assert "rectangle_rounded" in js

    def test_accent_bakes_in(self):
        from m4l_builder.engines.painters import lcd_slider_painter_js
        js = lcd_slider_painter_js(accent="0.9, 0.7, 0.2")
        assert "0.9, 0.7, 0.2" in js
