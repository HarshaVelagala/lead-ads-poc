import hashlib
import hmac
from datetime import datetime
from typing import Any

import httpx
from fastapi import HTTPException

from app import config
from app.schemas.lead import LeadCreate


def verify_signature(raw_body: bytes, signature: str | None) -> bool:
    if not config.META_APP_SECRET or not signature or not signature.startswith("sha256="):
        return False
    expected = hmac.new(config.META_APP_SECRET.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature.removeprefix("sha256="), expected)


def _field_value(field_data: list[dict[str, Any]], *field_names: str) -> str:
    for field in field_data:
        if field.get("name") in field_names:
            values = field.get("values") or []
            return str(values[0]) if values else ""
    return ""


async def fetch_lead(lead_id: str, form_id: str | None = None, page_id: str | None = None) -> LeadCreate:
    if not config.META_ACCESS_TOKEN:
        raise HTTPException(status_code=503, detail="META_ACCESS_TOKEN is not configured")
    if "X" in config.META_API_VERSION:
        raise HTTPException(status_code=503, detail="Set META_API_VERSION to a currently supported version")
    url = f"https://graph.facebook.com/{config.META_API_VERSION}/{lead_id}"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                url,
                params={"fields": "id,created_time,field_data,form_id", "access_token": config.META_ACCESS_TOKEN},
            )
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail="Could not connect to the Meta Graph API") from exc
    if response.is_error:
        raise HTTPException(status_code=502, detail="Meta Graph API could not retrieve the lead")
    try:
        data = response.json()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="Meta Graph API returned invalid JSON") from exc
    if not isinstance(data, dict):
        raise HTTPException(status_code=502, detail="Meta Graph API returned an unexpected response")
    fields = data.get("field_data") or []
    created_time = data.get("created_time")
    try:
        parsed_created_time = datetime.fromisoformat(created_time.replace("Z", "+00:00")) if created_time else None
    except (AttributeError, ValueError):
        parsed_created_time = None
    return LeadCreate(
        meta_lead_id=str(data.get("id", lead_id)),
        name=_field_value(fields, "full_name", "name") or "Meta lead",
        email=_field_value(fields, "email"),
        phone=_field_value(fields, "phone_number", "phone"),
        form_id=str(data.get("form_id") or form_id) if (data.get("form_id") or form_id) else None,
        page_id=page_id or config.META_PAGE_ID or None,
        created_time=parsed_created_time,
    )