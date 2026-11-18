import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from html import escape
from urllib.parse import quote

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_access_token,
    get_password_validation_error,
    hash_password,
    verify_password,
)
from app.models.password_reset_token import PasswordResetToken
from app.models.role import Role
from app.models.user import User
from app.schemas.user import UserCreate
from app.services.email_service import send_email_with_attachment


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _normalize_phone(phone: str) -> str:
    return "".join(character for character in phone.strip() if character.isdigit() or character == "+")


def validate_password_strength(password: str) -> None:
    validation_error = get_password_validation_error(password)
    if validation_error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=validation_error,
        )


def _hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _invalidate_unused_reset_tokens(db: Session, user_id, now: datetime) -> None:
    (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.user_id == user_id,
            PasswordResetToken.used_at.is_(None),
        )
        .update({"used_at": now}, synchronize_session=False)
    )


def _build_password_email_html(full_name: str, action_url: str, purpose: str) -> str:
    title = "Cambiar contraseña" if purpose == "change" else "Recuperar contraseña"
    return f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #222;">
        <h2>{title}</h2>
        <p>Hola {escape(full_name)},</p>
        <p>Hemos recibido una solicitud relacionada con la contraseña de tu cuenta.</p>
        <p>
          <a href="{escape(action_url)}"
             style="display:inline-block;padding:12px 16px;background:#111;color:#fff;text-decoration:none;border-radius:6px;">
            {title}
          </a>
        </p>
        <p>El enlace caduca en {settings.password_reset_token_expire_minutes} minutos y solo se puede usar una vez.</p>
        <p>Si no has sido tu, ignora este correo y ponte en contacto con nosotros si tienes dudas.</p>
      </body>
    </html>
    """


def _build_password_changed_email_html(full_name: str) -> str:
    return f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #222;">
        <h2>Contraseña actualizada</h2>
        <p>Hola {escape(full_name)},</p>
        <p>La contraseña de tu cuenta se ha actualizado correctamente.</p>
        <p>Por seguridad, tus sesiones anteriores se han cerrado.</p>
        <p>Si no has sido tu, ponte en contacto con nosotros cuanto antes.</p>
      </body>
    </html>
    """


def _create_reset_token(db: Session, user: User, purpose: str) -> str | None:
    now = datetime.now(timezone.utc)
    latest_token = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.purpose == purpose,
            PasswordResetToken.created_at >= now - timedelta(minutes=1),
        )
        .first()
    )
    if latest_token:
        return None

    _invalidate_unused_reset_tokens(db, user.id, now)
    raw_token = secrets.token_urlsafe(48)
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=_hash_reset_token(raw_token),
            purpose=purpose,
            expires_at=now + timedelta(minutes=settings.password_reset_token_expire_minutes),
        )
    )
    db.commit()
    return raw_token


def _send_password_link(user: User, raw_token: str, purpose: str) -> None:
    path = "/change-password" if purpose == "change" else "/reset-password"
    action_url = f"{settings.frontend_base_url}{path}?token={quote(raw_token)}"
    subject = "Cambio de contraseña" if purpose == "change" else "Recupera tu contraseña"
    send_email_with_attachment(
        to_email=user.email,
        subject=subject,
        html_body=_build_password_email_html(user.full_name, action_url, purpose),
    )


def _get_valid_reset_token(db: Session, raw_token: str, purpose: str) -> PasswordResetToken:
    now = datetime.now(timezone.utc)
    reset_token = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.token_hash == _hash_reset_token(raw_token),
            PasswordResetToken.purpose == purpose,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > now,
        )
        .first()
    )
    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El enlace no es valido o ha caducado",
        )
    return reset_token


def _update_user_password(db: Session, user: User, new_password: str, now: datetime) -> None:
    validate_password_strength(new_password)
    if verify_password(new_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La nueva contraseña debe ser diferente a la actual",
        )

    user.password_hash = hash_password(new_password)
    user.token_version += 1
    _invalidate_unused_reset_tokens(db, user.id, now)
    db.commit()
    send_email_with_attachment(
        to_email=user.email,
        subject="Tu contraseña ha cambiado",
        html_body=_build_password_changed_email_html(user.full_name),
    )


def register_user(db: Session, user_data: UserCreate):
    validate_password_strength(user_data.password)
    if not user_data.accept_terms or not user_data.accept_privacy:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debes aceptar las condiciones de uso y la politica de privacidad",
        )

    email = _normalize_email(str(user_data.email))
    phone = _normalize_phone(user_data.phone)
    if len(phone.replace("+", "")) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Indica un telefono de contacto valido",
        )

    existing_user = db.query(User).filter(func.lower(User.email) == email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un usuario con ese email",
        )

    role = db.query(Role).filter(Role.name == "buyer").first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Rol buyer no configurado en base de datos",
        )

    now = datetime.now(timezone.utc)
    user = User(
        email=email,
        full_name=user_data.full_name.strip(),
        phone=phone,
        country_code=user_data.country_code.strip().upper(),
        password_hash=hash_password(user_data.password),
        accepted_terms_at=now,
        accepted_privacy_at=now,
        marketing_consent=user_data.marketing_consent,
        marketing_consent_at=now if user_data.marketing_consent else None,
        marketing_consent_source=(
            user_data.registration_source if user_data.marketing_consent else None
        ),
        is_active=True,
        status="active",
        is_superadmin=False,
    )

    user.roles.append(role)

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def authenticate_user(db: Session, email: str, password: str):
    normalized_email = _normalize_email(email)
    user = db.query(User).filter(func.lower(User.email) == normalized_email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
        )

    if not user.is_active or user.status == "deactivated":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta cuenta está desactivada",
        )

    if not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
        )

    token = create_access_token(str(user.id), user.token_version)
    return {
        "access_token": token,
        "token_type": "bearer",
    }


def get_account_status(db: Session, email: str) -> dict[str, bool]:
    normalized_email = _normalize_email(email)
    user = (
        db.query(User.is_active, User.status)
        .filter(func.lower(User.email) == normalized_email)
        .first()
    )
    if not user:
        return {"exists": False, "can_login": False}

    return {
        "exists": True,
        "can_login": bool(user.is_active and user.status != "deactivated"),
    }


def request_forgot_password(db: Session, email: str, background_tasks=None) -> dict:
    normalized_email = _normalize_email(email)
    user = db.query(User).filter(func.lower(User.email) == normalized_email).first()
    if not user or not user.is_active or user.status == "deactivated":
        return {
            "success": True,
            "message": "Si existe una cuenta activa con ese correo, recibirás un enlace para cambiar la contraseña.",
        }

    raw_token = _create_reset_token(db, user, "reset")
    if raw_token:
        if background_tasks:
            background_tasks.add_task(_send_password_link, user, raw_token, "reset")
        else:
            _send_password_link(user, raw_token, "reset")

    return {
        "success": True,
        "message": "Si existe una cuenta activa con ese correo, recibirás un enlace para cambiar la contraseña.",
    }


def request_password_change(db: Session, user: User) -> dict:
    raw_token = _create_reset_token(db, user, "change")
    if not raw_token:
        return {
            "success": True,
            "message": "Ya te hemos enviado un enlace recientemente. Revisa tu correo.",
        }

    _send_password_link(user, raw_token, "change")
    return {
        "success": True,
        "message": "Te hemos enviado un enlace para cambiar la contraseña.",
    }


def reset_forgotten_password(
    db: Session,
    raw_token: str,
    new_password: str,
    new_password_confirm: str,
) -> dict:
    if new_password != new_password_confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Las contraseñas no coinciden",
        )

    reset_token = _get_valid_reset_token(db, raw_token, "reset")
    _update_user_password(db, reset_token.user, new_password, datetime.now(timezone.utc))
    return {"success": True, "message": "Contraseña actualizada correctamente"}


def change_password_from_link(
    db: Session,
    raw_token: str,
    current_password: str,
    new_password: str,
    new_password_confirm: str,
) -> dict:
    if new_password != new_password_confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Las contraseñas no coinciden",
        )

    reset_token = _get_valid_reset_token(db, raw_token, "change")
    user = reset_token.user
    if not verify_password(current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña actual no es correcta",
        )

    _update_user_password(db, user, new_password, datetime.now(timezone.utc))
    return {"success": True, "message": "Contraseña actualizada correctamente"}
