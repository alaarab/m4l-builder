"""Stage device artifacts and roll back an interrupted installation."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path


def write_artifacts(output_path, data: bytes, *, assets=()) -> int:
    """Install sidecars before the binary, retaining originals until success.

    Each replacement is atomic on the destination filesystem. A failed stage
    leaves the installation untouched; a failed commit restores earlier files.
    If rollback itself fails, keep the recovery directory and report its path.
    """
    target = Path(output_path).absolute()
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".m4l-build-", dir=target.parent))
    fresh, backup = staging / "new", staging / "old"
    fresh.mkdir()
    backup.mkdir()
    names = []
    committed = []
    recoverable = True
    try:
        for asset in assets:
            name = Path(asset.filename)
            if name.is_absolute() or ".." in name.parts or name == Path("."):
                raise ValueError(f"asset filename must stay inside the output directory: {name}")
            if name == Path(target.name) or name in names:
                raise ValueError(f"duplicate output filename: {name}")
            (fresh / name).parent.mkdir(parents=True, exist_ok=True)
            asset.write_to(str(fresh))
            names.append(name)
        (fresh / target.name).write_bytes(data)
        names.append(Path(target.name))
        # Prepare every backup before touching any installed file.
        for name in names:
            dest = target.parent / name
            if dest.exists():
                (backup / name).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(dest, backup / name)
        try:
            for name in names:
                dest = target.parent / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                os.replace(fresh / name, dest)
                committed.append(name)
        except BaseException:
            for name in reversed(committed):
                dest = target.parent / name
                try:
                    if (backup / name).exists():
                        os.replace(backup / name, dest)
                    else:
                        dest.unlink()
                except OSError as exc:
                    recoverable = False
                    raise OSError(f"Artifact rollback failed; originals retained at {backup}") from exc
            raise
    finally:
        if recoverable:
            shutil.rmtree(staging)
    return len(data)
