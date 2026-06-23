"""Tests for freezing .amxd devices into self-contained, portable files.

The frozen-footer layout these tests assert is the one produced by Max's
"Freeze Device" and parsed by Ableton's ``maxdevtools`` reference code. The
minimal parser below mirrors that reference (``freezing_utils.parse_footer`` /
``frozen_device_printer``) so the suite is self-contained.
"""

import struct

from m4l_builder.constants import AUDIO_EFFECT
from m4l_builder.freeze import (
    assemble_frozen_amxd,
    footer_type_for,
    freeze_amxd_file,
)

# Minimal jsui source that satisfies the framework's ES5 jsui contract.
VALID_JSUI = (
    "mgraphics.init();\n"
    "mgraphics.relative_coords = 0;\n"
    "mgraphics.autofill = 0;\n"
    "function paint() {\n"
    "\tvar w = box.rect[2] - box.rect[0];\n"
    "\tmgraphics.rectangle(0, 0, w, 10);\n"
    "\tmgraphics.fill();\n"
    "}\n"
    "function bang() { mgraphics.redraw(); }\n"
)


# --- Minimal reference parser (mirrors Ableton/maxdevtools) ------------------

def _parse_frozen(data: bytes):
    """Parse a frozen .amxd into ``(meta_value, {filename: (type, bytes)})``."""
    assert data[:4] == b"ampf"
    device_type = data[8:12]
    assert data[12:16] == b"meta"
    meta_value = struct.unpack_from("<I", data, 20)[0]
    ptch_off = 20 + struct.unpack_from("<I", data, 16)[0]
    assert data[ptch_off:ptch_off + 4] == b"ptch"
    ptch_len = struct.unpack_from("<I", data, ptch_off + 4)[0]
    mxc = data[ptch_off + 8:ptch_off + 8 + ptch_len]

    assert mxc[:4] == b"mx@c"
    assert struct.unpack_from(">I", mxc, 4)[0] == 16
    footer_off = struct.unpack_from(">Q", mxc, 8)[0]
    footer = mxc[footer_off:]
    assert footer[:4] == b"dlst"
    assert struct.unpack_from(">I", footer, 4)[0] == len(footer)

    files = {}
    d = footer[8:]
    order = []
    while d[:4] == b"dire":
        size = struct.unpack_from(">I", d, 4)[0]
        fields = {}
        f = d[8:size]
        while len(f) >= 8:
            tag = f[:4].decode("ascii")
            fsize = struct.unpack_from(">I", f, 4)[0]
            payload = f[8:fsize]
            if tag in ("type", "fnam"):
                fields[tag] = payload.rstrip(b"\x00").decode("ascii")
            else:
                fields[tag] = int.from_bytes(payload, "big")
            f = f[fsize:]
        name = fields["fnam"]
        blob = mxc[fields["of32"]:fields["of32"] + fields["sz32"]]
        files[name] = (fields["type"], blob, fields["flag"])
        order.append(name)
        d = d[size:]
    return device_type, meta_value, files, order


# --- assemble_frozen_amxd ----------------------------------------------------

class TestAssembleFrozenAmxd:
    def test_meta_marks_frozen(self):
        data = assemble_frozen_amxd(AUDIO_EFFECT, "X.amxd", b"{}\x00", [])
        _, meta_value, _, _ = _parse_frozen(data)
        assert meta_value == 7  # 0 == unfrozen, 7 == frozen

    def test_device_type_preserved(self):
        data = assemble_frozen_amxd(AUDIO_EFFECT, "X.amxd", b"{}\x00", [])
        device_type, _, _, _ = _parse_frozen(data)
        assert device_type == b"aaaa"

    def test_first_entry_is_device(self):
        dev = b'{"patcher":{}}\n\x00'
        data = assemble_frozen_amxd(AUDIO_EFFECT, "My Device.amxd", dev,
                                    [("a.js", b"// a")])
        _, _, files, order = _parse_frozen(data)
        assert order[0] == "My Device.amxd"
        assert files["My Device.amxd"][0] == "JSON"
        assert files["My Device.amxd"][1] == dev
        assert files["My Device.amxd"][2] == 0x11  # device flag

    def test_dependencies_roundtrip_exact_bytes(self):
        js = b"// timeline\nfunction paint(){ mgraphics.init(); }\n"
        gen = b'{ "patcher": { "classnamespace": "dsp.gen" } }'
        data = assemble_frozen_amxd(
            AUDIO_EFFECT, "D.amxd", b"{}\x00",
            [("ui.js", js), ("core.gendsp", gen)],
        )
        _, _, files, _ = _parse_frozen(data)
        assert files["ui.js"][1] == js
        assert files["core.gendsp"][1] == gen

    def test_footer_types_by_extension(self):
        data = assemble_frozen_amxd(
            AUDIO_EFFECT, "D.amxd", b"{}\x00",
            [("ui.js", b"x"), ("core.gendsp", b"y"), ("jit.genjit", b"z")],
        )
        _, _, files, _ = _parse_frozen(data)
        assert files["ui.js"][0] == "TEXT"
        assert files["core.gendsp"][0] == "gDSP"
        assert files["jit.genjit"][0] == "gJIT"

    def test_files_contiguous_offsets(self):
        # Offsets must be contiguous starting at 16 (no padding between files).
        dev = b"DEVICEJSON\x00"
        a, b = b"aaaaa", b"bbb"
        data = assemble_frozen_amxd(AUDIO_EFFECT, "D.amxd", dev,
                                    [("a.js", a), ("b.js", b)])
        _, _, _, order = _parse_frozen(data)
        # Re-extract raw to confirm packing
        ptch_off = 20 + 4
        ptch_len = struct.unpack_from("<I", data, ptch_off + 4)[0]
        mxc = data[ptch_off + 8:ptch_off + 8 + ptch_len]
        region = mxc[16:16 + len(dev) + len(a) + len(b)]
        assert region == dev + a + b


def test_footer_type_for_extensions():
    assert footer_type_for("x.js") == "TEXT"
    assert footer_type_for("x.gendsp") == "gDSP"
    assert footer_type_for("x.genjit") == "gJIT"
    assert footer_type_for("x.maxpat") == "JSON"
    assert footer_type_for("x.png") == "PNG"
    assert footer_type_for("x.unknown") == "TEXT"


# --- End-to-end: a real AudioEffect with a jsui dependency -------------------

class TestFreezeDeviceEndToEnd:
    def _device(self):
        from m4l_builder import AudioEffect

        dev = AudioEffect("Freeze Test", 200, 120)
        dev.add_jsui(
            "hero",
            [10, 10, 180, 80],
            js_code=VALID_JSUI,
            js_filename="freeze_hero_v1.js",
            numinlets=1,
            numoutlets=0,
        )
        return dev

    def test_frozen_embeds_jsui_script(self):
        dev = self._device()
        data = dev.to_bytes(freeze=True)
        _, meta_value, files, _ = _parse_frozen(data)
        assert meta_value == 7
        assert "freeze_hero_v1.js" in files
        assert b"mgraphics.init()" in files["freeze_hero_v1.js"][1]

    def test_frozen_device_json_matches_unfrozen(self):
        # Freeze must NOT mutate the patcher JSON: the device entry equals the
        # unfrozen ptch payload byte-for-byte.
        dev = self._device()
        unfrozen = dev.to_bytes()
        unfrozen_json = unfrozen[32:]
        _, _, files, _ = _parse_frozen(dev.to_bytes(freeze=True))
        assert files["Freeze Test.amxd"][1] == unfrozen_json

    def test_build_freeze_writes_no_sidecars(self, tmp_path):
        dev = self._device()
        out = tmp_path / "Freeze Test.amxd"
        dev.build(str(out), freeze=True)
        # Frozen build must NOT drop a loose .js next to the .amxd.
        assert out.exists()
        assert not (tmp_path / "freeze_hero_v1.js").exists()
        _, _, files, _ = _parse_frozen(out.read_bytes())
        assert "freeze_hero_v1.js" in files


# --- freeze_amxd_file: freeze an already-built device ------------------------

class TestFreezeAmxdFile:
    def test_freezes_unfrozen_file_with_sidecars(self, tmp_path):
        from m4l_builder import AudioEffect

        dev = AudioEffect("Inplace", 200, 120)
        dev.add_jsui("hero", [10, 10, 180, 80],
                     js_code=VALID_JSUI,
                     js_filename="inplace_v1.js", numinlets=1, numoutlets=0)
        out = tmp_path / "Inplace.amxd"
        dev.build(str(out))  # unfrozen: writes amxd + sidecar
        assert (tmp_path / "inplace_v1.js").exists()

        res = freeze_amxd_file(str(out))
        assert res["already_frozen"] is False
        assert "inplace_v1.js" in res["embedded"]
        assert res["missing"] == []

        _, meta_value, files, _ = _parse_frozen(out.read_bytes())
        assert meta_value == 7
        assert b"mgraphics.init()" in files["inplace_v1.js"][1]

    def test_idempotent_on_frozen_file(self, tmp_path):
        from m4l_builder import AudioEffect

        dev = AudioEffect("Once", 200, 120)
        dev.add_jsui("h", [0, 0, 100, 100], js_code=VALID_JSUI,
                     js_filename="once_v1.js", numinlets=1, numoutlets=0)
        out = tmp_path / "Once.amxd"
        dev.build(str(out), freeze=True)
        res = freeze_amxd_file(str(out))
        assert res["already_frozen"] is True

    def test_reports_missing_sidecars(self, tmp_path):
        from m4l_builder import AudioEffect

        dev = AudioEffect("Missing", 200, 120)
        dev.add_jsui("h", [0, 0, 100, 100], js_code=VALID_JSUI,
                     js_filename="missing_v1.js", numinlets=1, numoutlets=0)
        out = tmp_path / "Missing.amxd"
        dev.build(str(out))
        (tmp_path / "missing_v1.js").unlink()  # simulate lost sidecar
        res = freeze_amxd_file(str(out))
        assert res["missing"] == ["missing_v1.js"]


def test_public_api_exports():
    import m4l_builder

    assert hasattr(m4l_builder, "freeze_amxd_file")
    assert hasattr(m4l_builder, "device_to_frozen_bytes")
    assert hasattr(m4l_builder, "assemble_frozen_amxd")
