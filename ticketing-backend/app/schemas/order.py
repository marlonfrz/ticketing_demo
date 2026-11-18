from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.ticket import TicketResponse
from app.schemas.payment import PaymentResponse


class OrderCreateItem(BaseModel):
    ticket_type_id: str
    quantity: int = Field(..., gt=0)


class OrderCreate(BaseModel):
    event_id: str
    items: list[OrderCreateItem]


class OrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    ticket_type_id: str
    quantity: int
    unit_price: Decimal
    subtotal: Decimal


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    buyer_id: str | None = None
    event_id: str
    status: str
    total_amount: Decimal
    currency: str
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemResponse]
    tickets: list[TicketResponse]
    payments: list[PaymentResponse]


class CheckoutSummaryItemResponse(BaseModel):
    ticket_type_id: str
    ticket_type_name: str
    sale_group_id: str | None = None
    quantity: int
    unit_price: Decimal
    subtotal: Decimal


class CheckoutSummaryResponse(BaseModel):
    order_id: str
    event_id: str
    event_title: str | None = None
    status: str
    payment_status: str
    total_amount: Decimal
    tickets_subtotal: Decimal | None = None
    management_fee: Decimal | None = None
    currency: str
    expires_at: datetime | None = None
    items: list[CheckoutSummaryItemResponse]
