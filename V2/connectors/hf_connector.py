from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter
from huggingface_hub import HfApi

from .base import Connector


class HFConnector(Connector):
    """
    HF connector that prefers datasets-server schema, falls back to viewer rows to infer fields,
    and finally the dataset card.
    """

    def __init__(self, hf_token: Optional[str] = None, timeout: float = 5.0):
        self.hf_token = hf_token or os.getenv("HF_TOKEN")
        self.timeout = timeout
        self.api = HfApi(token=self.hf_token)
        self.client = httpx.Client(timeout=timeout)

    # --- helpers ---------------------------------------------------------
    def _headers(self) -> Dict[str, str]:
        hdrs: Dict[str, str] = {}
        if self.hf_token:
            hdrs["authorization"] = f"Bearer {self.hf_token}"
        return hdrs

    @retry(
        reraise=False,
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=0.2, max=2.0),
        retry=retry_if_exception_type(httpx.HTTPError),
    )
    def _fetch_json(self, url: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        resp = self.client.get(url, params=params, headers=self._headers())
        if resp.status_code in (429, 500, 502, 503, 504):
            resp.raise_for_status()
        if resp.status_code != 200:
            return None
        try:
            return resp.json()
        except Exception:
            return None

    def _fetch_info_api(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        return self._fetch_json(
            "https://datasets-server.huggingface.co/info", {"dataset": dataset_id}
        )

    def _features_from_info(self, info: Dict[str, Any]) -> Tuple[Optional[List[Dict[str, Any]]], Optional[Tuple[str, str]]]:
        splits = info.get("splits") or []
        default_config = info.get("default_config") or None
        default_split = info.get("default_split") or None
        chosen_cfg = default_config
        chosen_split = default_split
        if not chosen_cfg and splits:
            chosen_cfg = splits[0].get("config")
        if not chosen_split and splits:
            chosen_split = splits[0].get("split")
        for split in splits:
            feats = split.get("features")
            if feats:
                return feats, (split.get("config") or chosen_cfg, split.get("split") or chosen_split)
        feats = info.get("features")
        if feats:
            return feats, (chosen_cfg, chosen_split)
        return None, (chosen_cfg, chosen_split)

    def _features_from_card(self, dataset_id: str) -> Optional[List[Dict[str, Any]]]:
        try:
            ds = self.api.dataset_info(dataset_id)
        except Exception:
            return None
        card = getattr(ds, "cardData", None) or {}
        di = card.get("dataset_info") or {}
        features = di.get("features")
        if isinstance(features, dict):
            # dict of name->type; normalize to list
            return [
                {"name": k, "dtype": v.get("dtype") if isinstance(v, dict) else str(v)}
                for k, v in features.items()
            ]
        return features if isinstance(features, list) else None

    def _infer_dtype(self, value: Any) -> str:
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "bool"
        if isinstance(value, int):
            return "int64"
        if isinstance(value, float):
            return "float64"
        if isinstance(value, str):
            return "string"
        if isinstance(value, list):
            return "array"
        if isinstance(value, dict):
            return "struct"
        return "unknown"

    def _infer_schema_from_rows(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        acc: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            if "row" in row:
                row = row["row"]
            if not isinstance(row, dict):
                continue
            for k, v in row.items():
                dtype = self._infer_dtype(v)
                entry = acc.setdefault(k, {"name": k, "dtype": dtype, "nullable": False, "examples": []})
                entry["dtype"] = dtype if entry["dtype"] == dtype else entry["dtype"]
                if v is None:
                    entry["nullable"] = True
                if len(entry["examples"]) < 3:
                    entry["examples"].append(v)
        return list(acc.values())

    def _fetch_rows(self, dataset_id: str, config: Optional[str], split: Optional[str], limit: int) -> List[Dict[str, Any]]:
        if not config or not split:
            return []
        params = {
            "dataset": dataset_id,
            "config": config,
            "split": split,
            "offset": 0,
            "length": limit,
        }
        resp = self._fetch_json("https://datasets-server.huggingface.co/rows", params)
        if not resp:
            return []
        return resp.get("rows") or []

    # --- public ---------------------------------------------------------
    def fetch_schema_or_sample(
        self, dataset_id: str, *, kind: str, budget_ms: int, row_cap: int
    ) -> Dict[str, Any]:
        # budget_ms/row_cap are advisory; datasets-server calls are quick. We still
        # track actual elapsed time and signal when the budget was exceeded.
        start = time.perf_counter()
        requested_budget_ms = max(int(budget_ms or 0), 0)
        effective_row_cap = max(int(row_cap or 0), 0) or 200

        info = self._fetch_info_api(dataset_id)
        features: Optional[List[Dict[str, Any]]] = None
        config_split: Tuple[Optional[str], Optional[str]] = (None, None)
        if info:
            features, config_split = self._features_from_info(info)

        # Try rows if no features or empty
        if not features:
            cfg, split = config_split
            rows = self._fetch_rows(dataset_id, cfg, split, limit=effective_row_cap)
            if rows:
                features = self._infer_schema_from_rows(rows)

        # Fallback to dataset card
        if not features:
            features = self._features_from_card(dataset_id)

        elapsed_ms = int((time.perf_counter() - start) * 1000)
        base_payload: Dict[str, Any] = {
            "dataset_id": dataset_id,
            "kind": kind,
            "row_cap_applied": effective_row_cap,
            "fetched_ms": elapsed_ms,
            "budget_ms_requested": requested_budget_ms,
            "budget_exhausted": bool(requested_budget_ms and elapsed_ms > requested_budget_ms),
            "source": "hf_connector",
        }

        if not features:
            base_payload["schema"] = []
            base_payload["note"] = "schema_not_available"
            return base_payload

        base_payload.update(
            {
                "schema": features,
                "config": config_split[0],
                "split": config_split[1],
            }
        )
        return base_payload

    def close(self) -> None:
        try:
            self.client.close()
        except Exception:
            pass

    def __del__(self) -> None:
        self.close()
