from datetime import datetime

from pydantic import BaseModel, Field


class EventSessionCreate(BaseModel):
    title: str | None = Field(None, max_length=255)
    location_name: str = Field(..., min_length=2, max_length=255)
    location_address: str | None = None
    starts_at: datetime
    ends_at: datetime | None = None
    capacity: int = Field(..., gt=0)
    publish_at: datetime | None = None
    tickets_publish_at: datetime | None = None
    display_order: int | None = None


class EventSessionUpdate(BaseModel):
    title: str | None = Field(None, max_length=255)
    location_name: str | None = Field(None, min_length=2, max_length=255)
    location_address: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    capacity: int | None = Field(None, gt=0)
    publish_at: datetime | None = None
    tickets_publish_at: datetime | None = None
    display_order: int | None = None


class EventSessionResponse(BaseModel):
    id: str
    event_id: str
    title: str | None = None
    location_name: str
    location_address: str | None = None
    starts_at: datetime
    ends_at: datetime | None = None
    capacity: int
    status: str
    publish_at: datetime | None = None
    tickets_publish_at: datetime | None = None
    tickets_activated_at: datetime | None = None
    display_order: int | None = None
    ticket_types_count: int = 0
    sold_tickets_count: int = 0
    created_at: datetime
    updated_at: datetime
