"""FastAPI routers. Thin HTTP adapters over the store / bus / pipeline on ``app.state``."""

from fastapi import FastAPI

from argos.api.cameras import router as cameras_router
from argos.api.discovery import router as discovery_router
from argos.api.events import router as events_router
from argos.api.health import router as health_router
from argos.api.persons import router as persons_router
from argos.api.settings import router as settings_router


def include_routers(app: FastAPI) -> None:
    for router in (
        health_router,
        persons_router,
        events_router,
        discovery_router,
        cameras_router,
        settings_router,
    ):
        app.include_router(router, prefix="/api")
