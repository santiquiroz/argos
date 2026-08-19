"""FastAPI routers. Thin HTTP adapters over the store / bus / pipeline on ``app.state``."""

from fastapi import FastAPI

from argos.api.cameras import router as cameras_router
from argos.api.digest import router as digest_router
from argos.api.discovery import router as discovery_router
from argos.api.events import router as events_router
from argos.api.health import router as health_router
from argos.api.notify import router as notify_router
from argos.api.persons import router as persons_router
from argos.api.settings import router as settings_router
from argos.api.status import router as status_router
from argos.api.zones import router as zones_router


def include_routers(app: FastAPI) -> None:
    for router in (
        health_router,
        status_router,
        persons_router,
        events_router,
        discovery_router,
        cameras_router,
        settings_router,
        notify_router,
        zones_router,
        digest_router,
    ):
        app.include_router(router, prefix="/api")
