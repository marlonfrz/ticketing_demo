from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MeResponse(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    phone: str | None = None
    country_code: str | None = None
    marketing_consent: bool = False
    is_active: bool
    status: str
    roles: list[str]
    is_superadmin: bool = False


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class PasswordResetRequest(BaseModel):
    token: str
    new_password: str
    new_password_confirm: str


class PasswordChangeRequest(BaseModel):
    token: str
    current_password: str
    new_password: str
    new_password_confirm: str


class AuthMessageResponse(BaseModel):
    success: bool
    message: str


class AccountStatusRequest(BaseModel):
    email: EmailStr


class AccountStatusResponse(BaseModel):
    exists: bool
    can_login: bool
