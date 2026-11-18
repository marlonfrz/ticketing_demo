from pydantic import BaseModel, EmailStr, Field


class OrganizerContactRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=30)
    description: str = Field(min_length=20, max_length=3000)
    website: str | None = Field(default=None, max_length=200)


class ContactMessageResponse(BaseModel):
    success: bool
    message: str
