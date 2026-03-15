"""Tests for the newer architecture layers."""

import pytest

import m4l_builder as m4l
from m4l_builder import (
    AudioEffect,
    BuildValidationError,
    Device,
    ParameterSpec,
    PatcherProfile,
    Subpatcher,
    lint_graph,
    module_from_block,
)
from m4l_builder.stages import StageResult
from m4l_builder.ui import dial


class TestParameterSpecs:
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
        assert banks["1"]["parameters"][0]["name"] == "Cutoff"

    def test_assign_parameter_bank_accepts_box_refs(self):
        device = Device("test", 200, 100)
        dial_id = device.add_dial("gain_dial", "Gain", [10, 10, 45, 45])
        device.assign_parameter_bank(dial_id, bank=0, position=1)

        params = device.to_patcher()["patcher"]["parameters"]["parameterbanks"]["0"]["parameters"]
        assert any(param["name"] == "Gain" and param["index"] == 1 for param in params)


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
        device.add_jsui("display", [0, 0, 50, 50], js_code="// draw")
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
