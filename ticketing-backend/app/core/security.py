from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
PASSWORD_MIN_LENGTH = 12


def get_password_validation_error(password: str) -> str | None:
    if len(password) < PASSWORD_MIN_LENGTH:
        return f"La contraseña debe tener al menos {PASSWORD_MIN_LENGTH} caracteres"
    if not any(character.islower() for character in password):
        return "La contraseña debe incluir al menos una minúscula"
    if not any(character.isupper() for character in password):
        return "La contraseña debe incluir al menos una mayúscula"
    if not any(character.isdigit() for character in password):
        return "La contraseña debe incluir al menos un número"
    if not any(not character.isalnum() for character in password):
        return "La contraseña debe incluir al menos un carácter especial"
    return None


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(subject: str, token_version: int = 0) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": subject,
        "ver": token_version,
        "exp": expire,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError:
        return None
