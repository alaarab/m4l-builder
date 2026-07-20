"""Shared LiveMCP bridge-probe primitives (m4l_builder.bridge_probe) — was
copy-pasted across the EQ devices; now one parameterized primitive."""

import pytest

from m4l_builder import (
    AudioEffect,
    add_bridge_probe_runtime,
    env_flag,
    livemcp_asset_dir,
    register_bridge_probe_assets,
)


def _lines(d):
    return [(l["patchline"]["source"][0], l["patchline"]["source"][1],
             l["patchline"]["destination"][0], l["patchline"]["destination"][1])
            for l in d.lines]


def test_env_flag_reads_environ_at_call_time(monkeypatch):
    monkeypatch.delenv("PROBE_X", raising=False)
    assert env_flag("PROBE_X") is False
    monkeypatch.setenv("PROBE_X", "1")
    assert env_flag("PROBE_X") is True          # per-reload toggling works
    monkeypatch.setenv("PROBE_X", "yes")
    assert env_flag("PROBE_X") is True
    monkeypatch.setenv("PROBE_X", "0")
    assert env_flag("PROBE_X") is False


def test_livemcp_asset_dir_none_when_absent(tmp_path, monkeypatch):
    monkeypatch.delenv("LIVEMCP_ROOT", raising=False)
    assert livemcp_asset_dir(tmp_path / "repo") is None


def test_register_raises_without_livemcp(tmp_path, monkeypatch):
    monkeypatch.delenv("LIVEMCP_ROOT", raising=False)
    d = AudioEffect("t", width=300, height=168)
    with pytest.raises(RuntimeError, match="MY_PROBE=1 requires a livemcp"):
        register_bridge_probe_assets(
            d, probe_env="MY_PROBE", repo_root=tmp_path / "repo",
            runtime_file="r.js", server_file="s.js", schema_file="sc.json")


def test_runtime_boxes_and_wiring():
    d = AudioEffect("t", width=300, height=168)
    add_bridge_probe_runtime(d, runtime_file="device_bridge.js",
                             server_file="device_server.js", y=846)
    boxes = {b["box"]["id"]: b["box"] for b in d.boxes}
    assert boxes["bridge_runtime"]["text"] == "js device_bridge.js"
    assert boxes["bridge_server"]["text"] == "node.script device_server.js @autostart 1 @watch 0"
    assert boxes["bridge_thisdevice"]["patching_rect"][1] == 846      # y parameterized
    assert all(boxes[b]["hidden"] == 1 for b in ("bridge_thisdevice", "bridge_runtime"))
    L = _lines(d)
    assert ("bridge_thisdevice", 0, "bridge_defer", 0) in L
    assert ("bridge_defer", 0, "bridge_runtime", 0) in L
    assert ("bridge_server", 0, "bridge_runtime", 0) in L
    assert ("bridge_runtime", 0, "bridge_server", 0) in L
