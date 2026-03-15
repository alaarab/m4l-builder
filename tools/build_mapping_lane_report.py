"""Build a mapping/modulation lane markdown report for a local AMXD corpus."""

from __future__ import annotations

import argparse
from pathlib import Path

from m4l_builder import (
    analyze_amxd_corpus,
    build_mapping_lane_report,
    mapping_lane_report_markdown,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("corpus", help="Corpus directory to analyze")
    parser.add_argument("output", help="Markdown output path")
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of top mapping/modulation devices to include",
    )
    parser.add_argument(
        "--non-recursive",
        action="store_true",
        help="Do not recurse into subdirectories",
    )
    args = parser.parse_args()

    report = analyze_amxd_corpus(args.corpus, recursive=not args.non_recursive)
    markdown = mapping_lane_report_markdown(
        build_mapping_lane_report(report, limit=args.limit)
    )
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(markdown, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
