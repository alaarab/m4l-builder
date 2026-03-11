"""Resolve the external Max4LivePlugins repo before local plugin fallbacks."""

import sys
from pathlib import Path


def add_plugin_repo_paths() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    external_repo = repo_root.parent / "Max4LivePlugins"

    if (external_repo / "plugins").exists():
        external_str = str(external_repo)
        if external_str not in sys.path:
            sys.path.insert(0, external_str)

    repo_str = str(repo_root)
    if repo_str not in sys.path:
        sys.path.insert(0, repo_str)
