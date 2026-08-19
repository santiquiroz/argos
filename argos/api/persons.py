"""Person profiles + enrollment."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

router = APIRouter(tags=["persons"])


class EnrollRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)


@router.get("/persons")
def list_persons(request: Request) -> list[dict]:
    return request.app.state.store.list_persons()


@router.post("/persons/{person_id}/enroll")
def enroll_person(person_id: str, body: EnrollRequest, request: Request) -> dict:
    store = request.app.state.store
    known = {p["id"] for p in store.list_persons()}
    if person_id not in known:
        raise HTTPException(status_code=404, detail="person not found")
    store.enroll(person_id, body.name)
    return {"id": person_id, "name": body.name, "enrolled": True}


@router.get("/persons/{person_id}/thumbnail")
def person_thumbnail(person_id: str, request: Request) -> FileResponse:
    path = request.app.state.store.latest_crop_path(person_id)
    if path is None or not Path(path).is_file():
        raise HTTPException(status_code=404, detail="no thumbnail")
    return FileResponse(path, media_type="image/jpeg")
