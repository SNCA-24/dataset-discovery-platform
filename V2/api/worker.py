import logging
import threading
import time
from typing import Callable
from datetime import datetime

import httpx

from V2.config import Settings
from V2.connectors import Connector
from V2.storage import Artifact, StorageAdapter

logger = logging.getLogger(__name__)


class Worker:
    """Lightweight background worker that will claim jobs and emit artifacts."""

    def __init__(
        self,
        storage_factory: Callable[[], StorageAdapter],
        settings: Settings,
        connector: Connector,
    ):
        self.storage_factory = storage_factory
        self.settings = settings
        self.connector = connector
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _run_loop(self) -> None:
        storage = self.storage_factory()
        storage.init()
        while not self._stop.is_set():
            # Reclaim stale running jobs using a simple lease timeout so the
            # queue can self-heal after crashes or long hangs.
            try:
                storage.reclaim_stale_jobs(
                    self.settings.worker_lease_timeout_sec,
                    max_attempts=3,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Worker failed to reclaim stale jobs: %s", exc)

            job = storage.claim_next_job()
            if not job:
                time.sleep(self.settings.worker_poll_interval_sec)
                continue
            try:
                payload = self.connector.fetch_schema_or_sample(
                    job.dataset_id,
                    kind=job.kind,
                    budget_ms=job.budget_ms or self.settings.resolve_budget_ms_default,
                    row_cap=job.row_cap or self.settings.resolve_row_cap_default,
                )
                artifact = Artifact(
                    dataset_id=job.dataset_id,
                    kind=job.kind,
                    payload=payload,
                    created_at=job.started_at or job.enqueued_at,
                    stale=False,
                )
                storage.put_artifact(artifact)
                storage.mark_job_done(job.id)
                storage.log_event(
                    {
                        "type": "dataset.resolved_ok",
                        "dataset_id": job.dataset_id,
                        "job_id": job.id,
                        "kind": job.kind,
                        "created_at": datetime.utcnow(),
                    }
                )
            except Exception as exc:  # noqa: BLE001
                logger.exception("Worker failed job %s: %s", job.id, exc)
                error_class = "unknown"
                if isinstance(exc, httpx.TimeoutException):
                    error_class = "timeout"
                elif isinstance(exc, httpx.HTTPStatusError):
                    status_code = exc.response.status_code if exc.response is not None else None
                    if status_code == 429:
                        error_class = "rate_limited"
                    elif status_code and 500 <= status_code < 600:
                        error_class = "network"
                elif isinstance(exc, httpx.RequestError):
                    error_class = "network"
                elif isinstance(exc, ValueError):
                    # e.g. unexpected parsing issues
                    error_class = "parse_error"

                storage.mark_job_error(
                    job.id,
                    error_class=error_class,
                    error_detail=str(exc),
                )
                storage.log_event(
                    {
                        "type": "dataset.resolved_err",
                        "dataset_id": job.dataset_id,
                        "job_id": job.id,
                        "kind": job.kind,
                        "error_class": error_class,
                        "error_detail": str(exc)[:500],
                        "created_at": datetime.utcnow(),
                    }
                )
            time.sleep(self.settings.worker_poll_interval_sec)
        logger.info("Worker stopped.")
