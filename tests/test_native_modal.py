"""Independent acoustic fixtures and runtime invariants for the Foundry engine."""

import json
import shutil
import subprocess
import zipfile
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path

import pytest

from m4l_builder.build_fingerprint import device_fingerprint, file_fingerprint
from m4l_builder.freeze import extract_frozen_amxd, footer_type_for
from m4l_builder.native.external import NativeInstrument, modal_external


def test_concurrent_native_builds_share_one_complete_bundle(tmp_path, monkeypatch):
    pytest.importorskip("fcntl")
    import m4l_builder.native.external as native
    sdk = tmp_path / "sdk"
    header = sdk / "c74support/max-includes/ext.h"
    header.parent.mkdir(parents=True)
    header.write_text("// SDK fixture")
    monkeypatch.setenv("MAX_SDK_ROOT", str(sdk))
    monkeypatch.setenv("M4L_NATIVE_CACHE", str(tmp_path / "cache"))
    monkeypatch.setattr(native.sys, "platform", "darwin")
    monkeypatch.setattr(shutil, "which", lambda _: "/fixture/clang++")
    monkeypatch.setattr(subprocess, "check_output", lambda args, **kw:
        native.SDK_REVISION if args[0] == "git" else b"fixture compiler")
    compiles = []

    def run(args, **kwargs):
        if args[0] == "/fixture/clang++":
            destination = Path(args[args.index("-o") + 1])
            compiles.append(destination)
            destination.write_bytes(b"complete native executable")
        return subprocess.CompletedProcess(args, 0)

    monkeypatch.setattr(subprocess, "run", run)
    external = modal_external()
    with ThreadPoolExecutor(max_workers=4) as pool:
        bundles = list(pool.map(lambda _: external.compile(), range(8)))
    assert len(compiles) == 1
    assert len(set(bundles)) == 1
    assert (bundles[0] / "Contents/MacOS" / external.name).read_bytes() == b"complete native executable"
    assert (bundles[0] / "Contents/Info.plist").is_file()


def test_factory_does_not_compile_and_source_changes_address(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("factory invoked compiler")
    monkeypatch.setattr(subprocess, "run", forbidden)
    external = modal_external()
    instrument = NativeInstrument("Native Test", 300, 168)
    assert instrument.add_external(external) == external.name
    assert "modal_core.hpp" in external.manifest
    changed = type(external)(external.stem, external.sources + (("extra.hpp", "// change"),), external.entry)
    assert changed.name != external.name


@pytest.mark.skipif(shutil.which("clang++") is None, reason="native compiler unavailable")
def test_modal_physics_analysis_and_realtime_contract(tmp_path):
    root = Path(__file__).resolve().parents[1]
    binary = tmp_path / "modal_spec"
    subprocess.run(["clang++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
                    "-I", str(root / "src/m4l_builder/native/modal"),
                    str(root / "tests/native/modal_spec.cpp"), "-o", str(binary)],
                   check=True, capture_output=True, text=True)
    result = subprocess.run([str(binary)], check=True, capture_output=True, text=True)
    metrics = json.loads(result.stdout)
    assert metrics["frequency_error_cents"] < 3
    assert metrics["decay_relative_error"] < .08
    assert metrics["coupling_energy_error"] < 3e-15


@pytest.mark.parametrize("frozen", [False, True])
def test_native_bundle_is_complete_and_fingerprints_sources(tmp_path, monkeypatch, frozen):
    external = modal_external()
    bundle = tmp_path / "compile" / (external.name + ".mxo")
    executable = bundle / "Contents/MacOS" / external.name
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b"test executable bytes")
    (bundle / "Contents/Info.plist").write_bytes(b"test plist")
    monkeypatch.setattr(type(external), "compile", lambda self: bundle)
    instrument = NativeInstrument("Native Test", 300, 168)
    instrument.add_external(external)
    target = tmp_path / "output/Native Test.amxd"
    instrument.build(target, freeze=frozen)
    assert file_fingerprint(target) == device_fingerprint(instrument)
    if frozen:
        parts = extract_frozen_amxd(target.read_bytes())
        assert parts[external.name + ".mxo"] == b"\0" * 4
        assert parts[external.name + "/executable"] == executable.read_bytes()
        with zipfile.ZipFile(BytesIO(parts[external.name + "/zipfile"])) as archive:
            assert archive.read(f"{external.name}.mxo/Contents/MacOS/{external.name}") == executable.read_bytes()
        assert footer_type_for(external.name + "/zipfile") == "\0" * 4
        assert footer_type_for(external.name + ".mxo") == "iLaX"
    else:
        installed = target.parent / bundle.name / "Contents/MacOS" / external.name
        assert installed.stat().st_mode & 0o111
        installed.unlink()
        with pytest.raises(FileNotFoundError, match="executable missing"):
            file_fingerprint(target)
