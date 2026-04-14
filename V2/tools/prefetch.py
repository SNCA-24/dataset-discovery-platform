"""
Enqueue schema resolves for thin/no-README public datasets.

Respects the runtime auto-pause checks and skips enqueueing when resolve p95
or queue depth exceed thresholds.

Usage:
  HF_TOKEN=<token> python -m V2.tools.prefetch --duckdb-path data/discovery.duckdb --limit 100
"""

from __future__ import annotations

import argparse
from datetime import datetime

from V2.config import load_settings
from V2.storage import Job
from V2.storage.duckdb_backend import DuckDBStorage


def should_pause(metrics: dict, settings) -> tuple[bool, str | None]:
    if metrics.get("resolve_p95_ms", 0) > settings.resolve_p95_max_ms:
        return True, "resolve_slow"
    if metrics.get("queue_depth", 0) > settings.queue_depth_absolute_max:
        return True, "queue_depth"
    if not settings.prefetch_enabled:
        return True, "prefetch_disabled"
    return False, None


def prefetch(duckdb_path: str, limit: int) -> None:
    settings = load_settings()
    storage = DuckDBStorage(duckdb_path)
    storage.init()

    metrics = storage.admin_metrics()
    paused, reason = should_pause(metrics, settings)
    if paused:
        print(f"[prefetch] skipped: paused due to {reason}")
        return

    candidates = storage.prefetch_candidates(limit)
    if not candidates:
        print("[prefetch] no candidates")
        return

    enqueued = 0
    now = datetime.utcnow()
    for did in candidates:
        storage.enqueue_job(
            Job(
                id=f"prefetch-{did}",
                dataset_id=did,
                kind="schema",
                state="queued",
                attempts=0,
                enqueued_at=now,
                started_at=None,
                finished_at=None,
                error_class=None,
                error_detail=None,
                budget_ms=settings.resolve_budget_ms_default,
                row_cap=settings.resolve_row_cap_default,
            )
        )
        enqueued += 1
    print(f"[prefetch] enqueued {enqueued} schema jobs")


def main() -> None:
    ap = argparse.ArgumentParser(description="Prefetch thin/no-README datasets.")
    ap.add_argument("--duckdb-path", default="data/discovery.duckdb", help="Path to DuckDB file.")
    ap.add_argument("--limit", type=int, default=100, help="Max jobs to enqueue.")
    args = ap.parse_args()
    prefetch(args.duckdb_path, args.limit)


if __name__ == "__main__":
    main()
