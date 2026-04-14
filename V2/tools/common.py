from __future__ import annotations

import hashlib
import math
from typing import Optional, Tuple


def readme_stats(text: Optional[str]) -> Tuple[int, float, Optional[str], Optional[str]]:
    if not text:
        return 0, 0.0, None, None
    tokens = text.split()
    token_count = len(tokens)
    score = min(1.0, math.log1p(token_count) / math.log1p(400))
    title = None
    description = None
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            title = stripped.lstrip("#").strip() or None
            continue
        if not description:
            description = stripped
        if title and description:
            break
    return token_count, score, title, description


def compute_fingerprint(
    source: str,
    ns_local_id: str,
    readme_sha: Optional[str],
    last_modified: Optional[str],
    size_class: Optional[str],
    license_class: Optional[str],
) -> str:
    values = [
        source or "",
        ns_local_id or "",
        readme_sha or "",
        last_modified or "",
        size_class or "",
        license_class or "",
    ]
    blob = "|".join(values)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()
