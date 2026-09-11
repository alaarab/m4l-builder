"""Build and bundle native Max instruments without side effects in factories.

The macOS collective layout follows original Max-frozen externals: an iLaX
marker and a ZIP, executable and plist under the external's stem. Compilation
occurs only when serializing/building, never when constructing a device.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import plistlib
import shutil
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

from ..amxd import prepare_device_patcher
from ..artifact_io import write_artifacts
from ..assets import Asset
from ..constants import DEVICE_TYPE_CODES
from ..device import Instrument
from ..freeze import _asset_bytes, assemble_frozen_amxd

SDK_REVISION = "c03a2922a2a8ff149165a1e2ea134e9321d6e202"
BUILD_ABI = "c++17-macos11-universal-msp-v3"


@dataclass(frozen=True)
class NativeExternal:
    """Source-addressed C++ external; source files are carried with the device."""

    stem: str
    sources: tuple[tuple[str, str], ...]
    entry: str

    @property
    def manifest(self) -> str:
        return json.dumps({"abi": BUILD_ABI, "sdk": SDK_REVISION,
                           "builder": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                           "entry": self.entry, "sources": dict(self.sources)},
                          sort_keys=True, separators=(",", ":"))

    @property
    def name(self) -> str:
        digest = hashlib.sha256(self.manifest.encode()).hexdigest()[:12]
        return f"{self.stem}_{digest}~"

    def compile(self) -> Path:
        """Return an ad-hoc signed, universal .mxo in a content-addressed cache."""
        if sys.platform != "darwin":
            raise RuntimeError("This native build currently supports macOS only")
        sdk = Path(os.environ.get("MAX_SDK_ROOT",
                                  "~/.cache/m4l-builder/max-sdk-base")).expanduser()
        includes = sdk / "c74support"
        if not (includes / "max-includes/ext.h").is_file():
            raise RuntimeError("Set MAX_SDK_ROOT to a checkout of Cycling74/max-sdk-base")
        revision = subprocess.check_output(["git", "-C", str(sdk), "rev-parse", "HEAD"], text=True).strip()
        if revision != SDK_REVISION:
            raise RuntimeError(f"Native build requires Max SDK revision {SDK_REVISION}, got {revision}")
        subprocess.run(["git", "-C", str(sdk), "diff", "--exit-code", "HEAD", "--", "c74support"],
                       check=True, capture_output=True)
        compiler = shutil.which("clang++")
        if compiler is None:
            raise RuntimeError("clang++ is required to build the native engine")
        cache = Path(os.environ.get("M4L_NATIVE_CACHE", "~/.cache/m4l-builder/native")).expanduser()
        # Compiler identity and actual SDK headers also invalidate the local cache.
        identity = subprocess.check_output([compiler, "--version"])
        for path in sorted(includes.rglob("*.h")):
            identity += path.read_bytes()
        toolchain = hashlib.sha256(identity).hexdigest()[:12]
        cache = cache / self.name / toolchain
        bundle = cache / f"{self.name}.mxo"
        if (bundle / "Contents/MacOS" / self.name).is_file():
            return bundle
        cache.mkdir(parents=True, exist_ok=True)
        # Independent device builds share this cache. Serialize publication and
        # recheck after acquiring the lock; a second compiler otherwise replaces
        # an already populated bundle directory (ENOTEMPTY on macOS).
        import fcntl

        with (cache / ".compile.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if (bundle / "Contents/MacOS" / self.name).is_file():
                return bundle
            with tempfile.TemporaryDirectory(prefix="compile-", dir=cache) as temporary:
                root = Path(temporary)
                for name, source in self.sources:
                    path = root / name
                    if Path(name).is_absolute() or ".." in Path(name).parts:
                        raise ValueError("native source path must stay in its build directory")
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(source)
                staged = root / bundle.name
                contents = staged / "Contents"
                binary = contents / "MacOS" / self.name
                binary.parent.mkdir(parents=True)
                command = [compiler, "-std=c++17", "-O3", "-fvisibility=hidden", "-bundle",
                           "-arch", "arm64", "-arch", "x86_64", "-mmacosx-version-min=11.0",
                           "-undefined", "dynamic_lookup",
                           f'-DM4L_EXTERNAL_NAME="{self.name}"',
                           "-I", str(includes / "max-includes"),
                           "-I", str(includes / "msp-includes"),
                           "-F", str(includes / "msp-includes"), "-framework", "MaxAudioAPI",
                           str(root / self.entry), "-o", str(binary)]
                subprocess.run(command, check=True, capture_output=True, text=True)
                info = {"CFBundleExecutable": self.name, "CFBundleIdentifier":
                        "org.m4l-builder." + self.name.replace("~", ""),
                        "CFBundleName": self.name, "CFBundlePackageType": "iLaX",
                        "CFBundleVersion": "1", "CFBundleShortVersionString": "0.1.0"}
                (contents / "Info.plist").write_bytes(plistlib.dumps(info))
                (contents / "PkgInfo").write_bytes(b"iLaXmax2")
                license_path = sdk / "LICENSE.md"
                if license_path.is_file():
                    (contents / "Resources").mkdir()
                    (contents / "Resources/SDK-LICENSE.txt").write_bytes(license_path.read_bytes())
                subprocess.run(["codesign", "--force", "--sign", "-", "--timestamp=none", str(staged)],
                               check=True, capture_output=True)
                os.replace(staged, bundle)
        return bundle

    def frozen_files(self) -> list[tuple[str, bytes]]:
        bundle = self.compile()
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zipped:
            for path in sorted(bundle.rglob("*")):
                if path.is_file():
                    item = zipfile.ZipInfo(str(path.relative_to(bundle.parent)),
                                           date_time=(2020, 1, 1, 0, 0, 0))
                    item.external_attr = (0o100755 if "MacOS" in path.parts else 0o100644) << 16
                    item.compress_type = zipfile.ZIP_DEFLATED
                    zipped.writestr(item, path.read_bytes())
        return [(f"{self.name}/zipfile", archive.getvalue()),
                (f"{self.name}/executable", (bundle / "Contents/MacOS" / self.name).read_bytes()),
                (f"{self.name}/plist", (bundle / "Contents/Info.plist").read_bytes())]


class _BundleAsset(Asset):
    def write_to(self, output_dir: str) -> str:
        path = super().write_to(output_dir)
        if "MacOS" in Path(self.filename).parts:
            Path(path).chmod(0o755)
        return path


class NativeInstrument(Instrument):
    """Instrument whose compiled dependencies materialize at build time."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.native_externals: list[NativeExternal] = []

    def add_external(self, external: NativeExternal) -> str:
        self.native_externals.append(external)
        self.register_asset(f"{external.name}.mxo", b"\0" * 4, asset_type="iLaX")
        self.register_asset(f"{external.name}_source.json", external.manifest, asset_type="JSON")
        return external.name

    def to_bytes(self, *, validate=None, freeze=False) -> bytes:
        if not freeze:
            return super().to_bytes(validate=validate)
        patcher = prepare_device_patcher(self, validate=validate)
        dependencies = [(a.filename, _asset_bytes(a)) for a in self.assets()]
        for external in self.native_externals:
            dependencies.extend(external.frozen_files())
        return assemble_frozen_amxd(DEVICE_TYPE_CODES[self.device_type], f"{self.name}.amxd",
                                   json.dumps(patcher, indent="\t").encode() + b"\n\0",
                                   dependencies)

    def build(self, output_path, *, validate=None, freeze=False) -> int:
        if freeze:
            return write_artifacts(output_path, self.to_bytes(validate=validate, freeze=True))
        assets = [a for a in self.assets() if a.asset_type != "iLaX"]
        for external in self.native_externals:
            bundle = external.compile()
            for path in sorted(bundle.rglob("*")):
                if path.is_file():
                    assets.append(_BundleAsset(str(path.relative_to(bundle.parent)), path.read_bytes()))
        return write_artifacts(output_path, self.to_bytes(validate=validate), assets=assets)


def modal_external() -> NativeExternal:
    root = Path(__file__).with_name("modal")
    sources = tuple((p.name, p.read_text()) for p in sorted(root.iterdir())
                    if p.suffix in {".hpp", ".cpp"})
    sources += (("LICENSE.txt", root.parent.joinpath("LICENSE.txt").read_text()),)
    return NativeExternal("m4l.modal", sources, "modal_max.cpp")
