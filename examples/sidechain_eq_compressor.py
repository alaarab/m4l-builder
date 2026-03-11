"""Compatibility wrapper for the external Sidechain EQ Compressor plugin build script."""

from _plugin_repo import add_plugin_repo_paths

add_plugin_repo_paths()

from plugins.sidechain_eq_compressor.build import *  # noqa: F401,F403
