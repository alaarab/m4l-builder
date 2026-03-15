"""Tests for the reusable LiveMCP bridge helpers."""

import json
import shutil
import subprocess

import pytest

from m4l_builder import AudioEffect, Instrument, enable_livemcp_bridge
from m4l_builder.livemcp_bridge import (
    BRIDGE_CAPABILITIES,
    BRIDGE_COMMANDS,
    BRIDGE_RUNTIME_FILENAME,
    BRIDGE_SCHEMA_FILENAME,
    BRIDGE_SERVER_FILENAME,
    DEFAULT_BRIDGE_PORT,
    bridge_runtime_js,
    bridge_schema,
    bridge_server_js,
    build_livemcp_bridge_demo,
)


def _boxes(device):
    return {
        box["box"]["id"]: box["box"]
        for box in device.to_patcher()["patcher"]["boxes"]
    }


class TestBridgeSchema:
    def test_schema_has_required_top_level_fields(self):
        schema = bridge_schema()

        assert schema["protocol_version"] == 1
        assert schema["host"] == "127.0.0.1"
        assert schema["transport"] == "tcp-json-lines"
        assert schema["session_mode"] == "selected-device-server"
        assert schema["capabilities"] == BRIDGE_CAPABILITIES
        assert "commands" in schema

    def test_schema_covers_required_commands(self):
        schema = bridge_schema()

        for command in [
            "get_max_bridge_info",
            "find_device_session",
            "show_editor",
            "get_current_patcher",
            "list_boxes",
            "get_box_attrs",
            "set_box_attrs",
            "create_box",
            "connect_boxes",
            "disconnect_boxes",
            "delete_box",
            "set_presentation_rect",
            "set_presentation_mode",
            "save_device",
        ]:
            assert command in schema["commands"]

    def test_python_command_table_matches_schema(self):
        schema = bridge_schema()
        assert set(schema["commands"]) == set(BRIDGE_COMMANDS)


class TestBridgeEmbedding:
    def test_enable_bridge_embeds_runtime_objects_on_existing_device(self):
        device = AudioEffect("Bridge Ready", width=320, height=140)

        metadata = enable_livemcp_bridge(device)
        boxes = _boxes(device)

        assert metadata["port"] == DEFAULT_BRIDGE_PORT
        assert boxes["livemcp_bridge_runtime"]["text"] == "js %s" % BRIDGE_RUNTIME_FILENAME
        assert boxes["livemcp_bridge_server"]["text"] == (
            "node.script %s @autostart 1 @watch 0" % BRIDGE_SERVER_FILENAME
        )
        assert boxes["livemcp_bridge_thisdevice"]["text"] == "live.thisdevice"

    def test_enable_bridge_can_attach_to_non_audio_devices(self):
        device = Instrument("Bridge Synth", width=360, height=180)

        enable_livemcp_bridge(device)
        boxes = _boxes(device)

        assert "livemcp_bridge_runtime" in boxes
        assert "obj-plugin" not in boxes

    def test_enable_bridge_rejects_duplicate_prefix(self):
        device = AudioEffect("Dup", width=300, height=120)
        enable_livemcp_bridge(device, prefix="dup_bridge")

        with pytest.raises(ValueError, match="already exist"):
            enable_livemcp_bridge(device, prefix="dup_bridge")

    def test_enable_bridge_include_ui_alias_adds_compact_badge(self):
        device = AudioEffect("Badge", width=220, height=68)

        enable_livemcp_bridge(device, include_ui=True)
        boxes = _boxes(device)

        assert boxes["livemcp_bridge_accent"]["presentation_rect"] == [10, 10, 4, 48]
        assert boxes["livemcp_bridge_target"]["text"] == "Ready for patch edits."

    def test_demo_contains_named_target(self):
        device = build_livemcp_bridge_demo()
        boxes = _boxes(device)

        assert device.width == 220
        assert device.height == 68
        assert boxes["bridge_demo_accent"]["presentation_rect"] == [10, 10, 4, 48]
        assert boxes["bridge_demo_target"]["varname"] == "bridge_demo_target"
        assert boxes["bridge_demo_target"]["presentation_rect"] == [22, 27, 188, 14]
        assert boxes["bridge_demo_target"]["text"] == "Ready for patch edits."

    def test_demo_registers_support_files(self):
        device = build_livemcp_bridge_demo()
        patcher = device.to_patcher()
        deps = {dep["name"] for dep in patcher["patcher"]["dependency_cache"]}

        assert BRIDGE_RUNTIME_FILENAME in deps
        assert BRIDGE_SERVER_FILENAME in deps
        assert BRIDGE_SCHEMA_FILENAME in deps

    def test_build_writes_sidecars(self, tmp_path):
        device = build_livemcp_bridge_demo(port=DEFAULT_BRIDGE_PORT)
        output = tmp_path / "LiveMCP Bridge Demo.amxd"

        written = device.build(str(output))

        assert written > 0
        assert output.exists()
        assert (tmp_path / BRIDGE_RUNTIME_FILENAME).exists()
        assert (tmp_path / BRIDGE_SERVER_FILENAME).exists()
        schema_path = tmp_path / BRIDGE_SCHEMA_FILENAME
        assert schema_path.exists()
        assert json.loads(schema_path.read_text())["port"] == DEFAULT_BRIDGE_PORT


class TestBridgeSources:
    def test_runtime_source_mentions_required_operations(self):
        source = bridge_runtime_js()

        for snippet in [
            'command === "find_device_session"',
            'command === "set_box_attrs"',
            'command === "create_box"',
            'command === "connect_boxes"',
            'command === "save_device"',
            'this.patcher.message("front")',
            'this.patcher.message("write")',
            'this.patcher.remove(obj)',
        ]:
            assert snippet in source

    def test_server_source_embeds_transport_contract(self):
        source = bridge_server_js()

        assert '"get_max_bridge_info"' in source
        assert '"selected-device-server"' in source
        assert "127.0.0.1" in source
        assert str(DEFAULT_BRIDGE_PORT) in source

    def test_generated_js_parses_with_node_when_available(self, tmp_path):
        node = shutil.which("node")
        if not node:
            return

        runtime_path = tmp_path / BRIDGE_RUNTIME_FILENAME
        server_path = tmp_path / BRIDGE_SERVER_FILENAME
        runtime_path.write_text(bridge_runtime_js())
        server_path.write_text(bridge_server_js())

        subprocess.run([node, "--check", str(runtime_path)], check=True)
        subprocess.run([node, "--check", str(server_path)], check=True)
