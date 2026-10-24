from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field


class LeadCreate(BaseModel):
    meta_lead_id: str | None = Field(default=None, min_length=1, max_length=200)
    name: str = Field(min_length=1, max_length=300)
    email: str = Field(default="", max_length=320)
    phone: str = Field(default="", max_length=80)
    form_id: str | None = Field(default=None, max_length=200)
    page_id: str | None = Field(default=None, max_length=200)
    created_time: datetime | None = None


class LeadRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    meta_lead_id: str | None
    name: str
    email: str
    phone: str
    form_id: str | None
    page_id: str | None
    created_time: datetime | None
    received_at: datetime

    @computed_field
    @property
    def fullName(self) -> str:
        return self.name

    @computed_field
    @property
    def mobile_id(self) -> str:
        return self.meta_lead_id or str(self.id)

    @computed_field
    @property
    def createdAt(self) -> datetime:
        return self.created_time or self.received_at