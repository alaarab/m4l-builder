"""Binary .amxd container format (ampf header) encoding.

.amxd files have this binary structure:
    Offset  Content
    0-3     "ampf" magic bytes
    4-7     uint32 LE, value = 4 (format version)
    8-11    Device type code (ASCII): "aaaa"/"iiii"/"mmmm"
    12-15   "meta" section tag
    16-19   uint32 LE metadata length (typically 4)
    20-23   Metadata bytes (typically 0x00000000)
    24-27   "ptch" section tag
    28-31   uint32 LE JSON payload length (includes null terminator)
    32+     JSON patcher data, null-terminated
"""

import json
import struct

from .constants import AUDIO_EFFECT


def build_amxd(patcher_dict: dict, device_type: bytes = AUDIO_EFFECT) -> bytes:
    """Build a complete .amxd binary from a patcher dict.

    Args:
        patcher_dict: The full patcher JSON structure.
        device_type: Binary device type code (AUDIO_EFFECT, INSTRUMENT, or MIDI_EFFECT).

    Returns:
        Complete .amxd file contents as bytes.
    """
    json_bytes = json.dumps(patcher_dict, indent="\t").encode("utf-8") + b"\n\x00"

    header = b"ampf"
    header += struct.pack("<I", 4)          # format version
    header += device_type                    # device type code
    header += b"meta"                        # metadata section tag
    header += struct.pack("<I", 4)           # metadata length
    header += b"\x00\x00\x00\x00"           # metadata (empty)
    header += b"ptch"                        # patch section tag
    header += struct.pack("<I", len(json_bytes))  # JSON payload length

    return header + json_bytes


def write_amxd(patcher_dict: dict, path: str, device_type: bytes = AUDIO_EFFECT) -> int:
    """Build and write .amxd file to disk.

    Args:
        patcher_dict: The full patcher JSON structure.
        path: Output file path.
        device_type: Binary device type code.

    Returns:
        Number of bytes written.
    """
    data = build_amxd(patcher_dict, device_type)
    with open(path, "wb") as f:
        f.write(data)
    return len(data)
