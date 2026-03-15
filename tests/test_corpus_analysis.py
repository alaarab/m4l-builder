"""Tests for external AMXD corpus analysis helpers."""

from m4l_builder import (
    AudioEffect,
    MidiEffect,
    Subpatcher,
    analyze_amxd_corpus,
    build_corpus_comparison,
    build_reference_device_dossier,
    build_reference_device_dossiers,
    build_mapping_product_brief_from_path,
    build_mapping_product_briefs,
    build_reverse_candidate_family_profile,
    build_livemcp_bridge_demo,
    build_mapping_lane_report,
    build_reverse_candidate_family_profiles,
    build_source_lane_profiles,
    classify_corpus_source_metadata,
    corpus_comparison_markdown,
    corpus_report_markdown,
    family_profile_markdown,
    mapping_lane_report_markdown,
    mapping_product_brief_markdown,
    mapping_product_briefs_markdown,
    live_parameter_probe,
    live_thisdevice,
    midi_note_gate,
    param_smooth,
    rank_reverse_candidates,
    rank_reverse_candidate_families,
    rank_mapping_candidates,
    reference_device_dossiers_markdown,
    source_lane_profiles_markdown,
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
        assert any(entry["name"] == "embedded_ui_shell_v2" for entry in report["frequencies"]["embedded_ui_shell_candidates"])
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
        assert "Top Named Bus Router Candidates" in markdown
        assert "Top Init Dispatch Candidates" in markdown
        assert "Top State Bundle Router Candidates" in markdown
        assert "Top Poly Shell Candidates" in markdown
        assert "Top First-Party API Rig Candidates" in markdown
        assert "Top Building Block Candidates" in markdown
        assert "Top Source Lanes" in markdown
        assert "Top Pack Names" in markdown
        assert "Top Pack Sections" in markdown
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

    def test_analyze_amxd_corpus_tracks_factory_lane_metadata_and_first_party_candidates(self, tmp_path):
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
        api_device.build(str(api_root / "Max Api DeviceExplorer.amxd"))

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
        block.build(str(blocks_root / "Max DelayLine.amxd"))

        report = analyze_amxd_corpus(str(tmp_path))

        assert report["summary"]["source_lanes"]["factory"] == 2
        assert any(entry["name"] == "factory" for entry in report["frequencies"]["source_lanes"])
        assert any(entry["name"] == "M4L Building Tools" for entry in report["frequencies"]["pack_names"])
        assert any(
            entry["name"] == "M4L Building Tools / API"
            for entry in report["frequencies"]["pack_sections"]
        )
        assert any(
            entry["name"] == "first_party_api_rig"
            for entry in report["frequencies"]["first_party_api_rig_candidates"]
        )
        assert any(
            entry["name"] == "Max DelayLine"
            for entry in report["frequencies"]["building_block_candidates"]
        )
        assert any(
            entry["name"] == "named_bus_router"
            for entry in report["frequencies"]["named_bus_router_candidates"]
        )
        assert any(
            entry["name"] == "init_dispatch_chain"
            for entry in report["frequencies"]["init_dispatch_chain_candidates"]
        )

        api_item = next(item for item in report["items"] if item["name"] == "Max Api DeviceExplorer.amxd")
        assert api_item["source_lane"] == "factory"
        assert api_item["pack_name"] == "M4L Building Tools"
        assert api_item["pack_section"] == "API"
        assert api_item["first_party_api_rig_candidate_count"] == 1

    def test_classify_corpus_source_metadata_detects_factory_paths(self):
        metadata = classify_corpus_source_metadata(
            "/tmp/Factory Packs/M4L Building Tools/Building Blocks/Max Audio Effect/Max DelayLine.amxd"
        )

        assert metadata["source_lane"] == "factory"
        assert metadata["pack_name"] == "M4L Building Tools"
        assert metadata["pack_section"] == "Building Blocks"
        assert metadata["pack_subsection"] == "Max Audio Effect"

    def test_classify_corpus_source_metadata_resolves_symlink_targets(self, tmp_path):
        factory_root = tmp_path / "Factory Packs" / "M4L Building Tools" / "API"
        factory_root.mkdir(parents=True)
        target = factory_root / "Max Api DeviceExplorer.amxd"
        target.write_text("placeholder", encoding="utf-8")

        alias_root = tmp_path / "aliases"
        alias_root.mkdir()
        alias = alias_root / "api-device.amxd"
        alias.symlink_to(target)

        metadata = classify_corpus_source_metadata(str(alias))

        assert metadata["source_lane"] == "factory"
        assert metadata["pack_name"] == "M4L Building Tools"
        assert metadata["pack_section"] == "API"

    def test_build_source_lane_profiles_summarizes_factory_vs_public(self, tmp_path):
        public_fx = AudioEffect("Public FX", 220, 100)
        public_fx.add_dsp(*param_smooth("mod"))
        public_fx.build(str(tmp_path / "Public FX.amxd"))

        factory_root = tmp_path / "Factory Packs" / "M4L Building Tools" / "Building Blocks" / "Max Audio Effect"
        factory_root.mkdir(parents=True)
        factory_fx = AudioEffect("Max DelayLine", 220, 100)
        factory_fx.add_newobj("send_a", "s block_bus", numinlets=1, numoutlets=0, patching_rect=[20, 20, 70, 20])
        factory_fx.add_newobj("recv_a", "r block_bus", numinlets=0, numoutlets=1, patching_rect=[110, 20, 70, 20])
        factory_fx.add_newobj("gain_l", "M4L.gain1~", numinlets=2, numoutlets=1, patching_rect=[20, 60, 70, 20])
        factory_fx.add_newobj("gain_r", "M4L.gain1~", numinlets=2, numoutlets=1, patching_rect=[110, 60, 70, 20])
        factory_fx.add_dial("gain", "Gain", [66, 10, 44, 44], min_val=-70.0, max_val=6.0, initial=0.0, unitstyle=4)
        factory_fx.add_line("gain", 0, "gain_l", 1)
        factory_fx.add_line("gain", 0, "gain_r", 1)
        factory_fx.build(str(factory_root / "Max DelayLine.amxd"))

        report = analyze_amxd_corpus(str(tmp_path))
        profiles = build_source_lane_profiles(report)
        markdown = source_lane_profiles_markdown(profiles)

        assert {entry["lane"] for entry in profiles} == {"factory", "public"}
        factory_profile = next(entry for entry in profiles if entry["lane"] == "factory")
        assert factory_profile["count"] == 1
        assert any(entry["name"] == "M4L.gain1~" for entry in factory_profile["top_first_party_abstraction_hosts"])
        assert any(entry["name"] == "gain_shell" for entry in factory_profile["top_first_party_abstraction_families"])
        assert "AMXD Source Lane Profiles" in markdown
        assert "## factory" in markdown

    def test_analyze_amxd_corpus_tracks_presentation_widget_clusters(self, tmp_path):
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
        device.build(str(root / "Factory Presentation Cluster.amxd"))

        report = analyze_amxd_corpus(str(tmp_path / "Factory Packs"))

        assert report["summary"]["files_with_presentation_widget_cluster_candidates"] == 1
        assert any(
            entry["name"] == "presentation_widget_cluster"
            for entry in report["frequencies"]["presentation_widget_cluster_candidates"]
        )

    def test_analyze_amxd_corpus_tracks_first_party_abstraction_hosts(self, tmp_path):
        root = tmp_path / "Factory Packs" / "M4L Building Tools" / "Building Blocks" / "Max Audio Effect"
        root.mkdir(parents=True)
        device = AudioEffect("Max GainDualMono", 320, 180)
        device.add_newobj("gain_l", "M4L.gain1~", numinlets=2, numoutlets=1, patching_rect=[20, 70, 70, 20])
        device.add_newobj("gain_r", "M4L.gain1~", numinlets=2, numoutlets=1, patching_rect=[140, 70, 70, 20])
        device.add_dial("gain", "Gain", [72, 18, 44, 44], min_val=-70.0, max_val=6.0, initial=0.0, unitstyle=4)
        device.add_comment("label", [66, 66, 60, 18], "Gain")
        device.add_line("gain", 0, "gain_l", 1)
        device.add_line("gain", 0, "gain_r", 1)
        device.build(str(root / "Max GainDualMono.amxd"))

        report = analyze_amxd_corpus(str(tmp_path / "Factory Packs"))

        assert report["summary"]["files_with_first_party_abstraction_host_candidates"] == 1
        assert any(
            entry["name"] == "M4L.gain1~"
            for entry in report["frequencies"]["first_party_abstraction_host_candidates"]
        )
        assert any(
            entry["name"] == "gain_shell"
            for entry in report["frequencies"]["first_party_abstraction_host_families"]
        )

    def test_analyze_amxd_corpus_tracks_poly_shell_banks(self, tmp_path):
        device = AudioEffect("Rnd Style Voice Bank", 420, 260)
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
        device.build(str(tmp_path / "Rnd Style Voice Bank.amxd"))

        report = analyze_amxd_corpus(str(tmp_path))

        assert report["summary"]["files_with_poly_shell_candidates"] == 1
        assert report["summary"]["files_with_poly_shell_bank_candidates"] == 1
        assert report["summary"]["files_with_poly_editor_bank_candidates"] == 1
        assert report["summary"]["files_with_behavior_hints"] == 1
        assert any(
            entry["name"] == "poly_shell_bank"
            for entry in report["frequencies"]["poly_shell_bank_candidates"]
        )
        assert any(
            entry["name"] == "poly_editor_bank"
            for entry in report["frequencies"]["poly_editor_bank_candidates"]
        )
        assert any(
            entry["name"] == "multi_lane_mapping_bank"
            for entry in report["frequencies"]["behavior_hints"]
        )

    def test_analyze_amxd_corpus_tracks_mapping_workflow_candidates(self, tmp_path):
        device = AudioEffect("Rnd Workflow", 420, 260)
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

        device.build(str(tmp_path / "Rnd Workflow.amxd"))
        report = analyze_amxd_corpus(str(tmp_path))

        assert report["summary"]["files_with_mapping_behavior_traces"] == 1
        assert report["summary"]["files_with_mapping_semantic_candidates"] == 1
        assert report["summary"]["files_with_mapping_workflow_candidates"] == 1
        assert any(
            entry["name"] == "triggered_parameter_mapper"
            for entry in report["frequencies"]["mapping_semantic_candidates"]
        )
        assert any(
            entry["name"] == "mapping_session_lifecycle"
            for entry in report["frequencies"]["mapping_behavior_traces"]
        )
        assert any(
            entry["name"] == "mapping_workflow_shell"
            for entry in report["frequencies"]["mapping_workflow_candidates"]
        )

    def test_build_mapping_lane_report_classifies_modulation_families(self, tmp_path):
        rnd = AudioEffect("Rnd Workflow", 420, 260)
        rnd.add_box({
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
            rnd.add_box({
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
            rnd.add_newobj(f"poly_{index}", "poly~ Abl.Map.edit", numinlets=4, numoutlets=4, patching_rect=[170, y, 110, 20])
            rnd.add_newobj(f"send_{index}", f"s ---m{index}", numinlets=1, numoutlets=0, patching_rect=[310, y, 60, 20])
            rnd.add_line(f"ui_{index}", 0, f"poly_{index}", 0)
            rnd.add_line(f"ui_{index}", 1, f"poly_{index}", 1)
            rnd.add_line(f"poly_{index}", 0, f"ui_{index}", 0)
            rnd.add_line(f"poly_{index}", 1, f"ui_{index}", 1)
            rnd.add_line(f"poly_{index}", 2, f"send_{index}", 0)
            rnd.add_line("shared_mod", 0, f"poly_{index}", 2)
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
        rnd.add_subpatcher(midi_logic, "midi_logic", [20, 220, 120, 50])
        qm = Subpatcher("qm")
        qm.add_newobj("start", "s ---qmap_start", numinlets=1, numoutlets=0, patching_rect=[20, 20, 90, 20])
        qm.add_newobj("done", "r ---done_qmap", numinlets=0, numoutlets=1, patching_rect=[130, 20, 90, 20])
        qm.add_newobj("qmap", "s ---qmap", numinlets=1, numoutlets=0, patching_rect=[240, 20, 70, 20])
        qm.add_newobj("update", "s ---update_local", numinlets=1, numoutlets=0, patching_rect=[330, 20, 100, 20])
        rnd.add_subpatcher(qm, "qm_logic", [160, 220, 120, 50])
        rnd.build(str(tmp_path / "Rnd Workflow.amxd"))

        macro = AudioEffect("Macro Randomizer", 300, 140)
        for index in range(7):
            x = 8 + index * 30
            macro.add_dial(
                f"p{index+1}_dial",
                f"P{index+1}",
                [x, 38, 28, 70],
                min_val=0.0,
                max_val=100.0,
                initial=50.0,
                unitstyle=5,
                annotation_name=f"Parameter {index+1} — randomizable output",
            )
        macro.add_dial("rate_dial", "Rate", [222, 38, 40, 70], min_val=0.0, max_val=100.0, initial=25.0, unitstyle=5, annotation_name="Auto-randomize speed — 0 slow, 100 fast")
        macro.add_newobj("metro", "metro 500", numinlets=2, numoutlets=1, outlettype=["bang"], patching_rect=[20, 200, 70, 20])
        macro.add_newobj("rate_scale", "scale 0. 100. 2000. 50.", numinlets=6, numoutlets=1, outlettype=[""], patching_rect=[120, 200, 120, 20])
        macro.add_newobj("trig_sel", "sel 1", numinlets=2, numoutlets=2, outlettype=["bang", ""], patching_rect=[250, 200, 40, 20])
        macro.add_newobj("fan", "t b b b b b b b", numinlets=1, numoutlets=7, outlettype=["bang"] * 7, patching_rect=[20, 240, 200, 20])
        macro.add_line("rate_dial", 0, "rate_scale", 0)
        macro.add_line("rate_scale", 0, "metro", 1)
        macro.add_line("metro", 0, "fan", 0)
        macro.add_line("trig_sel", 0, "fan", 0)
        for index in range(7):
            macro.add_newobj(f"rand_{index+1}", "random 10001", numinlets=2, numoutlets=1, outlettype=[""], patching_rect=[20 + index * 50, 280, 65, 20])
            macro.add_newobj(f"rdiv_{index+1}", "/ 100.", numinlets=2, numoutlets=1, outlettype=[""], patching_rect=[20 + index * 50, 310, 40, 20])
            macro.add_line("fan", index, f"rand_{index+1}", 0)
            macro.add_line(f"rand_{index+1}", 0, f"rdiv_{index+1}", 0)
            macro.add_line(f"rdiv_{index+1}", 0, f"p{index+1}_dial", 0)
        macro.build(str(tmp_path / "Macro Randomizer.amxd"))

        expr = MidiEffect("Expression Control", 320, 115)
        for index in range(8):
            x = 8 + index * 38
            expr.add_dial(
                f"macro_{index+1}",
                f"M{index+1}",
                [x, 18, 34, 72],
                min_val=0.0,
                max_val=127.0,
                initial=64.0,
                unitstyle=8,
                annotation_name=f"Macro {index+1} — outputs CC {index+1}",
            )
            expr.add_newobj(f"int_{index+1}", "int", numinlets=2, numoutlets=1, outlettype=[""], patching_rect=[20 + index * 50, 200, 30, 20])
        expr.add_newobj(f"ctlout_{index+1}", f"ctlout {index+1} 1", numinlets=3, numoutlets=0, outlettype=[], patching_rect=[20 + index * 50, 230, 60, 20])
        expr.add_line(f"macro_{index+1}", 0, f"int_{index+1}", 0)
        expr.add_line(f"int_{index+1}", 0, f"ctlout_{index+1}", 0)
        expr.build(str(tmp_path / "Expression Control.amxd"))

        randomizer = AudioEffect("Device Randomizer", 340, 180)
        randomizer.add_button("trigger", "trigger", [10, 10, 24, 24])
        randomizer.add_newobj("sel", "sel 1", numinlets=2, numoutlets=2, patching_rect=[44, 14, 40, 20])
        randomizer.add_line("trigger", 0, "sel", 0)
        selected = Subpatcher("selectedID")
        selected.add_newobj("path", "live.path live_set view", numinlets=2, numoutlets=2, patching_rect=[20, 20, 100, 20])
        selected.add_newobj("object", "live.object", numinlets=2, numoutlets=1, outlettype=[""], patching_rect=[130, 20, 70, 20])
        selected.add_newobj("route", "route id", numinlets=2, numoutlets=2, patching_rect=[210, 20, 60, 20])
        randomizer.add_subpatcher(selected, "selected_shell", [20, 70, 110, 50])
        params = Subpatcher("checkParamAvalibility")
        params.add_newobj("path", "live.path", numinlets=2, numoutlets=2, patching_rect=[20, 20, 60, 20])
        params.add_newobj("object", "live.object", numinlets=2, numoutlets=1, outlettype=[""], patching_rect=[90, 20, 70, 20])
        params.add_newobj("route", "route is_quantized", numinlets=2, numoutlets=2, patching_rect=[170, 20, 90, 20])
        params.add_newobj("store", "s ---StoreRandSettings", numinlets=1, numoutlets=0, patching_rect=[20, 50, 120, 20])
        params.add_newobj("recall", "r ---RecallRandSettings", numinlets=0, numoutlets=1, patching_rect=[150, 50, 130, 20])
        randomizer.add_subpatcher(params, "params_shell", [150, 70, 120, 50])
        randomizer.build(str(tmp_path / "Device Randomizer.amxd"))

        lfo = MidiEffect("LFO MIDI", 320, 140)
        lfo.add_button("tap", "tap", [10, 10, 24, 24])
        lfo.add_dial("rate", "Rate", [10, 40, 34, 70], min_val=0.0, max_val=127.0, initial=64.0)
        lfo.add_dial("shape", "Shape", [50, 40, 34, 70], min_val=0.0, max_val=127.0, initial=64.0)
        lfo.add_dial("depth", "Depth", [90, 40, 34, 70], min_val=0.0, max_val=127.0, initial=64.0)
        lfo.add_newobj("sel", "sel 1", numinlets=2, numoutlets=2, patching_rect=[44, 14, 40, 20])
        lfo.add_line("tap", 0, "sel", 0)
        sync = Subpatcher("sync")
        sync.add_newobj("phasor", "phasor~ @lock 1", numinlets=2, numoutlets=1, outlettype=["signal"], patching_rect=[20, 20, 90, 20])
        lfo.add_subpatcher(sync, "sync_shell", [20, 60, 90, 50])
        waveform = Subpatcher("waveform_select")
        waveform.add_newobj("triangle", "triangle~ 0.5", numinlets=2, numoutlets=1, outlettype=["signal"], patching_rect=[20, 20, 90, 20])
        waveform.add_newobj("selector", "selector~ 2 1", numinlets=3, numoutlets=1, outlettype=["signal"], patching_rect=[20, 50, 80, 20])
        waveform.add_newobj("noise", "noise~", numinlets=1, numoutlets=1, outlettype=["signal"], patching_rect=[120, 20, 50, 20])
        lfo.add_subpatcher(waveform, "wave_shell", [120, 60, 120, 50])
        hold = Subpatcher("Hold")
        hold.add_newobj("snapshot", "snapshot~", numinlets=2, numoutlets=1, outlettype=["float"], patching_rect=[20, 20, 70, 20])
        lfo.add_subpatcher(hold, "hold_shell", [250, 60, 90, 50])
        lfo.build(str(tmp_path / "LFO MIDI.amxd"))

        report = analyze_amxd_corpus(str(tmp_path))
        lane_report = build_mapping_lane_report(report, limit=10)
        markdown = mapping_lane_report_markdown(lane_report)
        ranked = rank_mapping_candidates(report, limit=10)
        briefs = build_mapping_product_briefs(report, limit=10)
        brief_markdown = mapping_product_briefs_markdown(briefs)

        assert lane_report["summary"]["count"] == 5
        assert any(entry["name"] == "parameter_mapper" for entry in lane_report["product_classes"])
        assert any(entry["name"] == "parameter_randomizer" for entry in lane_report["product_classes"])
        assert any(entry["name"] == "random_modulation_source" for entry in lane_report["product_classes"])
        assert any(entry["name"] == "lfo_modulation_source" for entry in lane_report["product_classes"])
        assert any(entry["name"] == "modulation_bank" for entry in lane_report["product_classes"])
        assert any(entry["name"] == "triggered_parameter_mapper" for entry in lane_report["mapping_semantic_candidates"])
        assert any(entry["name"] == "device_parameter_randomizer" for entry in lane_report["mapping_semantic_candidates"])
        assert any(entry["name"] == "lfo_modulation_source" for entry in lane_report["mapping_semantic_candidates"])
        assert ranked[0]["product_class"] == "parameter_mapper"
        assert "Rnd Gen-style mapper" in markdown
        assert "Macro Randomizer-style device" in markdown
        assert "Expression Control-style bank" in markdown
        assert "Device Randomizer-style device" in markdown
        assert "LFO MIDI-style device" in markdown
        assert briefs[0]["product_class"] == "parameter_mapper"
        assert briefs[0]["product_thesis"] == (
            "Triggered mapping workflow that assigns and updates target parameters across multiple lanes."
        )
        assert briefs[0]["confidence"] == "high"
        assert any(
            brief["name"] == "Device Randomizer.amxd"
            and brief["target_model"].startswith("Targets come from the current device")
            for brief in briefs
        )
        assert "# Mapping / Modulation Product Briefs" in brief_markdown
        assert "Build cleanly as" in brief_markdown
        assert "Triggered mapping workflow that assigns and updates target parameters across multiple lanes." in brief_markdown

    def test_build_reference_device_dossier_reports_semantic_lift(self, tmp_path):
        factory_root = tmp_path / "Factory Packs" / "M4L Building Tools" / "Building Blocks" / "Max Audio Effect"
        factory_root.mkdir(parents=True)
        device = AudioEffect("Max DelayLine", 320, 180)
        device.add_newobj("send_a", "s shared_bus", numinlets=1, numoutlets=0, patching_rect=[20, 20, 70, 20])
        device.add_newobj("recv_a", "r shared_bus", numinlets=0, numoutlets=1, patching_rect=[110, 20, 70, 20])
        device.add_newobj("loadbang", "loadbang", numinlets=1, numoutlets=1, patching_rect=[20, 60, 60, 20])
        device.add_newobj("defer", "deferlow", numinlets=1, numoutlets=1, patching_rect=[100, 60, 60, 20])
        device.add_newobj("init_t", "t b b", numinlets=1, numoutlets=2, patching_rect=[180, 60, 40, 20])
        device.add_line("loadbang", 0, "defer", 0)
        device.add_line("defer", 0, "init_t", 0)
        path = factory_root / "Max DelayLine.amxd"
        device.build(str(path))

        dossier = build_reference_device_dossier(str(path))
        dossiers = build_reference_device_dossiers([str(path)])
        markdown = reference_device_dossiers_markdown(dossiers)

        assert dossier["source"]["source_lane"] == "factory"
        assert "named_bus_router" in dossier["recovered_classes"]
        assert "init_dispatch_chain" in dossier["recovered_classes"]
        assert dossier["semantic_add_box_count"] <= dossier["raw_add_box_count"]
        assert dossier["semantic_helper_call_count"] >= 2
        assert dossier["semantic_helper_calls"]["named_bus_router"] >= 1
        assert dossier["semantic_helper_calls"]["init_dispatch_chain"] >= 1
        assert dossier["structural_lift_score"] >= dossier["semantic_helper_call_count"]
        assert dossier["product_brief"]["product_class"] == "unknown"
        assert "AMXD Reference Device Dossiers" in markdown
        assert "Max DelayLine.amxd" in markdown
        assert "Structural lift score" in markdown
        assert "### Product Brief" in markdown

    def test_build_reference_device_dossier_records_errors_without_aborting(self, tmp_path):
        broken = tmp_path / "broken.amxd"
        broken.write_text("not an amxd", encoding="utf-8")

        dossier = build_reference_device_dossier(str(broken))
        markdown = reference_device_dossiers_markdown([dossier])

        assert "error" in dossier
        assert "analysis_error" in dossier["fallback_zones"]
        assert dossier["semantic_helper_call_count"] == 0
        assert dossier["structural_lift_score"] == 0
        assert dossier["product_brief"] is None
        assert "Error:" in markdown

    def test_build_mapping_product_brief_from_path_renders_single_device(self, tmp_path):
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
        device.add_subpatcher(waveform, "wave_shell", [120, 60, 120, 50])
        hold = Subpatcher("Hold")
        hold.add_newobj("snapshot", "snapshot~", numinlets=2, numoutlets=1, outlettype=["float"], patching_rect=[20, 20, 70, 20])
        device.add_subpatcher(hold, "hold_shell", [250, 60, 90, 50])
        path = tmp_path / "LFO MIDI.amxd"
        device.build(str(path))

        brief = build_mapping_product_brief_from_path(str(path))
        markdown = mapping_product_brief_markdown(brief)

        assert brief["product_class"] == "lfo_modulation_source"
        assert brief["closest_reference"] == "LFO MIDI-style device"
        assert brief["score"] > 0
        assert "waveform core" in brief["build_cleanly_as"]
        assert "# Mapping / Modulation Product Brief" in markdown
        assert "LFO MIDI-style device" in markdown
        assert "Product read" in markdown

    def test_build_corpus_comparison_summarizes_separate_roots(self, tmp_path):
        public_root = tmp_path / "public"
        public_root.mkdir()
        public_fx = AudioEffect("Public FX", 220, 100)
        public_fx.add_dsp(*param_smooth("mod"))
        public_fx.build(str(public_root / "Public FX.amxd"))

        factory_root = tmp_path / "Factory Packs" / "M4L Building Tools" / "Building Blocks" / "Max Audio Effect"
        factory_root.mkdir(parents=True)
        factory_fx = AudioEffect("Max DelayLine", 220, 100)
        factory_fx.add_newobj("send_a", "s shared_bus", numinlets=1, numoutlets=0, patching_rect=[20, 20, 70, 20])
        factory_fx.add_newobj("recv_a", "r shared_bus", numinlets=0, numoutlets=1, patching_rect=[110, 20, 70, 20])
        factory_fx.build(str(factory_root / "Max DelayLine.amxd"))

        comparison = build_corpus_comparison({
            "public": analyze_amxd_corpus(str(public_root)),
            "factory": analyze_amxd_corpus(str(tmp_path / "Factory Packs")),
        })
        markdown = corpus_comparison_markdown(comparison)

        assert {entry["label"] for entry in comparison["reports"]} == {"factory", "public"}
        assert "# AMXD Corpus Comparison" in markdown
        assert "## factory" in markdown
        assert "## public" in markdown

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
