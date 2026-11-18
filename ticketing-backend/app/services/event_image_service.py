import logging
import secrets
from io import BytesIO
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.event import Event
from app.models.user import User
from app.services.event_service import get_event_by_id_internal
from app.services.object_storage_service import delete_object, put_object


ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP", "MPO"}
MAX_DIMENSION = 4096
logger = logging.getLogger(__name__)


def _is_admin(user: User) -> bool:
    return any(role.name == "admin" for role in user.roles)


def _ensure_can_manage_event_image(event: Event, user: User) -> None:
    if not _is_admin(user) and event.promoter_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes modificar la imagen de un evento que no es tuyo",
        )


def _event_upload_dir() -> Path:
    upload_dir = Path(settings.upload_dir) / "events"
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def _delete_image(image_url: str | None) -> None:
    if not image_url:
        return

    if image_url.startswith("/uploads/events/"):
        filename = image_url.rsplit("/", 1)[-1]
        target = _event_upload_dir() / filename
        if target.exists() and target.is_file():
            target.unlink()
        return

    if image_url.startswith("/media/events/"):
        delete_object(image_url.removeprefix("/media/"))


async def upload_event_image(
    db: Session,
    event_id: str,
    user: User,
    image_file: UploadFile,
) -> Event:
    event = get_event_by_id_internal(db, event_id)
    _ensure_can_manage_event_image(event, user)

    if image_file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato de imagen no permitido. Usa JPG, PNG o WEBP.",
        )

    contents = await image_file.read()
    if not contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La imagen esta vacia",
        )

    if len(contents) > settings.event_image_max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La imagen es demasiado pesada. Maximo 8 MB.",
        )

    try:
        with Image.open(BytesIO(contents)) as image:
            image.verify()
        image = Image.open(BytesIO(contents))
    except UnidentifiedImageError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo no parece ser una imagen valida",
        ) from exc

    if image.format not in ALLOWED_FORMATS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato de imagen no permitido. Usa JPG, PNG o WEBP.",
        )

    image = ImageOps.exif_transpose(image)
    image.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.Resampling.LANCZOS)

    if image.mode in {"RGBA", "LA", "P"}:
        canvas = Image.new("RGB", image.size, "#ffffff")
        if image.mode == "P":
            image = image.convert("RGBA")
        canvas.paste(image, mask=image.getchannel("A") if image.mode in {"RGBA", "LA"} else None)
        image = canvas
    else:
        image = image.convert("RGB")

    filename = f"{event.id}-{secrets.token_hex(8)}.webp"
    image_buffer = BytesIO()
    image.save(image_buffer, "WEBP", lossless=True, method=6)
    image_contents = image_buffer.getvalue()
    previous_image_url = event.image_url

    if settings.object_storage_backend == "s3":
        object_key = f"events/{filename}"
        put_object(object_key, image_contents, "image/webp")
        new_image_url = f"/media/{object_key}"
    else:
        target = _event_upload_dir() / filename
        target.write_bytes(image_contents)
        new_image_url = f"/uploads/events/{filename}"

    try:
        event.image_url = new_image_url
        db.commit()
    except Exception:
        db.rollback()
        try:
            _delete_image(new_image_url)
        except Exception as cleanup_exc:
            logger.warning("Could not clean up uncommitted event image: %s", cleanup_exc)
        raise

    try:
        _delete_image(previous_image_url)
    except Exception as exc:
        logger.warning("Could not delete previous event image: %s", exc)

    db.refresh(event)
    return event
