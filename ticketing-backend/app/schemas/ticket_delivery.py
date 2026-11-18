from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr


class TicketDeliveryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    ticket_id: str
    delivery_channel: str
    delivery_status: str
    recipient_email: EmailStr
    subject: str | None
    error_message: str | None
    sent_at: datetime | None
    created_at: datetime


class TicketSendResponse(BaseModel):
    success: bool
    message: str
    delivery: TicketDeliveryResponse | None = None
