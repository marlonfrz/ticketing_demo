from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class TicketEventInfo(BaseModel):
    id: str
    title: str
    starts_at: datetime
    location_name: str | None = None


class TicketTypeInfo(BaseModel):
    id: str
    name: str


class TicketSessionInfo(BaseModel):
    id: str
    title: str | None = None
    starts_at: datetime
    ends_at: datetime | None = None
    location_name: str
    location_address: str | None = None


class TicketGeneratedByInfo(BaseModel):
    id: str
    full_name: str
    email: str


class TicketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    order_id: str
    event_id: str
    ticket_type_id: str
    owner_user_id: str | None
    generated_by_user_id: str | None = None
    ticket_code: str
    source: str = "purchase"
    recipient_name: str | None = None
    generation_note: str | None = None
    qr_image_url: str
    status: str
    is_valid: bool
    issued_at: datetime
    used_at: datetime | None
    created_at: datetime
    event: TicketEventInfo
    session: TicketSessionInfo | None = None
    ticket_type: TicketTypeInfo
    generated_by: TicketGeneratedByInfo | None = None


class TicketValidationRequest(BaseModel):
    qr_token: str


class TicketValidationResponse(BaseModel):
    valid: bool
    message: str
    ticket: TicketResponse | None = None


class ComplimentaryTicketCreateRequest(BaseModel):
    session_id: str | None = None
    ticket_type_id: str
    quantity: int = Field(..., gt=0, le=100)
    recipient_name: str | None = Field(None, max_length=255)
    note: str | None = Field(None, max_length=1000)


class ComplimentaryTicketBatchResponse(BaseModel):
    success: bool
    event_id: str
    session_id: str | None = None
    ticket_type_id: str
    quantity: int
    tickets: list[TicketResponse]


class ComplimentaryTicketTypeSummary(BaseModel):
    ticket_type_id: str
    ticket_type_name: str
    quantity: int


class ComplimentaryTicketSummaryResponse(BaseModel):
    event_id: str
    session_id: str | None = None
    total: int
    by_ticket_type: list[ComplimentaryTicketTypeSummary]
    tickets: list[TicketResponse]
