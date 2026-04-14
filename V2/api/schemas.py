from __future__ import annotations

from typing import List, Optional
from enum import Enum

from pydantic import BaseModel, Field


class SearchFilters(BaseModel):
    modality: Optional[str] = None
    license_class: Optional[str] = None
    size_class: Optional[str] = None
    language: Optional[str] = None


class SearchRequest(BaseModel):
    query: str
    filters: Optional[SearchFilters] = None
    limit: int = Field(default=30, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class SearchHit(BaseModel):
    id: str
    title: Optional[str] = None
    description: Optional[str] = None
    readme_text: Optional[str] = None
    why: List[str] = Field(default_factory=list)
    has_schema: bool = False
    blocked_reason: Optional[str] = None
    license_class: Optional[str] = None
    access_class: Optional[str] = None
    size_class: Optional[str] = None
    modalities: List[str] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    downloads: Optional[int] = None
    likes: Optional[int] = None


class SearchResponse(BaseModel):
    hits: List[SearchHit]
    total: int


class RequestResolve(BaseModel):
    id: str
    kind: str = Field(default="schema", pattern="^(schema|stats|snips)$")
    budget_ms: Optional[int] = None
    row_cap: Optional[int] = None
    ui_context: Optional[str] = None


class RequestResolveResponse(BaseModel):
    job_id: str


class PolicyCheckRequest(BaseModel):
    id: str
    action: str = Field(default="schema")
    budget_ms: Optional[int] = None
    row_cap: Optional[int] = None


class PolicyCheckResponse(BaseModel):
    allow: bool
    reason_code: Optional[str] = None


class ArtifactResponse(BaseModel):
    payload: dict
    stale: bool = False


class SignalRequest(BaseModel):
    session_id: str
    user_id: Optional[str] = None
    event: str
    dataset_id: Optional[str] = None
    query: Optional[str] = None
    rank: Optional[int] = None


class AdminMetricsResponse(BaseModel):
    freshness_pct: float
    thin_readme_pct: float
    resolve_p95_ms: float
    queue_depth: int
    error_taxonomy: dict
    public_no_schema_count: int
    public_with_schema_pct: float
    prefetch_paused: bool
    prefetch_reason: Optional[str] = None
    jobs_by_state: dict = Field(default_factory=dict)


class DiscoveryMode(str, Enum):
    topup = "topup"
    backfill = "backfill"


class AdminOpResponse(BaseModel):
    status: str
    detail: Optional[str] = None


class AdminDiscoveryRequest(BaseModel):
    mode: DiscoveryMode = Field(default=DiscoveryMode.topup)
    window_days: Optional[int] = None  # used when mode=backfill


class AdminDiscoveryResponse(AdminOpResponse):
    mode: DiscoveryMode
    window_days: Optional[int] = None


class AdminPrefetchRequest(BaseModel):
    limit: Optional[int] = None


class AdminPrefetchResponse(AdminOpResponse):
    enqueued: int = 0
