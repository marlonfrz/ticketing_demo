from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel


class PromoterDashboardEventItem(BaseModel):
    id: str
    title: str
    starts_at: datetime
    status: str
    capacity: int


class PromoterDashboardResponse(BaseModel):
    total_events: int
    total_tickets_sold: int
    total_tickets_validated: int
    total_revenue: Decimal
    upcoming_events: list[PromoterDashboardEventItem]


class EventStatsTicketTypeItem(BaseModel):
    ticket_type_id: str
    ticket_type_name: str
    stock: int
    sold_count: int
    remaining_stock: int
    revenue: Decimal


class EventStatsResponse(BaseModel):
    event_id: str
    title: str
    status: str
    capacity: int
    total_stock_defined: int
    total_tickets_sold: int
    total_tickets_validated: int
    remaining_capacity: int
    total_revenue: Decimal
    ticket_types: list[EventStatsTicketTypeItem]


class EventOrderItemResponse(BaseModel):
    id: str
    buyer_id: str | None = None
    status: str
    total_amount: Decimal
    currency: str
    created_at: datetime


class EventValidationItemResponse(BaseModel):
    id: str
    ticket_id: str | None
    result: str
    message: str
    validation_type: str
    device_id: str | None
    validated_by_user_id: str | None
    validation_station_id: str | None = None
    validation_station_name: str | None = None
    notes: str | None
    validated_at: datetime
