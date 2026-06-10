"""Resolve Ableton User Library paths across platforms."""

import os
import platform
from pathlib import Path
from typing import Optional

# Output directories relative to the User Library root. Regular devices live
# under Presets/; Live 12 MIDI Tools load from a top-level MIDI Tools folder.
_DEVICE_TYPE_SUBDIRS = {
    "audio_effect": "Presets/Audio Effects/Max Audio Effect",
    "instrument": "Presets/Instruments/Max Instrument",
    "midi_effect": "Presets/MIDI Effects/Max MIDI Effect",
    "note_transformation": "MIDI Tools/Max Transformations",
    "note_generator": "MIDI Tools/Max Generators",
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
        device_type: One of "audio_effect", "instrument", "midi_effect",
            "note_transformation", "note_generator".
        subfolder: Optional relative subfolder beneath the device-type directory.
    """
    try:
        subdir = _DEVICE_TYPE_SUBDIRS[device_type]
    except KeyError:
        valid = ", ".join(sorted(_DEVICE_TYPE_SUBDIRS))
        raise ValueError(f"unknown device_type {device_type!r}; expected one of: {valid}") from None
    path = user_library() / subdir
    validated_subfolder = _validated_subfolder(subfolder)
    if validated_subfolder is not None:
        path = path / validated_subfolder
    path = path / f"{name}.amxd"
    os.makedirs(path.parent, exist_ok=True)
    return str(path)


def _is_wsl():
    try:
        with open("/proc/version") as f:
            return "microsoft" in f.read().lower()
    except FileNotFoundError:
        return False
