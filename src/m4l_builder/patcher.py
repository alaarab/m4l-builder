"""Low-level patcher/JSON generation for M4L devices."""

from .profiles import DEFAULT_PATCHER_PROFILE


def build_patcher(boxes: list, lines: list, *,
                  name: str = "m4l_device",
                  width: float = 400.0,
                  height: float = 170.0,
                  device_type: str = "audio_effect",
                  profile=None) -> dict:
    """Build the complete M4L patcher dict ready for JSON serialization."""
    effective_profile = profile or DEFAULT_PATCHER_PROFILE
    return effective_profile.build_device_patcher(
        boxes,
        lines,
        width=width,
        height=height,
        device_type=device_type,
    )
