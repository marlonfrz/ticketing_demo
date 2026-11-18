from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


ALLOWED_GROUP_STRATEGIES = {
    "stock_cascade",
    "time_window",
    "time_and_stock_cascade",
}


class TicketTypeInSaleGroupCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: str | None = None
    price: Decimal = Field(..., gt=0)
    currency: str = Field(default="EUR", min_length=3, max_length=3)
    stock: int = Field(..., gt=0)
    max_per_purchase: int = Field(default=10, gt=0)
    status: str
    is_active: bool = True
    sale_order: int = Field(..., gt=0)


class TicketSaleGroupCreate(BaseModel):
    session_id: str | None = None
    name: str = Field(..., min_length=2, max_length=255)
    strategy: str = "stock_cascade"
    display_order: int | None = Field(default=None, gt=0)
    is_active: bool = True
    ticket_types: list[TicketTypeInSaleGroupCreate] = []


class TicketSaleGroupUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=255)
    strategy: str | None = None
    display_order: int | None = Field(None, gt=0)
    is_active: bool | None = None


class TicketSaleGroupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_id: str
    session_id: str | None = None
    name: str
    strategy: str
    is_active: bool
    status: str
    display_order: int | None = None
    sale_starts_at: datetime | None
    sale_ends_at: datetime | None
    created_at: datetime
    updated_at: datetime

