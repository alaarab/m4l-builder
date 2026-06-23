"""Freeze a Max for Live ``.amxd`` so it is self-contained and portable.

An unfrozen device only references its dependencies (``jsui`` ``.js`` scripts,
``gen~`` ``.gendsp`` patchers, images, abstractions) by *filename*; the actual
files live loose on the build machine's Max search path. Copy the lone ``.amxd``
to another computer and every ``jsui`` graphic renders blank and ``gen~`` DSP
fails, because the referenced files are missing.

Freezing embeds the raw bytes of every dependency *inside* the ``.amxd`` exactly
the way Max's "Freeze Device" button does. The patcher JSON is left byte-for-byte
identical (still ``"filename" : "foo.js"``, ``dependency_cache`` unchanged); the
device just gains a binary blob that Max consults first when resolving a
filename. The format was reverse-engineered against, and conformance-tested with,
Ableton's own ``maxdevtools`` reference parser.

Binary layout (all multi-byte values big-endian unless noted)::

    ampf <LE32 ver=4> <devtype 'aaaa'/'iiii'/'mmmm'/...>
    meta <LE32 len=4> <LE32 7>            # 7 == frozen (0 == unfrozen)
    ptch <LE32 len>   <mx@c block>

    mx@c block:
        'mx@c' <BE32 header_size=16> <BE64 footer_offset>
        <data region: device JSON bytes ++ each dependency's raw bytes,
         concatenated contiguously, first byte at offset 16>
        'dlst' <BE32 footer_size> <dire entries...>

    dire entry (size field counts the whole entry incl. its 8-byte header):
        'dire' <BE32 entry_size>
        fields, in order: type, fnam, sz32, of32, vers, flag, mdat
    field (size counts the whole field incl. its 8-byte header):
        <4-char tag> <BE32 field_size> <payload>
            type -> 4-char kind (JSON/TEXT/gDSP/gJIT/PNG/svg/AIFF/...)
            fnam -> ASCII filename, NUL-terminated, padded to a multiple of 4
            sz32 -> BE32 file size in bytes
            of32 -> BE32 offset of the file's bytes within the mx@c block
            vers -> BE32 (0)
            flag -> BE32 (0x11 for the device's own JSON, 0 for dependencies)
            mdat -> BE32 HFS+ modified date (seconds since 1904-01-01)

The first ``dire`` is always the device's own JSON (``of32`` == 16).
"""

from __future__ import annotations

import json
import os
import struct
from pathlib import Path

# meta-section value that marks a device as frozen (unfrozen devices use 0).
_FROZEN_META = 7
# flag value Max writes on the device's own JSON entry; dependencies use 0.
_DEVICE_FLAG = 0x11
# Seconds between the HFS+ epoch (1904-01-01) and the Unix epoch (1970-01-01).
_HFS_EPOCH_OFFSET = 2082844800
# Fixed modification stamp (2020-01-01 UTC) so frozen output is deterministic.
_DEFAULT_MDAT = 1577836800 + _HFS_EPOCH_OFFSET

# Map a dependency's file extension to its frozen-footer ``type`` tag. Note this
# is finer-grained than the ``dependency_cache`` "type" (which only ever says
# JSON/TEXT): a ``.gendsp`` is JSON in the cache but ``gDSP`` in the footer.
_FOOTER_TYPE_BY_EXT = {
    ".js": "TEXT",
    ".json": "JSON",
    ".maxpat": "JSON",
    ".amxd": "JSON",
    ".maxhelp": "JSON",
    ".gendsp": "gDSP",
    ".genjit": "gJIT",
    ".png": "PNG",
    ".svg": "svg",
    ".jpg": "JPG",
    ".jpeg": "JPG",
    ".aif": "AIFF",
    ".aiff": "AIFF",
    ".txt": "TEXT",
}


def footer_type_for(filename: str) -> str:
    """Return the frozen-footer ``type`` tag for a dependency filename."""
    return _FOOTER_TYPE_BY_EXT.get(Path(filename).suffix.lower(), "TEXT")


def _field(tag: str, payload: bytes) -> bytes:
    return tag.encode("ascii") + struct.pack(">I", 8 + len(payload)) + payload


def _int_field(tag: str, value: int) -> bytes:
    return _field(tag, struct.pack(">I", value))


def _name_field(name: str) -> bytes:
    raw = name.encode("ascii")
    # NUL-terminate, then pad to the next multiple of 4 (always >= 1 trailing 0).
    total = (len(raw) // 4 + 1) * 4
    return _field("fnam", raw + b"\x00" * (total - len(raw)))


def _dire_entry(filename: str, ftype: str, size: int, offset: int, flag: int,
                mdat: int) -> bytes:
    fields = (
        _field("type", ftype.encode("ascii"))
        + _name_field(filename)
        + _int_field("sz32", size)
        + _int_field("of32", offset)
        + _int_field("vers", 0)
        + _int_field("flag", flag)
        + _int_field("mdat", mdat)
    )
    return b"dire" + struct.pack(">I", 8 + len(fields)) + fields


def assemble_frozen_amxd(
    device_type_code: bytes,
    device_amxd_name: str,
    device_json: bytes,
    dependencies: list[tuple[str, bytes]],
    *,
    mdat: int = _DEFAULT_MDAT,
) -> bytes:
    """Assemble a frozen ``.amxd`` from raw parts.

    Args:
        device_type_code: 4-byte device type (``b"aaaa"`` / ``b"iiii"`` / ...).
        device_amxd_name: filename for the device's own JSON entry, e.g.
            ``"Pocket Delay.amxd"``.
        device_json: the device patcher JSON bytes (the unfrozen ``ptch``
            payload), embedded verbatim as the first footer entry.
        dependencies: ``(filename, raw_bytes)`` for each embedded file. The
            ``filename`` must match what the patcher references (and its
            ``dependency_cache`` name) so Max resolves it to these bytes.
        mdat: HFS+ modification stamp written on every entry.
    """
    region = bytearray(device_json)
    metas: list[tuple[str, str, int, int, int]] = [
        (device_amxd_name, "JSON", len(device_json), 16, _DEVICE_FLAG)
    ]
    offset = 16 + len(device_json)
    for name, data in dependencies:
        metas.append((name, footer_type_for(name), len(data), offset, 0))
        region += data
        offset += len(data)

    footer_offset = 16 + len(region)
    dires = b"".join(
        _dire_entry(name, ftype, size, off, flag, mdat)
        for name, ftype, size, off, flag in metas
    )
    footer = b"dlst" + struct.pack(">I", 8 + len(dires)) + dires

    mxc = (
        b"mx@c"
        + struct.pack(">I", 16)
        + struct.pack(">Q", footer_offset)
        + bytes(region)
        + footer
    )
    header = (
        b"ampf"
        + struct.pack("<I", 4)
        + device_type_code
        + b"meta"
        + struct.pack("<I", 4)
        + struct.pack("<I", _FROZEN_META)
        + b"ptch"
        + struct.pack("<I", len(mxc))
    )
    return header + mxc


def _asset_bytes(asset) -> bytes:
    content = asset.content
    if isinstance(content, bytes):
        return content
    return content.encode(getattr(asset, "encoding", "utf-8") or "utf-8")


def device_to_frozen_bytes(device, *, validate=None) -> bytes:
    """Build a self-contained (frozen) ``.amxd`` for an authoring ``Device``.

    Embeds every registered asset (``jsui`` scripts, ``gen~`` patchers, support
    files) so the single file is portable to other machines with no sidecars.
    """
    from .amxd import apply_validation_policy, device_to_patcher
    from .constants import DEVICE_TYPE_CODES

    apply_validation_policy(device, validate)
    patcher = device_to_patcher(device)
    device_json = json.dumps(patcher, indent="\t").encode("utf-8") + b"\n\x00"
    deps = [(asset.filename, _asset_bytes(asset)) for asset in device.assets()]
    return assemble_frozen_amxd(
        DEVICE_TYPE_CODES[device.device_type],
        f"{device.name}.amxd",
        device_json,
        deps,
    )


def _read_amxd(path: str) -> tuple[bytes, bytes, bool]:
    """Return ``(device_type_code, ptch_payload, is_frozen)`` for an ``.amxd``."""
    data = Path(path).read_bytes()
    if data[:4] != b"ampf":
        raise ValueError(f"{path}: not an .amxd file (missing 'ampf' magic)")
    device_type_code = data[8:12]
    meta_len = struct.unpack_from("<I", data, 16)[0]
    ptch_off = 20 + meta_len
    if data[ptch_off:ptch_off + 4] != b"ptch":
        raise ValueError(f"{path}: malformed container (no 'ptch' chunk)")
    ptch_len = struct.unpack_from("<I", data, ptch_off + 4)[0]
    payload = data[ptch_off + 8:ptch_off + 8 + ptch_len]
    return device_type_code, payload, payload[:4] == b"mx@c"


def _patcher_dict_from_payload(payload: bytes) -> dict:
    text = payload.split(b"\x00", 1)[0].decode("utf-8", "replace")
    return json.loads(text)


def freeze_amxd_file(
    amxd_path: str,
    *,
    search_dirs: list[str] | None = None,
    output_path: str | None = None,
) -> dict:
    """Freeze an already-built ``.amxd`` in place (or to ``output_path``).

    Reads the device's ``dependency_cache``, loads each listed file from the
    ``.amxd``'s own directory (and any extra ``search_dirs``), embeds them, and
    rewrites the file frozen. Dependencies that cannot be found are skipped and
    reported (these are typically Max factory files present on every install).

    Returns a summary dict: ``{embedded: [...], missing: [...], bytes: int,
    already_frozen: bool}``.
    """
    device_type_code, payload, is_frozen = _read_amxd(amxd_path)
    dest = output_path or amxd_path
    if is_frozen:
        return {"embedded": [], "missing": [], "bytes": 0, "already_frozen": True}

    patcher = _patcher_dict_from_payload(payload)
    dep_names = [
        d.get("name")
        for d in patcher.get("patcher", {}).get("dependency_cache", [])
        if d.get("name")
    ]

    dirs = [os.path.dirname(os.path.abspath(amxd_path))]
    dirs += [os.path.abspath(d) for d in (search_dirs or [])]

    embedded: list[tuple[str, bytes]] = []
    missing: list[str] = []
    for name in dep_names:
        for d in dirs:
            candidate = os.path.join(d, name)
            if os.path.isfile(candidate):
                embedded.append((name, Path(candidate).read_bytes()))
                break
        else:
            missing.append(name)

    frozen = assemble_frozen_amxd(
        device_type_code,
        f"{Path(amxd_path).stem}.amxd",
        payload,
        embedded,
    )
    Path(dest).write_bytes(frozen)
    return {
        "embedded": [n for n, _ in embedded],
        "missing": missing,
        "bytes": len(frozen),
        "already_frozen": False,
    }
