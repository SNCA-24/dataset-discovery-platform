from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.demo_data import build_demo_db


FIXTURE_PATH = Path("tests/fixtures/demo_catalog.json")


def _create_client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "smoke_demo.duckdb"
    build_demo_db(db_path, FIXTURE_PATH)
    os.environ["DUCKDB_PATH"] = str(db_path)
    os.environ["STORAGE_BACKEND"] = "duckdb"
    os.environ["PREFETCH_ENABLED"] = "true"

    from src.api.deps import _get_settings_cached

    _get_settings_cached.cache_clear()

    from src.api.main import create_app

    return TestClient(create_app())


def test_healthz(tmp_path: Path) -> None:
    with _create_client(tmp_path) as client:
        response = client.get("/v2/healthz")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


def test_search_returns_seeded_dataset(tmp_path: Path) -> None:
    with _create_client(tmp_path) as client:
        response = client.post(
            "/v2/search_index",
            json={"query": "text classification", "limit": 5},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["total"] >= 1
        assert payload["hits"][0]["id"] == "acme/text-classification-demo"
        assert payload["hits"][0]["has_schema"] is True


def test_admin_metrics_load(tmp_path: Path) -> None:
    with _create_client(tmp_path) as client:
        response = client.get("/v2/admin")
        assert response.status_code == 200
        payload = response.json()
        assert "freshness_pct" in payload
        assert "queue_depth" in payload
        assert "public_with_schema_pct" in payload


def test_get_artifact_returns_seeded_schema(tmp_path: Path) -> None:
    with _create_client(tmp_path) as client:
        response = client.get(
            "/v2/get_artifact",
            params={"id": "acme/text-classification-demo", "kind": "schema"},
        )
        assert response.status_code == 200
        payload = response.json()["payload"]
        assert payload["dataset_id"] == "acme/text-classification-demo"
        assert payload["schema"][0]["name"] == "text"


def test_request_resolve_returns_cached_for_seeded_artifact(tmp_path: Path) -> None:
    with _create_client(tmp_path) as client:
        response = client.post(
            "/v2/request_resolve",
            json={"id": "acme/text-classification-demo", "kind": "schema"},
        )
        assert response.status_code == 200
        assert response.json()["job_id"] == "cached-acme/text-classification-demo"
