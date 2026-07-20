"""Build reference-device semantic-lifting dossiers for one or more AMXDs."""

from __future__ import annotations

import argparse
from pathlib import Path

from m4l_builder import (
    build_reference_device_dossiers,
    reference_device_dossiers_markdown,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", help="Markdown output path")
    parser.add_argument("paths", nargs="+", help="Reference AMXD paths")
    args = parser.parse_args()

    dossiers = build_reference_device_dossiers(args.paths)
    markdown = reference_device_dossiers_markdown(dossiers)
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(markdown, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
