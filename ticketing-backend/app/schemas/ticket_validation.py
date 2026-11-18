from datetime import datetime
from pydantic import BaseModel, ConfigDict


class TicketValidationItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    ticket_id: str | None
    result: str
    message: str
    validation_type: str
    device_id: str | None
    validated_by_user_id: str | None
    validation_station_id: str | None = None
    notes: str | None
    validated_at: datetime


class TicketValidationRequest(BaseModel):
    qr_token: str
    device_id: str | None = None
    notes: str | None = None


class TicketValidationResponse(BaseModel):
    valid: bool
    message: str
    ticket: dict | None = None
