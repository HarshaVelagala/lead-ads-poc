from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.lead import Lead
from app.routes.auth import get_current_admin
from app.schemas.lead import LeadCreate, LeadRead
from app.services.websocket_manager import websocket_manager

router = APIRouter(prefix="/leads", tags=["leads"])


def _insert_lead(payload: LeadCreate, database: Session) -> tuple[Lead, bool]:
    if payload.meta_lead_id:
        existing = database.scalar(select(Lead).where(Lead.meta_lead_id == payload.meta_lead_id))
        if existing:
            return existing, False
    lead = Lead(**payload.model_dump())
    database.add(lead)
    try:
        database.commit()
    except IntegrityError:
        database.rollback()
        if payload.meta_lead_id:
            existing = database.scalar(select(Lead).where(Lead.meta_lead_id == payload.meta_lead_id))
            if existing:
                return existing, False
        raise
    except SQLAlchemyError as exc:
        database.rollback()
        raise HTTPException(status_code=500, detail="Could not save lead") from exc
    database.refresh(lead)
    return lead, True


@router.get("", response_model=list[LeadRead])
def list_leads(
    database: Session = Depends(get_db),
    _: str = Depends(get_current_admin),
) -> list[Lead]:
    return list(database.scalars(select(Lead).order_by(Lead.received_at.desc(), Lead.id.desc())))


@router.get("/{lead_id}", response_model=LeadRead)
def get_lead(
    lead_id: int,
    database: Session = Depends(get_db),
    _: str = Depends(get_current_admin),
) -> Lead:
    lead = database.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.post("", response_model=LeadRead, status_code=status.HTTP_201_CREATED)
async def create_lead(
    payload: LeadCreate,
    database: Session = Depends(get_db),
    _: str = Depends(get_current_admin),
) -> Lead:
    lead, created = _insert_lead(payload, database)
    if created:
        await websocket_manager.broadcast_lead(LeadRead.model_validate(lead))
    return lead
