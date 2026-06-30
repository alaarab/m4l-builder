"""Tests for the newer architecture layers."""

import pytest

import m4l_builder as m4l
from m4l_builder import (
    PARAM_HIDDEN,
    PARAM_VISIBLE,
    AudioEffect,
    BuildValidationError,
    Device,
    JsuiContractError,
    ParameterSpec,
    PatcherProfile,
    Subpatcher,
    find_jsui_contract_issues,
    find_v8ui_contract_issues,
    lint_graph,
    module_from_block,
    validate_jsui_contract,
    validate_v8ui_contract,
)
from m4l_builder.engines.filter_curve import filter_curve_js
from m4l_builder.stages import StageResult
from m4l_builder.ui import dial


class TestParameterSpecs:
    def test_annotation_name_and_info_round_trip(self):
        # A2 (unblocked by A0): hover-help lives in the param valueof and survives
        # both the spec round-trip AND the dial factory.
        spec = ParameterSpec.continuous(
            "Gain", minimum=-12.0, maximum=12.0, initial=0.0,
            annotation_name="Gain", info="Boosts or attenuates the input.",
        )
        vo = spec.to_valueof_dict()
        assert vo["parameter_annotation_name"] == "Gain"
        assert vo["parameter_info"] == "Boosts or attenuates the input."
        rebuilt = ParameterSpec.from_valueof_dict(vo)
        assert rebuilt.annotation_name == "Gain"
        assert rebuilt.info == "Boosts or attenuates the input."
        box = dial("g", "Gain", [0, 0, 44, 47], info="hover text")["box"]
        assert box["saved_attribute_attributes"]["valueof"]["parameter_info"] == "hover text"

    def test_parameter_units_round_trip(self):
        # E1: custom printf units + unitstyle=9, round-trips through valueof.
        spec = ParameterSpec.continuous("Ratio", minimum=0.0, maximum=8.0,
                                        initial=1.0, unitstyle=9, units="x %.2f")
        vo = spec.to_valueof_dict()
        assert vo["parameter_units"] == "x %.2f"
        assert vo["parameter_unitstyle"] == 9
        assert ParameterSpec.from_valueof_dict(vo).units == "x %.2f"

    def test_parameter_steps_round_trip(self):
        # E4: quantize a continuous range into N discrete steps; round-trips.
        spec = ParameterSpec.continuous("Mode", minimum=0.0, maximum=64.0,
                                        initial=0.0, steps=4)
        assert spec.to_valueof_dict()["parameter_steps"] == 4
        assert ParameterSpec.from_valueof_dict(spec.to_valueof_dict()).steps == 4
        box = dial("m", "Mode", [0, 0, 44, 47], min_val=0, max_val=64, steps=8)["box"]
        assert box["saved_attribute_attributes"]["valueof"]["parameter_steps"] == 8

    def test_ui_helpers_accept_parameter_spec(self):
        spec = ParameterSpec.continuous(
            "Cutoff",
            shortname="Cut",
            minimum=20.0,
            maximum=20000.0,
            initial=440.0,
            unitstyle=3,
            exponent=3.0,
        )
        result = dial("cutoff_dial", spec, [10, 10, 45, 45])
        valueof = result["box"]["saved_attribute_attributes"]["valueof"]

        assert result["box"]["varname"] == "Cutoff"
        assert valueof["parameter_shortname"] == "Cut"
        assert valueof["parameter_mmin"] == 20.0
        assert valueof["parameter_mmax"] == 20000.0
        assert valueof["parameter_unitstyle"] == 3
        assert valueof["parameter_exponent"] == 3.0

    def test_device_registers_parameter_specs_and_bank_metadata(self):
        device = AudioEffect("test", width=200, height=100)
        spec = ParameterSpec.continuous(
            "Cutoff",
            shortname="Cut",
            minimum=20.0,
            maximum=20000.0,
            initial=440.0,
            unitstyle=3,
            bank=1,
            position=2,
            bank_name="Filter",
        )
        dial_id = device.add_dial("cutoff_dial", spec, [10, 10, 45, 45])

        stored = device.parameter(dial_id)
        banks = device.to_patcher()["patcher"]["parameters"]["parameterbanks"]

        assert stored is not None
        assert stored.name == "Cutoff"
        assert banks["1"]["name"] == "Filter"
        # Flat 8-slot longname list, positioned by slot (this spec is at position 2).
        assert banks["1"]["parameters"][2] == "Cutoff"

    def test_assign_parameter_bank_accepts_box_refs(self):
        device = Device("test", 200, 100)
        dial_id = device.add_dial("gain_dial", "Gain", [10, 10, 45, 45])
        device.assign_parameter_bank(dial_id, bank=0, position=1)

        params = device.to_patcher()["patcher"]["parameters"]["parameterbanks"]["0"]["parameters"]
        assert params[1] == "Gain"

    def test_parameter_spec_normalizes_labels_and_visibility(self):
        spec = ParameterSpec.continuous("  Cutoff  ", shortname="  Cut  ", visible=False)

        assert spec.name == "Cutoff"
        assert spec.shortname == "Cut"
        assert spec.visible == PARAM_HIDDEN
        assert spec.with_visibility(PARAM_VISIBLE).visible == PARAM_VISIBLE

    def test_parameter_spec_rejects_blank_names(self):
        with pytest.raises(ValueError):
            ParameterSpec.continuous("   ")

    def test_integer_parameter_requires_native_range_opt_in(self):
        with pytest.raises(ValueError):
            ParameterSpec.integer("Steps", minimum=0, maximum=1024, initial=128)

        spec = ParameterSpec.integer(
            "Steps",
            minimum=0,
            maximum=1024,
            initial=128,
            allow_wide_range=True,
        )
        assert spec.maximum == 1024.0

    def test_hidden_visibility_round_trips_through_amxd(self, tmp_path):
        device = AudioEffect("test", width=200, height=100)
        spec = ParameterSpec.continuous(
            "Cutoff",
            minimum=20.0,
            maximum=20000.0,
            initial=440.0,
            visible=PARAM_HIDDEN,
            bank=0,
            position=0,
        )
        device.add_dial("cutoff_dial", spec, [10, 10, 45, 45])
        output = tmp_path / "hidden.amxd"

        device.build(str(output))
        rebuilt = Device.from_amxd(str(output))

        # The correct Live bank format is a flat longname list with NO per-slot
        # visible field, so Push bank MEMBERSHIP round-trips via the param's presence
        # in its slot. (The Max-level hide mechanism is parameter_invisible, which
        # round-trips separately via the param's own valueof.)
        assert rebuilt.parameter("Cutoff") is not None
        params = rebuilt.to_patcher()["patcher"]["parameters"]["parameterbanks"]["0"]["parameters"]
        assert params[0] == "Cutoff"


class TestJsuiContract:
    def test_contract_accepts_existing_engine_output(self):
        js = filter_curve_js()
        assert find_jsui_contract_issues(js) == []
        assert validate_jsui_contract(js) == js

    def test_contract_rejects_missing_bootstrap_and_es6(self):
        js = "const draw = () => {}; function paint() {}"
        issues = find_jsui_contract_issues(js)

        assert any("mgraphics.init()" in issue for issue in issues)
        assert any("ES6 'const'" in issue for issue in issues)
        with pytest.raises(JsuiContractError):
            validate_jsui_contract(js)

    def test_device_add_jsui_validates_by_default(self):
        device = AudioEffect("test", width=200, height=100)

        with pytest.raises(JsuiContractError):
            device.add_jsui("bad", [0, 0, 20, 20], js_code="function paint() {}")

    def test_device_add_jsui_can_opt_out_of_contract_validation(self):
        device = AudioEffect("test", width=200, height=100)
        box_id = device.add_jsui(
            "raw",
            [0, 0, 20, 20],
            js_code="function paint() {}",
            validate_contract=False,
        )

        assert str(box_id) == "raw"


class TestV8uiContract:
    """v8ui runs on V8 (ES6+ allowed); only the mgraphics bootstrap is required."""

    _ES6 = (
        "mgraphics.init();\n"
        "mgraphics.relative_coords = 0;\n"
        "mgraphics.autofill = 0;\n"
        "const draw = () => 1;\n"        # ES6 — must be allowed on v8ui
        "function paint() { let x = `${draw()}`; }\n"
        "mgraphics.redraw();\n"
    )

    def test_v8ui_contract_allows_es6(self):
        # the exact constructs the jsui (ES5) contract forbids
        assert find_v8ui_contract_issues(self._ES6) == []
        assert validate_v8ui_contract(self._ES6) == self._ES6
        # ...and the jsui contract WOULD reject the same source
        assert find_jsui_contract_issues(self._ES6) != []

    def test_v8ui_contract_requires_mgraphics_bootstrap(self):
        issues = find_v8ui_contract_issues("const f = () => 1;")
        assert any("mgraphics.init()" in i for i in issues)
        assert any("paint()" in i for i in issues)
        with pytest.raises(JsuiContractError):
            validate_v8ui_contract("const f = () => 1;")

    def test_device_add_v8ui_validates_by_default(self):
        device = AudioEffect("test", width=200, height=100)
        with pytest.raises(JsuiContractError):
            device.add_v8ui("bad", [0, 0, 20, 20], js_code="function paint() {}")

    def test_device_add_v8ui_accepts_es6_bootstrap(self):
        device = AudioEffect("test", width=200, height=100)
        box_id = device.add_v8ui("good", [0, 0, 20, 20], js_code=self._ES6)
        assert str(box_id) == "good"

    def test_device_add_v8ui_can_opt_out(self):
        device = AudioEffect("test", width=200, height=100)
        box_id = device.add_v8ui(
            "raw", [0, 0, 20, 20],
            js_code="function paint() {}", validate_contract=False,
        )
        assert str(box_id) == "raw"


class TestPublicExportSurface:
    """Every declared public export must actually load (guards lazy-getattr typos
    like the unloadable extract_controller_shell_candidates that shipped in __all__
    but was never imported in reverse_api)."""

    def test_every_root_export_is_loadable(self):
        from m4l_builder._exports import ROOT_ALL

        unloadable = []
        for name in ROOT_ALL:
            try:
                getattr(m4l, name)
            except Exception as exc:  # noqa: BLE001 - surfacing any import failure
                unloadable.append(f"{name}: {type(exc).__name__}")
        assert unloadable == [], f"unloadable exports: {unloadable}"

    def test_gen_registry_primitives_are_top_level(self):
        # The gen registry must be discoverable from the package root, not only
        # via deep module paths, so plugin authors don't hand-roll the math.
        for name in ("build_gendsp", "lint_genexpr", "ms_encode", "ms_decode",
                     "ms_width", "drive_blend", "peak_follower"):
            assert callable(getattr(m4l, name)), name


class TestTypedGraphHandles:
    def test_connect_accepts_typed_endpoints(self):
        device = Device("test", 200, 100)
        source = device.add_newobj("src", "noise~", numinlets=0, numoutlets=1, outlettype=["signal"])
        dest = device.add_newobj("dst", "*~ 1.", numinlets=2, numoutlets=1, outlettype=["signal"])

        device.connect(source.outlet(0), dest.inlet(1))

        patchline = device.lines[0]["patchline"]
        assert patchline["source"] == ["src", 0]
        assert patchline["destination"] == ["dst", 1]

    def test_add_line_accepts_outlet_and_inlet_refs(self):
        device = Device("test", 200, 100)
        source = device.add_newobj("src", "noise~", numinlets=0, numoutlets=1, outlettype=["signal"])
        dest = device.add_newobj("dst", "dac~", numinlets=2, numoutlets=0)

        device.add_line(source.outlet(0), dest.inlet(0))

        patchline = device.lines[0]["patchline"]
        assert patchline["source"] == ["src", 0]
        assert patchline["destination"] == ["dst", 0]


class TestIdGeneration:
    def test_unique_id_uses_nested_scopes(self):
        device = Device("test", 200, 100)

        with device.name_scope("band 1"):
            first = device.unique_id("gain")
            second = device.unique_id("gain")
            with device.name_scope("left"):
                nested = device.unique_id("gain")

        assert first == "band_1_gain"
        assert second == "band_1_gain_2"
        assert nested == "band_1_left_gain"

    def test_add_newobj_can_auto_generate_ids(self):
        device = Device("test", 200, 100)

        with device.name_scope("osc"):
            ref = device.add_newobj(text="cycle~ 440", numinlets=2, numoutlets=1)

        assert str(ref) == "osc_cycle_440"
        assert device.boxes[0]["box"]["id"] == "osc_cycle_440"


class TestModules:
    def test_graph_add_module_mounts_legacy_dsp_block(self):
        device = AudioEffect("test", width=200, height=100)
        gain_module = module_from_block(
            m4l.gain_stage,
            name="gain_module",
            mapping_factory=lambda prefix, **_: {"left": f"{prefix}_l", "right": f"{prefix}_r"},
            port_factory=lambda prefix, **_: {
                "left_in": m4l.InletRef(f"{prefix}_l", 0),
                "right_out": m4l.OutletRef(f"{prefix}_r", 0),
            },
        )

        result = device.add_module(gain_module, "band")

        assert isinstance(result, StageResult)
        assert result.name == "gain_module"
        assert result["left"] == "band_l"
        assert result.port("left_in").box_id == "band_l"
        assert result.port("right_out").box_id == "band_r"
        assert {"band_l", "band_r"}.issubset({box["box"]["id"] for box in device.boxes})


class TestStages:
    def test_recipes_return_stage_results(self):
        device = AudioEffect("test", width=200, height=100)
        result = m4l.gain_controlled_stage(device, "vol", [10, 10, 40, 40])

        assert isinstance(result, StageResult)
        assert result["gain"] == "vol_gain"
        assert result.param("gain").name == "vol_gain"
        assert result.port("audio_in").box_id == "vol_gain"
        assert result.port("audio_out").box_id == "vol_gain"

    def test_graph_add_stage_wraps_stage_results(self):
        device = AudioEffect("test", width=200, height=100)
        result = device.add_stage(m4l.dry_wet_stage, "mix", [10, 10, 40, 40])

        assert isinstance(result, StageResult)
        assert result.name == "dry_wet_stage"
        assert result.port("wet_in").box_id == "mix_wet_gain"
        assert result.port("dry_in").box_id == "mix_dry_gain"


class TestValidation:
    def test_library_linter_promotes_repo_rules(self):
        boxes = [
            {"box": {"id": "sig", "maxclass": "newobj", "text": "sig~"}},
            {"box": {"id": "sel", "maxclass": "newobj", "text": "selector~ 4"}},
            {"box": {"id": "panel", "maxclass": "panel", "background": 0}},
        ]

        issues = lint_graph(boxes, [], device_type="audio_effect")
        codes = {issue.code for issue in issues}

        assert "disallowed-sig-tilde" in codes
        assert "selector-missing-initial" in codes
        assert "panel-background" in codes

    def test_build_can_fail_on_validation_errors(self, tmp_path):
        device = Device("test", 200, 100)
        device.add_newobj("sig", "sig~", numinlets=1, numoutlets=1)

        with pytest.raises(BuildValidationError):
            device.build(str(tmp_path / "bad.amxd"), validate="error")

    def test_build_can_warn_and_continue(self, tmp_path):
        device = Device("test", 200, 100)
        device.add_newobj("lonely", "noise~", numinlets=0, numoutlets=1)
        output = tmp_path / "warn.amxd"

        with pytest.warns(UserWarning):
            written = device.build(str(output), validate="warn")

        assert written == output.stat().st_size
        assert output.exists()

    def test_default_build_rejects_unknown_patchline_ids(self, tmp_path):
        # Max silently drops patchlines to unknown box ids at load -> dead
        # wiring with no error. The default build must catch the typo.
        device = Device("test", 200, 100)
        device.add_newobj("gain", "live.gain~", numinlets=2, numoutlets=5)
        device.add_line("gain", 0, "no_such_box", 0)

        with pytest.raises(BuildValidationError) as excinfo:
            device.build(str(tmp_path / "bad.amxd"))
        assert "unknown-destination" in str(excinfo.value)
        assert "no_such_box" in str(excinfo.value)

    def test_default_build_rejects_unknown_source(self, tmp_path):
        device = Device("test", 200, 100)
        device.add_newobj("gain", "live.gain~", numinlets=2, numoutlets=5)
        device.add_line("ghost", 0, "gain", 0)

        with pytest.raises(BuildValidationError) as excinfo:
            device.build(str(tmp_path / "bad.amxd"))
        assert "unknown-source" in str(excinfo.value)

    def test_default_build_rejects_duplicate_box_ids(self, tmp_path):
        device = Device("test", 200, 100)
        device.add_newobj("dup", "+ 1", numinlets=2, numoutlets=1)
        device.add_newobj("dup", "+ 2", numinlets=2, numoutlets=1)

        with pytest.raises(BuildValidationError) as excinfo:
            device.build(str(tmp_path / "bad.amxd"))
        assert "duplicate-box-id" in str(excinfo.value)

    def test_default_build_ignores_style_rules(self, tmp_path):
        # Style/policy lint (sig~ ban, orphans, panel background) stays
        # opt-in via validate="warn"/"error"; the default only enforces
        # wiring integrity.
        device = Device("test", 200, 100)
        device.add_newobj("sig", "sig~ 1.", numinlets=1, numoutlets=1)
        output = tmp_path / "style_ok.amxd"

        written = device.build(str(output))
        assert written == output.stat().st_size

    def test_validate_false_skips_wiring_checks(self, tmp_path):
        device = Device("test", 200, 100)
        device.add_newobj("gain", "live.gain~", numinlets=2, numoutlets=5)
        device.add_line("gain", 0, "no_such_box", 0)
        output = tmp_path / "escape.amxd"

        written = device.build(str(output), validate=False)
        assert written == output.stat().st_size


class TestProfilesAndAssets:
    def test_device_and_subpatcher_share_profile_model(self):
        profile = PatcherProfile(
            device_rect=[10, 20, 300, 200],
            subpatch_rect=[1, 2, 333, 222],
            default_fontname="Test Sans",
        )
        device = Device("test", 200, 100, profile=profile)
        subpatcher = Subpatcher("nested", profile=profile)

        assert device.to_patcher()["patcher"]["rect"] == [10, 20, 300, 200]
        assert device.to_patcher()["patcher"]["default_fontname"] == "Test Sans"
        assert subpatcher.to_patcher_dict()["rect"] == [1, 2, 333, 222]

    def test_assets_registry_drives_dependency_cache(self):
        device = AudioEffect("test", width=200, height=100)
        device.add_jsui("display", [0, 0, 50, 50], js_code="// draw", validate_contract=False)
        device.add_support_file("kernel.maxpat", '{"patcher": {}}', file_type="JSON")

        asset_names = {asset.filename for asset in device.assets()}
        deps = {entry["name"]: entry["type"] for entry in device.to_patcher()["patcher"]["dependency_cache"]}

        assert asset_names == {"display.js", "kernel.maxpat"}
        assert deps["display.js"] == "TEXT"
        assert deps["kernel.maxpat"] == "JSON"
        assert device.asset("display.js").category == "js"
        assert device._js_files["display.js"] == "// draw"
        assert device._support_files["kernel.maxpat"]["type"] == "JSON"


class TestNamespaces:
    def test_package_exposes_namespaces(self):
        assert m4l.authoring.AudioEffect is m4l.AudioEffect
        assert m4l.builder.AudioEffect is m4l.AudioEffect
        assert m4l.builder.core.AudioEffect is m4l.AudioEffect
        assert m4l.builder.ui.dial is m4l.dial
        assert m4l.builder.dsp.gain_stage is m4l.gain_stage
        assert m4l.live.live_object_path is m4l.live_object_path
        assert m4l.builder.live.live_object_path is not None
        assert m4l.builder.recipes.gain_controlled_stage is m4l.gain_controlled_stage
        assert m4l.reverse_snapshot.snapshot_from_amxd is m4l.snapshot_from_amxd
        assert m4l.reverse_patterns.detect_snapshot_patterns is m4l.detect_snapshot_patterns
        assert m4l.reverse_analysis.analyze_snapshot is m4l.analyze_snapshot
        assert m4l.reverse_codegen.generate_python_from_amxd is m4l.generate_python_from_amxd
        assert m4l.reverse.generate_python_from_amxd is not None
        assert m4l.analysis.analyze_amxd_file is not None
        assert m4l.bridge.enable_livemcp_bridge is not None


class TestDefinedLatency:
    def test_default_latency_zero(self):
        device = Device("test", 200, 100)
        patcher = device.to_patcher()
        assert patcher["patcher"]["latency"] == 0

    def test_device_latency_lands_in_patcher(self):
        # "Defined Latency" (samples) is how an M4L device reports PDC
        # latency to Live — the patcher-level "latency" key.
        device = Device("test", 200, 100)
        device.latency = 2048
        patcher = device.to_patcher()
        assert patcher["patcher"]["latency"] == 2048
