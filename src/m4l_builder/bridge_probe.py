"""LiveMCP bridge-probe scaffolding as shared primitives.

The two EQ devices copy-pasted ~76 lines each to register the bridge probe's
runtime/server/schema assets and add its patcher boxes. This is that,
parameterized. Devices register assets early and add the runtime boxes later,
so it is two calls (matching that structure), gated by the caller's env flag:

    if env_flag(MY_PROBE_ENV):
        register_bridge_probe_assets(device, probe_env=MY_PROBE_ENV, repo_root=REPO_ROOT, ...)
    ...
    if env_flag(MY_PROBE_ENV):
        add_bridge_probe_runtime(device, runtime_file=..., server_file=..., y=860)

``env_flag`` reads ``os.environ`` at call time (not import time), so a per-reload
env var still toggles the probe variant.
"""
from __future__ import annotations

import os
from pathlib import Path


def env_flag(name: str) -> bool:
    """True if env var ``name`` holds a truthy flag (1/true/yes/on)."""
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def livemcp_asset_dir(repo_root, root_env: str = "LIVEMCP_ROOT") -> Path | None:
    """The ``livemcp/max_bridge`` asset dir — ``root_env`` override or the
    sibling ``../livemcp`` checkout next to ``repo_root`` — or None if absent.
    """
    candidates = []
    override = os.environ.get(root_env, "").strip()
    if override:
        candidates.append(Path(override).expanduser())
    candidates.append(Path(repo_root).parent / "livemcp")
    for candidate in candidates:
        asset_dir = candidate / "max_bridge"
        if asset_dir.is_dir():
            return asset_dir
    return None


def register_bridge_probe_assets(device, *, probe_env: str, repo_root,
                                 runtime_file: str, server_file: str,
                                 schema_file: str, root_env: str = "LIVEMCP_ROOT") -> None:
    """Register the bridge probe's runtime/server/schema support files on
    ``device``. Raises if the livemcp checkout is missing (``probe_env`` names
    the flag for the message).
    """
    asset_dir = livemcp_asset_dir(repo_root, root_env)
    if asset_dir is None:
        raise RuntimeError(
            f"{probe_env}=1 requires a livemcp checkout at ../livemcp or {root_env}.")
    for filename, file_type in ((runtime_file, "TEXT"), (server_file, "TEXT"),
                                (schema_file, "JSON")):
        device.add_support_file(
            filename, (asset_dir / filename).read_text(encoding="utf-8"),
            file_type=file_type)


def add_bridge_probe_runtime(device, *, runtime_file: str, server_file: str,
                             y: int = 860) -> None:
    """Add the hidden bridge-probe runtime boxes (thisdevice -> deferlow -> js
    runtime <-> node.script server) on ``device``. ``y`` is the row's rect Y.
    """
    k = {"hidden": 1}
    device.add_newobj("bridge_thisdevice", "live.thisdevice", numinlets=1, numoutlets=2,
                      outlettype=["bang", ""], patching_rect=[20, y, 90, 20],
                      varname="bridge_thisdevice", **k)
    device.add_newobj("bridge_defer", "deferlow", numinlets=1, numoutlets=1,
                      outlettype=[""], patching_rect=[118, y, 52, 20],
                      varname="bridge_defer", **k)
    device.add_newobj("bridge_runtime", f"js {runtime_file}", numinlets=1, numoutlets=1,
                      outlettype=[""], patching_rect=[178, y, 118, 20],
                      varname="bridge_runtime", **k)
    device.add_newobj("bridge_server", f"node.script {server_file} @autostart 1 @watch 0",
                      numinlets=1, numoutlets=1, outlettype=[""],
                      patching_rect=[304, y, 210, 20], varname="bridge_server", **k)
    device.add_line("bridge_thisdevice", 0, "bridge_defer", 0)
    device.add_line("bridge_defer", 0, "bridge_runtime", 0)
    device.add_line("bridge_server", 0, "bridge_runtime", 0)
    device.add_line("bridge_runtime", 0, "bridge_server", 0)
