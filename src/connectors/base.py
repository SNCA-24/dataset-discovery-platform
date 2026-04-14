from __future__ import annotations

import abc
from typing import Any, Dict


class Connector(abc.ABC):
    """Connector interface for on-demand resolve."""

    @abc.abstractmethod
    def fetch_schema_or_sample(
        self, dataset_id: str, *, kind: str, budget_ms: int, row_cap: int
    ) -> Dict[str, Any]:
        ...

