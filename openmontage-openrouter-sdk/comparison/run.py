#!/usr/bin/env python3
"""Fetch the live OpenRouter catalog and print / write the comparison report."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from comparison.catalog import run_comparison
from comparison.report import render_markdown


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "artifacts",
        help="Directory for markdown + JSON report files",
    )
    args = parser.parse_args()
    report = run_comparison()
    markdown = render_markdown(report)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "comparison-report.md").write_text(markdown, encoding="utf-8")
    (args.out_dir / "comparison-report.json").write_text(
        json.dumps(report.to_dict(), indent=2),
        encoding="utf-8",
    )
    sys.stdout.write(markdown)
    failures = report.extras.get("live_failures") or []
    if failures:
        sys.stderr.write(f"\nLive catalog drift: {failures}\n")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
