import json
import hmac
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app import config
from app.database import get_db
from app.models.lead import Lead
from app.schemas.lead import LeadRead
from app.services.meta_service import fetch_lead, verify_signature
from app.services.websocket_manager import websocket_manager

router = APIRouter(prefix="/webhook/meta", tags=["Meta webhook"])


@router.get("")
def verify_meta_webhook(
    mode: str | None = Query(default=None, alias="hub.mode"),
    token: str | None = Query(default=None, alias="hub.verify_token"),
    challenge: str | None = Query(default=None, alias="hub.challenge"),
) -> PlainTextResponse:
    if mode == "subscribe" and config.META_VERIFY_TOKEN and hmac.compare_digest(token or "", config.META_VERIFY_TOKEN):
        return PlainTextResponse(challenge or "")
    raise HTTPException(status_code=403, detail="Webhook verification failed")


@router.post("")
async def receive_meta_webhook(
    request: Request,
    database: Session = Depends(get_db),
    x_hub_signature_256: str | None = Header(default=None),
) -> dict[str, bool]:
    raw_body = await request.body()
    if not verify_signature(raw_body, x_hub_signature_256):
        raise HTTPException(status_code=403, detail="Invalid Meta webhook signature")
    try:
        payload: Any = json.loads(raw_body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="Webhook body must be valid JSON")
    if not isinstance(payload, dict):
        return {"received": True}

    entries = payload.get("entry")
    if not isinstance(entries, list):
        return {"received": True}

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        page_id = str(entry.get("id")) if entry.get("id") is not None else None
        changes = entry.get("changes")
        if not isinstance(changes, list):
            continue
        for change in changes:
            if not isinstance(change, dict) or change.get("field") != "leadgen":
                continue
            value = change.get("value")
            if not isinstance(value, dict) or not value.get("leadgen_id"):
                continue
            meta_lead_id = str(value["leadgen_id"])
            existing = database.scalar(select(Lead).where(Lead.meta_lead_id == meta_lead_id))
            if existing:
                continue
            details = await fetch_lead(
                meta_lead_id,
                str(value["form_id"]) if value.get("form_id") is not None else None,
                page_id,
            )
            lead = Lead(**details.model_dump())
            database.add(lead)
            try:
                database.commit()
            except IntegrityError:
                database.rollback()
                continue
            except SQLAlchemyError as exc:
                database.rollback()
                raise HTTPException(status_code=500, detail="Could not save Meta lead") from exc
            database.refresh(lead)
            await websocket_manager.broadcast_lead(LeadRead.model_validate(lead))
    return {"received": True}