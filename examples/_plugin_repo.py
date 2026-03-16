"""Resolve the canonical the device repo repo for flagship build wrappers."""

import os
import sys
from pathlib import Path


def _resolve_plugin_repo(repo_root: Path) -> Path | None:
    env_root = os.environ.get("M4L_DEVICES_ROOT")
    candidates = []
    if env_root:
        candidates.append(Path(env_root).expanduser())
    candidates.append(repo_root.parent / "the device repo")

    for candidate in candidates:
        if (candidate / "plugins").exists():
            return candidate
    return None


def add_plugin_repo_paths() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    plugin_repo = _resolve_plugin_repo(repo_root)
    if plugin_repo is None:
        raise RuntimeError(
            "Flagship plugin wrappers now live in the device repo. "
            "Set M4L_DEVICES_ROOT or check out ../the device repo."
        )

    plugin_repo_str = str(plugin_repo)
    if plugin_repo_str not in sys.path:
        sys.path.insert(0, plugin_repo_str)

    repo_str = str(repo_root)
    if repo_str not in sys.path:
        sys.path.insert(0, repo_str)
