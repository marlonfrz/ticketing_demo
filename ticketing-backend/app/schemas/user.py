from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)
    phone: str = Field(..., min_length=6, max_length=50)
    country_code: str = Field(default="ES", min_length=2, max_length=5)
    password: str = Field(..., min_length=12)
    accept_terms: bool
    accept_privacy: bool
    marketing_consent: bool = False
    registration_source: Literal["registration", "guest_checkout"] = "registration"


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    full_name: str
    phone: str | None = None
    country_code: str | None = None
    marketing_consent: bool = False
    is_active: bool
    status: str
    roles: list[str]

