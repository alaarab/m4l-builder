"""Tests for external AMXD corpus analysis helpers."""

from m4l_builder import (
    AudioEffect,
    MidiEffect,
    Subpatcher,
    analyze_amxd_corpus,
    build_reverse_candidate_family_profile,
    build_livemcp_bridge_demo,
    build_reverse_candidate_family_profiles,
    corpus_report_markdown,
    family_profile_markdown,
    live_parameter_probe,
    live_thisdevice,
    midi_note_gate,
    param_smooth,
    rank_reverse_candidates,
    rank_reverse_candidate_families,
    write_family_profile,
    write_corpus_report,
)


class TestCorpusAnalysis:
    def test_analyze_amxd_corpus_aggregates_metrics_and_errors(self, tmp_path):
        fx = AudioEffect("Corpus FX", 220, 100)
        fx.add_dial(
            "gain",
            "Gain",
            [12, 10, 46, 84],
            min_val=-70.0,
            max_val=6.0,
            initial=0.0,
            unitstyle=4,
        )
        fx.add_dsp(*param_smooth("mod"))
        fx.add_newobj("send_a", "s bus_alpha", numinlets=1, numoutlets=0, patching_rect=[120, 12, 70, 20])
        fx.add_newobj("recv_a", "r bus_alpha", numinlets=0, numoutlets=1, patching_rect=[120, 40, 70, 20])
        fx.add_newobj("route", "route mode", numinlets=1, numoutlets=2, patching_rect=[12, 70, 80, 20])
        fx.add_newobj("trigger", "t i i", numinlets=1, numoutlets=2, patching_rect=[100, 70, 40, 20])
        fx.add_newobj("prepend", "prepend value", numinlets=1, numoutlets=1, patching_rect=[150, 70, 80, 20])
        fx.add_line("route", 0, "trigger", 0)
        fx.add_newobj("path", "live.path live_set", numinlets=2, numoutlets=2, patching_rect=[12, 100, 90, 20])
        fx.add_newobj("observer", "live.observer", numinlets=2, numoutlets=2, patching_rect=[110, 100, 80, 20])
        fx.add_box({
            "box": {
                "id": "observer_property",
                "maxclass": "message",
                "text": "property is_playing",
                "patching_rect": [200, 100, 100, 20],
                "numinlets": 2,
                "numoutlets": 1,
            }
        })
        fx.add_line("path", 1, "observer", 1)
        fx.add_line("observer_property", 0, "observer", 0)
        fx.add_dsp(*live_thisdevice("dev", device_rect=[12, 130, 80, 20], device_attrs={"fontsize": 12.0}))
        fx.add_newobj("path_direct", "live.path live_set", numinlets=2, numoutlets=2, patching_rect=[110, 130, 90, 20])
        fx.add_newobj("observer_direct", "live.observer", numinlets=2, numoutlets=2, patching_rect=[210, 130, 90, 20])
        fx.add_newobj("observer_defer", "deferlow", numinlets=1, numoutlets=1, patching_rect=[210, 160, 60, 20])
        fx.add_box({
            "box": {
                "id": "observer_direct_property",
                "maxclass": "message",
                "text": "property tempo",
                "patching_rect": [110, 160, 90, 20],
                "numinlets": 2,
                "numoutlets": 1,
            }
        })
        fx.add_line("path_direct", 1, "observer_direct", 1)
        fx.add_line("observer_direct_property", 0, "observer_direct", 0)
        fx.add_line("observer_defer", 0, "observer_direct", 0)
        fx.add_dsp(
            *live_parameter_probe(
                "probe",
                path="live_set tracks 0 devices 0 parameters 0",
                commands=["get max", "get min", "get value", "call str_for_value 0.5"],
                path_rect=[12, 190, 160, 20],
                object_rect=[12, 220, 80, 20],
                message_rect=[180, 220, 170, 20],
            )
        )
        sub = Subpatcher("analysis")
        sub.add_newobj("route", "route done", numinlets=1, numoutlets=2, patching_rect=[10, 10, 70, 20])
        sub.add_dsp(*param_smooth("embedded_mod"))
        sub.add_newobj("send_sub", "s inner_bus", numinlets=1, numoutlets=0, patching_rect=[10, 40, 70, 20])
        sub.add_newobj("recv_sub", "r inner_bus", numinlets=0, numoutlets=1, patching_rect=[90, 40, 70, 20])
        sub.add_newobj("sub_path", "live.path live_set", numinlets=2, numoutlets=2, patching_rect=[10, 70, 90, 20])
        sub.add_newobj("sub_observer", "live.observer", numinlets=2, numoutlets=2, patching_rect=[110, 70, 80, 20])
        sub.add_box({
            "box": {
                "id": "sub_property",
                "maxclass": "message",
                "text": "property tempo",
                "patching_rect": [200, 70, 90, 20],
                "numinlets": 2,
                "numoutlets": 1,
            }
        })
        sub.add_line("sub_path", 1, "sub_observer", 1)
        sub.add_line("sub_property", 0, "sub_observer", 0)
        fx.add_subpatcher(sub, "analysis_sub", [120, 68, 90, 50])
        fx.build(str(tmp_path / "Corpus FX.amxd"))

        midi = MidiEffect("Corpus MIDI", 220, 100)
        midi_note_gate(midi, "keys", x=60, y=40)
        midi.build(str(tmp_path / "Corpus MIDI.amxd"))

        bridge = build_livemcp_bridge_demo()
        bridge.build(str(tmp_path / "Bridge.amxd"))

        (tmp_path / "broken.amxd").write_text("not an amxd", encoding="utf-8")

        report = analyze_amxd_corpus(str(tmp_path))

        assert report["summary"]["count"] == 4
        assert report["summary"]["ok"] == 3
        assert report["summary"]["error"] == 1
        assert report["summary"]["bridge_enabled_files"] == 1
        assert report["summary"]["files_with_patterns"] >= 1
        assert report["summary"]["files_with_recipes"] >= 1
        assert report["summary"]["files_with_motifs"] >= 1
        assert report["summary"]["files_with_live_api_helpers"] >= 1
        assert report["summary"]["files_with_live_api_helper_opportunities"] >= 1
        assert report["summary"]["files_with_embedded_ui_shell_candidates"] >= 1
        assert report["summary"]["files_with_embedded_patchers"] >= 1
        assert report["summary"]["files_with_embedded_patterns"] >= 1
        assert report["summary"]["files_with_embedded_motifs"] >= 1
        assert report["summary"]["device_types"]["audio_effect"] == 2
        assert report["summary"]["device_types"]["midi_effect"] == 1
        assert any(entry["name"] == "param_smooth" for entry in report["frequencies"]["patterns"])
        assert any(entry["name"] == "midi_note_gate" for entry in report["frequencies"]["recipes"])
        assert any(entry["name"] == "named_bus" for entry in report["frequencies"]["motifs"])
        assert any(entry["name"] == "named_bus:message" for entry in report["frequencies"]["motif_signatures"])
        assert any(entry["name"] == "subpatcher" for entry in report["frequencies"]["embedded_patcher_host_kinds"])
        assert any(entry["name"] == "param_smooth" for entry in report["frequencies"]["embedded_patterns"])
        assert any(entry["name"] == "named_bus" for entry in report["frequencies"]["embedded_motifs"])
        assert any(entry["name"] == "live_set" for entry in report["frequencies"]["live_api_path_targets"])
        assert any(entry["name"] == "is_playing" for entry in report["frequencies"]["live_api_properties"])
        assert any(entry["name"] == "transport_state_observer" for entry in report["frequencies"]["live_api_archetypes"])
        assert any(entry["name"] == "live_thisdevice" for entry in report["frequencies"]["live_api_helpers"])
        assert any(entry["name"] == "live_parameter_probe" for entry in report["frequencies"]["live_api_helpers"])
        assert any(entry["name"] == "exact" for entry in report["frequencies"]["live_api_normalization_levels"])
        assert any(entry["name"] == "manual_review" for entry in report["frequencies"]["live_api_normalization_levels"])
        assert any(entry["name"] == "live_observer" for entry in report["frequencies"]["live_api_helper_opportunities"])
        assert any(entry["name"] == "noncanonical_box_attrs_or_layout" for entry in report["frequencies"]["live_api_helper_opportunity_blockers"])
        assert any(entry["name"] == "controller_surface_shell" for entry in report["frequencies"]["controller_shell_candidates"])
        assert any(entry["name"] == "embedded_ui_shell" for entry in report["frequencies"]["embedded_ui_shell_candidates"])
        assert any(entry["name"] == "live_set" for entry in report["frequencies"]["embedded_live_api_path_targets"])
        assert any(entry["name"] == "tempo" for entry in report["frequencies"]["embedded_live_api_properties"])
        assert any(entry["name"] == "tempo_observer" for entry in report["frequencies"]["embedded_live_api_archetypes"])
        assert any(entry["name"] == "line~" for entry in report["frequencies"]["object_names"])
        assert any(entry["name"] == "live.dial" for entry in report["frequencies"]["control_maxclasses"])
        assert any(entry["name"] == "4" for entry in report["frequencies"]["control_unitstyles"])
        assert any(entry["name"] == "labels" for entry in report["frequencies"]["display_roles"])
        assert any(entry["name"] == "ValueError" for entry in report["frequencies"]["error_types"])
        assert report["frequencies"]["errors"][0]["count"] == 1

    def test_corpus_report_markdown_and_writer(self, tmp_path):
        fx = AudioEffect("Report FX", 220, 100)
        fx.add_dsp(*param_smooth("mod"))
        fx.build(str(tmp_path / "Report FX.amxd"))

        report = analyze_amxd_corpus(str(tmp_path))
        markdown = corpus_report_markdown(report)

        assert "# AMXD Corpus Report" in markdown
        assert "Top Patterns" in markdown
        assert "Top Motifs" in markdown
        assert "Top Motif Signatures" in markdown
        assert "Top Object Names" in markdown
        assert "Top Control Maxclasses" in markdown
        assert "Top Embedded Patcher Host Kinds" in markdown
        assert "Top Embedded Patterns" in markdown
        assert "Top Embedded Motifs" in markdown
        assert "Top Live API Path Targets" in markdown
        assert "Top Live API Properties" in markdown
        assert "Top Live API Archetypes" in markdown
        assert "Top Live API Helper Recoveries" in markdown
        assert "Top Live API Normalization Levels" in markdown
        assert "Top Live API Helper Opportunities" in markdown
        assert "Top Live API Helper Opportunity Blockers" in markdown
        assert "Top Controller Shell Candidates" in markdown
        assert "Top Embedded UI Shell Candidates" in markdown
        assert "Top Embedded Live API Path Targets" in markdown
        assert "Top Embedded Live API Properties" in markdown
        assert "Top Embedded Live API Archetypes" in markdown
        assert "Top Error Types" in markdown
        assert "Largest Devices By Boxes" in markdown

        output = tmp_path / "report.md"
        written = write_corpus_report(report, str(output))

        assert written == len(output.read_text(encoding="utf-8").encode("utf-8"))
        assert output.read_text(encoding="utf-8") == markdown

    def test_analyze_amxd_corpus_dedupes_symlinked_duplicates(self, tmp_path):
        fx = AudioEffect("Linked FX", 220, 100)
        fx.build(str(tmp_path / "Linked FX.amxd"))
        linked_dir = tmp_path / "linked"
        linked_dir.mkdir()
        link_path = linked_dir / "Linked FX copy.amxd"
        try:
            link_path.symlink_to(tmp_path / "Linked FX.amxd")
        except (OSError, NotImplementedError):
            return

        report = analyze_amxd_corpus(str(tmp_path))

        assert report["summary"]["count"] == 1
        assert report["summary"]["ok"] == 1

    def test_analyze_amxd_corpus_tracks_generic_controller_motif_signatures(self, tmp_path):
        device = AudioEffect("Controller Motifs", 320, 180)
        device.add_newobj("route", "route mode", numinlets=1, numoutlets=2, patching_rect=[20, 20, 80, 20])
        device.add_newobj("trigger", "t i i", numinlets=1, numoutlets=2, patching_rect=[120, 20, 40, 20])
        device.add_newobj("gate", "gate 2", numinlets=2, numoutlets=2, patching_rect=[180, 20, 50, 20])
        device.add_line("route", 0, "trigger", 0)
        device.add_line("trigger", 0, "gate", 0)

        device.add_newobj("loadbang", "loadbang", numinlets=1, numoutlets=1, patching_rect=[20, 70, 60, 20])
        device.add_newobj("defer", "deferlow", numinlets=1, numoutlets=1, patching_rect=[100, 70, 60, 20])
        device.add_newobj("init_t", "t b b", numinlets=1, numoutlets=2, patching_rect=[180, 70, 40, 20])
        device.add_line("loadbang", 0, "defer", 0)
        device.add_line("defer", 0, "init_t", 0)

        device.add_newobj("pack", "pack 0 0", numinlets=2, numoutlets=1, patching_rect=[20, 120, 70, 20])
        device.add_newobj("zl", "zl.rev", numinlets=2, numoutlets=2, patching_rect=[110, 120, 60, 20])
        device.add_newobj("unpack", "unpack 0 0", numinlets=1, numoutlets=2, patching_rect=[190, 120, 80, 20])
        device.add_line("pack", 0, "zl", 0)
        device.add_line("zl", 0, "unpack", 0)
        device.build(str(tmp_path / "Controller Motifs.amxd"))

        report = analyze_amxd_corpus(str(tmp_path))
        motif_signatures = {entry["name"] for entry in report["frequencies"]["motif_signatures"]}

        assert any(name.startswith("controller_dispatch:") for name in motif_signatures)
        assert any(name.startswith("scheduler_chain:") for name in motif_signatures)
        assert any(name.startswith("state_bundle:") for name in motif_signatures)

    def test_analyze_amxd_corpus_tracks_cross_scope_named_bus_networks(self, tmp_path):
        device = AudioEffect("Bus Networks", 280, 160)
        device.add_newobj("send_root", "s shared_bus", numinlets=1, numoutlets=0, patching_rect=[20, 20, 70, 20])
        device.add_newobj("recv_root", "r shared_bus", numinlets=0, numoutlets=1, patching_rect=[110, 20, 70, 20])
        sub = Subpatcher("inner")
        sub.add_newobj("send_inner", "s shared_bus", numinlets=1, numoutlets=0, patching_rect=[10, 10, 70, 20])
        sub.add_newobj("recv_inner", "r shared_bus", numinlets=0, numoutlets=1, patching_rect=[90, 10, 70, 20])
        device.add_subpatcher(sub, "inner_host", [20, 80, 120, 50])
        device.build(str(tmp_path / "Bus Networks.amxd"))

        report = analyze_amxd_corpus(str(tmp_path))

        assert report["summary"]["files_with_named_bus_networks"] == 1
        assert report["summary"]["files_with_cross_scope_named_bus_networks"] == 1
        assert any(entry["name"] == "shared_bus" for entry in report["frequencies"]["named_bus_network_names"])
        assert any(entry["name"] == "shared_bus" for entry in report["frequencies"]["cross_scope_named_bus_network_names"])

    def test_rank_reverse_candidates_prefers_motif_rich_embedded_devices(self, tmp_path):
        rich = AudioEffect("Rich Device", 320, 180)
        rich.add_newobj("send_a", "s rich_bus", numinlets=1, numoutlets=0, patching_rect=[20, 20, 60, 20])
        rich.add_newobj("recv_a", "r rich_bus", numinlets=0, numoutlets=1, patching_rect=[100, 20, 60, 20])
        rich.add_newobj("route", "route mode", numinlets=1, numoutlets=2, patching_rect=[20, 60, 80, 20])
        rich.add_newobj("trigger", "t i i", numinlets=1, numoutlets=2, patching_rect=[120, 60, 40, 20])
        rich.add_newobj("gate", "gate 2", numinlets=2, numoutlets=2, patching_rect=[180, 60, 50, 20])
        rich.add_line("route", 0, "trigger", 0)
        rich.add_line("trigger", 0, "gate", 0)
        sub = Subpatcher("inner")
        sub.add_newobj("inner_send", "s rich_bus", numinlets=1, numoutlets=0, patching_rect=[10, 10, 60, 20])
        sub.add_newobj("inner_recv", "r rich_bus", numinlets=0, numoutlets=1, patching_rect=[90, 10, 60, 20])
        rich.add_subpatcher(sub, "host", [20, 110, 100, 40])
        rich.build(str(tmp_path / "Rich Device.amxd"))

        simple = AudioEffect("Simple Device", 220, 100)
        simple.build(str(tmp_path / "Simple Device.amxd"))

        report = analyze_amxd_corpus(str(tmp_path))
        candidates = rank_reverse_candidates(report)

        assert candidates[0]["name"] == "Rich Device.amxd"
        assert candidates[0]["score"] > candidates[1]["score"]
        assert any("generic motifs" in reason for reason in candidates[0]["reasons"])
        assert any("embedded patchers" in reason for reason in candidates[0]["reasons"])
        assert any("cross-scope bus networks" in reason for reason in candidates[0]["reasons"])

    def test_rank_reverse_candidate_families_collapses_versioned_variants(self, tmp_path):
        for name in [
            "repo__CoolDevice-1.0.0.amxd",
            "repo__CoolDevice-1.1.0.amxd",
        ]:
            rich = AudioEffect("Cool Device", 320, 180)
            rich.add_box({
                "box": {
                    "id": "msg",
                    "maxclass": "message",
                    "text": "mode 1",
                    "patching_rect": [20, 10, 60, 20],
                    "numinlets": 2,
                    "numoutlets": 1,
                }
            })
            rich.add_newobj("send_a", "s rich_bus", numinlets=1, numoutlets=0, patching_rect=[20, 20, 60, 20])
            rich.add_newobj("recv_a", "r rich_bus", numinlets=0, numoutlets=1, patching_rect=[100, 20, 60, 20])
            rich.add_newobj("route", "route mode", numinlets=1, numoutlets=2, patching_rect=[20, 60, 80, 20])
            rich.add_newobj("trigger", "t i i", numinlets=1, numoutlets=2, patching_rect=[120, 60, 40, 20])
            rich.add_newobj("prepend", "prepend value", numinlets=1, numoutlets=1, patching_rect=[120, 90, 80, 20])
            rich.add_newobj("gate", "gate 2", numinlets=2, numoutlets=2, patching_rect=[180, 60, 50, 20])
            rich.add_newobj("device", "live.thisdevice", numinlets=1, numoutlets=2, patching_rect=[20, 120, 90, 20])
            rich.add_line("route", 0, "trigger", 0)
            rich.add_line("trigger", 0, "gate", 0)
            rich.build(str(tmp_path / name))

        plain = AudioEffect("Other Device", 220, 100)
        plain.build(str(tmp_path / "repo__OtherDevice-1.0.0.amxd"))

        report = analyze_amxd_corpus(str(tmp_path))
        families = rank_reverse_candidate_families(report)

        assert families[0]["family"] == "CoolDevice"
        assert families[0]["variants"] == 2
        assert families[0]["best_name"].startswith("repo__CoolDevice-")

    def test_build_reverse_candidate_family_profiles_aggregates_variant_signals(self, tmp_path):
        for name in [
            "repo__CoolDevice-1.0.0.amxd",
            "repo__CoolDevice-1.1.0.amxd",
        ]:
            rich = AudioEffect("Cool Device", 320, 180)
            rich.add_box({
                "box": {
                    "id": "msg",
                    "maxclass": "message",
                    "text": "mode 1",
                    "patching_rect": [20, 0, 60, 20],
                    "numinlets": 2,
                    "numoutlets": 1,
                }
            })
            rich.add_newobj("send_a", "s rich_bus", numinlets=1, numoutlets=0, patching_rect=[20, 20, 60, 20])
            rich.add_newobj("recv_a", "r rich_bus", numinlets=0, numoutlets=1, patching_rect=[100, 20, 60, 20])
            rich.add_newobj("route", "route mode", numinlets=1, numoutlets=2, patching_rect=[20, 60, 80, 20])
            rich.add_newobj("trigger", "t i i", numinlets=1, numoutlets=2, patching_rect=[120, 60, 40, 20])
            rich.add_newobj("prepend", "prepend value", numinlets=1, numoutlets=1, patching_rect=[120, 90, 80, 20])
            rich.add_newobj("gate", "gate 2", numinlets=2, numoutlets=2, patching_rect=[180, 60, 50, 20])
            rich.add_newobj("device", "live.thisdevice", numinlets=1, numoutlets=2, patching_rect=[20, 120, 90, 20])
            rich.add_line("route", 0, "trigger", 0)
            rich.add_line("trigger", 0, "gate", 0)
            rich.build(str(tmp_path / name))

        report = analyze_amxd_corpus(str(tmp_path))
        profiles = build_reverse_candidate_family_profiles(report)
        profile = next(entry for entry in profiles if entry["family"] == "CoolDevice")

        assert profile["variants"] == 2
        assert profile["best_name"].startswith("repo__CoolDevice-")
        assert any(entry["name"].startswith("controller_dispatch:") for entry in profile["top_motif_signatures"])
        assert "route" in {entry["name"] for entry in profile["top_object_names"]}
        assert any(entry["name"] == "controller_surface_shell" for entry in profile["semantic_targets"])

    def test_build_reverse_candidate_family_profile_tracks_stable_and_variable_signals(self, tmp_path):
        first = AudioEffect("Cool Device", 320, 180)
        first.add_box({
            "box": {
                "id": "msg",
                "maxclass": "message",
                "text": "mode 1",
                "patching_rect": [20, 0, 60, 20],
                "numinlets": 2,
                "numoutlets": 1,
            }
        })
        first.add_newobj("route", "route mode", numinlets=1, numoutlets=2, patching_rect=[20, 20, 80, 20])
        first.add_newobj("selector", "sel 0 1", numinlets=1, numoutlets=3, patching_rect=[120, 20, 60, 20])
        first.add_newobj("trigger", "t i i", numinlets=1, numoutlets=2, patching_rect=[200, 20, 40, 20])
        first.add_newobj("prepend", "prepend value", numinlets=1, numoutlets=1, patching_rect=[20, 50, 80, 20])
        first.add_newobj("device", "live.thisdevice", numinlets=1, numoutlets=2, patching_rect=[120, 50, 90, 20])
        first.add_newobj("send_a", "s rich_bus", numinlets=1, numoutlets=0, patching_rect=[20, 60, 60, 20])
        first.add_newobj("recv_a", "r rich_bus", numinlets=0, numoutlets=1, patching_rect=[100, 60, 60, 20])
        first.add_line("route", 0, "selector", 0)
        first.add_line("selector", 0, "trigger", 0)
        first.build(str(tmp_path / "repo__CoolDevice-1.0.0.amxd"))

        second = AudioEffect("Cool Device", 320, 180)
        second.add_box({
            "box": {
                "id": "msg",
                "maxclass": "message",
                "text": "mode 1",
                "patching_rect": [20, 0, 60, 20],
                "numinlets": 2,
                "numoutlets": 1,
            }
        })
        second.add_newobj("route", "route mode", numinlets=1, numoutlets=2, patching_rect=[20, 20, 80, 20])
        second.add_newobj("selector", "sel 0 1", numinlets=1, numoutlets=3, patching_rect=[120, 20, 60, 20])
        second.add_newobj("trigger", "t i i", numinlets=1, numoutlets=2, patching_rect=[200, 20, 40, 20])
        second.add_newobj("prepend", "prepend value", numinlets=1, numoutlets=1, patching_rect=[20, 50, 80, 20])
        second.add_newobj("device", "live.thisdevice", numinlets=1, numoutlets=2, patching_rect=[120, 50, 90, 20])
        second.add_newobj("loadbang", "loadbang", numinlets=1, numoutlets=1, patching_rect=[20, 60, 60, 20])
        second.add_line("route", 0, "selector", 0)
        second.add_line("selector", 0, "trigger", 0)
        second.build(str(tmp_path / "repo__CoolDevice-1.1.0.amxd"))

        report = analyze_amxd_corpus(str(tmp_path))
        profile = build_reverse_candidate_family_profile(report, "CoolDevice")

        assert profile is not None
        assert profile["variant_count"] == 2
        assert any(
            entry["name"].startswith("controller_dispatch:")
            for entry in profile["stable_signals"]["motif_signatures"]
        )
        assert any(entry["name"] == "route" for entry in profile["stable_signals"]["object_names"])
        assert any(entry["name"] == "rich_bus" for entry in profile["variable_signals"]["named_bus_network_names"])
        assert {entry["name"] for entry in profile["variants"]} == {
            "repo__CoolDevice-1.0.0.amxd",
            "repo__CoolDevice-1.1.0.amxd",
        }
        assert any(entry["name"] == "controller_surface_shell" for entry in profile["semantic_targets"])
        assert any(entry["name"] == "optional_named_bus_layer" for entry in profile["semantic_targets"])
        assert any("controller-surface abstraction" in item for item in profile["next_work_items"])

    def test_family_profile_markdown_and_writer(self, tmp_path):
        device = AudioEffect("Cool Device", 320, 180)
        device.add_newobj("route", "route mode", numinlets=1, numoutlets=2, patching_rect=[20, 20, 80, 20])
        device.add_newobj("selector", "sel 0 1", numinlets=1, numoutlets=3, patching_rect=[120, 20, 60, 20])
        device.add_line("route", 0, "selector", 0)
        device.build(str(tmp_path / "repo__CoolDevice-1.0.0.amxd"))

        report = analyze_amxd_corpus(str(tmp_path))
        profile = build_reverse_candidate_family_profile(report, "CoolDevice")
        markdown = family_profile_markdown(profile)

        assert "# AMXD Family Report" in markdown
        assert "Semantic Targets" in markdown
        assert "Next Work Items" in markdown
        assert "Stable Motif Signatures" in markdown
        assert "Variable Object Names" in markdown
        assert "Variants" in markdown

        output = tmp_path / "family-report.md"
        written = write_family_profile(profile, str(output))

        assert written == len(output.read_text(encoding="utf-8").encode("utf-8"))
        assert output.read_text(encoding="utf-8") == markdown

    def test_build_reverse_candidate_family_profile_infers_sequencer_dispatch_shell(self, tmp_path):
        device = MidiEffect("Trigger Seq", 320, 180)
        device.add_newobj("sel", "sel 0 1", numinlets=1, numoutlets=3, patching_rect=[20, 20, 60, 20])
        device.add_newobj("gate", "gate 2", numinlets=2, numoutlets=2, patching_rect=[100, 20, 50, 20])
        device.add_newobj("route", "route loop", numinlets=1, numoutlets=2, patching_rect=[170, 20, 70, 20])
        device.add_newobj("defer", "deferlow", numinlets=1, numoutlets=1, patching_rect=[20, 60, 60, 20])
        device.add_newobj("delay", "delay 5", numinlets=2, numoutlets=1, patching_rect=[100, 60, 60, 20])
        device.add_newobj("send_loop", "s ---loop", numinlets=1, numoutlets=0, patching_rect=[20, 100, 70, 20])
        device.add_newobj("recv_loop", "r ---loop", numinlets=0, numoutlets=1, patching_rect=[110, 100, 70, 20])
        device.add_line("sel", 0, "gate", 0)
        device.add_line("gate", 0, "route", 0)
        device.add_line("defer", 0, "delay", 0)
        device.build(str(tmp_path / "repo__TriggerSeq-v3.amxd"))

        report = analyze_amxd_corpus(str(tmp_path))
        profile = build_reverse_candidate_family_profile(report, "TriggerSeq-v3")

        assert profile is not None
        assert any(entry["name"] == "sequencer_dispatch_shell" for entry in profile["semantic_targets"])
        assert any("sequencer-control normalization" in item for item in profile["next_work_items"])
