import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import router
from src.config import load_settings
from src.api.worker import Worker
from src.connectors import HFConnector, OfflineStubConnector
from src.storage import DuckDBStorage

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    settings = load_settings()
    app = FastAPI(title="Dataset Discovery Platform", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)

    def storage_factory() -> DuckDBStorage:
        ds = DuckDBStorage(settings.duckdb_uri())
        ds.init()
        return ds

    try:
        connector = HFConnector()
    except Exception:
        connector = OfflineStubConnector()
    worker = Worker(storage_factory=storage_factory, settings=settings, connector=connector)

    @app.on_event("startup")
    async def _on_startup() -> None:
        logger.info("Starting dataset discovery API with backend=%s", settings.storage_backend)
        worker.start()

    @app.on_event("shutdown")
    async def _on_shutdown() -> None:
        worker.stop()

    return app


app = create_app()
