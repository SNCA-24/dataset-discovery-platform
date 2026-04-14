from __future__ import annotations

import random
from typing import Any, Dict, List

from .base import Connector


class OfflineStubConnector(Connector):
    """
    Offline connector that returns a placeholder schema without external calls.
    Useful in sandboxed environments; replace with HFConnector later.
    """

    def fetch_schema_or_sample(
        self, dataset_id: str, *, kind: str, budget_ms: int, row_cap: int
    ) -> Dict[str, Any]:
        random.seed(dataset_id)
        fields: List[Dict[str, Any]] = []
        for name in ["text", "label", "id"]:
            fields.append(
                {
                    "name": name,
                    "dtype": random.choice(["string", "int64", "float32"]),
                    "nullable": True,
                }
            )
        return {
            "dataset_id": dataset_id,
            "kind": kind,
            "schema": fields,
            "row_cap_applied": row_cap,
            "fetched_ms": min(budget_ms, 100),
            "source": "offline_stub",
        }

