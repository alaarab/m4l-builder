"""live_reload: swapping a rebuilt device into the open Live set.

Live isn't available in CI, so ``FakeLive`` stands in for LiveMCP's remote
script: it keeps tracks of devices, answers the same commands, and (like a
real Max device) only shows a new device's parameters after a few polls.
"""

from __future__ import annotations

import json
import socket
import threading
from pathlib import Path

import pytest

from m4l_builder.live_reload import (
    LiveClient,
    LiveCommandError,
    LiveUnavailable,
    find_device_instances,
    reload_device,
    user_library_uri,
)


def _params(**values):
    params = [{"name": "Device On", "value": 1.0, "min": 0.0, "max": 1.0}]
    for name, (value, lo, hi) in values.items():
        params.append({"name": name, "value": value, "min": lo, "max": hi})
    return params


class FakeLive:
    """In-memory LiveMCP. ``build`` is what the rebuilt file loads as."""

    def __init__(self, tracks, build, *, has_replace=True, polls_until_loaded=2):
        self.tracks = tracks  # list of lists of device dicts
        self.build = build  # {"name":..., "params": [...]} for the new file
        self.has_replace = has_replace
        self.polls_until_loaded = polls_until_loaded
        self.selected = (0, None)
        self.calls = []

    def _new_device(self):
        return {"name": self.build["name"], "class_name": "MxDeviceAudioEffect",
                "params": [dict(p) for p in self.build["params"]],
                "polls_left": self.polls_until_loaded}

    def call(self, command, params=None):
        params = params or {}
        self.calls.append((command, params))
        t, d = params.get("track_index"), params.get("device_index")
        if command == "get_session_info":
            return {"track_count": len(self.tracks)}
        if command == "get_track_info":
            return {"devices": [{"index": i, "name": dev["name"], "class_name": dev["class_name"]}
                                for i, dev in enumerate(self.tracks[t])]}
        if command == "get_device_parameters":
            dev = self.tracks[t][d]
            if dev.get("polls_left", 0) > 0:  # patcher still loading
                dev["polls_left"] -= 1
                return {"parameters": dev["params"][:1]}
            return {"parameters": [dict(p, index=i) for i, p in enumerate(dev["params"])]}
        if command == "replace_device":
            if not self.has_replace:
                raise LiveCommandError("replace_device: Unknown command: replace_device")
            self.tracks[t][d] = self._new_device()
            return {"in_place": True}
        if command == "select_device":
            self.selected = (t, d)
            return {}
        if command == "load_browser_item":
            chain = self.tracks[t]
            sel_t, sel_d = self.selected
            at = sel_d + 1 if sel_t == t and sel_d is not None else len(chain)
            chain.insert(at, self._new_device())
            return {"loaded": True}
        if command == "delete_device":
            del self.tracks[t][d]
            return {}
        if command == "set_device_parameter":
            for p in self.tracks[t][d]["params"]:
                if p["name"] == params["parameter_name"]:
                    p["value"] = params["value"]
                    return {}
            raise LiveCommandError("Parameter not found")
        if command == "get_selected_track":
            return {"index": self.selected[0]}
        raise LiveCommandError(f"{command}: Unknown command: {command}")

    def names(self, track):
        return [dev["name"] for dev in self.tracks[track]]


def _device(name, params, cls="MxDeviceAudioEffect"):
    return {"name": name, "class_name": cls, "params": params}


@pytest.fixture
def library(tmp_path):
    folder = tmp_path / "User Library" / "Presets" / "Audio Effects" / "Max Audio Effect"
    folder.mkdir(parents=True)
    amxd = folder / "My Gain.amxd"
    amxd.write_bytes(b"ampf")
    return tmp_path / "User Library", amxd


def _no_sleep(_seconds):
    pass


def test_swaps_in_place_and_restores_values_by_name(library):
    root, amxd = library
    live = FakeLive(
        [[_device("EQ", _params()), _device("My Gain", _params(Gain=(-12.0, -70.0, 6.0))),
          _device("Utility", _params())]],
        build={"name": "My Gain", "params": _params(Gain=(0.0, -70.0, 12.0), Tone=(0.5, 0, 1))},
    )
    result = reload_device(live, amxd, library=root, sleep=_no_sleep)
    assert live.names(0) == ["EQ", "My Gain", "Utility"]
    assert result.method == "replace_device"
    assert result.slots == [(0, 1)]
    gain = next(p for p in live.tracks[0][1]["params"] if p["name"] == "Gain")
    assert gain["value"] == -12.0
    assert result.restored == 1
    replace = [c for c in live.calls if c[0] == "replace_device"]
    assert replace[0][1]["uri"] == (
        "user_library/Presets/Audio Effects/Max Audio Effect/My Gain.amxd")


def test_old_livemcp_falls_back_to_load_beside_then_delete(library):
    root, amxd = library
    live = FakeLive(
        [[_device("EQ", _params()), _device("My Gain", _params(Gain=(-6.0, -70.0, 6.0))),
          _device("Utility", _params())]],
        build={"name": "My Gain", "params": _params(Gain=(0.0, -70.0, 6.0))},
        has_replace=False,
    )
    result = reload_device(live, amxd, library=root, sleep=_no_sleep)
    assert live.names(0) == ["EQ", "My Gain", "Utility"]
    assert result.method == "delete+load"
    assert live.tracks[0][1]["params"][1]["value"] == -6.0


def test_every_copy_is_swapped_and_renamed_copies_are_left_alone(library):
    root, amxd = library
    live = FakeLive(
        [[_device("My Gain", _params())],
         [_device("My Gain (vocals)", _params()), _device("My Gain", _params())],
         [_device("My Gain", _params(), cls="PluginDevice")]],
        build={"name": "My Gain", "params": _params()},
    )
    result = reload_device(live, amxd, library=root, sleep=_no_sleep)
    assert result.slots == [(0, 0), (1, 1)]
    assert "polls_left" not in live.tracks[1][0]  # renamed copy untouched
    assert "polls_left" not in live.tracks[2][0]  # not a Max device


def test_values_are_clamped_to_the_new_range_and_missing_names_warned(library):
    root, amxd = library
    live = FakeLive(
        [[_device("My Gain", _params(Gain=(6.0, -70.0, 6.0), Drive=(0.8, 0.0, 1.0)))]],
        build={"name": "My Gain", "params": _params(Gain=(0.0, -24.0, 3.0))},
    )
    result = reload_device(live, amxd, library=root, sleep=_no_sleep)
    gain = next(p for p in live.tracks[0][0]["params"] if p["name"] == "Gain")
    assert gain["value"] == 3.0
    assert any("Drive" in w for w in result.warnings)


def test_keep_parameters_false_skips_the_snapshot(library):
    root, amxd = library
    live = FakeLive([[_device("My Gain", _params(Gain=(-6.0, -70.0, 6.0)))]],
                    build={"name": "My Gain", "params": _params(Gain=(0.0, -70.0, 6.0))})
    result = reload_device(live, amxd, library=root, keep_parameters=False, sleep=_no_sleep)
    assert result.restored == 0
    assert not [c for c in live.calls if c[0] == "get_device_parameters"]


def test_device_not_in_the_set_is_loaded_onto_the_selected_track(library):
    root, amxd = library
    live = FakeLive([[_device("EQ", _params())], []],
                    build={"name": "My Gain", "params": _params()})
    live.selected = (1, None)
    result = reload_device(live, amxd, library=root, sleep=_no_sleep)
    assert result.method == "load"
    assert result.loaded_onto == 1
    assert live.names(1) == ["My Gain"]
    assert "loaded onto track 2" in result.summary()


def test_slow_patcher_stops_waiting_at_the_timeout(library):
    root, amxd = library
    live = FakeLive([[_device("My Gain", _params(Gain=(-6.0, -70.0, 6.0)))]],
                    build={"name": "My Gain", "params": _params(Gain=(0.0, -70.0, 6.0))},
                    polls_until_loaded=10_000)
    now = [0.0]

    def tick(seconds):
        now[0] += seconds

    result = reload_device(live, amxd, library=root, settle_timeout=1.0,
                           clock=lambda: now[0], sleep=tick)
    assert result.restored == 0
    assert any("Gain" in w for w in result.warnings)


def test_other_command_errors_are_not_mistaken_for_an_old_livemcp(library):
    root, amxd = library

    class Refusing(FakeLive):
        def call(self, command, params=None):
            if command == "replace_device":
                raise LiveCommandError("replace_device: Browser item not found")
            return super().call(command, params)

    live = Refusing([[_device("My Gain", _params())]],
                    build={"name": "My Gain", "params": _params()})
    with pytest.raises(LiveCommandError, match="Browser item not found"):
        reload_device(live, amxd, library=root, sleep=_no_sleep)
    assert live.names(0) == ["My Gain"]


def test_user_library_uri_rejects_files_outside_the_library(tmp_path):
    with pytest.raises(ValueError, match="isn't in the User Library"):
        user_library_uri(tmp_path / "build" / "My Gain.amxd", tmp_path / "User Library")


def test_find_device_instances_only_matches_max_devices():
    live = FakeLive([[_device("Gain", _params()), _device("Gain", _params(), cls="StereoGain")]],
                    build={"name": "Gain", "params": _params()})
    assert find_device_instances(live, "Gain") == [(0, 0)]


# --- LiveClient over a real socket ------------------------------------------


class _OneShotServer:
    """Answers each JSON line with ``respond(request)``, on a free local port."""

    def __init__(self, respond):
        self.respond = respond
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(1)
        self.port = self.sock.getsockname()[1]
        self.requests = []
        threading.Thread(target=self._serve, daemon=True).start()

    def _serve(self):
        conn, _ = self.sock.accept()
        with conn:
            buf = b""
            while True:
                data = conn.recv(4096)
                if not data:
                    return
                buf += data
                while b"\n" in buf:
                    line, _, buf = buf.partition(b"\n")
                    request = json.loads(line)
                    self.requests.append(request)
                    reply = self.respond(request)
                    # Split the reply across two sends to exercise buffering.
                    raw = json.dumps(reply).encode() + b"\n"
                    conn.sendall(raw[:5])
                    conn.sendall(raw[5:])


def test_client_round_trip_and_error_reply():
    def respond(request):
        if request["type"] == "boom":
            return {"id": request["id"], "status": "error",
                    "error": {"code": "x", "message": "Unknown command: boom"}}
        return {"id": request["id"], "status": "success", "result": {"echo": request["params"]}}

    server = _OneShotServer(respond)
    with LiveClient(port=server.port, timeout=2.0) as client:
        assert client.call("ping", {"a": 1}) == {"echo": {"a": 1}}
        with pytest.raises(LiveCommandError, match="Unknown command: boom"):
            client.call("boom")
        assert client.call("ping") == {"echo": {}}
    assert [r["id"] for r in server.requests] == [1, 2, 3]


def test_client_reports_live_unavailable_when_nothing_listens():
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()  # nothing listens on this port now
    client = LiveClient(port=port, timeout=0.5)
    with pytest.raises(LiveUnavailable, match="Is Live open"):
        client.call("get_session_info")
    with pytest.raises(LiveUnavailable):  # and it keeps failing cleanly
        client.call("get_session_info")


def test_reload_rejects_a_build_outside_the_user_library(tmp_path):
    live = FakeLive([[]], build={"name": "x", "params": _params()})
    with pytest.raises(ValueError):
        reload_device(live, Path(tmp_path) / "x.amxd", library=tmp_path / "UL")
