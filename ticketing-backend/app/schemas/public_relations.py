from datetime import datetime
from pydantic import BaseModel, Field


class PublicRelationsRegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    phone: str = Field(..., min_length=6, max_length=50)
    email: str | None = Field(default=None, max_length=255)
    social_handle: str | None = Field(default=None, max_length=255)
    accept_privacy: bool


class PublicRelationsRegisterInfoResponse(BaseModel):
    event_id: str
    event_title: str
    event_status: str


class PublicRelationsRegisterResponse(BaseModel):
    id: str
    event_id: str
    full_name: str
    phone: str
    email: str | None = None
    social_handle: str | None = None
    sales_code: str
    sales_url: str


class PublicRelationsTicketTypeBreakdown(BaseModel):
    ticket_type_id: str
    ticket_type_name: str
    quantity: int


class PublicRelationsSessionBreakdown(BaseModel):
    session_id: str
    location_name: str
    starts_at: datetime
    quantity: int
    ticket_types: list[PublicRelationsTicketTypeBreakdown]


class PublicRelationsSummaryResponse(BaseModel):
    id: str
    event_id: str
    full_name: str
    phone: str
    email: str | None = None
    social_handle: str | None = None
    sales_code: str
    sales_url: str
    registration_url: str
    status: str
    total_sold: int
    by_ticket_type: list[PublicRelationsTicketTypeBreakdown]
    by_session: list[PublicRelationsSessionBreakdown]
    created_at: datetime
