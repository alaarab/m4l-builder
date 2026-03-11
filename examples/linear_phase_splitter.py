"""Compatibility wrapper for the external Linear Phase Crossover plugin build script."""

from _plugin_repo import add_plugin_repo_paths

add_plugin_repo_paths()

from plugins.linear_phase_crossover.build import *  # noqa: F401,F403
