"""FastAPI routers. Thin HTTP adapters over the store / bus / pipeline on ``app.state``."""

from fastapi import FastAPI

from argos.api.discovery import router as discovery_router
from argos.api.events import router as events_router
from argos.api.health import router as health_router
from argos.api.persons import router as persons_router


def include_routers(app: FastAPI) -> None:
    app.include_router(health_router, prefix="/api")
    app.include_router(persons_router, prefix="/api")
    app.include_router(events_router, prefix="/api")
    app.include_router(discovery_router, prefix="/api")
