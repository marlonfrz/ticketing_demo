from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
optional_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

def has_role(user: User, role_name: str) -> bool:
    return any(role.name == role_name for role in user.roles)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado",
        )
    
    if not user.is_active or user.status == "deactivated":
        raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Usuario inactivo o desactivado",
    )

    if payload.get("ver", 0) != user.token_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="La sesion ya no es valida",
        )

    return user


def get_optional_current_user(
    db: Session = Depends(get_db),
    token: str | None = Depends(optional_oauth2_scheme),
) -> User | None:
    if not token:
        return None

    payload = decode_access_token(token)
    if not payload:
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active or user.status == "deactivated":
        return None

    if payload.get("ver", 0) != user.token_version:
        return None

    return user

def require_promoter(current_user: User = Depends(get_current_user)) -> User:
    role_names = [role.name for role in current_user.roles]
    if "promoter" not in role_names:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los promotores pueden realizar esta acción",
        )
    return current_user

def require_promoter_or_admin(current_user: User = Depends(get_current_user)) -> User:
    role_names = [role.name for role in current_user.roles]
    if "promoter" not in role_names and "admin" not in role_names:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo promotores o administradores pueden realizar esta acción",
        )
    return current_user

def require_ticket_validator(current_user: User = Depends(get_current_user)) -> User:
    if (
        not has_role(current_user, "promoter")
        and not has_role(current_user, "admin")
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo promotores o administradores pueden validar entradas desde una cuenta",
        )
    return current_user

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    role_names = [role.name for role in current_user.roles]
    if "admin" not in role_names:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores pueden realizar esta acción",
        )
    return current_user

