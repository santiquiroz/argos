"""FastAPI app factory + lifespan composition root (pattern from bipolar-code).

Lifespan builds the shared services (store, bus, ingestor, analyzers, pipeline), starts the pipeline
and retention workers, and stashes everything on ``app.state``. The built React SPA is served as a
fallback when ``frontend/dist`` exists, so the whole thing runs as one process / one binary.
"""

from __future__ import annotations

import asyncio
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse, Response

from argos import __version__
from argos.api import include_routers
from argos.config import Settings, get_settings
from argos.events import EventBus
from argos.factory import build_action_analyzer, build_crop_analyzers, build_ingestor
from argos.logging import configure_logging, get_logger
from argos.middleware import APIKeyMiddleware
from argos.pipeline import Pipeline
from argos.profiling.store import ProfileStore

log = get_logger(__name__)

_RETENTION_INTERVAL_S = 6 * 3600


async def _retention_loop(store: ProfileStore, settings: Settings) -> None:
    while True:
        store.purge_expired(
            embeddings_days=settings.retain_embeddings_days,
            events_days=settings.retain_events_days,
        )
        await asyncio.sleep(_RETENTION_INTERVAL_S)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging()
    store = ProfileStore(settings.db_path())
    bus = EventBus()
    crop_analyzers = build_crop_analyzers(settings)
    action_analyzer = build_action_analyzer(settings)
    ingestor = build_ingestor(settings)
    pipeline = Pipeline(
        settings=settings,
        store=store,
        bus=bus,
        ingestor=ingestor,
        crop_analyzers=crop_analyzers,
        action_analyzer=action_analyzer,
    )
    app.state.settings = settings
    app.state.store = store
    app.state.bus = bus
    app.state.crop_analyzers = crop_analyzers
    app.state.pipeline = pipeline
    app.state.pipeline_task = asyncio.create_task(pipeline.run())
    app.state.retention_task = asyncio.create_task(_retention_loop(store, settings))
    log.info("argos_started", version=__version__, device=settings.device, ingest=settings.ingest)
    try:
        yield
    finally:
        await pipeline.stop()
        for task in (app.state.pipeline_task, app.state.retention_task):
            task.cancel()
        store.close()
        log.info("argos_stopped")


def _mount_spa(app: FastAPI) -> None:
    """Serve the built React SPA with a client-route fallback, if present."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    dist = base / "frontend" / "dist"
    if not dist.is_dir():
        return

    class SPAStatic(StaticFiles):
        async def get_response(self, path: str, scope) -> Response:
            response = await super().get_response(path, scope)
            if response.status_code == 404:
                return FileResponse(dist / "index.html")
            return response

    app.mount("/", SPAStatic(directory=str(dist), html=True), name="spa")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Argos", version=__version__, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list(),
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(APIKeyMiddleware, api_key=settings.api_key)
    include_routers(app)
    _mount_spa(app)
    return app


app = create_app()
