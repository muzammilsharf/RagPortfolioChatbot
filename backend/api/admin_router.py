from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException

from core import settings
from services import IngestService


router = APIRouter()


@router.post("/api/v1/admin/ingest")
async def ingest(x_api_key: str | None = Header(default=None)) -> dict:
    if not settings.admin_api_key:
        raise HTTPException(status_code=500, detail="The keys to the office are missing! I can't access my admin tools right now. Please notify the dev team.") 
    if x_api_key != settings.admin_api_key:
        raise HTTPException(status_code=401, detail="Access Denied. It looks like you don't have the permissions for this area. Maybe try again?")

    svc = IngestService()
    return svc.ingest_all_pdfs()
