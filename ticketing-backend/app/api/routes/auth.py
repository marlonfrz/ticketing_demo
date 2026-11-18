from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.rate_limit import (
    account_status_rate_limit,
    forgot_password_rate_limit,
    login_rate_limit,
    register_rate_limit,
    reset_password_rate_limit,
)
from app.models.user import User
from app.schemas.auth import (
    AccountStatusRequest,
    AccountStatusResponse,
    AuthMessageResponse,
    ForgotPasswordRequest,
    MeResponse,
    PasswordChangeRequest,
    PasswordResetRequest,
    TokenResponse,
)
from app.schemas.user import UserCreate, UserResponse
from app.services.auth_service import (
    authenticate_user,
    change_password_from_link,
    get_account_status,
    register_user,
    request_forgot_password,
    request_password_change,
    reset_forgotten_password,
)
from app.schemas.status_action import StatusActionResponse
from app.services.user_service import deactivate_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/account-status", response_model=AccountStatusResponse)
def account_status(
    data: AccountStatusRequest,
    db: Session = Depends(get_db),
    _: None = Depends(account_status_rate_limit),
):
    return get_account_status(db, str(data.email))


@router.post("/register", response_model=UserResponse)
def register(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    _: None = Depends(register_rate_limit),
):
    user = register_user(db, user_data)
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "phone": user.phone,
        "country_code": user.country_code,
        "marketing_consent": user.marketing_consent,
        "is_active": user.is_active,
        "status": user.status,
        "roles": [role.name for role in user.roles],
    }


@router.post("/login", response_model=TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    _: None = Depends(login_rate_limit),
):
    return authenticate_user(db, form_data.username, form_data.password)


@router.post("/forgot-password", response_model=AuthMessageResponse)
def forgot_password(
    data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _: None = Depends(forgot_password_rate_limit),
):
    return request_forgot_password(db, data.email, background_tasks)


@router.post("/reset-password", response_model=AuthMessageResponse)
def reset_password(
    data: PasswordResetRequest,
    db: Session = Depends(get_db),
    _: None = Depends(reset_password_rate_limit),
):
    return reset_forgotten_password(
        db,
        data.token,
        data.new_password,
        data.new_password_confirm,
    )


@router.post("/request-password-change", response_model=AuthMessageResponse)
def request_my_password_change(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return request_password_change(db, current_user)


@router.post("/change-password", response_model=AuthMessageResponse)
def change_password(data: PasswordChangeRequest, db: Session = Depends(get_db)):
    return change_password_from_link(
        db,
        data.token,
        data.current_password,
        data.new_password,
        data.new_password_confirm,
    )


@router.get("/me", response_model=MeResponse)
def me(current_user: User = Depends(get_current_user)):
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "phone": current_user.phone,
        "country_code": current_user.country_code,
        "marketing_consent": current_user.marketing_consent,
        "is_active": current_user.is_active,
        "status": current_user.status,
        "roles": [role.name for role in current_user.roles],
        "is_superadmin": current_user.is_superadmin,
    }

@router.delete("/me", response_model=StatusActionResponse)
def deactivate_my_account(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return deactivate_user(db, str(current_user.id), current_user)
