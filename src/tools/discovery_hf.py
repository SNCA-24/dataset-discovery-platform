"""
Discovery tool for the optional Hugging Face-backed catalog sync path.

Fetches dataset listings in newest-to-oldest order, stops at the stored
cursor, and upserts new or updated rows into DuckDB. Cursor state is stored in
the `connectors` table under source='hf' as
{"max_seen": {"lastModified": ..., "id": ...}}.

Usage:
  python -m src.tools.discovery_hf --duckdb-path data/discovery.duckdb --limit 1000 --qps 1.0 [--backfill-until 2024-01-01T00:00:00Z]
"""

from __future__ import annotations

import argparse
import os
import time
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple

from huggingface_hub import HfApi

from src.storage import Dataset, DuckDBStorage
from src.tools.common import compute_fingerprint, readme_stats


def parse_lm(lm: Optional[str]) -> Optional[datetime]:
    if not lm:
        return None
    try:
        if lm.endswith("Z"):
            lm = lm.replace("Z", "+00:00")
        dt = datetime.fromisoformat(lm)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def tuple_gt(a: Tuple[datetime, str], b: Optional[Tuple[datetime, str]]) -> bool:
    if b is None:
        return True
    if a[0] > b[0]:
        return True
    if a[0] == b[0] and a[1] > b[1]:
        return True
    return False


def discover(
    duckdb_path: str,
    limit: Optional[int],
    qps: float,
    backfill_until: Optional[datetime],
) -> None:
    os.makedirs(os.path.dirname(duckdb_path) or ".", exist_ok=True)
    storage = DuckDBStorage(duckdb_path)
    storage.init()
    api = HfApi()

    cursor = storage.get_connector_cursor("hf")
    max_seen_prev = None
    if cursor and "max_seen" in cursor:
        ms = cursor["max_seen"]
        max_seen_prev = (
            parse_lm(ms.get("lastModified")) or datetime.min.replace(tzinfo=timezone.utc),
            ms.get("id", ""),
        )
    if max_seen_prev:
        print(f"[discovery] Using cursor boundary: {max_seen_prev[0]} {max_seen_prev[1]}")
    else:
        print("[discovery] No cursor boundary found; full scan until limit/backfill.")

    processed = 0
    last_q = 1.0 / max(qps, 1e-6)
    max_seen_new: Optional[Tuple[datetime, str]] = None
    batch = []

    try:
        iterator = api.list_datasets(sort="lastModified", direction=-1, full=False)
    except Exception as exc:  # noqa: BLE001
        print(f"[discovery] list_datasets failed: {exc}")
        return

    for ds in iterator:
        lm = parse_lm(getattr(ds, "lastModified", None) or ds.last_modified if hasattr(ds, "last_modified") else None)
        did = ds.id
        if lm is None:
            continue
        tup = (lm, did)
        if max_seen_prev and (
            tup[0] < max_seen_prev[0]
            or (tup[0] == max_seen_prev[0] and tup[1] <= max_seen_prev[1])
        ):
            # Reached boundary; lists are newest->oldest, so break here.
            break
        if backfill_until and tup[0] < backfill_until:
            # Backfill stop boundary (older than target)
            break

        # Build dataset row (no README/cards yet)
        ns_local_id = did.split("/", 1)[1] if "/" in did else did
        tags = getattr(ds, "tags", []) or []
        license_class = getattr(ds, "license", None) or None
        readme_tokens, readme_score, title_guess, desc_guess = readme_stats(None)
        fingerprint = compute_fingerprint(
            source="hf",
            ns_local_id=ns_local_id,
            readme_sha=None,
            last_modified=lm.isoformat(),
            size_class=None,
            license_class=license_class,
        )
        dataset = Dataset(
            id=did,
            source="hf",
            ns_local_id=ns_local_id,
            title=title_guess or getattr(ds, "cardData", {}).get("title") if hasattr(ds, "cardData") else did,
            description=desc_guess,
            readme_text=None,
            tags=tags,
            modalities=None,
            license_class=license_class,
            access_class="public" if not getattr(ds, "private", False) else "private",
            size_class=None,
            languages=None,
            last_seen_lm=lm,
            readme_sha256=None,
            card_sha256=None,
            fingerprint=fingerprint,
            indexed_at=datetime.utcnow(),
            readme_tokens=readme_tokens,
            readme_score=readme_score,
            eligibility_flags=None,
            quality_signals={
                "downloads": getattr(ds, "downloads", None),
                "likes": getattr(ds, "likes", None),
                "gated": getattr(ds, "gated", None),
            },
            schema_hint=None,
        )
        batch.append(dataset)
        if max_seen_new is None or tuple_gt(tup, max_seen_new):
            max_seen_new = tup
        processed += 1
        if len(batch) >= 500:
            storage.bulk_upsert_datasets(batch)
            batch.clear()
        if limit and processed >= limit:
            break
        time.sleep(last_q)

    if batch:
        storage.bulk_upsert_datasets(batch)

    if max_seen_new:
        storage.upsert_connector(
            "hf",
            cursor={
                "max_seen": {
                    "lastModified": max_seen_new[0].isoformat(),
                    "id": max_seen_new[1],
                }
            },
        )
    storage.refresh_dataset_state_view()
    storage.rebuild_search_index()
    boundary = max_seen_prev[0].isoformat() if max_seen_prev else "none"
    print(f"[discovery] Discovered {processed} datasets; boundary={boundary}")


def main() -> None:
    parser = argparse.ArgumentParser(description="HF discovery into DuckDB (Module A2).")
    parser.add_argument("--duckdb-path", default="data/discovery.duckdb", help="DuckDB destination.")
    parser.add_argument("--limit", type=int, default=None, help="Max datasets to pull this run.")
    parser.add_argument("--qps", type=float, default=1.0, help="Listing QPS (float).")
    parser.add_argument(
        "--backfill-until",
        type=str,
        default=None,
        help="Optional ISO8601 boundary (oldest lastModified to fetch, inclusive).",
    )
    args = parser.parse_args()
    backfill_until = parse_lm(args.backfill_until) if args.backfill_until else None
    discover(args.duckdb_path, args.limit, args.qps, backfill_until)


if __name__ == "__main__":
    main()
