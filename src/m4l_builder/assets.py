"""Asset registry for sidecar files emitted with Max for Live devices."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Union


@dataclass
class Asset:
    """A file dependency emitted alongside a built device."""

    filename: str
    content: Union[str, bytes]
    asset_type: str = "TEXT"
    category: str = "support"
    encoding: str = "utf-8"

    def dependency_entry(self) -> dict:
        """Return the Max dependency cache entry for this asset."""
        return {
            "name": self.filename,
            "type": self.asset_type,
            "implicit": 1,
        }

    def write_to(self, output_dir: str) -> str:
        """Write the asset into the given directory and return the file path."""
        path = Path(output_dir) / self.filename
        if isinstance(self.content, bytes):
            path.write_bytes(self.content)
        else:
            path.write_text(self.content, encoding=self.encoding)
        return str(path)
