from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from src.storage import Artifact, Dataset, DuckDBStorage


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _token_count(text: str | None) -> int:
    return len((text or "").split())


def _readme_score(text: str | None) -> float:
    tokens = _token_count(text)
    if tokens <= 0:
        return 0.0
    return min(tokens / 50.0, 1.0)


def load_fixture(path: str | Path) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def build_demo_db(db_path: str | Path, fixture_path: str | Path) -> Path:
    db_path = Path(db_path)
    fixture_path = Path(fixture_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    storage = DuckDBStorage(str(db_path))
    storage.init()

    fixture = load_fixture(fixture_path)
    indexed_at = _now_utc()
    datasets = []
    for item in fixture["datasets"]:
        readme_text = item.get("readme_text")
        datasets.append(
            Dataset(
                id=item["id"],
                source=item.get("source", "hf"),
                ns_local_id=item.get("ns_local_id", item["id"]),
                title=item.get("title"),
                description=item.get("description"),
                readme_text=readme_text,
                tags=item.get("tags"),
                modalities=item.get("modalities"),
                license_class=item.get("license_class"),
                access_class=item.get("access_class", "public"),
                size_class=item.get("size_class"),
                languages=item.get("languages"),
                fingerprint=f"fixture:{item['id']}",
                indexed_at=indexed_at,
                readme_tokens=_token_count(readme_text),
                readme_score=_readme_score(readme_text),
                quality_signals=item.get("quality_signals"),
            )
        )

    storage.bulk_upsert_datasets(datasets)

    for artifact in fixture.get("artifacts", []):
        storage.put_artifact(
            Artifact(
                dataset_id=artifact["dataset_id"],
                kind=artifact["kind"],
                payload=artifact["payload"],
                created_at=indexed_at,
                stale=False,
            )
        )

    storage.refresh_dataset_state_view()
    storage.rebuild_search_index()
    return db_path
