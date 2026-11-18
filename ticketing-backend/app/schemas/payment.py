from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    order_id: str
    provider: str
    status: str
    amount: Decimal
    currency: str
    provider_order_id: str | None
    provider_payment_id: str | None
    raw_request: str | None
    raw_response: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class DemoCheckoutResponse(BaseModel):
    payment_id: str
    order_id: str
    checkout_session_id: str
    checkout_url: str
    expires_at: datetime
