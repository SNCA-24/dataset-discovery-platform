from functools import lru_cache

from fastapi import Depends

from V2.config import Settings, load_settings
from V2.storage import DuckDBStorage, PostgresStorage, StorageAdapter


@lru_cache
def _get_settings_cached() -> Settings:
    return load_settings()


def get_settings() -> Settings:
    return _get_settings_cached()


def get_storage(settings: Settings = Depends(get_settings)) -> StorageAdapter:
    if settings.storage_backend == "duckdb":
        storage = DuckDBStorage(settings.duckdb_uri())
    elif settings.storage_backend == "postgres":
        if not settings.postgres_dsn:
            raise RuntimeError("POSTGRES_DSN is required when using postgres backend.")
        storage = PostgresStorage(settings.postgres_dsn)
    else:
        raise RuntimeError(f"Unknown storage backend: {settings.storage_backend}")

    # init is idempotent and cheap; safe to call at request start.
    storage.init()
    return storage

