"""Reload a rebuilt device into the open Live set through LiveMCP.

LiveMCP's remote script runs inside Live and listens on ``127.0.0.1:9877``.
It speaks JSON lines: one ``{"id", "type", "params"}`` request per line and
one ``{"id", "status", "result" | "error"}`` reply per line.

:func:`reload_device` finds every copy of a device on the set's tracks and
swaps each for the rebuilt ``.amxd`` in the same chain slot, then restores
the old parameter values by name. When the device isn't in the set yet, it
loads it from the User Library onto the selected track.

Stdlib only, like the rest of the package.
"""

from __future__ import annotations

import json
import socket
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .paths import user_library

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 9877

# What a LiveCommandError says when LiveMCP stopped waiting for Live's main
# thread (it replies with an empty error). The command may still complete.
TIMED_OUT = "LiveMCP stopped waiting for Live (the command may still finish)"

# Max devices report one of these Live class names.
_MAX_DEVICE_CLASSES = ("MxDeviceAudioEffect", "MxDeviceInstrument", "MxDeviceMidiEffect")


class LiveUnavailable(ConnectionError):
    """Live isn't running, or LiveMCP's remote script isn't listening."""


class LiveCommandError(RuntimeError):
    """LiveMCP ran a command and reported an error."""


class LiveClient:
    """A small JSON-lines client for LiveMCP's remote script.

    Connects on first use. Any socket failure closes the connection and
    raises :class:`LiveUnavailable`, so the next call reconnects. The default
    timeout is longer than LiveMCP's own 15 s limit on main-thread commands,
    so a slow command comes back as LiveMCP's error rather than a dropped socket.
    """

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT,
                 timeout: float = 30.0) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self._sock: socket.socket | None = None
        self._buffer = b""
        self._next_id = 0

    def __enter__(self) -> LiveClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
        self._sock = None
        self._buffer = b""

    def call(self, command: str, params: dict[str, Any] | None = None) -> Any:
        """Send one command and return its ``result``."""
        self._next_id += 1
        request_id = self._next_id
        payload = json.dumps({"id": request_id, "type": command, "params": params or {}})
        try:
            if self._sock is None:
                self._sock = socket.create_connection((self.host, self.port), self.timeout)
            self._sock.settimeout(self.timeout)
            self._sock.sendall(payload.encode("utf-8") + b"\n")
            line = self._read_line()
        except TimeoutError as exc:
            self.close()
            raise LiveUnavailable(
                f"LiveMCP didn't answer {command} within {self.timeout:g}s") from exc
        except OSError as exc:
            self.close()
            raise LiveUnavailable(
                f"can't reach LiveMCP at {self.host}:{self.port} ({exc}). Is Live open "
                "with LiveMCP selected as a Control Surface?") from exc
        try:
            reply = json.loads(line)
        except ValueError as exc:
            self.close()
            raise LiveUnavailable(f"LiveMCP sent a reply that isn't JSON: {line[:200]!r}") from exc
        if reply.get("id") not in (None, request_id):
            self.close()
            raise LiveUnavailable(
                f"LiveMCP answered request {reply.get('id')} while waiting for {request_id}")
        if reply.get("status") == "error":
            error = reply.get("error") or reply.get("message")
            if isinstance(error, dict):
                error = error.get("message") or json.dumps(error)
            if not error:  # LiveMCP's main-thread wait ran out; Live may still finish
                error = TIMED_OUT
            raise LiveCommandError(f"{command}: {error}")
        return reply.get("result", {})

    def _read_line(self) -> bytes:
        assert self._sock is not None
        while b"\n" not in self._buffer:
            chunk = self._sock.recv(65536)
            if not chunk:
                raise ConnectionError("LiveMCP closed the connection")
            self._buffer += chunk
        line, _, self._buffer = self._buffer.partition(b"\n")
        return line


@dataclass
class ReloadResult:
    """What :func:`reload_device` did."""

    device_name: str
    method: str  # "replace_device", "delete+load", or "load" (wasn't in the set)
    slots: list[tuple[int, int]] = field(default_factory=list)  # (track, device) swapped
    loaded_onto: int | None = None  # track index, when method is "load"
    restored: int = 0  # parameter values written back
    seconds: float = 0.0
    warnings: list[str] = field(default_factory=list)

    def summary(self) -> str:
        if self.method == "load":
            where = f"not in the set yet, loaded onto track {(self.loaded_onto or 0) + 1}"
        else:
            copies = len(self.slots)
            where = f"swapped {copies} cop{'y' if copies == 1 else 'ies'} in place"
            if self.method == "delete+load":
                where += " (LiveMCP without replace_device: loaded beside, old copy deleted)"
            if self.restored:
                where += f", restored {self.restored} parameter values"
        return f"{self.device_name}: {where} in {self.seconds:.2f}s"


def user_library_uri(amxd_path: str | Path, library: Path | None = None) -> str:
    """The LiveMCP browser path for a file inside the User Library.

    LiveMCP walks ``user_library/<folders>/<file>`` folder by folder, which is
    much faster than searching the whole browser.
    """
    library = (library or user_library()).resolve()
    path = Path(amxd_path).resolve()
    try:
        relative = path.relative_to(library)
    except ValueError:
        raise ValueError(
            f"{path} isn't in the User Library ({library}); Live can only load "
            "devices it can see in its browser") from None
    return "user_library/" + relative.as_posix()


def find_device_instances(client: LiveClient, name: str,
                          unreadable: list[int] | None = None) -> list[tuple[int, int]]:
    """``(track_index, device_index)`` of every Max device called ``name``
    on the set's tracks (top level of each track's chain).

    A track LiveMCP can't describe is skipped and its index appended to
    ``unreadable``: older LiveMCP versions fail ``get_track_info`` on group
    tracks because they read the arm state, which group tracks don't have.
    """
    track_count = int(client.call("get_session_info").get("track_count", 0))
    found = []
    for track_index in range(track_count):
        try:
            info = client.call("get_track_info", {"track_index": track_index})
        except LiveCommandError:
            if unreadable is not None:
                unreadable.append(track_index)
            continue
        for device in info.get("devices", []):
            if device.get("name") == name and device.get("class_name") in _MAX_DEVICE_CLASSES:
                found.append((track_index, int(device["index"])))
    return found


def _device_params(client: LiveClient, track_index: int,
                   device_index: int) -> tuple[str | None, list[dict]]:
    """The device's name and parameters in one call."""
    result = client.call("get_device_parameters",
                         {"track_index": track_index, "device_index": device_index})
    return result.get("device_name"), list(result.get("parameters", []))


def _parameters(client: LiveClient, track_index: int, device_index: int) -> list[dict]:
    return _device_params(client, track_index, device_index)[1]


@dataclass
class SlotCache:
    """Where each device was last found, for a watch that reloads repeatedly.

    Each LiveMCP call costs a few tenths of a second inside Live, so scanning
    every track on every save is the slow part of a reload on a big set. With
    a cache, a reload first reads every track's device count in one call; if
    nothing changed since the last scan and each remembered slot still holds
    the device, the scan is skipped. Anything else rescans.
    """

    layout: list[int] | None = None
    slots: dict[str, list[tuple[int, int]]] = field(default_factory=dict)
    warnings: dict[str, list[str]] = field(default_factory=dict)


def _layout(client: LiveClient) -> list[int] | None:
    """Device count per track, or None when LiveMCP can't list every track
    (older versions fail on group tracks)."""
    try:
        tracks = client.call("get_all_tracks_info").get("tracks", [])
    except LiveCommandError:
        return None
    return [int(t.get("device_count", 0)) for t in tracks]


def _swap(client: LiveClient, track_index: int, device_index: int, uri: str,
          use_replace: bool) -> bool:
    """Put the item at ``uri`` in this slot. Returns whether ``replace_device``
    was used (False once the installed LiveMCP turns out not to have it)."""
    slot = {"track_index": track_index, "device_index": device_index}
    if use_replace:
        try:
            client.call("replace_device", {**slot, "uri": uri})
            return True
        except LiveCommandError as exc:
            if "Unknown command" not in str(exc):
                raise
    # Older LiveMCP: load the new copy, delete the old one, then move the new
    # one into the old slot. Live puts a loaded device after the selected one
    # or at the end of the chain, so find where it actually landed.
    before = [d.get("name") for d in _chain(client, track_index)]
    client.call("select_device", slot)
    _load(client, track_index, uri, len(before))
    after = [d.get("name") for d in _chain(client, track_index)]
    landed = _inserted_at(before, after)
    if landed <= device_index:
        raise LiveCommandError(
            f"the new copy loaded at {landed + 1}, ahead of the old one; left both in place")
    client.call("delete_device", slot)
    if landed - 1 != device_index:
        client.call("move_device", {"track_index": track_index, "device_index": landed - 1,
                                    "new_index": device_index})
    return False


def _inserted_at(before: list, after: list) -> int:
    """Index of the one item ``after`` has that ``before`` doesn't."""
    for i, name in enumerate(before):
        if after[i] != name:
            return i
    return len(before)


def _chain(client: LiveClient, track_index: int) -> list[dict]:
    return list(client.call("get_track_info", {"track_index": track_index}).get("devices", []))


def _load(client: LiveClient, track_index: int, uri: str, count_before: int,
          timeout: float = 120.0, clock: Callable[[], float] = time.monotonic,
          sleep: Callable[[float], None] = time.sleep) -> None:
    """``load_browser_item``, waiting out LiveMCP's 15 s limit if Live is slow.

    Older LiveMCP searches the whole browser by URI before it tries the
    folder path, which can take longer than LiveMCP waits for Live. The load
    still lands, so on that error watch the track until the device shows up.
    """
    try:
        client.call("load_browser_item", {"track_index": track_index, "uri": uri})
        return
    except LiveCommandError as exc:
        if TIMED_OUT not in str(exc):
            raise
    deadline = clock() + timeout
    while len(_chain(client, track_index)) <= count_before:
        if clock() >= deadline:
            raise LiveCommandError(
                f"load_browser_item: {uri} hadn't appeared after {timeout:g}s")
        sleep(0.25)


def _wait_for_parameters(client: LiveClient, track_index: int, device_index: int,
                         want: set[str], timeout: float,
                         clock: Callable[[], float], sleep: Callable[[float], None]) -> list[dict]:
    """A Max device's parameters appear once its patcher loads, a moment
    after Live adds the device. Poll until every name we want shows up, or
    until the patcher has clearly loaded (more than "Device On") and the list
    has stopped changing, which is what a build that dropped a dial looks like."""
    deadline = clock() + timeout
    previous: set[str] | None = None
    while True:
        params = _parameters(client, track_index, device_index)
        names = {str(p.get("name")) for p in params}
        if want <= names or clock() >= deadline:
            return params
        if names == previous and names - {"Device On"}:
            return params
        previous = names
        sleep(0.05)


def _restore(client: LiveClient, track_index: int, device_index: int,
             before: list[dict], after: list[dict]) -> int:
    """Write the old values back by parameter name, clamped to the new range.
    A renamed or removed parameter is left at its new default."""
    current = {p["name"]: p for p in after}
    restored = 0
    for old in before:
        new = current.get(old.get("name"))
        if new is None:
            continue
        value = min(max(float(old["value"]), float(new["min"])), float(new["max"]))
        if value == float(new["value"]):
            continue
        client.call("set_device_parameter", {
            "track_index": track_index, "device_index": device_index,
            "parameter_name": new["name"], "value": value,
        })
        restored += 1
    return restored


def reload_device(client: LiveClient, amxd_path: str | Path, *,
                  library: Path | None = None, keep_parameters: bool = True,
                  settle_timeout: float = 5.0, cache: SlotCache | None = None,
                  clock: Callable[[], float] = time.monotonic,
                  sleep: Callable[[float], None] = time.sleep) -> ReloadResult:
    """Swap every copy of the device built at ``amxd_path`` for the new build.

    Matches devices by name (the file name without ``.amxd``), so a copy the
    user renamed in Live is left alone. Raises :class:`LiveUnavailable` when
    LiveMCP can't be reached and :class:`LiveCommandError` when Live refuses.
    Pass the same ``cache`` to repeated calls to skip rescanning the set.
    """
    start = clock()
    path = Path(amxd_path)
    name = path.stem
    uri = user_library_uri(path, library)

    layout = _layout(client) if cache is not None else None
    slots: list[tuple[int, int]] | None = None
    befores: dict[tuple[int, int], list[dict]] = {}
    warnings: list[str] = []
    if cache is not None and layout is not None and layout == cache.layout \
            and cache.slots.get(name):
        slots = list(cache.slots[name])
        warnings = list(cache.warnings.get(name, []))
        for slot in slots:  # each remembered slot must still hold the device
            try:
                device_name, params = _device_params(client, *slot)
            except LiveCommandError:
                device_name, params = None, []
            if device_name != name:
                slots, befores, warnings = None, {}, []
                break
            befores[slot] = params
    if slots is None:
        unreadable: list[int] = []
        slots = find_device_instances(client, name, unreadable)
        if unreadable:
            warnings.append(
                f"couldn't list devices on {len(unreadable)} track(s) (group tracks need "
                "a newer LiveMCP), so copies there weren't reloaded")
        if cache is not None and slots:
            cache.layout = layout
            cache.slots[name] = list(slots)
            cache.warnings[name] = list(warnings)

    if not slots:
        track = client.call("get_selected_track")
        track_index = track.get("index", track.get("track_index"))
        if track_index is None:
            raise LiveCommandError(
                f"{name} isn't in the set and no track is selected to load it onto")
        track_index = int(track_index)
        _load(client, track_index, uri, len(_chain(client, track_index)))
        return ReloadResult(name, "load", [], loaded_onto=track_index,
                            seconds=clock() - start, warnings=warnings)

    result = ReloadResult(name, "replace_device", slots, warnings=warnings)
    use_replace = True
    for track_index, device_index in slots:
        if not keep_parameters:
            before = []
        elif (track_index, device_index) in befores:
            before = befores[(track_index, device_index)]
        else:
            before = _parameters(client, track_index, device_index)
        use_replace = _swap(client, track_index, device_index, uri, use_replace)
        if not use_replace:
            result.method = "delete+load"
        try:
            now_there = _device_params(client, track_index, device_index)[0]
        except LiveCommandError:
            now_there = None
        if now_there != name:
            result.warnings.append(
                f"track {track_index + 1}: slot {device_index + 1} holds "
                f"{now_there or 'nothing'} after the swap; values not restored")
            if cache is not None:
                cache.slots.pop(name, None)
            continue
        if before:
            want = {p["name"] for p in before}
            after = _wait_for_parameters(client, track_index, device_index, want,
                                         settle_timeout, clock, sleep)
            missing = want - {p.get("name") for p in after}
            if missing:
                result.warnings.append(
                    f"track {track_index + 1}: not restored (gone or not loaded yet): "
                    + ", ".join(sorted(missing)))
            result.restored += _restore(client, track_index, device_index, before, after)
    result.seconds = clock() - start
    return result
