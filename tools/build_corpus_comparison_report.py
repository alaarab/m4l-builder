"""Build a comparison markdown report across multiple corpus roots."""

from __future__ import annotations

import argparse
from pathlib import Path

from m4l_builder import (
    analyze_amxd_corpus,
    build_corpus_comparison,
    corpus_comparison_markdown,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", help="Markdown output path")
    parser.add_argument(
        "pairs",
        nargs="+",
        help="Comparison entries in the form label=/path/to/corpus",
    )
    parser.add_argument("--non-recursive", action="store_true", help="Do not recurse into subdirectories")
    args = parser.parse_args()

    reports = {}
    for pair in args.pairs:
        if "=" not in pair:
            raise SystemExit(f"Expected label=/path syntax, got: {pair}")
        label, corpus = pair.split("=", 1)
        reports[label] = analyze_amxd_corpus(corpus, recursive=not args.non_recursive)

    markdown = corpus_comparison_markdown(build_corpus_comparison(reports))
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(markdown, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
