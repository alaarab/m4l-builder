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

# Max devices report one of these Live class names.
_MAX_DEVICE_CLASSES = ("MxDeviceAudioEffect", "MxDeviceInstrument", "MxDeviceMidiEffect")


class LiveUnavailable(ConnectionError):
    """Live isn't running, or LiveMCP's remote script isn't listening."""


class LiveCommandError(RuntimeError):
    """LiveMCP ran a command and reported an error."""


class LiveClient:
    """A small JSON-lines client for LiveMCP's remote script.

    Connects on first use. Any socket failure closes the connection and
    raises :class:`LiveUnavailable`, so the next call reconnects.
    """

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT,
                 timeout: float = 15.0) -> None:
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


def find_device_instances(client: LiveClient, name: str) -> list[tuple[int, int]]:
    """``(track_index, device_index)`` of every Max device called ``name``
    on the set's tracks (top level of each track's chain)."""
    track_count = int(client.call("get_session_info").get("track_count", 0))
    found = []
    for track_index in range(track_count):
        info = client.call("get_track_info", {"track_index": track_index})
        for device in info.get("devices", []):
            if device.get("name") == name and device.get("class_name") in _MAX_DEVICE_CLASSES:
                found.append((track_index, int(device["index"])))
    return found


def _parameters(client: LiveClient, track_index: int, device_index: int) -> list[dict]:
    result = client.call("get_device_parameters",
                         {"track_index": track_index, "device_index": device_index})
    return list(result.get("parameters", []))


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
    # Older LiveMCP: select the old device so the new one loads right after
    # it, then delete the old one. The new device ends up in the same slot.
    client.call("select_device", slot)
    client.call("load_browser_item", {"track_index": track_index, "uri": uri})
    client.call("delete_device", slot)
    return False


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
                  settle_timeout: float = 5.0,
                  clock: Callable[[], float] = time.monotonic,
                  sleep: Callable[[float], None] = time.sleep) -> ReloadResult:
    """Swap every copy of the device built at ``amxd_path`` for the new build.

    Matches devices by name (the file name without ``.amxd``), so a copy the
    user renamed in Live is left alone. Raises :class:`LiveUnavailable` when
    LiveMCP can't be reached and :class:`LiveCommandError` when Live refuses.
    """
    start = clock()
    path = Path(amxd_path)
    name = path.stem
    uri = user_library_uri(path, library)
    slots = find_device_instances(client, name)

    if not slots:
        track = client.call("get_selected_track")
        track_index = track.get("index", track.get("track_index"))
        if track_index is None:
            raise LiveCommandError(
                f"{name} isn't in the set and no track is selected to load it onto")
        client.call("load_browser_item", {"track_index": int(track_index), "uri": uri})
        return ReloadResult(name, "load", [], loaded_onto=int(track_index),
                            seconds=clock() - start)

    result = ReloadResult(name, "replace_device", slots)
    use_replace = True
    for track_index, device_index in slots:
        before = _parameters(client, track_index, device_index) if keep_parameters else []
        use_replace = _swap(client, track_index, device_index, uri, use_replace)
        if not use_replace:
            result.method = "delete+load"
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
