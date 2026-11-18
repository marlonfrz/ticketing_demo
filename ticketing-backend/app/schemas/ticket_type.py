from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class TicketTypeCreate(BaseModel):
    session_id: str | None = None
    name: str = Field(..., min_length=2, max_length=100)
    description: str | None = None
    price: Decimal = Field(..., gt=0)
    currency: str = Field(default="EUR", min_length=3, max_length=3)
    stock: int = Field(..., gt=0)
    max_per_purchase: int = Field(default=10, gt=0)
    display_order: int | None = Field(default=None, gt=0)
    is_active: bool = True


class TicketTypeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(None, min_length=2, max_length=100)
    description: str | None = None
    price: Decimal | None = Field(None, gt=0)
    currency: str | None = Field(None, min_length=3, max_length=3)
    stock: int | None = Field(None, gt=0)
    max_per_purchase: int | None = Field(None, gt=0)
    display_order: int | None = Field(None, gt=0)
    is_active: bool | None = None


class TicketTypeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_id: str
    session_id: str | None = None
    sale_group_id: str | None = None
    sale_order: int | None = None
    display_order: int | None = None
    name: str
    description: str | None
    price: Decimal
    currency: str
    stock: int
    sold_count: int
    max_per_purchase: int
    sale_starts_at: datetime | None
    sale_ends_at: datetime | None
    is_active: bool
    status: str
    created_at: datetime
    updated_at: datetime

