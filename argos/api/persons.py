"""Person profiles + enrollment."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
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
