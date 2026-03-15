"""Build a local reverse/codegen fixture from an external AMXD corpus."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from m4l_builder import (  # noqa: E402
    build_corpus_manifest,
    run_corpus_fixture,
    write_corpus_fixture_results,
    write_corpus_manifest,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("corpus_dir", help="Directory containing .amxd files")
    parser.add_argument("fixture_dir", help="Directory where fixture artifacts should be written")
    parser.add_argument(
        "--selection",
        default="stable",
        help="Subset to materialize: stable, all, ok, errors, bridge_enabled, family:<name>, or category:<tag>",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Optional limit after subset selection",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=12,
        help="Stable-sample size when building the corpus manifest",
    )
    parser.add_argument(
        "--modes",
        default="exact,builder,optimized,semantic",
        help="Comma-separated generation modes to write into the fixture",
    )
    parser.add_argument(
        "--non-recursive",
        action="store_true",
        help="Only scan the top level of the corpus directory",
    )
    parser.add_argument(
        "--manifest-out",
        help="Optional path for the generated manifest JSON (default: <fixture_dir>/manifest.json)",
    )
    parser.add_argument(
        "--results-out",
        help="Optional path for the fixture results JSON (default: <fixture_dir>/fixture.json)",
    )
    args = parser.parse_args()

    corpus_dir = Path(args.corpus_dir).expanduser().resolve()
    fixture_dir = Path(args.fixture_dir).expanduser().resolve()
    fixture_dir.mkdir(parents=True, exist_ok=True)

    manifest = build_corpus_manifest(
        str(corpus_dir),
        recursive=not args.non_recursive,
        stable_sample_size=args.sample_size,
    )
    manifest_out = Path(args.manifest_out) if args.manifest_out else fixture_dir / "manifest.json"
    write_corpus_manifest(manifest, str(manifest_out))

    modes = tuple(mode.strip() for mode in args.modes.split(",") if mode.strip())
    results = run_corpus_fixture(
        manifest,
        str(fixture_dir),
        selection=args.selection,
        limit=args.limit,
        modes=modes,
    )
    results_out = Path(args.results_out) if args.results_out else fixture_dir / "fixture.json"
    write_corpus_fixture_results(results, str(results_out))

    print(f"Manifest: {manifest_out}")
    print(f"Fixture: {results_out}")
    print(f"Selection: {results['selection']}")
    print(f"Selected files: {results['selected_count']}")
    print(f"Modes: {', '.join(results['modes'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
