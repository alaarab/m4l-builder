"""Mine a directory of .amxd files into a reusable JSON + markdown report."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from m4l_builder import analyze_amxd_corpus, build_corpus_manifest, write_corpus_manifest, write_corpus_report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("corpus_dir", help="Directory containing .amxd files")
    parser.add_argument(
        "--non-recursive",
        action="store_true",
        help="Only scan the top level of the corpus directory",
    )
    parser.add_argument(
        "--json-out",
        help="Output path for JSON analysis (default: <corpus_dir>/analysis.json)",
    )
    parser.add_argument(
        "--md-out",
        help="Output path for markdown report (default: <corpus_dir>/report.md)",
    )
    parser.add_argument(
        "--manifest-out",
        help="Output path for corpus manifest JSON (default: <corpus_dir>/manifest.json)",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=12,
        help="Stable sample size when generating the manifest",
    )
    args = parser.parse_args()

    corpus_dir = Path(args.corpus_dir).expanduser().resolve()
    report = analyze_amxd_corpus(str(corpus_dir), recursive=not args.non_recursive)

    json_out = Path(args.json_out) if args.json_out else corpus_dir / "analysis.json"
    md_out = Path(args.md_out) if args.md_out else corpus_dir / "report.md"
    manifest_out = Path(args.manifest_out) if args.manifest_out else corpus_dir / "manifest.json"

    json_out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_corpus_report(report, str(md_out))
    manifest = build_corpus_manifest(
        str(corpus_dir),
        recursive=not args.non_recursive,
        stable_sample_size=args.sample_size,
        analysis=report,
    )
    write_corpus_manifest(manifest, str(manifest_out))

    summary = report["summary"]
    print(f"Scanned: {summary['count']}")
    print(f"Parsed: {summary['ok']}")
    print(f"Errors: {summary['error']}")
    print(f"JSON: {json_out}")
    print(f"Report: {md_out}")
    print(f"Manifest: {manifest_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
