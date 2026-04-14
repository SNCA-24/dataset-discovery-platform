from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


DatasetID = str
ArtifactKind = str  # 'schema' | 'stats' | 'snips'
JobState = str  # 'queued' | 'running' | 'done' | 'error'


@dataclass
class Dataset:
    id: DatasetID
    source: str
    ns_local_id: str
    title: Optional[str] = None
    description: Optional[str] = None
    readme_text: Optional[str] = None
    tags: Optional[List[str]] = None
    modalities: Optional[List[str]] = None
    license_class: Optional[str] = None
    access_class: Optional[str] = None
    size_class: Optional[str] = None
    languages: Optional[List[str]] = None
    last_seen_lm: Optional[datetime] = None
    readme_sha256: Optional[str] = None
    card_sha256: Optional[str] = None
    fingerprint: Optional[str] = None
    indexed_at: Optional[datetime] = None
    readme_tokens: Optional[int] = None
    readme_score: Optional[float] = None
    eligibility_flags: Optional[List[str]] = None
    quality_signals: Optional[Dict[str, Any]] = None
    schema_hint: Optional[str] = None


@dataclass
class Artifact:
    dataset_id: DatasetID
    kind: ArtifactKind
    payload: Dict[str, Any]
    created_at: datetime
    stale: bool = False


@dataclass
class Job:
    id: str
    dataset_id: DatasetID
    kind: ArtifactKind
    state: JobState
    attempts: int
    enqueued_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error_class: Optional[str] = None
    error_detail: Optional[str] = None
    budget_ms: Optional[int] = None
    row_cap: Optional[int] = None


@dataclass
class Event:
    id: str
    type: str
    dataset_id: Optional[DatasetID]
    payload: Dict[str, Any]
    created_at: datetime


@dataclass
class Signal:
    id: str
    session_id: str
    user_id: Optional[str]
    event: str
    dataset_id: Optional[DatasetID]
    query: Optional[str]
    rank: Optional[int]
    created_at: datetime


@dataclass
class Connector:
    source: str
    cursor: Optional[str]
    qps_limit: Optional[int]
    backoff_state: Optional[str]


__all__ = [
    "Artifact",
    "ArtifactKind",
    "Connector",
    "Dataset",
    "DatasetID",
    "Event",
    "Job",
    "JobState",
    "Signal",
]
