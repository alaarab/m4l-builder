"""Resolve Ableton User Library paths across platforms."""

import os
import platform
from pathlib import Path
from typing import Optional

_DEVICE_TYPE_SUBDIRS = {
    "audio_effect": "Audio Effects/Max Audio Effect",
    "instrument": "Instruments/Max Instrument",
    "midi_effect": "MIDI Effects/Max MIDI Effect",
}


def user_library() -> Path:
    """Return the Ableton User Library path.

    Checks M4L_USER_LIBRARY env var first, then platform defaults.
    """
    env = os.environ.get("M4L_USER_LIBRARY")
    if env:
        return Path(env)

    system = platform.system()

    if system == "Darwin":
        return Path.home() / "Music" / "Ableton" / "User Library"

    if system == "Windows":
        # Common Windows locations
        for drive in ["D:", "C:"]:
            p = Path(drive) / "Music" / "Ableton" / "User Library"
            if p.is_dir():
                return p
        # Fallback to user's Music folder
        return Path.home() / "Music" / "Ableton" / "User Library"

    # Linux / WSL
    if _is_wsl():
        for drive in ["/mnt/d", "/mnt/c"]:
            p = Path(drive) / "Music" / "Ableton" / "User Library"
            if p.is_dir():
                return p

    return Path.home() / "Music" / "Ableton" / "User Library"


def _validated_subfolder(subfolder: Optional[str]) -> Optional[Path]:
    if not subfolder:
        return None
    path = Path(subfolder)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("subfolder must be a relative path inside the device output directory")
    return path


def device_output_path(
    name: str,
    device_type: str = "audio_effect",
    *,
    subfolder: Optional[str] = None,
) -> str:
    """Return the full output path for a device .amxd file.

    Args:
        name: Device name (without .amxd extension).
        device_type: One of "audio_effect", "instrument", "midi_effect".
        subfolder: Optional relative subfolder beneath the device-type directory.
    """
    subdir = _DEVICE_TYPE_SUBDIRS.get(device_type, _DEVICE_TYPE_SUBDIRS["audio_effect"])
    path = user_library() / "Presets" / subdir
    validated_subfolder = _validated_subfolder(subfolder)
    if validated_subfolder is not None:
        path = path / validated_subfolder
    path = path / f"{name}.amxd"
    os.makedirs(path.parent, exist_ok=True)
    return str(path)


def _is_wsl():
    try:
        with open("/proc/version", "r") as f:
            return "microsoft" in f.read().lower()
    except FileNotFoundError:
        return False
