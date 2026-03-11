"""Compatibility wrapper for the external Linear Phase EQ plugin build script."""

from _plugin_repo import add_plugin_repo_paths

add_plugin_repo_paths()

from plugins.linear_phase_eq.build import *  # noqa: F401,F403
