from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.event_session import EventSessionCreate, EventSessionResponse


ALLOWED_EVENT_STATUSES = {
    "not_reviewed",
    "in_review",
    "draft",
    "published",
    "unpublished",
    "cancelled",
    "finished",
    "sold_out",
    "archived",
    "disabled",
}


class EventCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: str | None = None
    initial_session: EventSessionCreate
    status: str = "not_reviewed"


class EventUpdate(BaseModel):
    title: str | None = Field(None, min_length=3, max_length=255)
    description: str | None = None
    status: str | None = None


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    promoter_id: str
    title: str
    description: str | None
    publish_at: datetime | None = None
    status: str
    platform_fee_type: str | None = None
    platform_fee_value: Decimal | None = None
    image_url: str | None = None
    financial_summary: dict | None = None
    sessions: list[EventSessionResponse] = []
    created_at: datetime
    updated_at: datetime

