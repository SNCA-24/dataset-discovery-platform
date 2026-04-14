"""
Nightly prefetch scheduler (Module E helper).

Runs prefetch at a fixed interval (default 24h) or once immediately.

Usage:
  HF_TOKEN=<token> python -m V2.tools.prefetch_scheduler --duckdb-path data/discovery.duckdb --limit 100 --every-hours 24
"""

from __future__ import annotations

import argparse
import time

from V2.tools.prefetch import prefetch


def main() -> None:
    ap = argparse.ArgumentParser(description="Prefetch scheduler loop.")
    ap.add_argument("--duckdb-path", default="data/discovery.duckdb", help="Path to DuckDB file.")
    ap.add_argument("--limit", type=int, default=100, help="Max jobs to enqueue per run.")
    ap.add_argument("--every-hours", type=float, default=24.0, help="Interval hours between runs.")
    ap.add_argument("--once", action="store_true", help="Run once then exit.")
    args = ap.parse_args()

    interval_sec = args.every_hours * 3600
    while True:
        prefetch(args.duckdb_path, args.limit)
        if args.once:
            break
        time.sleep(interval_sec)


if __name__ == "__main__":
    main()
