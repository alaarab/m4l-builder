"""Compatibility wrapper for the external Ducking Delay plugin build script."""

from _plugin_repo import add_plugin_repo_paths

add_plugin_repo_paths()

from plugins.ducking_delay.build import *  # noqa: F401,F403
