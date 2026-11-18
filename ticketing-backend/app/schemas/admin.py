from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field


class AdminDashboardResponse(BaseModel):
    total_users: int
    total_events: int
    pending_event_reviews: int
    total_orders: int
    total_paid_orders: int
    total_revenue: Decimal
    total_tickets: int
    total_validated_tickets: int


class AdminUserItemResponse(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    phone: str | None = None
    country_code: str | None = None
    is_active: bool
    status: str
    roles: list[str]
    is_superadmin: bool = False


class AdminEventPromoterResponse(BaseModel):
    id: str
    email: EmailStr
    full_name: str


class AdminEventSessionReviewResponse(BaseModel):
    id: str
    title: str | None = None
    location_name: str
    starts_at: datetime
    status: str
    capacity: int


class AdminEventItemResponse(BaseModel):
    id: str
    promoter_id: str
    promoter: AdminEventPromoterResponse | None = None
    review_entity_type: str = "event"
    review_entity_id: str | None = None
    session: AdminEventSessionReviewResponse | None = None
    title: str
    location_name: str
    starts_at: datetime
    status: str
    capacity: int
    platform_fee_type: str | None = None
    platform_fee_value: Decimal | None = None
    created_at: datetime


class AdminPaginatedUsersResponse(BaseModel):
    items: list[AdminUserItemResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class AdminPaginatedEventsResponse(BaseModel):
    items: list[AdminEventItemResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class AdminPromoterEventsResponse(BaseModel):
    promoter: AdminUserItemResponse
    events: list[AdminEventItemResponse]


class AdminUpdateUserRolesRequest(BaseModel):
    roles: list[str]


class AdminUpdateEventRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None


class AdminEventFeeRequest(BaseModel):
    platform_fee_type: str = Field(..., pattern="^(percentage|fixed)$")
    platform_fee_value: Decimal = Field(..., ge=0)


class AdminCreateUserRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)
    phone: str = Field(..., min_length=6, max_length=50)
    country_code: str = Field(default="ES", min_length=2, max_length=5)
    password: str = Field(..., min_length=12)


class AdminCreateUserResponse(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    phone: str | None = None
    country_code: str | None = None
    is_active: bool
    status: str
    roles: list[str]
    is_superadmin: bool = False
