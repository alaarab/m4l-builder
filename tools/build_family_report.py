"""Build a focused reverse-engineering report for one external AMXD family."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from m4l_builder import (  # noqa: E402
    analyze_amxd_corpus,
    build_reverse_candidate_family_profile,
    family_profile_markdown,
    write_family_profile,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("corpus_dir", help="Directory containing .amxd files")
    parser.add_argument("family", help="Normalized family name or source filename stem")
    parser.add_argument(
        "--out",
        help="Optional path for the markdown family report (default: <corpus_dir>/<family>-family-report.md)",
    )
    parser.add_argument(
        "--json-out",
        help="Optional path for the family profile JSON (default: alongside the markdown report)",
    )
    parser.add_argument(
        "--non-recursive",
        action="store_true",
        help="Only scan the top level of the corpus directory",
    )
    args = parser.parse_args()

    corpus_dir = Path(args.corpus_dir).expanduser().resolve()
    report = analyze_amxd_corpus(str(corpus_dir), recursive=not args.non_recursive)
    profile = build_reverse_candidate_family_profile(report, args.family)
    if profile is None:
        parser.error(f"No parsed family named {args.family!r} found in {corpus_dir}")

    default_stem = f"{profile['family']}-family-report"
    out_path = Path(args.out).expanduser().resolve() if args.out else corpus_dir / f"{default_stem}.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_family_profile(profile, str(out_path))

    json_out = Path(args.json_out).expanduser().resolve() if args.json_out else out_path.with_suffix(".json")
    with json_out.open("w", encoding="utf-8") as handle:
        json.dump(profile, handle, indent=2, sort_keys=True)
        handle.write("\n")

    print(f"Family: {profile['family']}")
    print(f"Variants: {profile['variant_count']}")
    print(f"Markdown: {out_path}")
    print(f"JSON: {json_out}")
    print()
    print(family_profile_markdown(profile))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
