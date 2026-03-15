"""Build a mapping/modulation product brief for one AMXD device."""

from __future__ import annotations

import argparse
from pathlib import Path

from m4l_builder import (
    build_mapping_product_brief_from_path,
    mapping_product_brief_markdown,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("amxd", help="AMXD file to analyze")
    parser.add_argument("output", help="Markdown output path")
    args = parser.parse_args()

    brief = build_mapping_product_brief_from_path(args.amxd)
    markdown = mapping_product_brief_markdown(brief)
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(markdown, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
