from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field


class ReservationItemCreate(BaseModel):
    ticket_type_id: str
    quantity: int = Field(..., gt=0)


class ReservationCustomerCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    email: str = Field(..., min_length=5, max_length=255)
    email_confirm: str = Field(..., min_length=5, max_length=255)
    phone: str = Field(..., min_length=6, max_length=50)
    country_code: str | None = Field(default=None, max_length=5)
    accept_terms: bool
    accept_privacy: bool


class ReservationWithOrderCreateRequest(BaseModel):
    items: list[ReservationItemCreate] = Field(..., min_length=1)
    customer: ReservationCustomerCreate | None = None
    public_relations_code: str | None = Field(default=None, max_length=80)


class ReservationItemResponse(BaseModel):
    ticket_type_id: str
    ticket_type_name: str
    sale_group_id: str | None = None
    quantity: int
    unit_price: Decimal
    subtotal: Decimal


class ReservationWithOrderResponse(BaseModel):
    reservation_group_token: str
    order_id: str
    payment_id: str
    event_id: str
    status: str
    payment_status: str
    total_amount: Decimal
    tickets_subtotal: Decimal | None = None
    management_fee: Decimal | None = None
    currency: str
    expires_at: datetime
    guest_access_token: str | None = None
    items: list[ReservationItemResponse]
