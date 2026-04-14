from __future__ import annotations

from typing import Optional

from V2.config import Settings
from V2.storage import Dataset


SIZE_ORDER = [
    "n<1K",
    "1K<n<10K",
    "10K<n<100K",
    "100K<n<1M",
    "1M<n<10M",
    "10M<n<100M",
    "n>100M",
]


def _size_rank(size_class: Optional[str]) -> int:
    if not size_class:
        return -1
    if size_class in SIZE_ORDER:
        return SIZE_ORDER.index(size_class)
    return -1


def evaluate_policy(
    dataset: Optional[Dataset],
    *,
    budget_ms: Optional[int],
    row_cap: Optional[int],
    settings: Settings,
) -> tuple[bool, Optional[str]]:
    if dataset is None:
        return False, "not_applicable"

    # Access control
    if dataset.access_class and dataset.access_class != "public":
        return False, "gated_private"

    # License allowlist
    if dataset.license_class and dataset.license_class not in settings.license_allowlist:
        return False, "license_denied"

    # Size ceiling (optional)
    if settings.max_size_class:
        max_rank = _size_rank(settings.max_size_class)
        if max_rank >= 0:
            ds_rank = _size_rank(dataset.size_class)
            if ds_rank > max_rank:
                return False, "size_exceeded"

    # Budget caps
    if budget_ms and budget_ms > settings.resolve_budget_ms_default:
        return False, "time_budget_exceeded"
    if row_cap and row_cap > settings.resolve_row_cap_default:
        return False, "time_budget_exceeded"

    return True, None

