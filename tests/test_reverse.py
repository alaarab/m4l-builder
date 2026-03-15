"""Tests for reverse-engineering snapshots and starter code generation."""

import os

from m4l_builder import (
    AudioEffect,
    Instrument,
    MidiEffect,
    Subpatcher,
    build_livemcp_bridge_demo,
    delay_line,
    device_active_state,
    dry_wet_stage,
    gain_stage,
    gain_controlled_stage,
    init_dispatch_chain,
    live_object_path,
    live_parameter_probe,
    live_observer,
    live_state_observer,
    live_set_control,
    live_thisdevice,
    midi_note_gate,
    named_bus_router,
    patchline,
    param_smooth,
    poly_shell,
    poly_shell_bank,
    tempo_synced_delay,
    transport_lfo,
    transport_sync_lfo_recipe,
)
from m4l_builder.constants import DEVICE_TYPE_CODES
from m4l_builder.container import build_amxd
from m4l_builder.reverse import (
    analyze_snapshot,
    extract_building_block_candidates,
    detect_snapshot_motifs,
    detect_snapshot_patterns,
    detect_snapshot_recipes,
    extract_controller_shell_candidates,
    extract_behavior_hints,
    extract_mapping_behavior_traces,
    extract_mapping_semantic_candidates,
    extract_mapping_workflow_candidates,
    extract_embedded_ui_shell_candidates,
    extract_embedded_patcher_snapshots,
    extract_first_party_abstraction_family_candidates,
    extract_first_party_abstraction_host_candidates,
    extract_first_party_api_rig_candidates,
    extract_init_dispatch_chain_candidates,
    extract_live_api_normalization_candidates,
    extract_named_bus_router_candidates,
    extract_parameter_specs,
    extract_poly_editor_bank_candidates,
    extract_poly_shell_candidates,
    extract_poly_shell_bank_candidates,
    extract_sample_buffer_candidates,
    extract_gen_processing_candidates,
    extract_presentation_widget_cluster_candidates,
    extract_snapshot_knowledge,
    generate_builder_python_from_snapshot,
    generate_optimized_python_from_snapshot,
    generate_semantic_python_from_snapshot,
    generate_python_from_snapshot,
    read_amxd,
    snapshot_from_amxd,
    snapshot_from_bridge_payload,
    snapshot_from_device,
)


class TestSnapshotHelpers:
    def test_read_amxd_supports_ptch_only_chunk_layout(self, tmp_path):
        device = AudioEffect("Chunk Variant", 220, 100)
        device.add_comment("label", [10, 10, 80, 16], "Chunked")
        standard = device.to_bytes()
        ptch_payload = standard[32:]
        ptch_only = (
            b"ampf"
            + (4).to_bytes(4, "little")
            + b"aaaa"
            + b"ptch"
            + len(ptch_payload).to_bytes(4, "little")
            + ptch_payload
        )
        path = tmp_path / "ptch_only.amxd"
        path.write_bytes(ptch_only)

        loaded = read_amxd(str(path))

        assert loaded["device_type"] == "audio_effect"
        assert loaded["patcher"] == device.to_patcher()

    def test_read_amxd_supports_prefixed_ptch_payload(self, tmp_path):
        device = AudioEffect("Prefixed Variant", 220, 100)
        device.add_comment("label", [10, 10, 80, 16], "Prefixed")
        standard = device.to_bytes()
        ptch_payload = standard[32:]
        prefixed_payload = b"mx@c" + (16).to_bytes(4, "little") + (0).to_bytes(4, "little") + len(ptch_payload).to_bytes(4, "little") + ptch_payload
        prefixed = bytearray(standard[:32])
        prefixed[28:32] = len(prefixed_payload).to_bytes(4, "little")
        data = bytes(prefixed) + prefixed_payload
        path = tmp_path / "prefixed_ptch.amxd"
        path.write_bytes(data)

        loaded = read_amxd(str(path))

        assert loaded["device_type"] == "audio_effect"
        assert loaded["patcher"] == device.to_patcher()

    def test_read_amxd_ignores_trailing_asset_data_in_ptch_chunk(self, tmp_path):
        device = AudioEffect("Trailing Assets", 220, 100)
        device.add_comment("label", [10, 10, 80, 16], "Trailing")
        standard = bytearray(device.to_bytes())
        ptch_payload = bytes(standard[32:])
        trailing_payload = ptch_payload + b'<?xml version="1.0" encoding="utf-8"?><svg></svg>' + b"\x88\x99"
        standard[28:32] = len(trailing_payload).to_bytes(4, "little")
        data = bytes(standard[:32]) + trailing_payload
        path = tmp_path / "trailing_assets.amxd"
        path.write_bytes(data)

        loaded = read_amxd(str(path))

        assert loaded["device_type"] == "audio_effect"
        assert loaded["patcher"] == device.to_patcher()

    def test_read_amxd_supports_double_braced_ptch_payload(self, tmp_path):
        device = AudioEffect("Double Braced", 220, 100)
        device.add_comment("label", [10, 10, 80, 16], "Double")
        standard = bytearray(device.to_bytes())
        ptch_payload = bytes(standard[32:])
        doubled_payload = b"{" + ptch_payload
        standard[28:32] = len(doubled_payload).to_bytes(4, "little")
        data = bytes(standard[:32]) + doubled_payload
        path = tmp_path / "double_braced.amxd"
        path.write_bytes(data)

        loaded = read_amxd(str(path))

        assert loaded["device_type"] == "audio_effect"
        assert loaded["patcher"] == device.to_patcher()

    def test_read_amxd_supports_relaxed_prefixed_ptch_payload(self, tmp_path):
        device = AudioEffect("Relaxed Prefixed", 220, 100)
        device.add_comment("label", [10, 10, 80, 16], "Relaxed")
        standard = bytearray(device.to_bytes())
        ptch_payload = bytes(standard[32:])
        relaxed_payload = ptch_payload.replace(b"10.0", b"10.", 1)
        prefixed_payload = b"{\xcc" + relaxed_payload
        standard[28:32] = len(prefixed_payload).to_bytes(4, "little")
        data = bytes(standard[:32]) + prefixed_payload
        path = tmp_path / "relaxed_prefixed.amxd"
        path.write_bytes(data)

        loaded = read_amxd(str(path))

        assert loaded["device_type"] == "audio_effect"
        assert loaded["patcher"] == device.to_patcher()

    def test_snapshot_from_device_captures_support_files(self):
        device = build_livemcp_bridge_demo()

        snapshot = snapshot_from_device(device)
        support_names = {entry["name"] for entry in snapshot["support_files"]}

        assert snapshot["schema_version"] == 1
        assert snapshot["source"]["kind"] == "device"
        assert snapshot["device"]["device_type"] == "audio_effect"
        assert "livemcp_bridge_runtime.js" in support_names
        assert "livemcp_bridge_server.js" in support_names
        assert "livemcp_bridge_schema.json" in support_names

    def test_snapshot_from_amxd_recovers_sidecars_next_to_device(self, tmp_path):
        device = build_livemcp_bridge_demo()
        output = tmp_path / "LiveMCP Bridge Demo.amxd"
        device.build(str(output))

        snapshot = snapshot_from_amxd(str(output))
        support_names = {entry["name"] for entry in snapshot["support_files"]}

        assert snapshot["source"]["kind"] == "amxd"
        assert snapshot["source"]["path"] == os.path.abspath(str(output))
        assert "livemcp_bridge_runtime.js" in support_names
        assert "livemcp_bridge_server.js" in support_names
        assert "livemcp_bridge_schema.json" in support_names
        assert snapshot["missing_support_files"] == []

    def test_snapshot_from_bridge_payload_normalizes_live_bridge_data(self):
        snapshot = snapshot_from_bridge_payload(
            current_patcher={
                "bridge_session_id": "livemcp-session-99",
                "name": "Bridge Ready",
                "filepath": "/tmp/Bridge Ready.amxd",
                "locked": False,
                "presentation_mode": True,
            },
            selected_device={
                "device_name": "Bridge Ready",
                "class_name": "MxDeviceAudioEffect",
                "live_path": "live_set tracks 0 devices 1",
            },
            boxes=[
                {
                    "box_id": "obj-plugin",
                    "maxclass": "newobj",
                    "varname": None,
                    "boxtext": "plugin~",
                    "rect": [30.0, 100.0, 46.0, 22.0],
                    "presentation_rect": None,
                    "hidden": False,
                    "background": False,
                },
                {
                    "box_id": "bridge_demo_target",
                    "maxclass": "live.comment",
                    "varname": "bridge_demo_target",
                    "boxtext": "Ready for patch edits.",
                    "rect": [700.0, 400.0, 188.0, 14.0],
                    "presentation_rect": [22.0, 27.0, 188.0, 14.0],
                    "hidden": False,
                    "background": False,
                },
                {
                    "box_id": "bridge_demo_runtime",
                    "maxclass": "newobj",
                    "varname": "bridge_demo_runtime",
                    "boxtext": "js livemcp_bridge_runtime.js",
                    "rect": [200.0, 240.0, 160.0, 20.0],
                    "presentation_rect": None,
                    "hidden": False,
                    "background": False,
                },
            ],
            box_attrs={
                "bridge_demo_target": {
                    "object_attrs": {
                        "text": "Ready for patch edits.",
                    },
                    "box_attrs": {
                        "fontsize": 10.5,
                        "presentation": 1,
                    },
                }
            },
            patchlines=[
                {
                    "from_box_id": "obj-plugin",
                    "outlet": 0,
                    "to_box_id": "bridge_demo_target",
                    "inlet": 0,
                }
            ],
            support_files=[
                {
                    "name": "livemcp_bridge_runtime.js",
                    "type": "TEXT",
                    "content": "autowatch = 1;\n",
                }
            ],
        )

        assert snapshot["source"]["kind"] == "bridge"
        assert snapshot["device"]["device_type"] == "audio_effect"
        assert snapshot["fidelity"]["exact_patcher_dict"] is False
        assert snapshot["fidelity"]["has_line_data"] is True
        assert snapshot["patcher"]["patcher"]["name"] == "Bridge Ready"
        assert snapshot["analysis"]["bridge_box_ids"] == ["bridge_demo_runtime"]
        assert "bridge_demo_target" in snapshot["analysis"]["ui_box_ids"]
        assert snapshot["lines"][0]["patchline"]["destination"] == ["bridge_demo_target", 0]

    def test_snapshot_analysis_notes_missing_line_data(self):
        snapshot = snapshot_from_bridge_payload(
            current_patcher={
                "bridge_session_id": "livemcp-session-77",
                "name": "No Lines",
                "filepath": None,
                "locked": True,
                "presentation_mode": False,
            },
            selected_device={
                "device_name": "No Lines",
                "class_name": "MxDeviceMidiEffect",
            },
            boxes=[
                {
                    "box_id": "dial_1",
                    "maxclass": "live.dial",
                    "varname": "Gain",
                    "boxtext": None,
                    "rect": [700.0, 100.0, 50.0, 90.0],
                    "presentation_rect": [10.0, 6.0, 50.0, 90.0],
                    "hidden": False,
                    "background": False,
                }
            ],
        )

        analysis = analyze_snapshot(snapshot)

        assert snapshot["device"]["device_type"] == "midi_effect"
        assert analysis["parameter_box_ids"] == ["dial_1"]
        assert analysis["line_count"] == 0
        assert "No patchline data was available in the source snapshot." in analysis["notes"]

    def test_generic_live_thisdevice_and_deferlow_do_not_count_as_bridge(self):
        device = AudioEffect("Plain Max Device", 220, 100)
        device.add_newobj(
            "plain_thisdevice",
            "live.thisdevice",
            numinlets=1,
            numoutlets=2,
            outlettype=["bang", ""],
            patching_rect=[30, 120, 90, 20],
        )
        device.add_newobj(
            "plain_defer",
            "deferlow",
            numinlets=1,
            numoutlets=1,
            outlettype=[""],
            patching_rect=[130, 120, 52, 20],
        )

        snapshot = snapshot_from_device(device)
        knowledge = extract_snapshot_knowledge(snapshot)

        assert snapshot["analysis"]["bridge_box_ids"] == []
        assert knowledge["summary"]["bridge_enabled"] is False

    def test_extract_parameter_specs_reads_range_enum_and_initial(self):
        device = AudioEffect("Params", 220, 100)
        device.add_dial(
            "gain",
            "Gain",
            [10, 8, 50, 90],
            min_val=-70.0,
            max_val=6.0,
            initial=0.0,
            unitstyle=4,
        )
        device.add_tab(
            "mode",
            "Mode",
            [70, 12, 120, 24],
            options=["Clean", "Drive", "Crush"],
        )

        snapshot = snapshot_from_device(device)
        specs = extract_parameter_specs(snapshot)
        by_varname = {spec["varname"]: spec for spec in specs}

        assert by_varname["Gain"]["min"] == -70.0
        assert by_varname["Gain"]["max"] == 6.0
        assert by_varname["Gain"]["initial"] == 0.0
        assert by_varname["Gain"]["unitstyle"] == 4
        assert by_varname["Mode"]["enum"] == ["Clean", "Drive", "Crush"]

    def test_detect_snapshot_patterns_finds_known_dsp_helpers(self):
        device = AudioEffect("Patterns", 220, 120)
        device.add_dsp(*param_smooth("mod"))
        device.add_dsp(*delay_line("echo", max_delay_ms=750))
        device.add_dsp(*transport_lfo("sync", division="1/8", shape="square"))
        device.add_dsp(
            *gain_stage(
                "trim",
                patching_rect_l=[40, 120, 40, 20],
                patching_rect_r=[160, 120, 40, 20],
            )
        )

        snapshot = snapshot_from_device(device)
        patterns = detect_snapshot_patterns(snapshot)
        by_kind = {pattern["kind"]: pattern for pattern in patterns}

        assert by_kind["param_smooth"]["params"]["smooth_ms"] == 20
        assert by_kind["param_smooth"]["helperizable"] is True
        assert by_kind["delay_line"]["params"]["max_delay_ms"] == 750
        assert by_kind["delay_line"]["helper"]["name"] == "delay_line"
        assert by_kind["transport_lfo"]["params"] == {"division": "1/8", "shape": "square"}
        assert by_kind["transport_lfo"]["helper"]["kwargs"] == {"division": "1/8", "shape": "square"}
        assert by_kind["gain_stage"]["helper"]["kwargs"]["patching_rect_l"] == [40, 120, 40, 20]
        assert by_kind["gain_stage"]["helperizable"] is True
        assert snapshot["analysis"]["patterns"] == patterns
        assert "Recognized 4 known m4l-builder helper pattern(s)." in snapshot["analysis"]["notes"]

    def test_detect_snapshot_recipes_finds_known_recipe_blocks(self):
        device = AudioEffect("Recipe Patterns", 320, 140)
        gain_controlled_stage(device, "trim", [10, 10, 44, 88], x=45, y=60)
        dry_wet_stage(device, "mix", [66, 10, 44, 88], x=120, y=90)
        midi_note_gate(device, "keys", x=180, y=30)
        transport_sync_lfo_recipe(device, "sync", x=240, y=30)
        tempo_synced_delay(
            device,
            "echo",
            [122, 10, 44, 88],
            [178, 10, 44, 88],
            x=210,
            y=120,
        )

        snapshot = snapshot_from_device(device)
        recipes = detect_snapshot_recipes(snapshot)
        by_kind = {recipe["kind"]: recipe for recipe in recipes}

        assert by_kind["gain_controlled_stage"]["recipeizable"] is True
        assert by_kind["gain_controlled_stage"]["recipe"]["kwargs"] == {"x": 45, "y": 60}
        assert by_kind["dry_wet_stage"]["recipeizable"] is True
        assert by_kind["dry_wet_stage"]["recipe"]["kwargs"] == {"x": 120, "y": 90}
        assert by_kind["midi_note_gate"]["recipeizable"] is True
        assert by_kind["midi_note_gate"]["recipe"]["kwargs"] == {"x": 180}
        assert by_kind["transport_sync_lfo_recipe"]["recipeizable"] is True
        assert by_kind["transport_sync_lfo_recipe"]["recipe"]["kwargs"] == {"x": 240}
        assert by_kind["tempo_synced_delay"]["recipeizable"] is True
        assert by_kind["tempo_synced_delay"]["recipe"]["kwargs"] == {"x": 210, "y": 120}
        assert snapshot["analysis"]["recipes"] == recipes
        assert "Recognized 5 known m4l-builder recipe pattern(s)." in snapshot["analysis"]["notes"]

    def test_detect_snapshot_motifs_finds_named_buses_live_api_and_embedded_patchers(self):
        device = AudioEffect("Generic Motifs", 320, 160)
        device.add_newobj("send_a", "s clock_bus", numinlets=1, numoutlets=0, patching_rect=[20, 20, 60, 20])
        device.add_newobj("recv_a", "r clock_bus", numinlets=0, numoutlets=1, patching_rect=[110, 20, 60, 20])
        device.add_newobj("recv_b", "receive clock_bus", numinlets=0, numoutlets=1, patching_rect=[200, 20, 90, 20])
        device.add_newobj("device", "live.thisdevice", numinlets=1, numoutlets=2, patching_rect=[20, 70, 77, 20])
        device.add_newobj("path", "live.path live_set", numinlets=2, numoutlets=2, patching_rect=[120, 70, 90, 20])
        device.add_newobj("observer", "live.observer", numinlets=2, numoutlets=2, patching_rect=[240, 70, 80, 20])
        device.add_newobj("route", "route id", numinlets=1, numoutlets=2, patching_rect=[120, 100, 60, 20])
        device.add_box({
            "box": {
                "id": "observer_property",
                "maxclass": "message",
                "text": "property is_playing",
                "patching_rect": [240, 40, 100, 20],
                "numinlets": 2,
                "numoutlets": 1,
            }
        })
        device.add_line("device", 1, "path", 0)
        device.add_line("path", 1, "observer", 1)
        device.add_line("path", 0, "route", 0)
        device.add_line("observer_property", 0, "observer", 0)
        device.add_bpatcher("panel_host", [20, 110, 110, 40], "macro_panel.maxpat")
        device.add_newobj("voice_bank", "poly~ voices 8", numinlets=2, numoutlets=2, patching_rect=[170, 120, 90, 20])

        snapshot = snapshot_from_device(device)
        motifs = detect_snapshot_motifs(snapshot)
        by_kind = {}
        for motif in motifs:
            by_kind.setdefault(motif["kind"], []).append(motif)

        named_bus = by_kind["named_bus"][0]
        assert named_bus["params"]["name"] == "clock_bus"
        assert named_bus["params"]["sender_count"] == 1
        assert named_bus["params"]["receiver_count"] == 2

        live_api = by_kind["live_api_component"][0]
        assert live_api["params"]["core_operator_count"] == 3
        assert live_api["params"]["operator_counts"]["route"] == 1
        assert live_api["params"]["path_targets"] == ["live_set"]
        assert live_api["params"]["property_names"] == ["is_playing"]
        assert live_api["params"]["route_selectors"] == ["id"]
        assert live_api["params"]["archetypes"] == ["transport_state_observer"]

        embedded = by_kind["embedded_patcher"]
        assert any(entry["params"]["host_kind"] == "bpatcher" for entry in embedded)
        assert any(entry["params"]["host_kind"] == "poly" for entry in embedded)
        assert snapshot["analysis"]["motifs"] == motifs
        assert "Recognized 4 generic Max motif(s)." in snapshot["analysis"]["notes"]

    def test_detect_snapshot_motifs_splits_live_api_message_commands(self):
        device = AudioEffect("Live API Commands", 280, 120)
        device.add_newobj("api", "live.object", numinlets=2, numoutlets=1, patching_rect=[80, 40, 70, 20])
        device.add_newobj("defer", "deferlow", numinlets=1, numoutlets=1, patching_rect=[170, 40, 60, 20])
        device.add_line("defer", 0, "api", 1)
        device.add_box({
            "box": {
                "id": "api_message",
                "maxclass": "message",
                "text": "name, get max, get min, get value, set value 0.5, call str_for_value 0.5",
                "patching_rect": [20, 40, 240, 20],
                "numinlets": 2,
                "numoutlets": 1,
            }
        })
        device.add_line("api_message", 0, "api", 0)

        motifs = detect_snapshot_motifs(snapshot_from_device(device))
        live_api = next(entry for entry in motifs if entry["kind"] == "live_api_component")

        assert live_api["params"]["get_targets"] == ["max", "min", "value"]
        assert live_api["params"]["set_targets"] == ["value"]
        assert live_api["params"]["call_targets"] == ["str_for_value"]
        assert live_api["params"]["archetypes"] == ["parameter_probe"]

    def test_detect_snapshot_motifs_finds_controller_dispatch_clusters(self):
        device = AudioEffect("Dispatch Motifs", 280, 140)
        device.add_newobj("route", "route mode bypass", numinlets=1, numoutlets=3, patching_rect=[20, 20, 110, 20])
        device.add_newobj("trigger", "t i i", numinlets=1, numoutlets=2, patching_rect=[150, 20, 40, 20])
        device.add_newobj("gate", "gate 2", numinlets=2, numoutlets=2, patching_rect=[210, 20, 50, 20])
        device.add_line("route", 0, "trigger", 0)
        device.add_line("trigger", 0, "gate", 0)
        device.add_box({
            "box": {
                "id": "dispatch_message",
                "maxclass": "message",
                "text": "mode 1",
                "patching_rect": [20, 50, 70, 20],
                "numinlets": 2,
                "numoutlets": 1,
            }
        })
        device.add_line("dispatch_message", 0, "route", 0)

        motifs = detect_snapshot_motifs(snapshot_from_device(device))
        dispatch = next(entry for entry in motifs if entry["kind"] == "controller_dispatch")

        assert dispatch["params"]["primary_operators"] == ["gate", "route"]
        assert dispatch["params"]["route_selectors"] == ["bypass", "mode"]
        assert dispatch["params"]["trigger_shapes"] == ["i i"]
        assert dispatch["params"]["archetypes"] == [
            "gated_route",
            "route_dispatch",
            "state_gate",
            "trigger_fanout",
        ]
        assert dispatch["params"]["adjacent_message_texts"] == ["mode 1"]

    def test_detect_snapshot_motifs_finds_scheduler_and_state_bundle_clusters(self):
        device = AudioEffect("Controller Utility Motifs", 320, 180)
        device.add_newobj("loadbang", "loadbang", numinlets=1, numoutlets=1, patching_rect=[20, 20, 60, 20])
        device.add_newobj("defer", "deferlow", numinlets=1, numoutlets=1, patching_rect=[100, 20, 60, 20])
        device.add_newobj("trigger", "t b b", numinlets=1, numoutlets=2, patching_rect=[180, 20, 40, 20])
        device.add_line("loadbang", 0, "defer", 0)
        device.add_line("defer", 0, "trigger", 0)
        device.add_box({
            "box": {
                "id": "init_message",
                "maxclass": "message",
                "text": "bang",
                "patching_rect": [20, 50, 50, 20],
                "numinlets": 2,
                "numoutlets": 1,
            }
        })
        device.add_line("trigger", 0, "init_message", 0)

        device.add_newobj("pack", "pack 0 0", numinlets=2, numoutlets=1, patching_rect=[20, 100, 70, 20])
        device.add_newobj("zl", "zl.rev", numinlets=2, numoutlets=2, patching_rect=[110, 100, 60, 20])
        device.add_newobj("unpack", "unpack 0 0", numinlets=1, numoutlets=2, patching_rect=[190, 100, 80, 20])
        device.add_line("pack", 0, "zl", 0)
        device.add_line("zl", 0, "unpack", 0)

        motifs = detect_snapshot_motifs(snapshot_from_device(device))
        scheduler = next(entry for entry in motifs if entry["kind"] == "scheduler_chain")
        state_bundle = next(entry for entry in motifs if entry["kind"] == "state_bundle")

        assert scheduler["params"]["archetypes"] == [
            "deferred_fanout",
            "deferred_init",
            "init_chain",
            "init_fanout",
        ]
        assert scheduler["params"]["trigger_shapes"] == ["b b"]
        assert state_bundle["params"]["archetypes"] == ["bundle_fanout", "bundle_pack", "list_transform", "pack_unpack"]
        assert state_bundle["params"]["zl_operators"] == ["zl.rev"]
        assert state_bundle["params"]["pack_texts"] == ["pack 0 0"]
        assert state_bundle["params"]["unpack_texts"] == ["unpack 0 0"]

    def test_detect_snapshot_motifs_finds_sample_buffer_toolchains(self):
        device = AudioEffect("Sample Buffer Motifs", 360, 180)
        device.add_box({
            "box": {
                "id": "drop",
                "maxclass": "live.drop",
                "varname": "SampleDrop",
                "patching_rect": [20, 20, 80, 24],
                "presentation_rect": [20, 20, 80, 24],
                "presentation": 1,
                "numinlets": 1,
                "numoutlets": 1,
            }
        })
        device.add_newobj("buffer", "buffer~ grains", numinlets=2, numoutlets=2, patching_rect=[120, 20, 90, 20])
        device.add_newobj("info", "info~ grains", numinlets=1, numoutlets=9, patching_rect=[230, 20, 70, 20])
        device.add_newobj("peek", "peek~ grains", numinlets=2, numoutlets=1, patching_rect=[120, 60, 70, 20])
        device.add_newobj("metro", "metro 40", numinlets=2, numoutlets=1, patching_rect=[20, 60, 60, 20])
        device.add_newobj("strippath", "strippath", numinlets=1, numoutlets=1, patching_rect=[20, 100, 60, 20])
        device.add_line("drop", 0, "buffer", 0)
        device.add_line("buffer", 0, "info", 0)
        device.add_line("metro", 0, "peek", 0)
        device.add_line("buffer", 0, "peek", 1)
        device.add_line("drop", 0, "strippath", 0)

        motifs = detect_snapshot_motifs(snapshot_from_device(device))
        sample_buffer = next(entry for entry in motifs if entry["kind"] == "sample_buffer_toolchain")

        assert sample_buffer["params"]["has_live_drop"] is True
        assert sample_buffer["params"]["buffer_targets"] == ["grains"]
        assert sample_buffer["params"]["drop_varnames"] == ["SampleDrop"]
        assert sample_buffer["params"]["core_operators"] == ["buffer~", "info~", "peek~"]
        assert sample_buffer["params"]["file_operators"] == ["strippath"]
        assert sample_buffer["params"]["archetypes"] == [
            "driven_visual_probe",
            "sample_import",
            "sample_metadata",
            "waveform_probe",
        ]

    def test_detect_snapshot_motifs_merges_sample_buffer_components_by_shared_target(self):
        device = AudioEffect("Named Buffer Motifs", 360, 180)
        device.add_newobj("metro", "metro 30", numinlets=2, numoutlets=1, patching_rect=[20, 20, 60, 20])
        device.add_newobj("uzi", "uzi 12 1", numinlets=2, numoutlets=3, patching_rect=[100, 20, 60, 20])
        device.add_newobj("peek_a", "peek~ grains", numinlets=2, numoutlets=1, patching_rect=[180, 20, 70, 20])
        device.add_newobj("peek_b", "peek~ grains", numinlets=2, numoutlets=1, patching_rect=[180, 50, 70, 20])
        device.add_newobj("buffer", "buffer~ grains @samps 64", numinlets=2, numoutlets=2, patching_rect=[20, 80, 120, 20])
        device.add_line("metro", 0, "uzi", 0)
        device.add_line("uzi", 0, "peek_a", 0)
        device.add_line("uzi", 1, "peek_b", 0)

        motifs = detect_snapshot_motifs(snapshot_from_device(device))
        sample_buffer = next(entry for entry in motifs if entry["kind"] == "sample_buffer_toolchain")

        assert sample_buffer["params"]["buffer_targets"] == ["grains"]
        assert sample_buffer["params"]["operator_counts"]["buffer~"] == 1
        assert sample_buffer["params"]["operator_counts"]["peek~"] == 2
        assert sample_buffer["params"]["operator_counts"]["uzi"] == 1
        assert sample_buffer["params"]["archetypes"] == ["driven_visual_probe", "waveform_probe"]

    def test_detect_snapshot_motifs_finds_gen_processing_cores(self):
        device = AudioEffect("Gen Core Motifs", 360, 180)
        device.add_newobj("route", "route capture", numinlets=1, numoutlets=2, patching_rect=[20, 20, 90, 20])
        device.add_newobj("delay", "delay 10", numinlets=2, numoutlets=1, patching_rect=[130, 20, 60, 20])
        device.add_newobj("click", "click~", numinlets=1, numoutlets=1, patching_rect=[210, 20, 50, 20])
        device.add_newobj("gen", "gen~ @title Capture", numinlets=2, numoutlets=1, patching_rect=[120, 60, 100, 20])
        device.add_newobj("buffer", "buffer~ grains", numinlets=2, numoutlets=2, patching_rect=[240, 60, 90, 20])
        device.add_newobj("sub", "p CaptureDSP", numinlets=1, numoutlets=1, patching_rect=[20, 60, 80, 20])
        device.add_line("route", 0, "delay", 0)
        device.add_line("delay", 0, "click", 0)
        device.add_line("click", 0, "gen", 0)
        device.add_line("sub", 0, "gen", 1)
        device.add_line("gen", 0, "buffer", 0)

        motifs = detect_snapshot_motifs(snapshot_from_device(device))
        gen_core = next(entry for entry in motifs if entry["kind"] == "gen_processing_core")

        assert gen_core["params"]["core_operators"] == ["gen~"]
        assert gen_core["params"]["buffer_targets"] == ["grains"]
        assert gen_core["params"]["operator_counts"]["click~"] == 1
        assert gen_core["params"]["operator_counts"]["route"] == 1
        assert gen_core["params"]["operator_counts"]["p"] == 1
        assert gen_core["params"]["archetypes"] == [
            "buffered_gen_core",
            "nested_gen_shell",
            "routed_gen_core",
            "triggered_gen_core",
        ]

    def test_extract_sample_buffer_and_gen_processing_candidates(self):
        sample_device = AudioEffect("Sample Candidates", 360, 180)
        sample_device.add_newobj("buffer", "buffer~ grains", numinlets=2, numoutlets=2, patching_rect=[20, 20, 90, 20])
        sample_device.add_newobj("info", "info~ grains", numinlets=1, numoutlets=9, patching_rect=[130, 20, 70, 20])
        sample_device.add_newobj("path_fix", "strippath", numinlets=1, numoutlets=1, patching_rect=[220, 20, 60, 20])
        sample_device.add_line("buffer", 0, "info", 0)
        sample_snapshot = snapshot_from_device(sample_device)
        sample_candidates = extract_sample_buffer_candidates(sample_snapshot)
        sample_knowledge = extract_snapshot_knowledge(sample_snapshot)

        assert len(sample_candidates) == 1
        assert sample_candidates[0]["candidate_name"] == "sample_file_handling_shell"
        assert sample_candidates[0]["motif_kinds"] == ["sample_buffer_toolchain"]
        assert sample_knowledge["summary"]["sample_buffer_candidate_count"] == 1
        assert sample_knowledge["sample_buffer_candidates"][0]["candidate_name"] == "sample_file_handling_shell"

        gen_device = AudioEffect("Gen Candidates", 360, 180)
        gen_device.add_newobj("delay", "delay 10", numinlets=2, numoutlets=1, patching_rect=[20, 20, 60, 20])
        gen_device.add_newobj("click", "click~", numinlets=1, numoutlets=1, patching_rect=[100, 20, 50, 20])
        gen_device.add_newobj("gen", "gen~ @title Capture", numinlets=2, numoutlets=1, patching_rect=[170, 20, 100, 20])
        gen_device.add_newobj("buffer", "buffer~ grains", numinlets=2, numoutlets=2, patching_rect=[290, 20, 90, 20])
        gen_device.add_line("delay", 0, "click", 0)
        gen_device.add_line("click", 0, "gen", 0)
        gen_device.add_line("gen", 0, "buffer", 0)
        gen_snapshot = snapshot_from_device(gen_device)
        gen_candidates = extract_gen_processing_candidates(gen_snapshot)
        gen_knowledge = extract_snapshot_knowledge(gen_snapshot)

        assert len(gen_candidates) == 1
        assert gen_candidates[0]["candidate_name"] == "buffered_gen_capture_shell"
        assert gen_candidates[0]["motif_kinds"] == ["gen_processing_core"]
        assert gen_knowledge["summary"]["gen_processing_candidate_count"] == 1
        assert gen_knowledge["gen_processing_candidates"][0]["candidate_name"] == "buffered_gen_capture_shell"

    def test_generate_semantic_python_groups_sample_and_gen_candidates(self):
        device = AudioEffect("Semantic Granular Groups", 400, 220)
        device.add_newobj("buffer", "buffer~ grains", numinlets=2, numoutlets=2, patching_rect=[20, 20, 90, 20])
        device.add_newobj("peek", "peek~ grains", numinlets=2, numoutlets=1, patching_rect=[140, 20, 70, 20])
        device.add_newobj("metro", "metro 30", numinlets=2, numoutlets=1, patching_rect=[230, 20, 60, 20])
        device.add_line("metro", 0, "peek", 0)
        device.add_newobj("delay", "delay 10", numinlets=2, numoutlets=1, patching_rect=[20, 80, 60, 20])
        device.add_newobj("click", "click~", numinlets=1, numoutlets=1, patching_rect=[100, 80, 50, 20])
        device.add_newobj("gen", "gen~ @title Capture", numinlets=2, numoutlets=1, patching_rect=[170, 80, 100, 20])
        device.add_newobj("buffer_capture", "buffer~ captured", numinlets=2, numoutlets=2, patching_rect=[290, 80, 100, 20])
        device.add_line("delay", 0, "click", 0)
        device.add_line("click", 0, "gen", 0)
        device.add_line("gen", 0, "buffer_capture", 0)

        semantic_source = generate_semantic_python_from_snapshot(snapshot_from_device(device))

        assert "SNAPSHOT_SAMPLE_BUFFER_CANDIDATES" in semantic_source
        assert "SNAPSHOT_GEN_PROCESSING_CANDIDATES" in semantic_source
        assert "# semantic group: sample_visualization_shell" in semantic_source
        assert "# semantic group: buffered_gen_capture_shell" in semantic_source

    def test_extract_snapshot_knowledge_summarizes_controls_patterns_and_bridge(self):
        device = build_livemcp_bridge_demo()
        device.add_dial(
            "gain",
            "Gain",
            [18, 12, 48, 88],
            min_val=-70.0,
            max_val=6.0,
            initial=0.0,
            unitstyle=4,
        )
        device.add_dsp(*param_smooth("mod"))

        snapshot = snapshot_from_device(device)
        knowledge = extract_snapshot_knowledge(snapshot)

        assert knowledge["summary"]["bridge_enabled"] is True
        assert knowledge["summary"]["control_count"] >= 1
        assert knowledge["summary"]["recipe_count"] == 0
        assert knowledge["summary"]["display_role_counts"]["labels"] >= 1
        assert knowledge["bridge"]["enabled"] is True
        assert "livemcp_bridge_runtime.js" in knowledge["bridge"]["support_files"]
        assert any(control["varname"] == "Gain" for control in knowledge["controls"])
        assert any(pattern["kind"] == "param_smooth" for pattern in knowledge["patterns"])
        assert any(sidecar["kind"] == "javascript" for sidecar in knowledge["sidecars"])
        assert knowledge["display_groups"]["labels"]
        assert knowledge["lossiness"]["exact_patcher_dict"] is True
        assert knowledge["lossiness"]["bridge_reconstructed"] is False

    def test_extract_snapshot_knowledge_includes_generic_motifs(self):
        device = AudioEffect("Motif Knowledge", 260, 120)
        device.add_newobj("send_a", "s control_bus", numinlets=1, numoutlets=0, patching_rect=[20, 40, 70, 20])
        device.add_newobj("recv_a", "r control_bus", numinlets=0, numoutlets=1, patching_rect=[110, 40, 70, 20])
        device.add_bpatcher("panel_host", [20, 80, 100, 30], "status_panel.maxpat")

        snapshot = snapshot_from_device(device)
        knowledge = extract_snapshot_knowledge(snapshot)

        assert knowledge["summary"]["motif_count"] == 2
        assert any(entry["kind"] == "named_bus" for entry in knowledge["motifs"])
        assert any(entry["kind"] == "embedded_patcher" for entry in knowledge["motifs"])

    def test_extract_snapshot_knowledge_builds_cross_scope_named_bus_networks(self):
        device = AudioEffect("Bus Networks", 280, 160)
        device.add_newobj("send_root", "s shared_bus", numinlets=1, numoutlets=0, patching_rect=[20, 20, 70, 20])
        device.add_newobj("recv_root", "r shared_bus", numinlets=0, numoutlets=1, patching_rect=[110, 20, 70, 20])
        sub = Subpatcher("inner")
        sub.add_newobj("send_inner", "s shared_bus", numinlets=1, numoutlets=0, patching_rect=[10, 10, 70, 20])
        sub.add_newobj("recv_inner", "r shared_bus", numinlets=0, numoutlets=1, patching_rect=[90, 10, 70, 20])
        sub.add_newobj("send_local", "s local_bus", numinlets=1, numoutlets=0, patching_rect=[10, 40, 70, 20])
        sub.add_newobj("recv_local", "r local_bus", numinlets=0, numoutlets=1, patching_rect=[90, 40, 70, 20])
        device.add_subpatcher(sub, "inner_host", [20, 80, 120, 50])

        knowledge = extract_snapshot_knowledge(snapshot_from_device(device))

        shared = next(entry for entry in knowledge["named_bus_networks"] if entry["name"] == "shared_bus")
        local = next(entry for entry in knowledge["named_bus_networks"] if entry["name"] == "local_bus")

        assert knowledge["summary"]["named_bus_network_count"] == 2
        assert knowledge["summary"]["cross_scope_named_bus_network_count"] == 1
        assert shared["cross_scope"] is True
        assert shared["scope_count"] == 2
        assert shared["embedded_scope_count"] == 1
        assert shared["total_sender_count"] == 2
        assert shared["total_receiver_count"] == 2
        assert [scope["scope"] for scope in shared["scopes"]] == ["root", "embedded"]
        assert local["cross_scope"] is False
        assert local["scope_count"] == 1

    def test_extract_snapshot_knowledge_reports_live_api_helper_opportunities(self):
        device = AudioEffect("Live API Opportunities", 300, 180)
        device.add_dsp(*live_thisdevice("exact_dev", device_rect=[10, 120, 80, 20], device_attrs={"fontsize": 12.0}))
        device.add_dsp(
            *live_observer(
                "tempo",
                path="live_set",
                prop="tempo",
                path_rect=[120, 120, 100, 20],
                object_rect=[120, 150, 80, 20],
                observer_rect=[120, 180, 120, 20],
            )
        )
        for wrapped in device.boxes:
            box = wrapped["box"]
            if box["id"] == "tempo_observer":
                box["text"] = "live.observer"
                box["fontsize"] = 12.0
                break
        device.add_box({
            "box": {
                "id": "tempo_property",
                "maxclass": "message",
                "text": "property tempo",
                "patching_rect": [250, 180, 90, 20],
                "numinlets": 2,
                "numoutlets": 1,
            }
        })
        device.add_line("tempo_property", 0, "tempo_observer", 0)

        knowledge = extract_snapshot_knowledge(snapshot_from_device(device))

        assert knowledge["summary"]["live_api_helper_count"] == 1
        assert knowledge["summary"]["live_api_helper_opportunity_count"] == 1
        assert knowledge["live_api_helpers"][0]["helper_name"] == "live_thisdevice"
        assert knowledge["live_api_helper_opportunities"][0]["helper_name"] == "live_observer"
        assert knowledge["live_api_helper_opportunities"][0]["params"]["prop"] == "tempo"
        assert "indirect_property_binding" in knowledge["live_api_helper_opportunities"][0]["blocking_factors"]
        assert "noncanonical_box_attrs_or_layout" in knowledge["live_api_helper_opportunities"][0]["blocking_factors"]
        assert knowledge["live_api_helper_opportunities"][0]["normalization_level"] == "normalized_with_binding"
        assert knowledge["summary"]["live_api_normalization_candidate_count"] == 2
        assert knowledge["live_api_normalization_candidates"][0]["normalization_level"] == "exact"
        assert knowledge["live_api_normalization_candidates"][1]["helper_call"]["name"] == "live_observer"
        assert knowledge["live_api_normalization_candidates"][1]["helper_call"]["kwargs"]["prop"] == "tempo"
        assert "tempo_property" in knowledge["live_api_normalization_candidates"][1]["consume_box_ids"]
        assert knowledge["live_api_normalization_candidates"][1]["helper_call"]["kwargs"]["property_id"] == "tempo_property"

    def test_extract_controller_shell_candidates_detects_surface_and_sequencer_shells(self):
        device = AudioEffect("Controller Shells", 360, 200)
        device.add_box({
            "box": {
                "id": "msg",
                "maxclass": "message",
                "text": "mode 1",
                "patching_rect": [20, 0, 60, 20],
                "numinlets": 2,
                "numoutlets": 1,
            }
        })
        device.add_newobj("route", "route mode", numinlets=1, numoutlets=2, patching_rect=[20, 20, 80, 20])
        device.add_newobj("trigger", "t i i", numinlets=1, numoutlets=2, patching_rect=[120, 20, 40, 20])
        device.add_newobj("prepend", "prepend value", numinlets=1, numoutlets=1, patching_rect=[180, 20, 80, 20])
        device.add_newobj("device", "live.thisdevice", numinlets=1, numoutlets=2, patching_rect=[20, 50, 90, 20])
        device.add_newobj("send_a", "s shell_bus", numinlets=1, numoutlets=0, patching_rect=[120, 50, 70, 20])
        device.add_newobj("recv_a", "r shell_bus", numinlets=0, numoutlets=1, patching_rect=[210, 50, 70, 20])
        device.add_line("route", 0, "trigger", 0)

        device.add_newobj("sel", "sel 0 1", numinlets=1, numoutlets=3, patching_rect=[20, 100, 60, 20])
        device.add_newobj("gate", "gate 2", numinlets=2, numoutlets=2, patching_rect=[100, 100, 50, 20])
        device.add_newobj("delay", "delay 5", numinlets=2, numoutlets=1, patching_rect=[170, 100, 60, 20])
        device.add_newobj("defer", "deferlow", numinlets=1, numoutlets=1, patching_rect=[250, 100, 60, 20])
        device.add_newobj("send_loop", "s ---loop", numinlets=1, numoutlets=0, patching_rect=[20, 130, 70, 20])
        device.add_newobj("recv_loop", "r ---loop", numinlets=0, numoutlets=1, patching_rect=[110, 130, 70, 20])
        device.add_line("sel", 0, "gate", 0)
        device.add_line("defer", 0, "delay", 0)

        snapshot = snapshot_from_device(device)
        candidates = extract_controller_shell_candidates(snapshot)
        knowledge = extract_snapshot_knowledge(snapshot)

        assert {entry["candidate_name"] for entry in candidates} == {
            "controller_surface_shell",
            "sequencer_dispatch_shell",
        }
        assert {entry["helper_call"]["name"] for entry in candidates} == {
            "controller_surface_shell",
            "sequencer_dispatch_shell",
        }
        assert all(entry["exact"] for entry in candidates)
        assert knowledge["summary"]["controller_shell_candidate_count"] == 2
        assert {entry["candidate_name"] for entry in knowledge["controller_shell_candidates"]} == {
            "controller_surface_shell",
            "sequencer_dispatch_shell",
        }

    def test_extract_embedded_ui_shell_candidates_detects_embedded_hosts(self):
        device = AudioEffect("Embedded Shells", 320, 180)
        sub = Subpatcher("inner")
        sub.add_newobj("send", "s nested_bus", numinlets=1, numoutlets=0, patching_rect=[10, 10, 70, 20])
        sub.add_newobj("recv", "r nested_bus", numinlets=0, numoutlets=1, patching_rect=[90, 10, 70, 20])
        device.add_subpatcher(sub, "inner_host", [20, 70, 120, 60])
        device.add_newobj("host_send", "s outer_bus", numinlets=1, numoutlets=0, patching_rect=[20, 20, 70, 20])
        device.add_line("inner_host", 0, "host_send", 0)
        device.add_bpatcher("panel_host", [170, 70, 100, 40], "panel.maxpat", args="seed 9", embed=1)

        snapshot = snapshot_from_device(device)
        candidates = extract_embedded_ui_shell_candidates(snapshot)
        knowledge = extract_snapshot_knowledge(snapshot)

        assert len(candidates) == 2
        assert {entry["helper_call"]["name"] for entry in candidates} == {"embedded_ui_shell_v2"}
        assert {entry["params"]["host_kind"] for entry in candidates} == {"subpatcher", "bpatcher"}
        assert all(entry["exact"] for entry in candidates)
        subpatcher_candidate = next(entry for entry in candidates if entry["params"]["host_kind"] == "subpatcher")
        assert subpatcher_candidate["params"]["attached_box_count"] >= 1
        assert subpatcher_candidate["params"]["connected_line_count"] == 1
        assert knowledge["summary"]["embedded_ui_shell_candidate_count"] == 2
        assert len(knowledge["embedded_ui_shell_candidates"]) == 2
        assert {entry["params"]["host_kind"] for entry in knowledge["embedded_ui_shell_candidates"]} == {
            "subpatcher",
            "bpatcher",
        }

    def test_extract_factory_candidates_and_source_metadata(self, tmp_path):
        api_root = tmp_path / "Factory Packs" / "M4L Building Tools" / "API"
        api_root.mkdir(parents=True)
        api_device = AudioEffect("Max Api DeviceExplorer", 320, 180)
        api_device.add_dsp(*live_thisdevice("dev"))
        api_device.add_dsp(
            *live_parameter_probe(
                "probe",
                path="live_set tracks 0 devices 0 parameters 0",
                commands=["get value"],
            )
        )
        api_path = api_root / "Max Api DeviceExplorer.amxd"
        api_device.build(str(api_path))

        api_snapshot = snapshot_from_amxd(str(api_path))
        api_knowledge = extract_snapshot_knowledge(api_snapshot)
        api_candidates = extract_first_party_api_rig_candidates(api_snapshot)

        assert api_knowledge["source"]["source_lane"] == "factory"
        assert api_knowledge["source"]["pack_name"] == "M4L Building Tools"
        assert api_knowledge["source"]["pack_section"] == "API"
        assert len(api_candidates) == 1
        assert api_candidates[0]["params"]["api_family"] == "DeviceExplorer"
        assert api_knowledge["summary"]["first_party_api_rig_candidate_count"] == 1

        blocks_root = tmp_path / "Factory Packs" / "M4L Building Tools" / "Building Blocks" / "Max Audio Effect"
        blocks_root.mkdir(parents=True)
        block = AudioEffect("Max DelayLine", 320, 180)
        block.add_dsp(*param_smooth("smooth"))
        block.add_newobj("send_a", "s block_bus", numinlets=1, numoutlets=0, patching_rect=[20, 20, 70, 20])
        block.add_newobj("recv_a", "r block_bus", numinlets=0, numoutlets=1, patching_rect=[110, 20, 70, 20])
        block.add_newobj("loadbang", "loadbang", numinlets=1, numoutlets=1, patching_rect=[20, 60, 60, 20])
        block.add_newobj("defer", "deferlow", numinlets=1, numoutlets=1, patching_rect=[100, 60, 60, 20])
        block.add_newobj("init_t", "t b b", numinlets=1, numoutlets=2, patching_rect=[180, 60, 40, 20])
        block.add_line("loadbang", 0, "defer", 0)
        block.add_line("defer", 0, "init_t", 0)
        block_path = blocks_root / "Max DelayLine.amxd"
        block.build(str(block_path))

        block_snapshot = snapshot_from_amxd(str(block_path))
        block_knowledge = extract_snapshot_knowledge(block_snapshot)

        named_bus_candidates = extract_named_bus_router_candidates(block_snapshot)
        init_candidates = extract_init_dispatch_chain_candidates(block_snapshot)
        building_block_candidates = extract_building_block_candidates(block_snapshot)

        assert block_knowledge["source"]["pack_section"] == "Building Blocks"
        assert block_knowledge["source"]["pack_subsection"] == "Max Audio Effect"
        assert len(named_bus_candidates) == 1
        assert named_bus_candidates[0]["helper_call"]["name"] == "named_bus_router"
        assert len(init_candidates) == 1
        assert init_candidates[0]["helper_call"]["name"] == "init_dispatch_chain"
        assert len(building_block_candidates) == 1
        assert building_block_candidates[0]["params"]["block_name"] == "Max DelayLine"
        assert block_knowledge["summary"]["named_bus_router_candidate_count"] == 1
        assert block_knowledge["summary"]["init_dispatch_chain_candidate_count"] == 1
        assert block_knowledge["summary"]["building_block_candidate_count"] == 1

    def test_extract_first_party_abstraction_host_candidates_from_factory_path(self, tmp_path):
        root = tmp_path / "Factory Packs" / "M4L Building Tools" / "Building Blocks" / "Max Audio Effect"
        root.mkdir(parents=True)
        device = AudioEffect("Max GainDualMono", 320, 180)
        device.add_newobj("gain_l", "M4L.gain1~", numinlets=2, numoutlets=1, patching_rect=[20, 70, 70, 20])
        device.add_newobj("gain_r", "M4L.gain1~", numinlets=2, numoutlets=1, patching_rect=[140, 70, 70, 20])
        device.add_dial("gain", "Gain", [72, 18, 44, 44], min_val=-70.0, max_val=6.0, initial=0.0, unitstyle=4)
        device.add_comment("label", [66, 66, 60, 18], "Gain")
        device.add_line("gain", 0, "gain_l", 1)
        device.add_line("gain", 0, "gain_r", 1)
        path = root / "Max GainDualMono.amxd"
        device.build(str(path))

        snapshot = snapshot_from_amxd(str(path))
        candidates = extract_first_party_abstraction_host_candidates(snapshot)
        family_candidates = extract_first_party_abstraction_family_candidates(snapshot)
        knowledge = extract_snapshot_knowledge(snapshot)

        assert len(candidates) == 1
        candidate = candidates[0]
        assert candidate["params"]["primary_abstraction_name"] == "M4L.gain1~"
        assert candidate["params"]["abstraction_family"] == "gain_shell"
        assert candidate["params"]["host_box_count"] == 2
        assert candidate["params"]["attached_control_count"] >= 1
        assert candidate["params"]["control_varnames"] == ["Gain"]
        assert {"gain_l", "gain_r", "gain"} <= set(candidate["box_ids"])
        assert len(family_candidates) == 1
        assert family_candidates[0]["candidate_name"] == "gain_shell"
        assert knowledge["summary"]["first_party_abstraction_host_candidate_count"] == 1
        assert knowledge["summary"]["first_party_abstraction_family_candidate_count"] == 1
        assert len(knowledge["first_party_abstraction_host_candidates"]) == 1
        assert len(knowledge["first_party_abstraction_family_candidates"]) == 1

    def test_extract_poly_shell_candidates_detects_poly_hosts(self):
        device = AudioEffect("Poly Shell", 320, 180)
        device.add_newobj("voices", "poly~ grain_voice 8", numinlets=3, numoutlets=2, patching_rect=[20, 20, 100, 20])
        device.add_newobj("settings", "p Settings", numinlets=1, numoutlets=1, patching_rect=[20, 60, 80, 20])
        device.add_newobj("send_poly", "s voice_bus", numinlets=1, numoutlets=0, patching_rect=[140, 20, 70, 20])
        device.add_newobj("recv_poly", "r voice_bus", numinlets=0, numoutlets=1, patching_rect=[220, 20, 70, 20])
        device.add_line("voices", 0, "send_poly", 0)
        device.add_line("settings", 0, "voices", 1)

        snapshot = snapshot_from_device(device)
        candidates = extract_poly_shell_candidates(snapshot)
        knowledge = extract_snapshot_knowledge(snapshot)

        assert len(candidates) == 1
        assert candidates[0]["helper_call"]["name"] == "poly_shell"
        assert candidates[0]["params"]["attached_bus_names"] == ["voice_bus"]
        assert "settings" in candidates[0]["box_ids"]
        assert candidates[0]["params"]["direct_neighbor_count"] >= 2
        assert knowledge["summary"]["poly_shell_candidate_count"] == 1

    def test_extract_poly_shell_bank_candidates_groups_repeated_poly_hosts(self):
        device = AudioEffect("Poly Shell Bank", 420, 260)
        device.add_box({
            "box": {
                "id": "shared_mod",
                "maxclass": "flonum",
                "patching_rect": [190, 20, 50, 22],
                "numinlets": 1,
                "numoutlets": 2,
                "outlettype": ["", "bang"],
            }
        })
        for index in range(1, 4):
            y = 40 + (index - 1) * 60
            device.add_box({
                "box": {
                    "id": f"ui_{index}",
                    "maxclass": "bpatcher",
                    "name": "VoiceUi.maxpat",
                    "patching_rect": [20, y, 120, 24],
                    "numinlets": 4,
                    "numoutlets": 4,
                    "outlettype": ["", "", "", ""],
                }
            })
            device.add_newobj(
                f"poly_{index}",
                "poly~ voice_editor",
                numinlets=4,
                numoutlets=4,
                patching_rect=[170, y, 110, 20],
            )
            device.add_newobj(
                f"send_{index}",
                f"s voice{index}",
                numinlets=1,
                numoutlets=0,
                patching_rect=[310, y, 60, 20],
            )
            device.add_line(f"ui_{index}", 0, f"poly_{index}", 0)
            device.add_line(f"ui_{index}", 1, f"poly_{index}", 1)
            device.add_line(f"poly_{index}", 0, f"ui_{index}", 0)
            device.add_line(f"poly_{index}", 1, f"ui_{index}", 1)
            device.add_line(f"poly_{index}", 2, f"send_{index}", 0)
            device.add_line("shared_mod", 0, f"poly_{index}", 2)

        snapshot = snapshot_from_device(device)
        candidates = extract_poly_shell_bank_candidates(snapshot)
        knowledge = extract_snapshot_knowledge(snapshot)

        assert len(candidates) == 1
        assert candidates[0]["helper_call"]["name"] == "poly_shell_bank"
        assert candidates[0]["params"]["poly_shell_count"] == 3
        assert candidates[0]["params"]["target"] == "voice_editor"
        assert candidates[0]["params"]["indexed_bus_prefix"] == "voice"
        assert candidates[0]["params"]["indexed_bus_indices"] == [1, 2, 3]
        assert candidates[0]["params"]["bpatcher_names"] == ["VoiceUi.maxpat"]
        assert "shared_mod" in candidates[0]["params"]["shared_box_ids"]
        assert knowledge["summary"]["poly_shell_bank_candidate_count"] == 1

        editor_candidates = extract_poly_editor_bank_candidates(snapshot)
        assert len(editor_candidates) == 1
        assert editor_candidates[0]["candidate_name"] == "poly_editor_bank"
        assert editor_candidates[0]["params"]["voice_count"] == 3
        assert editor_candidates[0]["params"]["editor_ui_names"] == ["VoiceUi.maxpat"]
        assert knowledge["summary"]["poly_editor_bank_candidate_count"] == 1

    def test_extract_behavior_hints_for_mapping_workflow(self):
        device = Instrument("Mapped Random Control", 420, 260)
        device.add_box({
            "box": {
                "id": "shared_mod",
                "maxclass": "flonum",
                "patching_rect": [190, 20, 50, 22],
                "numinlets": 1,
                "numoutlets": 2,
                "outlettype": ["", "bang"],
            }
        })
        for index in range(1, 4):
            y = 40 + (index - 1) * 60
            device.add_box({
                "box": {
                    "id": f"ui_{index}",
                    "maxclass": "bpatcher",
                    "name": "Abl.MapUi.RNDGEN.maxpat",
                    "patching_rect": [20, y, 120, 24],
                    "numinlets": 4,
                    "numoutlets": 4,
                    "outlettype": ["", "", "", ""],
                }
            })
            device.add_newobj(
                f"poly_{index}",
                "poly~ Abl.Map.edit",
                numinlets=4,
                numoutlets=4,
                patching_rect=[170, y, 110, 20],
            )
            device.add_newobj(
                f"send_{index}",
                f"s ---m{index}",
                numinlets=1,
                numoutlets=0,
                patching_rect=[310, y, 60, 20],
            )
            device.add_line(f"ui_{index}", 0, f"poly_{index}", 0)
            device.add_line(f"ui_{index}", 1, f"poly_{index}", 1)
            device.add_line(f"poly_{index}", 0, f"ui_{index}", 0)
            device.add_line(f"poly_{index}", 1, f"ui_{index}", 1)
            device.add_line(f"poly_{index}", 2, f"send_{index}", 0)
            device.add_line("shared_mod", 0, f"poly_{index}", 2)

        midi_logic = Subpatcher("MIDILogic")
        midi_logic.add_newobj("manualmode", "r ---manualmode", numinlets=0, numoutlets=1, patching_rect=[20, 20, 90, 20])
        midi_logic.add_newobj("compare", "== 0", numinlets=2, numoutlets=1, patching_rect=[120, 20, 40, 20])
        midi_logic.add_newobj("gate", "gate", numinlets=2, numoutlets=1, patching_rect=[180, 20, 40, 20])
        midi_logic.add_newobj("parse", "midiparse", numinlets=1, numoutlets=1, patching_rect=[240, 20, 70, 20])
        midi_logic.add_newobj("unpack", "unpack i i", numinlets=1, numoutlets=2, patching_rect=[320, 20, 70, 20])
        midi_logic.add_newobj("strip", "stripnote", numinlets=2, numoutlets=2, patching_rect=[400, 20, 70, 20])
        midi_logic.add_newobj("trigger", "t b", numinlets=1, numoutlets=1, patching_rect=[480, 20, 30, 20])
        midi_logic.add_newobj("send", "s ---notebang", numinlets=1, numoutlets=0, patching_rect=[520, 20, 80, 20])
        midi_logic.add_line("manualmode", 0, "compare", 0)
        midi_logic.add_line("compare", 0, "gate", 0)
        midi_logic.add_line("gate", 0, "parse", 0)
        midi_logic.add_line("parse", 0, "unpack", 0)
        midi_logic.add_line("unpack", 0, "strip", 0)
        midi_logic.add_line("unpack", 1, "strip", 1)
        midi_logic.add_line("strip", 1, "trigger", 0)
        midi_logic.add_line("trigger", 0, "send", 0)
        device.add_subpatcher(midi_logic, "midi_logic", [20, 220, 120, 50])

        qm = Subpatcher("qm")
        qm.add_newobj("start", "s ---qmap_start", numinlets=1, numoutlets=0, patching_rect=[20, 20, 90, 20])
        qm.add_newobj("done", "r ---done_qmap", numinlets=0, numoutlets=1, patching_rect=[130, 20, 90, 20])
        qm.add_newobj("qmap", "s ---qmap", numinlets=1, numoutlets=0, patching_rect=[240, 20, 70, 20])
        qm.add_newobj("update", "s ---update_local", numinlets=1, numoutlets=0, patching_rect=[330, 20, 100, 20])
        qm.add_newobj("clear", "r ---clearqmap", numinlets=0, numoutlets=1, patching_rect=[450, 20, 90, 20])
        device.add_subpatcher(qm, "qm_logic", [160, 220, 120, 50])

        ui = Subpatcher("UiScripting")
        ui.add_box({
            "box": {
                "id": "move",
                "maxclass": "message",
                "text": "setUiPos $1 $2 $3 $4",
                "patching_rect": [20, 20, 110, 20],
                "numinlets": 2,
                "numoutlets": 1,
            }
        })
        ui.add_box({
            "box": {
                "id": "width",
                "maxclass": "message",
                "text": "setwidth $1",
                "patching_rect": [150, 20, 80, 20],
                "numinlets": 2,
                "numoutlets": 1,
            }
        })
        ui.add_box({
            "box": {
                "id": "script",
                "maxclass": "message",
                "text": "script sendbox global presentation_rect 17. $1 65. 169.",
                "patching_rect": [250, 20, 220, 20],
                "numinlets": 2,
                "numoutlets": 1,
            }
        })
        device.add_subpatcher(ui, "ui_logic", [300, 220, 120, 50])

        snapshot = snapshot_from_device(device)
        snapshot["missing_support_files"] = [
            {"name": "Abl.Map.edit.maxpat"},
            {"name": "Transformdnk5.maxpat"},
        ]
        hints = extract_behavior_hints(snapshot)
        traces = extract_mapping_behavior_traces(snapshot)
        semantic_candidates = extract_mapping_semantic_candidates(snapshot)
        workflow_candidates = extract_mapping_workflow_candidates(snapshot)
        knowledge = extract_snapshot_knowledge(snapshot)
        hint_names = {entry["name"] for entry in hints}
        trace_names = {entry["name"] for entry in traces}
        semantic_candidate_names = {entry["candidate_name"] for entry in semantic_candidates}

        assert "multi_lane_mapping_bank" in hint_names
        assert "manual_or_midi_trigger_mode" in hint_names
        assert "mapping_session_controller" in hint_names
        assert "dynamic_panel_relayout" in hint_names
        assert "mapped_random_control_device" in hint_names
        assert "modulation_output_bank" in trace_names
        assert "trigger_source_cluster" in trace_names
        assert "mapping_session_lifecycle" in trace_names
        assert "lane_update_paths" in trace_names
        assert "hidden_mapping_engine" in trace_names
        assert "mapped_modulation_bank" in semantic_candidate_names
        assert "random_modulation_mapper" in semantic_candidate_names
        assert "triggered_parameter_mapper" in semantic_candidate_names
        assert len(workflow_candidates) == 1
        assert workflow_candidates[0]["candidate_name"] == "mapping_workflow_shell"
        assert workflow_candidates[0]["params"]["voice_count"] == 3
        assert workflow_candidates[0]["params"]["editor_target"] == "Abl.Map.edit"
        assert workflow_candidates[0]["params"]["manual_mode_bus"] == "---manualmode"
        assert workflow_candidates[0]["params"]["mapping_start_bus"] == "---qmap_start"
        assert workflow_candidates[0]["params"]["dynamic_panel_relayout"] is True
        assert knowledge["summary"]["behavior_hint_count"] == len(hints)
        assert knowledge["summary"]["mapping_behavior_trace_count"] == len(traces)
        assert knowledge["summary"]["mapping_semantic_candidate_count"] == len(semantic_candidates)
        assert knowledge["summary"]["mapping_workflow_candidate_count"] == 1

    def test_extract_mapping_semantic_candidates_for_control_banks(self):
        device = MidiEffect("Expression Control", 320, 115)
        for index in range(8):
            x = 8 + index * 38
            device.add_dial(
                f"macro_{index+1}",
                f"M{index+1}",
                [x, 18, 34, 72],
                min_val=0.0,
                max_val=127.0,
                initial=64.0,
                unitstyle=8,
                annotation_name=f"Macro {index+1} — outputs CC {index+1}",
            )
            device.add_newobj(
                f"int_{index+1}",
                "int",
                numinlets=2,
                numoutlets=1,
                outlettype=[""],
                patching_rect=[20 + index * 50, 200, 30, 20],
            )
            device.add_newobj(
                f"ctlout_{index+1}",
                f"ctlout {index+1} 1",
                numinlets=3,
                numoutlets=0,
                outlettype=[],
                patching_rect=[20 + index * 50, 230, 60, 20],
            )
            device.add_line(f"macro_{index+1}", 0, f"int_{index+1}", 0)
            device.add_line(f"int_{index+1}", 0, f"ctlout_{index+1}", 0)

        traces = extract_mapping_behavior_traces(snapshot_from_device(device))
        candidates = extract_mapping_semantic_candidates(snapshot_from_device(device))

        assert any(
            entry["name"] == "modulation_output_bank"
            and entry["params"]["output_mode"] == "midi_cc_output_bank"
            and entry["params"]["lane_count"] == 8
            for entry in traces
        )
        assert any(
            entry["candidate_name"] == "mapped_modulation_bank"
            for entry in candidates
        )
        assert not any(
            entry["candidate_name"] == "random_modulation_mapper"
            for entry in candidates
        )

    def test_extract_mapping_semantic_candidates_for_random_output_mapper(self):
        device = AudioEffect("Macro Randomizer", 300, 140)
        for index in range(7):
            x = 8 + index * 30
            device.add_dial(
                f"p{index+1}_dial",
                f"P{index+1}",
                [x, 38, 28, 70],
                min_val=0.0,
                max_val=100.0,
                initial=50.0,
                unitstyle=5,
                annotation_name=f"Parameter {index+1} — randomizable output",
            )
        device.add_dial(
            "rate_dial",
            "Rate",
            [222, 38, 40, 70],
            min_val=0.0,
            max_val=100.0,
            initial=25.0,
            unitstyle=5,
            annotation_name="Auto-randomize speed — 0 slow, 100 fast",
        )
        device.add_newobj("metro", "metro 500", numinlets=2, numoutlets=1, outlettype=["bang"], patching_rect=[20, 200, 70, 20])
        device.add_newobj("rate_scale", "scale 0. 100. 2000. 50.", numinlets=6, numoutlets=1, outlettype=[""], patching_rect=[120, 200, 120, 20])
        device.add_newobj("trig_sel", "sel 1", numinlets=2, numoutlets=2, outlettype=["bang", ""], patching_rect=[250, 200, 40, 20])
        device.add_newobj("fan", "t b b b b b b b", numinlets=1, numoutlets=7, outlettype=["bang"] * 7, patching_rect=[20, 240, 200, 20])
        device.add_line("rate_dial", 0, "rate_scale", 0)
        device.add_line("rate_scale", 0, "metro", 1)
        device.add_line("metro", 0, "fan", 0)
        device.add_line("trig_sel", 0, "fan", 0)
        for index in range(7):
            device.add_newobj(
                f"rand_{index+1}",
                "random 10001",
                numinlets=2,
                numoutlets=1,
                outlettype=[""],
                patching_rect=[20 + index * 50, 280, 65, 20],
            )
            device.add_newobj(
                f"rdiv_{index+1}",
                "/ 100.",
                numinlets=2,
                numoutlets=1,
                outlettype=[""],
                patching_rect=[20 + index * 50, 310, 40, 20],
            )
            device.add_line("fan", index, f"rand_{index+1}", 0)
            device.add_line(f"rand_{index+1}", 0, f"rdiv_{index+1}", 0)
            device.add_line(f"rdiv_{index+1}", 0, f"p{index+1}_dial", 0)

        traces = extract_mapping_behavior_traces(snapshot_from_device(device))
        candidates = extract_mapping_semantic_candidates(snapshot_from_device(device))

        assert any(entry["name"] == "trigger_source_cluster" for entry in traces)
        assert any(entry["name"] == "random_value_generation" for entry in traces)
        assert any(
            entry["candidate_name"] == "random_modulation_mapper"
            for entry in candidates
        )

    def test_extract_mapping_semantic_candidates_for_lfo_modulation_source(self):
        device = MidiEffect("LFO MIDI", 320, 140)
        device.add_button("tap", "tap", [10, 10, 24, 24])
        device.add_dial("rate", "Rate", [10, 40, 34, 70], min_val=0.0, max_val=127.0, initial=64.0)
        device.add_dial("shape", "Shape", [50, 40, 34, 70], min_val=0.0, max_val=127.0, initial=64.0)
        device.add_dial("depth", "Depth", [90, 40, 34, 70], min_val=0.0, max_val=127.0, initial=64.0)
        device.add_newobj("sel", "sel 1", numinlets=2, numoutlets=2, patching_rect=[44, 14, 40, 20])
        device.add_line("tap", 0, "sel", 0)

        sync = Subpatcher("sync")
        sync.add_newobj("phasor", "phasor~ @lock 1", numinlets=2, numoutlets=1, outlettype=["signal"], patching_rect=[20, 20, 90, 20])
        device.add_subpatcher(sync, "sync_shell", [20, 60, 90, 50])

        waveform = Subpatcher("waveform_select")
        waveform.add_newobj("triangle", "triangle~ 0.5", numinlets=2, numoutlets=1, outlettype=["signal"], patching_rect=[20, 20, 90, 20])
        waveform.add_newobj("selector", "selector~ 2 1", numinlets=3, numoutlets=1, outlettype=["signal"], patching_rect=[20, 50, 80, 20])
        waveform.add_newobj("noise", "noise~", numinlets=1, numoutlets=1, outlettype=["signal"], patching_rect=[120, 20, 50, 20])
        device.add_subpatcher(waveform, "wave_shell", [120, 60, 120, 50])

        hold = Subpatcher("Hold")
        hold.add_newobj("snapshot", "snapshot~", numinlets=2, numoutlets=1, outlettype=["float"], patching_rect=[20, 20, 70, 20])
        device.add_subpatcher(hold, "hold_shell", [250, 60, 90, 50])

        traces = extract_mapping_behavior_traces(snapshot_from_device(device))
        candidates = extract_mapping_semantic_candidates(snapshot_from_device(device))

        assert any(entry["name"] == "periodic_modulation_core" for entry in traces)
        assert any(
            entry["candidate_name"] == "lfo_modulation_source"
            for entry in candidates
        )

    def test_extract_mapping_semantic_candidates_for_device_parameter_randomizer(self):
        device = AudioEffect("Device Randomizer", 340, 180)
        device.add_button("trigger", "trigger", [10, 10, 24, 24])
        device.add_newobj("sel", "sel 1", numinlets=2, numoutlets=2, patching_rect=[44, 14, 40, 20])
        device.add_line("trigger", 0, "sel", 0)

        selected = Subpatcher("selectedID")
        selected.add_newobj("path", "live.path live_set view", numinlets=2, numoutlets=2, patching_rect=[20, 20, 100, 20])
        selected.add_newobj("object", "live.object", numinlets=2, numoutlets=1, outlettype=[""], patching_rect=[130, 20, 70, 20])
        selected.add_newobj("route", "route id", numinlets=2, numoutlets=2, patching_rect=[210, 20, 60, 20])
        device.add_subpatcher(selected, "selected_shell", [20, 70, 110, 50])

        params = Subpatcher("checkParamAvalibility")
        params.add_newobj("path", "live.path", numinlets=2, numoutlets=2, patching_rect=[20, 20, 60, 20])
        params.add_newobj("object", "live.object", numinlets=2, numoutlets=1, outlettype=[""], patching_rect=[90, 20, 70, 20])
        params.add_newobj("route", "route is_quantized", numinlets=2, numoutlets=2, patching_rect=[170, 20, 90, 20])
        params.add_newobj("store", "s ---StoreRandSettings", numinlets=1, numoutlets=0, patching_rect=[20, 50, 120, 20])
        params.add_newobj("recall", "r ---RecallRandSettings", numinlets=0, numoutlets=1, patching_rect=[150, 50, 130, 20])
        device.add_subpatcher(params, "params_shell", [150, 70, 120, 50])

        traces = extract_mapping_behavior_traces(snapshot_from_device(device))
        candidates = extract_mapping_semantic_candidates(snapshot_from_device(device))

        assert any(entry["name"] == "parameter_target_scan" for entry in traces)
        assert any(
            entry["candidate_name"] == "device_parameter_randomizer"
            for entry in candidates
        )

    def test_extract_mapping_semantic_candidates_do_not_promote_generic_periodic_core(self):
        device = MidiEffect("Periodic Internal", 320, 140)
        device.add_button("tap", "tap", [10, 10, 24, 24])
        device.add_newobj("sel", "sel 1", numinlets=2, numoutlets=2, patching_rect=[44, 14, 40, 20])
        device.add_line("tap", 0, "sel", 0)

        sync = Subpatcher("sync")
        sync.add_newobj("phasor", "phasor~ @lock 1", numinlets=2, numoutlets=1, outlettype=["signal"], patching_rect=[20, 20, 90, 20])
        sync.add_newobj("send", "s ---freq", numinlets=1, numoutlets=0, patching_rect=[120, 20, 60, 20])
        device.add_subpatcher(sync, "sync_shell", [20, 60, 90, 50])

        toctl = Subpatcher("toctlout")
        toctl.add_newobj("snapshot", "snapshot~ 10", numinlets=2, numoutlets=1, outlettype=["float"], patching_rect=[20, 20, 80, 20])
        device.add_subpatcher(toctl, "ctl_shell", [120, 60, 90, 50])

        traces = extract_mapping_behavior_traces(snapshot_from_device(device))
        candidates = extract_mapping_semantic_candidates(snapshot_from_device(device))

        assert any(entry["name"] == "periodic_modulation_core" for entry in traces)
        assert not any(
            entry["candidate_name"] == "lfo_modulation_source"
            for entry in candidates
        )

    def test_extract_mapping_semantic_candidates_do_not_promote_generic_parameter_scan(self):
        device = AudioEffect("Generic Parameter Scan", 340, 180)
        device.add_button("trigger", "trigger", [10, 10, 24, 24])
        device.add_newobj("sel", "sel 1", numinlets=2, numoutlets=2, patching_rect=[44, 14, 40, 20])
        device.add_line("trigger", 0, "sel", 0)

        api = Subpatcher("API.getDeviceOn")
        api.add_newobj("path", "live.path live_set", numinlets=2, numoutlets=2, patching_rect=[20, 20, 80, 20])
        api.add_newobj("object", "live.object", numinlets=2, numoutlets=1, outlettype=[""], patching_rect=[110, 20, 70, 20])
        api.add_newobj("message", "route Device On", numinlets=2, numoutlets=2, patching_rect=[190, 20, 90, 20])
        device.add_subpatcher(api, "api_shell", [20, 70, 110, 50])

        traces = extract_mapping_behavior_traces(snapshot_from_device(device))
        candidates = extract_mapping_semantic_candidates(snapshot_from_device(device))

        assert any(entry["name"] == "parameter_target_scan" for entry in traces)
        assert not any(
            entry["candidate_name"] == "device_parameter_randomizer"
            for entry in candidates
        )

    def test_extract_named_bus_router_candidates_include_attached_shell_neighbors(self):
        device = AudioEffect("Named Bus Shell", 320, 180)
        device.add_newobj("sender", "s voice_bus", numinlets=1, numoutlets=0, patching_rect=[20, 20, 70, 20])
        device.add_newobj("receiver", "r voice_bus", numinlets=0, numoutlets=1, patching_rect=[120, 20, 70, 20])
        device.add_box({
            "box": {
                "id": "monitor",
                "maxclass": "flonum",
                "patching_rect": [220, 20, 50, 20],
                "numinlets": 1,
                "numoutlets": 2,
                "outlettype": ["", "bang"],
            }
        })
        device.add_line("receiver", 0, "monitor", 0)

        candidates = extract_named_bus_router_candidates(snapshot_from_device(device))

        assert len(candidates) == 1
        assert candidates[0]["helper_call"]["name"] == "named_bus_router"
        assert "monitor" in candidates[0]["box_ids"]
        assert candidates[0]["params"]["attached_neighbor_count"] >= 1

    def test_extract_presentation_widget_cluster_candidates_detect_factory_clusters(self, tmp_path):
        root = tmp_path / "Factory Packs" / "M4L Building Tools" / "Tools" / "Max Audio Effect"
        root.mkdir(parents=True)
        device = AudioEffect("Factory UI Cluster", 320, 180)
        for box_id, maxclass, text, rect in [
            ("dial_a", "live.dial", None, [20, 20, 44, 44]),
            ("dial_b", "live.dial", None, [72, 20, 44, 44]),
            ("label_a", "comment", "Rate", [20, 68, 40, 18]),
            ("label_b", "comment", "Depth", [72, 68, 40, 18]),
        ]:
            box = {
                "id": box_id,
                "maxclass": maxclass,
                "patching_rect": rect,
                "presentation_rect": rect,
                "presentation": 1,
                "numinlets": 1,
                "numoutlets": 1 if maxclass != "comment" else 0,
            }
            if text is not None:
                box["text"] = text
            device.add_box({"box": box})
        device.add_box({
            "box": {
                "id": "far_toggle",
                "maxclass": "live.toggle",
                "patching_rect": [220, 120, 20, 20],
                "presentation_rect": [220, 120, 20, 20],
                "presentation": 1,
                "numinlets": 1,
                "numoutlets": 1,
            }
        })
        path = root / "Factory UI Cluster.amxd"
        device.build(str(path))

        snapshot = snapshot_from_amxd(str(path))
        candidates = extract_presentation_widget_cluster_candidates(snapshot)
        knowledge = extract_snapshot_knowledge(snapshot)

        assert len(candidates) == 1
        assert set(candidates[0]["box_ids"]) >= {"dial_a", "dial_b", "label_a", "label_b"}
        assert "far_toggle" not in candidates[0]["box_ids"]
        assert knowledge["summary"]["presentation_widget_cluster_candidate_count"] == 1

    def test_extract_live_api_normalization_candidates_marks_manual_review(self):
        device = AudioEffect("Live API Manual Review", 320, 180)
        device.add_newobj("path_direct", "live.path live_set", numinlets=2, numoutlets=2, patching_rect=[20, 120, 90, 20])
        device.add_newobj("observer_direct", "live.observer", numinlets=2, numoutlets=2, patching_rect=[120, 120, 90, 20])
        device.add_newobj("observer_defer", "deferlow", numinlets=1, numoutlets=1, patching_rect=[220, 120, 60, 20])
        device.add_box({
            "box": {
                "id": "observer_direct_property",
                "maxclass": "message",
                "text": "property tempo",
                "patching_rect": [20, 150, 90, 20],
                "numinlets": 2,
                "numoutlets": 1,
            }
        })
        device.add_line("path_direct", 1, "observer_direct", 1)
        device.add_line("observer_direct_property", 0, "observer_direct", 0)
        device.add_line("observer_defer", 0, "observer_direct", 0)

        candidates = extract_live_api_normalization_candidates(snapshot_from_device(device))

        assert len(candidates) == 1
        assert candidates[0]["helper_name"] == "live_observer"
        assert candidates[0]["normalization_level"] == "manual_review"
        assert "extra_component_boxes" in candidates[0]["blocking_factors"]

    def test_extract_snapshot_knowledge_reports_embedded_patcher_structure(self):
        device = AudioEffect("Embedded Knowledge", 260, 140)
        outer = Subpatcher("outer")
        outer.add_newobj("route", "route value", numinlets=1, numoutlets=2, patching_rect=[10, 10, 70, 20])
        outer.add_newobj("send_outer", "s nested_bus", numinlets=1, numoutlets=0, patching_rect=[95, 10, 80, 20])
        outer.add_newobj("recv_outer", "r nested_bus", numinlets=0, numoutlets=1, patching_rect=[185, 10, 80, 20])
        inner = Subpatcher("inner")
        inner.add_dsp(*param_smooth("smooth"))
        inner.add_newobj("tap", "s nested_bus", numinlets=1, numoutlets=0, patching_rect=[10, 10, 70, 20])
        inner.add_newobj("recv_inner", "r nested_bus", numinlets=0, numoutlets=1, patching_rect=[90, 10, 70, 20])
        outer.add_box(inner.to_box("inner_box", [20, 50, 120, 70]))
        device.add_subpatcher(outer, "outer_box", [20, 50, 120, 70])

        snapshot = snapshot_from_device(device)
        knowledge = extract_snapshot_knowledge(snapshot)

        assert knowledge["summary"]["embedded_patcher_count"] == 2
        assert knowledge["embedded_patchers"][0]["host_kind"] == "subpatcher"
        assert knowledge["embedded_patchers"][0]["box_count"] == 4
        assert knowledge["embedded_patchers"][0]["direct_embedded_child_count"] == 1
        assert knowledge["embedded_patchers"][0]["motif_count"] == 2
        assert knowledge["embedded_patchers"][0]["motif_kinds"] == ["named_bus", "embedded_patcher"]
        assert knowledge["embedded_patchers"][1]["depth"] == 2
        assert knowledge["embedded_patchers"][1]["object_name_counts"]["s"] == 1
        assert knowledge["embedded_patchers"][1]["pattern_count"] == 1
        assert knowledge["embedded_patchers"][1]["pattern_kinds"] == ["param_smooth"]
        assert knowledge["embedded_patchers"][1]["motif_kinds"] == ["named_bus"]
        assert knowledge["embedded_patchers"][1]["live_api_archetypes"] == []
        assert knowledge["summary"]["embedded_pattern_count"] == 1
        assert knowledge["summary"]["embedded_motif_count"] == 3

    def test_extract_embedded_patcher_snapshots_returns_nested_snapshots(self):
        device = AudioEffect("Embedded Snapshot Export", 260, 140)
        outer = Subpatcher("outer")
        inner = Subpatcher("inner")
        inner.add_dsp(*param_smooth("smooth"))
        inner.add_newobj("send_inner", "s inner_bus", numinlets=1, numoutlets=0, patching_rect=[10, 40, 70, 20])
        inner.add_newobj("recv_inner", "r inner_bus", numinlets=0, numoutlets=1, patching_rect=[90, 40, 70, 20])
        outer.add_box(inner.to_box("inner_box", [20, 50, 120, 70]))
        device.add_subpatcher(outer, "outer_box", [20, 50, 120, 70])

        snapshot = snapshot_from_device(device)
        embedded = extract_embedded_patcher_snapshots(snapshot)

        assert len(embedded) == 2
        assert embedded[0]["host_box_id"] == "outer_box"
        assert embedded[1]["ancestry_box_ids"] == ["outer_box"]
        assert embedded[1]["snapshot"]["analysis"]["patterns"][0]["kind"] == "param_smooth"
        assert embedded[1]["snapshot"]["analysis"]["motifs"][0]["kind"] == "named_bus"

    def test_extract_snapshot_knowledge_reports_recipes_and_bridge_lossiness(self):
        device = AudioEffect("Knowledge Recipes", 260, 120)
        gain_controlled_stage(device, "trim", [10, 10, 44, 88], x=45, y=60)
        recipe_snapshot = snapshot_from_device(device)
        recipe_knowledge = extract_snapshot_knowledge(recipe_snapshot)

        assert recipe_knowledge["summary"]["recipe_count"] == 1
        assert recipe_knowledge["recipes"][0]["kind"] == "gain_controlled_stage"
        assert recipe_knowledge["recipes"][0]["recipeizable"] is True

        bridge_snapshot = snapshot_from_bridge_payload(
            current_patcher={
                "bridge_session_id": "livemcp-session-88",
                "name": "Bridge Lossy",
                "filepath": None,
                "locked": False,
                "presentation_mode": True,
            },
            selected_device={
                "device_name": "Bridge Lossy",
                "class_name": "MxDeviceAudioEffect",
            },
            boxes=[
                {
                    "box_id": "bridge_demo_runtime",
                    "maxclass": "newobj",
                    "varname": "bridge_demo_runtime",
                    "boxtext": "js livemcp_bridge_runtime.js",
                    "rect": [200.0, 240.0, 160.0, 20.0],
                    "presentation_rect": None,
                    "hidden": False,
                    "background": False,
                }
            ],
            support_files=[
                {
                    "name": "livemcp_bridge_runtime.js",
                    "type": "TEXT",
                    "content": "autowatch = 1;\n",
                }
            ],
        )
        bridge_knowledge = extract_snapshot_knowledge(bridge_snapshot)

        assert bridge_knowledge["lossiness"]["bridge_reconstructed"] is True
        assert bridge_knowledge["lossiness"]["exact_patcher_dict"] is False
        assert bridge_knowledge["lossiness"]["has_line_data"] is False
        assert bridge_knowledge["summary"]["lossy"] is True
        assert bridge_knowledge["lossiness"]["notes"]
        assert bridge_knowledge["lossiness"]["notes"][-1].startswith("Snapshot originated from a LiveMCP bridge payload")

    def test_extract_snapshot_knowledge_handles_uncollapsed_patterns(self):
        device = AudioEffect("Selector Knowledge", 260, 120)
        device.add_newobj(
            "route",
            "selector~ 2 1",
            numinlets=3,
            numoutlets=1,
            outlettype=["signal"],
            patching_rect=[90, 60, 72, 20],
        )

        snapshot = snapshot_from_device(device)
        knowledge = extract_snapshot_knowledge(snapshot)

        assert knowledge["summary"]["pattern_count"] == 1
        assert knowledge["patterns"][0]["kind"] == "selector"
        assert knowledge["patterns"][0]["helperizable"] is False
        assert knowledge["patterns"][0]["helper_name"] is None

    def test_detect_snapshot_recipes_can_be_recognized_without_recipe_collapse(self):
        device = AudioEffect("Recipe Variants", 260, 120)
        gain_controlled_stage(device, "trim", [10, 10, 44, 88], x=45, y=60)
        for wrapped in device.boxes:
            box = wrapped["box"]
            if box["id"] == "trim_gain":
                box["patching_rect"] = [300, 300, 40, 20]
                break

        snapshot = snapshot_from_device(device)
        recipes = detect_snapshot_recipes(snapshot)

        assert len(recipes) == 1
        assert recipes[0]["kind"] == "gain_controlled_stage"
        assert recipes[0]["recipeizable"] is False
        assert recipes[0]["recipe"] is None

    def test_detect_snapshot_recipes_midi_note_gate_nondefault_channel_stays_uncollapsed(self):
        device = AudioEffect("MIDI Recipe Variants", 260, 120)
        midi_note_gate(device, "keys", x=50, y=40)
        for wrapped in device.boxes:
            box = wrapped["box"]
            if box["id"] == "keys_notein":
                box["text"] = "notein 2"
                break

        snapshot = snapshot_from_device(device)
        recipes = detect_snapshot_recipes(snapshot)

        assert len(recipes) == 1
        assert recipes[0]["kind"] == "midi_note_gate"
        assert recipes[0]["params"]["channel"] == 2
        assert recipes[0]["recipeizable"] is False
        assert recipes[0]["recipe"] is None

    def test_detect_snapshot_recipes_transport_sync_lfo_nondefault_lfo_stays_uncollapsed(self):
        device = AudioEffect("Transport LFO Variants", 260, 120)
        transport_sync_lfo_recipe(device, "sync", x=50, y=40)
        for wrapped in device.boxes:
            box = wrapped["box"]
            if box["id"] == "sync_lfo_osc":
                box["text"] = "phasor~"
                break

        snapshot = snapshot_from_device(device)
        recipes = detect_snapshot_recipes(snapshot)

        assert len(recipes) == 1
        assert recipes[0]["kind"] == "transport_sync_lfo_recipe"
        assert recipes[0]["params"]["shape"] == "saw"
        assert recipes[0]["recipeizable"] is False
        assert recipes[0]["recipe"] is None


class TestGeneratedPython:
    def test_generated_python_rebuilds_equivalent_device(self, tmp_path):
        device = AudioEffect("Reverse Me", 180, 96)
        device.add_panel("bg", [0, 0, 180, 96], bgcolor=[0.08, 0.09, 0.10, 1.0])
        device.add_comment("label", [16, 18, 148, 18], "Reverse me")
        device.add_support_file("helper.js", "outlets = 1;\n", file_type="TEXT")

        snapshot = snapshot_from_device(device)
        source = generate_python_from_snapshot(snapshot)
        namespace = {}

        exec(source, namespace)

        output = tmp_path / "reverse_me.amxd"
        written = namespace["build"](str(output))
        rebuilt = output.read_bytes()
        expected = build_amxd(
            snapshot["patcher"],
            DEVICE_TYPE_CODES[snapshot["device"]["device_type"]],
        )

        assert written == len(expected)
        assert rebuilt == expected
        assert (tmp_path / "helper.js").read_text() == "outlets = 1;\n"
        assert "write_amxd" in source
        assert "SUPPORT_FILES" in source

    def test_builder_python_rebuilds_semantic_device(self, tmp_path):
        device = AudioEffect("Semantic Reverse", 180, 96)
        device.add_panel("bg", [0, 0, 180, 96], bgcolor=[0.08, 0.09, 0.10, 1.0])
        device.add_comment("label", [16, 18, 148, 18], "Semantic")
        device.add_newobj(
            "mul_l",
            "*~ 1.",
            numinlets=2,
            numoutlets=1,
            outlettype=["signal"],
            patching_rect=[30, 100, 40, 20],
        )
        device.add_line("obj-plugin", 0, "mul_l", 0)

        snapshot = snapshot_from_device(device)
        source = generate_builder_python_from_snapshot(snapshot)
        namespace = {}

        exec(source, namespace)

        rebuilt_device = namespace["build_device"]()
        output = tmp_path / "semantic_reverse.amxd"
        written = namespace["build"](str(output))
        rebuilt = output.read_bytes()
        expected = device.to_bytes()

        assert written == len(expected)
        assert rebuilt == expected
        assert rebuilt_device.device_type == "audio_effect"
        assert "AudioEffect" in source
        assert "device.add_panel(" in source
        assert "device.add_comment(" in source
        assert "device.add_newobj(" in source

    def test_optimized_python_rebuilds_helper_pattern_device(self, tmp_path):
        device = AudioEffect("Optimized Reverse", 240, 110)
        device.add_dsp(*param_smooth("mod"))
        device.add_dsp(*delay_line("echo", max_delay_ms=750))
        device.add_dsp(
            *gain_stage(
                "trim",
                patching_rect_l=[40, 120, 40, 20],
                patching_rect_r=[160, 120, 40, 20],
            )
        )
        device.add_line("obj-plugin", 0, "echo_tapin", 0)
        device.add_line("echo_tapout", 0, "trim_l", 0)
        device.add_line("obj-plugin", 1, "trim_r", 0)
        device.add_line("trim_l", 0, "obj-plugout", 0)
        device.add_line("trim_r", 0, "obj-plugout", 1)

        snapshot = snapshot_from_device(device)
        source = generate_optimized_python_from_snapshot(snapshot)
        namespace = {}

        exec(source, namespace)

        rebuilt_device = namespace["build_device"]()
        output = tmp_path / "optimized_reverse.amxd"
        written = namespace["build"](str(output))
        rebuilt = output.read_bytes()
        expected = device.to_bytes()

        assert written == len(expected)
        assert rebuilt == expected
        assert rebuilt_device.device_type == "audio_effect"
        assert "param_smooth" in source
        assert "delay_line" in source
        assert "gain_stage" in source
        assert "device.add_dsp(" in source

    def test_optimized_python_rebuilds_live_object_path_probe(self, tmp_path):
        device = AudioEffect("Live API Probe", 300, 140)
        device.add_dsp(
            *live_object_path(
                "probe",
                path="live_set tracks 0 devices 0 parameters 0",
                path_rect=[30, 120, 180, 20],
                object_rect=[30, 150, 100, 20],
            )
        )
        device.add_box({
            "box": {
                "id": "probe_message",
                "maxclass": "message",
                "text": "id",
                "patching_rect": [150, 150, 180, 20],
                "numinlets": 2,
                "numoutlets": 1,
            }
        })
        device.add_line("probe_message", 0, "probe_obj", 0)

        snapshot = snapshot_from_device(device)
        source = generate_optimized_python_from_snapshot(snapshot)
        namespace = {}

        exec(source, namespace)

        output = tmp_path / "live_api_probe.amxd"
        written = namespace["build"](str(output))
        rebuilt = output.read_bytes()
        expected = device.to_bytes()

        assert written == len(expected)
        assert rebuilt == expected
        assert "live_object_path(" in source
        assert "device.add_newobj('probe_path'" not in source
        assert "device.add_newobj('probe_obj'" not in source

    def test_optimized_python_rebuilds_live_parameter_probe_helper(self, tmp_path):
        device = AudioEffect("Live API Parameter Probe", 340, 150)
        device.add_dsp(
            *live_parameter_probe(
                "probe",
                path="live_set tracks 0 devices 0 parameters 0",
                commands=["get max", "get min", "get value", "call str_for_value 0.5"],
                path_rect=[30, 120, 180, 20],
                object_rect=[30, 150, 100, 20],
                message_rect=[150, 150, 180, 20],
            )
        )

        snapshot = snapshot_from_device(device)
        knowledge = extract_snapshot_knowledge(snapshot)
        source = generate_optimized_python_from_snapshot(snapshot)
        namespace = {}

        exec(source, namespace)

        output = tmp_path / "live_api_parameter_probe.amxd"
        written = namespace["build"](str(output))
        rebuilt = output.read_bytes()
        expected = device.to_bytes()

        assert written == len(expected)
        assert rebuilt == expected
        assert any(entry["helper_name"] == "live_parameter_probe" for entry in knowledge["live_api_helpers"])
        assert "live_parameter_probe(" in source
        assert "device.add_box({'box': {'id': 'probe_message'" not in source

    def test_optimized_python_rebuilds_object_only_live_parameter_probe_helper(self, tmp_path):
        device = AudioEffect("Object Probe", 360, 170)
        device.add_dsp(
            *live_parameter_probe(
                "probe",
                path=None,
                commands=["get name", "get max", "get min", "get value"],
                route_selectors=["value", "max", "min", "name"],
                object_rect=[40, 120, 121, 22],
                message_rect=[20, 90, 186, 20],
                route_rect=[40, 150, 134, 20],
            )
        )

        snapshot = snapshot_from_device(device)
        knowledge = extract_snapshot_knowledge(snapshot)
        source = generate_optimized_python_from_snapshot(snapshot)
        namespace = {}

        exec(source, namespace)

        output = tmp_path / "object_probe.amxd"
        written = namespace["build"](str(output))
        rebuilt = output.read_bytes()
        expected = device.to_bytes()

        assert written == len(expected)
        assert rebuilt == expected
        assert any(entry["helper_name"] == "live_parameter_probe" for entry in knowledge["live_api_helpers"])
        assert "live_parameter_probe(" in source
        assert "path=None" in source
        assert "route_selectors=['value', 'max', 'min', 'name']" in source
        assert "device.add_newobj(\n        'probe_route'" not in source

    def test_optimized_python_recovers_trigger_wrapped_live_parameter_probe(self, tmp_path):
        device = AudioEffect("External Probe", 360, 170)
        device.add_newobj(
            "probe_route",
            "route value max min name",
            numinlets=5,
            numoutlets=5,
            outlettype=["", "", "", "", ""],
            patching_rect=[40, 150, 134, 20],
        )
        device.add_box({
            "box": {
                "id": "probe_message",
                "maxclass": "message",
                "text": "get name, get max, get min, get value",
                "patching_rect": [20, 90, 186, 20],
                "numinlets": 2,
                "numoutlets": 1,
                "outlettype": [""],
            }
        })
        device.add_newobj(
            "probe_trigger",
            "t b s",
            numinlets=1,
            numoutlets=2,
            outlettype=["bang", ""],
            patching_rect=[34, 60, 29.5, 20],
        )
        device.add_newobj(
            "probe_obj",
            "live.object",
            numinlets=2,
            numoutlets=1,
            outlettype=[""],
            patching_rect=[40, 120, 121, 22],
        )
        device.add_line("probe_message", 0, "probe_obj", 0)
        device.add_line("probe_trigger", 0, "probe_message", 0)
        device.lines.append(patchline("probe_trigger", 1, "probe_obj", 0, order=1))
        device.add_line("probe_obj", 0, "probe_route", 0)

        snapshot = snapshot_from_device(device)
        knowledge = extract_snapshot_knowledge(snapshot)
        source = generate_optimized_python_from_snapshot(snapshot)
        namespace = {}

        exec(source, namespace)

        output = tmp_path / "external_probe.amxd"
        written = namespace["build"](str(output))
        rebuilt = output.read_bytes()
        expected = device.to_bytes()

        assert written == len(expected)
        assert rebuilt == expected
        assert any(entry["helper_name"] == "live_parameter_probe" for entry in knowledge["live_api_helpers"])
        assert "live_parameter_probe(" in source
        assert "trigger_text='t b s'" in source
        assert "device.add_newobj(\n        'probe_trigger'" not in source

    def test_optimized_python_rebuilds_live_observer_helper(self, tmp_path):
        device = AudioEffect("Live API Observer", 300, 160)
        device.add_dsp(
            *live_observer(
                "tempo",
                path="live_set",
                prop="tempo",
                path_rect=[30, 120, 100, 20],
                object_rect=[30, 150, 80, 20],
                observer_rect=[30, 180, 120, 20],
            )
        )
        device.add_number_box(
            "tempo_display",
            "Tempo",
            [10, 10, 90, 22],
            min_val=60.0,
            max_val=200.0,
            initial=120.0,
            unitstyle=3,
        )
        device.add_line("tempo_observer", 0, "tempo_display", 0)

        snapshot = snapshot_from_device(device)
        source = generate_optimized_python_from_snapshot(snapshot)
        namespace = {}

        exec(source, namespace)

        output = tmp_path / "live_api_observer.amxd"
        written = namespace["build"](str(output))
        rebuilt = output.read_bytes()
        expected = device.to_bytes()

        assert written == len(expected)
        assert rebuilt == expected
        assert "live_observer(" in source
        assert "device.add_newobj('tempo_observer'" not in source

    def test_optimized_python_rebuilds_direct_live_observer_helper(self, tmp_path):
        device = AudioEffect("Live API Direct Observer", 300, 160)
        device.add_dsp(
            *live_observer(
                "transport",
                path="live_set",
                prop="is_playing",
                via_object=False,
                bind_via_message=True,
                path_rect=[30, 120, 100, 20],
                property_rect=[140, 120, 100, 20],
                observer_rect=[250, 120, 100, 20],
            )
        )

        snapshot = snapshot_from_device(device)
        source = generate_optimized_python_from_snapshot(snapshot)
        namespace = {}

        exec(source, namespace)

        output = tmp_path / "live_api_direct_observer.amxd"
        written = namespace["build"](str(output))
        rebuilt = output.read_bytes()
        expected = device.to_bytes()

        assert written == len(expected)
        assert rebuilt == expected
        assert "live_observer(" in source
        assert "via_object=False" in source
        assert "bind_via_message=True" in source

    def test_optimized_python_rebuilds_live_set_control_helper(self, tmp_path):
        device = AudioEffect("Live API Control", 300, 160)
        device.add_dsp(
            *live_set_control(
                "tempo",
                path="live_set",
                prop="tempo",
                path_rect=[30, 120, 100, 20],
                object_rect=[30, 150, 120, 20],
            )
        )
        device.add_newobj(
            "tempo_value",
            "f 120.",
            numinlets=2,
            numoutlets=1,
            outlettype=[""],
            patching_rect=[180, 150, 42, 20],
        )
        device.add_line("tempo_value", 0, "tempo_obj", 0)

        snapshot = snapshot_from_device(device)
        source = generate_optimized_python_from_snapshot(snapshot)
        namespace = {}

        exec(source, namespace)

        output = tmp_path / "live_api_control.amxd"
        written = namespace["build"](str(output))
        rebuilt = output.read_bytes()
        expected = device.to_bytes()

        assert written == len(expected)
        assert rebuilt == expected
        assert "live_set_control(" in source
        assert "device.add_newobj('tempo_obj'" not in source

    def test_optimized_python_rebuilds_device_active_state_helper(self, tmp_path):
        device = AudioEffect("Device Active Control", 280, 140)
        device.add_toggle("power", "Power", [10, 10, 40, 22])
        device.add_dsp(
            *device_active_state(
                "active",
                prepend_rect=[30, 120, 92, 20],
                device_rect=[30, 150, 80, 20],
            )
        )
        device.add_line("power", 0, "active_prepend", 0)

        snapshot = snapshot_from_device(device)
        source = generate_optimized_python_from_snapshot(snapshot)
        namespace = {}

        exec(source, namespace)

        output = tmp_path / "device_active_state.amxd"
        written = namespace["build"](str(output))
        rebuilt = output.read_bytes()
        expected = device.to_bytes()

        assert written == len(expected)
        assert rebuilt == expected
        assert "device_active_state(" in source
        assert "device.add_newobj('active_device'" not in source

    def test_optimized_python_recovers_device_to_prepend_active_state(self, tmp_path):
        device = AudioEffect("External Device Active", 280, 140)
        device.add_newobj(
            "active_device",
            "live.thisdevice",
            numinlets=1,
            numoutlets=3,
            outlettype=["bang", "int", "int"],
            patching_rect=[30, 150, 77, 20],
        )
        device.add_newobj(
            "active_prepend",
            "prepend active",
            numinlets=1,
            numoutlets=1,
            outlettype=[""],
            patching_rect=[30, 120, 79, 20],
        )
        device.lines.append(patchline("active_device", 1, "active_prepend", 0, order=1))

        snapshot = snapshot_from_device(device)
        knowledge = extract_snapshot_knowledge(snapshot)
        source = generate_optimized_python_from_snapshot(snapshot)
        namespace = {}

        exec(source, namespace)

        output = tmp_path / "device_active_state_external.amxd"
        written = namespace["build"](str(output))
        rebuilt = output.read_bytes()
        expected = device.to_bytes()

        assert written == len(expected)
        assert rebuilt == expected
        assert any(entry["helper_name"] == "device_active_state" for entry in knowledge["live_api_helpers"])
        assert "device_active_state(" in source
        assert "from_device_outlet=1" in source
        assert "device.add_newobj('active_device'" not in source

    def test_optimized_python_recovers_live_state_observer_helper(self, tmp_path):
        device = AudioEffect("Scale State", 320, 180)
        device.add_dsp(
            *live_state_observer(
                "state",
                path="live_set",
                prop="scale_mode",
                device_rect=[642, 316, 77, 20],
                init_trigger_rect=[642, 357, 30, 20],
                path_rect=[653, 444, 89, 20],
                property_rect=[637, 403, 109, 20],
                observer_rect=[637, 485, 70, 20],
                value_trigger_rect=[637, 524, 30, 20],
                selector_rect=[637, 569, 31, 20],
                box_order=["value_trigger", "selector", "property", "observer", "init_trigger", "path", "device"],
                include_default_style=False,
            )
        )

        snapshot = snapshot_from_device(device)
        knowledge = extract_snapshot_knowledge(snapshot)
        source = generate_optimized_python_from_snapshot(snapshot)
        namespace = {}

        exec(source, namespace)

        output = tmp_path / "live_state_observer.amxd"
        written = namespace["build"](str(output))
        rebuilt = output.read_bytes()
        expected = device.to_bytes()

        assert written == len(expected)
        assert rebuilt == expected
        assert any(entry["helper_name"] == "live_state_observer" for entry in knowledge["live_api_helpers"])
        assert "live_state_observer(" in source
        assert "device.add_newobj('state_observer'" not in source

    def test_optimized_python_rebuilds_live_thisdevice_helper(self, tmp_path):
        device = AudioEffect("ThisDevice Helper", 260, 120)
        device.add_dsp(*live_thisdevice("dev", device_rect=[30, 120, 80, 20]))

        snapshot = snapshot_from_device(device)
        source = generate_optimized_python_from_snapshot(snapshot)
        namespace = {}

        exec(source, namespace)

        output = tmp_path / "thisdevice_helper.amxd"
        written = namespace["build"](str(output))
        rebuilt = output.read_bytes()
        expected = device.to_bytes()

        assert written == len(expected)
        assert rebuilt == expected
        assert "live_thisdevice(" in source

    def test_semantic_python_normalizes_live_api_property_binding(self, tmp_path):
        device = AudioEffect("Semantic Live API", 320, 200)
        device.add_dsp(
            *live_observer(
                "tempo",
                path="live_set",
                prop="tempo",
                path_rect=[120, 120, 100, 20],
                object_rect=[120, 150, 80, 20],
                observer_rect=[120, 180, 120, 20],
            )
        )
        for wrapped in device.boxes:
            box = wrapped["box"]
            if box["id"] == "tempo_observer":
                box["text"] = "live.observer"
                box["fontsize"] = 12.0
                break
        device.add_box({
            "box": {
                "id": "tempo_property",
                "maxclass": "message",
                "text": "property tempo",
                "patching_rect": [250, 180, 90, 20],
                "numinlets": 2,
                "numoutlets": 1,
            }
        })
        device.add_line("tempo_property", 0, "tempo_observer", 0)

        snapshot = snapshot_from_device(device)
        source = generate_semantic_python_from_snapshot(snapshot)
        namespace = {}

        exec(source, namespace)

        output = tmp_path / "semantic_live_api.amxd"
        written = namespace["build"](str(output))
        rebuilt = output.read_bytes()
        expected = device.to_bytes()

        assert written == len(expected)
        assert rebuilt == expected
        assert "live_observer(" in source
        assert "bind_via_message=True" in source
        assert "property_id='tempo_property'" in source
        assert "device.add_newobj('tempo_observer'" not in source
        assert "device.add_box({'box': {'id': 'tempo_property'" not in source

    def test_semantic_python_leaves_manual_review_live_api_expanded(self, tmp_path):
        device = AudioEffect("Semantic Manual Review", 320, 180)
        device.add_newobj("path_direct", "live.path live_set", numinlets=2, numoutlets=2, patching_rect=[20, 120, 90, 20])
        device.add_newobj("observer_direct", "live.observer", numinlets=2, numoutlets=2, patching_rect=[120, 120, 90, 20])
        device.add_newobj("observer_defer", "deferlow", numinlets=1, numoutlets=1, patching_rect=[220, 120, 60, 20])
        device.add_box({
            "box": {
                "id": "observer_direct_property",
                "maxclass": "message",
                "text": "property tempo",
                "patching_rect": [20, 150, 90, 20],
                "numinlets": 2,
                "numoutlets": 1,
            }
        })
        device.add_line("path_direct", 1, "observer_direct", 1)
        device.add_line("observer_direct_property", 0, "observer_direct", 0)
        device.add_line("observer_defer", 0, "observer_direct", 0)

        snapshot = snapshot_from_device(device)
        source = generate_semantic_python_from_snapshot(snapshot)
        namespace = {}

        exec(source, namespace)

        output = tmp_path / "semantic_manual_review.amxd"
        written = namespace["build"](str(output))
        rebuilt = output.read_bytes()
        expected = device.to_bytes()

        assert written == len(expected)
        assert rebuilt == expected
        assert "# Live API clusters left expanded for manual review:" in source
        assert "live_observer ->" in source
        assert "observer_defer" in source
        assert "device.add_newobj(\n        'path_direct'" in source

    def test_semantic_python_groups_controller_shell_candidates(self, tmp_path):
        device = AudioEffect("Semantic Controller Shells", 360, 200)
        device.add_box({
            "box": {
                "id": "msg",
                "maxclass": "message",
                "text": "mode 1",
                "patching_rect": [20, 0, 60, 20],
                "numinlets": 2,
                "numoutlets": 1,
            }
        })
        device.add_newobj("route", "route mode", numinlets=1, numoutlets=2, patching_rect=[20, 20, 80, 20])
        device.add_newobj("trigger", "t i i", numinlets=1, numoutlets=2, patching_rect=[120, 20, 40, 20])
        device.add_newobj("prepend", "prepend value", numinlets=1, numoutlets=1, patching_rect=[180, 20, 80, 20])
        device.add_newobj("device", "live.thisdevice", numinlets=1, numoutlets=2, patching_rect=[20, 50, 90, 20])
        device.add_newobj("send_a", "s shell_bus", numinlets=1, numoutlets=0, patching_rect=[120, 50, 70, 20])
        device.add_newobj("recv_a", "r shell_bus", numinlets=0, numoutlets=1, patching_rect=[210, 50, 70, 20])
        device.add_line("route", 0, "trigger", 0)

        device.add_newobj("sel", "sel 0 1", numinlets=1, numoutlets=3, patching_rect=[20, 100, 60, 20])
        device.add_newobj("gate", "gate 2", numinlets=2, numoutlets=2, patching_rect=[100, 100, 50, 20])
        device.add_newobj("delay", "delay 5", numinlets=2, numoutlets=1, patching_rect=[170, 100, 60, 20])
        device.add_newobj("defer", "deferlow", numinlets=1, numoutlets=1, patching_rect=[250, 100, 60, 20])
        device.add_newobj("send_loop", "s ---loop", numinlets=1, numoutlets=0, patching_rect=[20, 130, 70, 20])
        device.add_newobj("recv_loop", "r ---loop", numinlets=0, numoutlets=1, patching_rect=[110, 130, 70, 20])
        device.add_line("sel", 0, "gate", 0)
        device.add_line("defer", 0, "delay", 0)

        snapshot = snapshot_from_device(device)
        source = generate_semantic_python_from_snapshot(snapshot)
        namespace = {}

        exec(source, namespace)

        output = tmp_path / "semantic_controller_shells.amxd"
        written = namespace["build"](str(output))
        rebuilt = output.read_bytes()
        expected = device.to_bytes()

        assert written == len(expected)
        assert rebuilt == expected
        assert "SNAPSHOT_CONTROLLER_SHELL_CANDIDATES" in source
        assert "controller_surface_shell" in source
        assert "sequencer_dispatch_shell" in source
        assert "*controller_surface_shell(" in source
        assert "*sequencer_dispatch_shell(" not in source
        assert "def _controller_surface_shell_" not in source
        assert "def _sequencer_dispatch_shell_" not in source

    def test_optimized_python_groups_controller_shell_candidates(self, tmp_path):
        device = AudioEffect("Optimized Controller Shells", 360, 200)
        device.add_box({
            "box": {
                "id": "msg",
                "maxclass": "message",
                "text": "mode 1",
                "patching_rect": [20, 0, 60, 20],
                "numinlets": 2,
                "numoutlets": 1,
            }
        })
        device.add_newobj("route", "route mode", numinlets=1, numoutlets=2, patching_rect=[20, 20, 80, 20])
        device.add_newobj("trigger", "t i i", numinlets=1, numoutlets=2, patching_rect=[120, 20, 40, 20])
        device.add_newobj("prepend", "prepend value", numinlets=1, numoutlets=1, patching_rect=[180, 20, 80, 20])
        device.add_newobj("device", "live.thisdevice", numinlets=1, numoutlets=2, patching_rect=[20, 50, 90, 20])
        device.add_newobj("send_a", "s shell_bus", numinlets=1, numoutlets=0, patching_rect=[120, 50, 70, 20])
        device.add_newobj("recv_a", "r shell_bus", numinlets=0, numoutlets=1, patching_rect=[210, 50, 70, 20])
        device.add_line("route", 0, "trigger", 0)

        device.add_newobj("sel", "sel 0 1", numinlets=1, numoutlets=3, patching_rect=[20, 100, 60, 20])
        device.add_newobj("gate", "gate 2", numinlets=2, numoutlets=2, patching_rect=[100, 100, 50, 20])
        device.add_newobj("delay", "delay 5", numinlets=2, numoutlets=1, patching_rect=[170, 100, 60, 20])
        device.add_newobj("defer", "deferlow", numinlets=1, numoutlets=1, patching_rect=[250, 100, 60, 20])
        device.add_newobj("send_loop", "s ---loop", numinlets=1, numoutlets=0, patching_rect=[20, 130, 70, 20])
        device.add_newobj("recv_loop", "r ---loop", numinlets=0, numoutlets=1, patching_rect=[110, 130, 70, 20])
        device.add_line("sel", 0, "gate", 0)
        device.add_line("defer", 0, "delay", 0)

        snapshot = snapshot_from_device(device)
        source = generate_optimized_python_from_snapshot(snapshot)
        namespace = {}

        exec(source, namespace)

        output = tmp_path / "optimized_controller_shells.amxd"
        written = namespace["build"](str(output))
        rebuilt = output.read_bytes()
        expected = device.to_bytes()

        assert written == len(expected)
        assert rebuilt == expected
        assert "*controller_surface_shell(" in source
        assert "*sequencer_dispatch_shell(" not in source
        assert "# Live API clusters left expanded for manual review:" not in source

    def test_optimized_python_groups_embedded_ui_shell_candidates(self, tmp_path):
        device = AudioEffect("Optimized Embedded Shells", 320, 180)
        sub = Subpatcher("inner")
        sub.add_newobj("send", "s nested_bus", numinlets=1, numoutlets=0, patching_rect=[10, 10, 70, 20])
        sub.add_newobj("recv", "r nested_bus", numinlets=0, numoutlets=1, patching_rect=[90, 10, 70, 20])
        device.add_subpatcher(sub, "inner_host", [20, 70, 120, 60])
        device.add_bpatcher("panel_host", [170, 70, 100, 40], "panel.maxpat", args="seed 9", embed=1)

        snapshot = snapshot_from_device(device)
        source = generate_optimized_python_from_snapshot(snapshot)
        namespace = {}

        exec(source, namespace)

        output = tmp_path / "optimized_embedded_shells.amxd"
        written = namespace["build"](str(output))
        rebuilt = output.read_bytes()
        expected = device.to_bytes()

        assert written == len(expected)
        assert rebuilt == expected
        assert "SNAPSHOT_EMBEDDED_UI_SHELL_CANDIDATES" in source
        assert "*embedded_ui_shell_v2(" in source

    def test_semantic_python_groups_first_party_exact_helpers(self, tmp_path):
        device = AudioEffect("Factory Semantic Helpers", 360, 220)
        device.add_newobj("send_a", "s shared_bus", numinlets=1, numoutlets=0, patching_rect=[20, 20, 70, 20])
        device.add_newobj("recv_a", "r shared_bus", numinlets=0, numoutlets=1, patching_rect=[110, 20, 70, 20])
        device.add_newobj("loadbang", "loadbang", numinlets=1, numoutlets=1, patching_rect=[20, 60, 60, 20])
        device.add_newobj("defer", "deferlow", numinlets=1, numoutlets=1, patching_rect=[100, 60, 60, 20])
        device.add_newobj("init_t", "t b b", numinlets=1, numoutlets=2, patching_rect=[180, 60, 40, 20])
        device.add_line("loadbang", 0, "defer", 0)
        device.add_line("defer", 0, "init_t", 0)
        device.add_newobj("voices", "poly~ grain_voice 8", numinlets=3, numoutlets=2, patching_rect=[20, 120, 100, 20])
        device.add_newobj("send_poly", "s voice_bus", numinlets=1, numoutlets=0, patching_rect=[140, 120, 70, 20])
        device.add_newobj("recv_poly", "r voice_bus", numinlets=0, numoutlets=1, patching_rect=[220, 120, 70, 20])
        device.add_line("voices", 0, "send_poly", 0)

        snapshot = snapshot_from_device(device)
        source = generate_semantic_python_from_snapshot(snapshot)
        namespace = {}

        exec(source, namespace)

        output = tmp_path / "factory_semantic_helpers.amxd"
        written = namespace["build"](str(output))
        rebuilt = output.read_bytes()
        expected = device.to_bytes()

        assert written == len(expected)
        assert rebuilt == expected
        assert "SNAPSHOT_NAMED_BUS_ROUTER_CANDIDATES" in source
        assert "SNAPSHOT_INIT_DISPATCH_CHAIN_CANDIDATES" in source
        assert "SNAPSHOT_POLY_SHELL_CANDIDATES" in source
        assert "*named_bus_router(" in source
        assert "*init_dispatch_chain(" in source
        assert "*poly_shell(" in source

    def test_optimized_python_prefers_poly_shell_bank_over_individual_shells(self):
        device = AudioEffect("Poly Shell Bank", 420, 260)
        device.add_box({
            "box": {
                "id": "shared_mod",
                "maxclass": "flonum",
                "patching_rect": [190, 20, 50, 22],
                "numinlets": 1,
                "numoutlets": 2,
                "outlettype": ["", "bang"],
            }
        })
        for index in range(1, 4):
            y = 40 + (index - 1) * 60
            device.add_box({
                "box": {
                    "id": f"ui_{index}",
                    "maxclass": "bpatcher",
                    "name": "VoiceUi.maxpat",
                    "patching_rect": [20, y, 120, 24],
                    "numinlets": 4,
                    "numoutlets": 4,
                    "outlettype": ["", "", "", ""],
                }
            })
            device.add_newobj(
                f"poly_{index}",
                "poly~ voice_editor",
                numinlets=4,
                numoutlets=4,
                patching_rect=[170, y, 110, 20],
            )
            device.add_newobj(
                f"send_{index}",
                f"s voice{index}",
                numinlets=1,
                numoutlets=0,
                patching_rect=[310, y, 60, 20],
            )
            device.add_line(f"ui_{index}", 0, f"poly_{index}", 0)
            device.add_line(f"ui_{index}", 1, f"poly_{index}", 1)
            device.add_line(f"poly_{index}", 0, f"ui_{index}", 0)
            device.add_line(f"poly_{index}", 1, f"ui_{index}", 1)
            device.add_line(f"poly_{index}", 2, f"send_{index}", 0)
            device.add_line("shared_mod", 0, f"poly_{index}", 2)

        source = generate_optimized_python_from_snapshot(snapshot_from_device(device))

        assert "SNAPSHOT_POLY_SHELL_BANK_CANDIDATES" in source
        assert "# semantic target: poly_shell_bank" in source
        assert "*poly_shell_bank(" in source
        assert "\n        *poly_shell(" not in source

    def test_semantic_python_prefers_poly_editor_bank_group_over_exact_bank(self):
        device = AudioEffect("Poly Editor Bank", 420, 260)
        device.add_box({
            "box": {
                "id": "shared_mod",
                "maxclass": "flonum",
                "patching_rect": [190, 20, 50, 22],
                "numinlets": 1,
                "numoutlets": 2,
                "outlettype": ["", "bang"],
            }
        })
        for index in range(1, 4):
            y = 40 + (index - 1) * 60
            device.add_box({
                "box": {
                    "id": f"ui_{index}",
                    "maxclass": "bpatcher",
                    "name": "VoiceUi.maxpat",
                    "patching_rect": [20, y, 120, 24],
                    "numinlets": 4,
                    "numoutlets": 4,
                    "outlettype": ["", "", "", ""],
                }
            })
            device.add_newobj(
                f"poly_{index}",
                "poly~ voice_editor",
                numinlets=4,
                numoutlets=4,
                patching_rect=[170, y, 110, 20],
            )
            device.add_newobj(
                f"send_{index}",
                f"s voice{index}",
                numinlets=1,
                numoutlets=0,
                patching_rect=[310, y, 60, 20],
            )
            device.add_line(f"ui_{index}", 0, f"poly_{index}", 0)
            device.add_line(f"ui_{index}", 1, f"poly_{index}", 1)
            device.add_line(f"poly_{index}", 0, f"ui_{index}", 0)
            device.add_line(f"poly_{index}", 1, f"ui_{index}", 1)
            device.add_line(f"poly_{index}", 2, f"send_{index}", 0)
            device.add_line("shared_mod", 0, f"poly_{index}", 2)

        source = generate_semantic_python_from_snapshot(snapshot_from_device(device))

        assert "SNAPSHOT_POLY_EDITOR_BANK_CANDIDATES" in source
        assert "# semantic group: poly_editor_bank" in source
        assert "# semantic target: poly_shell_bank" not in source

    def test_semantic_python_prefers_triggered_parameter_mapper_over_lower_mapping_groups(self):
        device = Instrument("Mapped Random Control", 420, 260)
        device.add_box({
            "box": {
                "id": "shared_mod",
                "maxclass": "flonum",
                "patching_rect": [190, 20, 50, 22],
                "numinlets": 1,
                "numoutlets": 2,
                "outlettype": ["", "bang"],
            }
        })
        for index in range(1, 4):
            y = 40 + (index - 1) * 60
            device.add_box({
                "box": {
                    "id": f"ui_{index}",
                    "maxclass": "bpatcher",
                    "name": "Abl.MapUi.RNDGEN.maxpat",
                    "patching_rect": [20, y, 120, 24],
                    "numinlets": 4,
                    "numoutlets": 4,
                    "outlettype": ["", "", "", ""],
                }
            })
            device.add_newobj(
                f"poly_{index}",
                "poly~ Abl.Map.edit",
                numinlets=4,
                numoutlets=4,
                patching_rect=[170, y, 110, 20],
            )
            device.add_newobj(
                f"send_{index}",
                f"s ---m{index}",
                numinlets=1,
                numoutlets=0,
                patching_rect=[310, y, 60, 20],
            )
            device.add_line(f"ui_{index}", 0, f"poly_{index}", 0)
            device.add_line(f"ui_{index}", 1, f"poly_{index}", 1)
            device.add_line(f"poly_{index}", 0, f"ui_{index}", 0)
            device.add_line(f"poly_{index}", 1, f"ui_{index}", 1)
            device.add_line(f"poly_{index}", 2, f"send_{index}", 0)
            device.add_line("shared_mod", 0, f"poly_{index}", 2)

        midi_logic = Subpatcher("MIDILogic")
        midi_logic.add_newobj("manualmode", "r ---manualmode", numinlets=0, numoutlets=1, patching_rect=[20, 20, 90, 20])
        midi_logic.add_newobj("compare", "== 0", numinlets=2, numoutlets=1, patching_rect=[120, 20, 40, 20])
        midi_logic.add_newobj("gate", "gate", numinlets=2, numoutlets=1, patching_rect=[180, 20, 40, 20])
        midi_logic.add_newobj("parse", "midiparse", numinlets=1, numoutlets=1, patching_rect=[240, 20, 70, 20])
        midi_logic.add_newobj("unpack", "unpack i i", numinlets=1, numoutlets=2, patching_rect=[320, 20, 70, 20])
        midi_logic.add_newobj("strip", "stripnote", numinlets=2, numoutlets=2, patching_rect=[400, 20, 70, 20])
        midi_logic.add_newobj("trigger", "t b", numinlets=1, numoutlets=1, patching_rect=[480, 20, 30, 20])
        midi_logic.add_newobj("send", "s ---notebang", numinlets=1, numoutlets=0, patching_rect=[520, 20, 80, 20])
        midi_logic.add_line("manualmode", 0, "compare", 0)
        midi_logic.add_line("compare", 0, "gate", 0)
        midi_logic.add_line("gate", 0, "parse", 0)
        midi_logic.add_line("parse", 0, "unpack", 0)
        midi_logic.add_line("unpack", 0, "strip", 0)
        midi_logic.add_line("unpack", 1, "strip", 1)
        midi_logic.add_line("strip", 1, "trigger", 0)
        midi_logic.add_line("trigger", 0, "send", 0)
        device.add_subpatcher(midi_logic, "midi_logic", [20, 220, 120, 50])

        qm = Subpatcher("qm")
        qm.add_newobj("start", "s ---qmap_start", numinlets=1, numoutlets=0, patching_rect=[20, 20, 90, 20])
        qm.add_newobj("done", "r ---done_qmap", numinlets=0, numoutlets=1, patching_rect=[130, 20, 90, 20])
        qm.add_newobj("qmap", "s ---qmap", numinlets=1, numoutlets=0, patching_rect=[240, 20, 70, 20])
        qm.add_newobj("update", "s ---update_local", numinlets=1, numoutlets=0, patching_rect=[330, 20, 100, 20])
        device.add_subpatcher(qm, "qm_logic", [160, 220, 120, 50])

        source = generate_semantic_python_from_snapshot(snapshot_from_device(device))

        assert "SNAPSHOT_MAPPING_SEMANTIC_CANDIDATES" in source
        assert "# semantic group: triggered_parameter_mapper" in source
        assert "# semantic group: random_modulation_mapper" not in source
        assert "# semantic group: mapped_modulation_bank" not in source
        assert "# semantic group: mapping_workflow_shell" not in source
        assert "# semantic group: poly_editor_bank" not in source
        assert "# semantic target: poly_shell_bank" not in source

    def test_semantic_python_groups_factory_presentation_widget_clusters(self, tmp_path):
        root = tmp_path / "Factory Packs" / "M4L Building Tools" / "Tools" / "Max Audio Effect"
        root.mkdir(parents=True)
        device = AudioEffect("Factory Presentation Cluster", 320, 180)
        for box_id, maxclass, text, rect in [
            ("dial_a", "live.dial", None, [20, 20, 44, 44]),
            ("dial_b", "live.dial", None, [72, 20, 44, 44]),
            ("label_a", "comment", "Rate", [20, 68, 40, 18]),
            ("label_b", "comment", "Depth", [72, 68, 40, 18]),
            ("toggle_a", "live.toggle", None, [124, 24, 20, 20]),
        ]:
            box = {
                "id": box_id,
                "maxclass": maxclass,
                "patching_rect": rect,
                "presentation_rect": rect,
                "presentation": 1,
                "numinlets": 1,
                "numoutlets": 1 if maxclass != "comment" else 0,
            }
            if text is not None:
                box["text"] = text
            device.add_box({"box": box})
        path = root / "Factory Presentation Cluster.amxd"
        device.build(str(path))

        snapshot = snapshot_from_amxd(str(path))
        builder_source = generate_builder_python_from_snapshot(snapshot)
        semantic_source = generate_semantic_python_from_snapshot(snapshot)

        assert "SNAPSHOT_PRESENTATION_WIDGET_CLUSTER_CANDIDATES" in semantic_source
        assert "# semantic group: presentation_widget_cluster" in semantic_source
        assert semantic_source.count("device.add_box(") < builder_source.count("device.add_box(")

    def test_semantic_python_groups_first_party_abstraction_hosts_before_building_block(self, tmp_path):
        root = tmp_path / "Factory Packs" / "M4L Building Tools" / "Building Blocks" / "Max Audio Effect"
        root.mkdir(parents=True)
        device = AudioEffect("Max GainDualMono", 320, 180)
        device.add_newobj("gain_l", "M4L.gain1~", numinlets=2, numoutlets=1, patching_rect=[20, 70, 70, 20])
        device.add_newobj("gain_r", "M4L.gain1~", numinlets=2, numoutlets=1, patching_rect=[140, 70, 70, 20])
        device.add_dial("gain", "Gain", [72, 18, 44, 44], min_val=-70.0, max_val=6.0, initial=0.0, unitstyle=4)
        device.add_comment("label", [66, 66, 60, 18], "Gain")
        device.add_line("gain", 0, "gain_l", 1)
        device.add_line("gain", 0, "gain_r", 1)
        path = root / "Max GainDualMono.amxd"
        device.build(str(path))

        snapshot = snapshot_from_amxd(str(path))
        builder_source = generate_builder_python_from_snapshot(snapshot)
        semantic_source = generate_semantic_python_from_snapshot(snapshot)

        assert "SNAPSHOT_FIRST_PARTY_ABSTRACTION_FAMILY_CANDIDATES" in semantic_source
        assert "# semantic group: gain_shell" in semantic_source
        assert "SNAPSHOT_FIRST_PARTY_ABSTRACTION_HOST_CANDIDATES" in semantic_source
        assert "# semantic group: first_party_abstraction_host" not in semantic_source
        if "# semantic group: building_block_candidate" in semantic_source:
            assert semantic_source.index("# semantic group: gain_shell") < semantic_source.index(
                "# semantic group: building_block_candidate"
            )
        assert semantic_source.count("device.add_dsp(") > builder_source.count("device.add_dsp(")

    def test_semantic_python_groups_building_block_candidates_from_factory_path(self, tmp_path):
        factory_root = tmp_path / "Factory Packs" / "M4L Building Tools" / "Building Blocks" / "Max Audio Effect"
        factory_root.mkdir(parents=True)
        device = AudioEffect("Max DelayLine", 320, 180)
        device.add_comment("label", [20, 20, 100, 18], "Delay")
        device.add_dial("delay", "Delay", [20, 50, 50, 90], min_val=0.0, max_val=2000.0, initial=400.0, unitstyle=2)
        device.add_comment("hint", [90, 70, 120, 18], "Factory block")
        path = factory_root / "Max DelayLine.amxd"
        device.build(str(path))

        source = generate_semantic_python_from_snapshot(snapshot_from_amxd(str(path)))

        assert "# semantic group: building_block_candidate" in source
        assert "SNAPSHOT_BUILDING_BLOCK_CANDIDATES" in source
        assert source.count("device.add_box(") == 0
        assert "device.add_dsp(" in source

    def test_semantic_python_groups_first_party_api_rig_candidates_from_factory_path(self, tmp_path):
        api_root = tmp_path / "Factory Packs" / "M4L Building Tools" / "API"
        api_root.mkdir(parents=True)
        device = AudioEffect("Max Api DeviceExplorer", 320, 180)
        device.add_comment("label", [20, 20, 140, 18], "API rig")
        device.add_box({
            "box": {
                "id": "msg",
                "maxclass": "message",
                "text": "observe selection",
                "patching_rect": [20, 50, 110, 20],
                "numinlets": 2,
                "numoutlets": 1,
            }
        })
        path = api_root / "Max Api DeviceExplorer.amxd"
        device.build(str(path))

        source = generate_semantic_python_from_snapshot(snapshot_from_amxd(str(path)))

        assert "# semantic group: first_party_api_rig" in source
        assert "SNAPSHOT_FIRST_PARTY_API_RIG_CANDIDATES" in source
        assert source.count("device.add_box(") == 0
        assert "device.add_dsp(" in source

    def test_builder_python_semantically_rebuilds_jsui_device(self, tmp_path):
        device = AudioEffect("JSUI Reverse", 220, 100)
        device.add_jsui(
            "display",
            [10, 10, 120, 60],
            js_code="mgraphics.init();\n",
            js_filename="display.js",
            numinlets=2,
            numoutlets=1,
            border=1,
        )

        snapshot = snapshot_from_device(device)
        source = generate_builder_python_from_snapshot(snapshot)
        namespace = {}

        exec(source, namespace)

        output = tmp_path / "jsui_reverse.amxd"
        written = namespace["build"](str(output))
        rebuilt = output.read_bytes()
        expected = device.to_bytes()

        assert written == len(expected)
        assert rebuilt == expected
        assert (tmp_path / "display.js").read_text() == "mgraphics.init();\n"
        assert "add_jsui" in source
        assert 'add_support_file(\n        \'display.js\'' not in source

    def test_builder_python_supports_string_parameter_bank_slots(self):
        device = AudioEffect("Banked Reverse", 220, 100)
        device.add_dial("gain", "Gain", [10, 10, 48, 84])
        snapshot = snapshot_from_device(device)
        snapshot["parameterbanks"] = {
            "0": {
                "index": 0,
                "name": "Parameters",
                "parameters": ["Gain", "-", "Drive"],
            }
        }

        source = generate_builder_python_from_snapshot(snapshot)

        assert "assign_parameter_bank(\n        'Gain'" in source
        assert "assign_parameter_bank(\n        'Drive'" in source
        assert "'-'" not in source

    def test_builder_python_semantically_rebuilds_extended_ui_objects(self, tmp_path):
        device = AudioEffect("Semantic Widgets", 320, 180)
        device.add_support_file("mini.maxpat", '{"patcher": {"boxes": [], "lines": []}}')
        device.add_panel("bg", [0, 0, 320, 180], bgcolor=[0.1, 0.1, 0.1, 1.0])
        device.add_fpic("logo", [12, 10, 40, 40], pic="badge.png", autofit=1)
        device.add_multislider(
            "bars",
            [60, 10, 120, 40],
            size=8,
            setminmax=[-1.0, 1.0],
            slidercolor=[0.8, 0.2, 0.2, 1.0],
        )
        device.add_textbutton("go", [190, 10, 70, 22], text="Go", texton="Stop", mode=1)
        device.add_umenu("menu", [12, 60, 110, 22], items=["One", ",", "Two"])
        device.add_radiogroup("modes", [130, 60, 40, 60], itemcount=3, value=2)
        device.add_bpatcher("mini", [190, 60, 100, 60], "mini.maxpat", args="seed 7", embed=1)

        snapshot = snapshot_from_device(device)
        source = generate_builder_python_from_snapshot(snapshot)
        namespace = {}

        exec(source, namespace)

        output = tmp_path / "semantic_widgets.amxd"
        written = namespace["build"](str(output))
        rebuilt = output.read_bytes()
        expected = device.to_bytes()

        assert written == len(expected)
        assert rebuilt == expected
        assert (tmp_path / "mini.maxpat").read_text() == '{"patcher": {"boxes": [], "lines": []}}'
        assert "add_fpic" in source
        assert "add_multislider" in source
        assert "add_textbutton" in source
        assert "add_umenu" in source
        assert "add_radiogroup" in source
        assert "add_bpatcher" in source

    def test_builder_python_semantically_rebuilds_advanced_ui_objects(self, tmp_path):
        device = AudioEffect("Advanced Widgets", 420, 240)
        device.add_v8ui(
            "canvas",
            [10, 10, 140, 60],
            js_code="mgraphics.init();\n",
            js_filename="canvas.js",
            numinlets=2,
            numoutlets=1,
        )
        device.add_adsrui("env", [160, 10, 120, 60], bgcolor=[0.1, 0.1, 0.1, 1.0])
        device.add_live_drop("drop", [290, 10, 100, 40], bgcolor=[0.2, 0.2, 0.2, 1.0])
        device.add_swatch("sw", [10, 80, 30, 30])
        device.add_textedit("txt", [50, 80, 120, 22], fontsize=11.0)
        device.add_live_step("step", [180, 80, 160, 60], nstep=8, nseq=2, loop_start=1, loop_end=6, mode=1)
        device.add_live_grid("grid", [10, 120, 90, 60], columns=4, rows=3, direction=1)
        device.add_live_line("divider", [110, 120, 120, 2], justification=1)
        device.add_live_arrows("arrows", [240, 120, 40, 20])
        device.add_rslider("range", [290, 120, 24, 80], min_val=10, max_val=90)
        device.add_kslider("keys", [10, 190, 160, 40], range=49, offset=24)
        device.add_nodes("curve", [180, 190, 80, 40], numnodes=3, xmin=0.0, xmax=1.0, ymin=-1.0, ymax=1.0)
        device.add_matrixctrl("matrix", [270, 190, 70, 40], rows=3, columns=5)
        device.add_ubutton("click", [350, 190, 30, 20])
        device.add_nslider("staff", [350, 215, 60, 20], staffs=2)

        snapshot = snapshot_from_device(device)
        source = generate_builder_python_from_snapshot(snapshot)
        namespace = {}

        exec(source, namespace)

        output = tmp_path / "advanced_widgets.amxd"
        written = namespace["build"](str(output))
        rebuilt = output.read_bytes()
        expected = device.to_bytes()

        assert written == len(expected)
        assert rebuilt == expected
        assert (tmp_path / "canvas.js").read_text() == "mgraphics.init();\n"
        assert "add_v8ui" in source
        assert "add_adsrui" in source
        assert "add_live_drop" in source
        assert "add_swatch" in source
        assert "add_textedit" in source
        assert "add_live_step" in source
        assert "add_live_grid" in source
        assert "add_live_line" in source
        assert "add_live_arrows" in source
        assert "add_rslider" in source
        assert "add_kslider" in source
        assert "add_nodes" in source
        assert "add_matrixctrl" in source
        assert "add_ubutton" in source
        assert "add_nslider" in source
        assert 'add_support_file(\n        \'canvas.js\'' not in source

    def test_optimized_python_recipe_precedence_rebuilds_recipe_device(self, tmp_path):
        device = AudioEffect("Optimized Recipe", 260, 120)
        tempo_synced_delay(
            device,
            "echo",
            [10, 10, 44, 88],
            [66, 10, 44, 88],
            x=120,
            y=70,
        )

        snapshot = snapshot_from_device(device)
        source = generate_optimized_python_from_snapshot(snapshot)
        namespace = {}

        exec(source, namespace)

        rebuilt_device = namespace["build_device"]()
        output = tmp_path / "optimized_recipe.amxd"
        written = namespace["build"](str(output))
        rebuilt = output.read_bytes()
        expected = device.to_bytes()

        assert written == len(expected)
        assert rebuilt == expected
        assert rebuilt_device.device_type == "audio_effect"
        assert "tempo_synced_delay" in source
        assert "*delay_line(" not in source
        assert "*param_smooth(" not in source

    def test_optimized_python_rebuilds_midi_note_gate_recipe(self, tmp_path):
        device = AudioEffect("Optimized MIDI Recipe", 240, 120)
        midi_note_gate(device, "keys", x=60, y=40)

        snapshot = snapshot_from_device(device)
        source = generate_optimized_python_from_snapshot(snapshot)
        namespace = {}

        exec(source, namespace)

        output = tmp_path / "optimized_midi_recipe.amxd"
        written = namespace["build"](str(output))
        rebuilt = output.read_bytes()
        expected = device.to_bytes()

        assert written == len(expected)
        assert rebuilt == expected
        assert "\n    midi_note_gate(" in source

    def test_optimized_python_rebuilds_transport_sync_lfo_recipe(self, tmp_path):
        device = AudioEffect("Optimized Transport Recipe", 260, 120)
        transport_sync_lfo_recipe(device, "sync", x=60, y=40)

        snapshot = snapshot_from_device(device)
        source = generate_optimized_python_from_snapshot(snapshot)
        namespace = {}

        exec(source, namespace)

        output = tmp_path / "optimized_transport_recipe.amxd"
        written = namespace["build"](str(output))
        rebuilt = output.read_bytes()
        expected = device.to_bytes()

        assert written == len(expected)
        assert rebuilt == expected
        assert "\n    transport_sync_lfo_recipe(" in source

    def test_optimized_python_falls_back_when_recipe_is_not_recipeizable(self, tmp_path):
        device = AudioEffect("Optimized Partial Recipe", 260, 120)
        gain_controlled_stage(device, "trim", [10, 10, 44, 88], x=45, y=60)
        for wrapped in device.boxes:
            box = wrapped["box"]
            if box["id"] == "trim_gain":
                box["patching_rect"] = [300, 300, 40, 20]
                break

        snapshot = snapshot_from_device(device)
        source = generate_optimized_python_from_snapshot(snapshot)
        namespace = {}

        exec(source, namespace)

        output = tmp_path / "optimized_partial_recipe.amxd"
        written = namespace["build"](str(output))
        rebuilt = output.read_bytes()
        expected = device.to_bytes()

        assert written == len(expected)
        assert rebuilt == expected
        assert "\n    gain_controlled_stage(" not in source
        assert "from m4l_builder import Device, AudioEffect, Instrument, MidiEffect, param_smooth" in source
        assert "param_smooth" in source

    def test_optimized_python_preserves_unknown_box_fallback(self, tmp_path):
        device = AudioEffect("Fallback Reverse", 220, 120)
        device.add_box(
            {
                "box": {
                    "id": "mystery",
                    "maxclass": "mystery.widget",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "patching_rect": [80, 120, 40, 40],
                    "presentation": 1,
                    "presentation_rect": [10, 10, 40, 40],
                    "customattr": 7,
                }
            }
        )

        snapshot = snapshot_from_device(device)
        source = generate_optimized_python_from_snapshot(snapshot)
        namespace = {}

        exec(source, namespace)

        output = tmp_path / "fallback_reverse.amxd"
        written = namespace["build"](str(output))
        rebuilt = output.read_bytes()
        expected = device.to_bytes()

        assert written == len(expected)
        assert rebuilt == expected
        assert "device.add_box({'box': {'id': 'mystery'" in source
