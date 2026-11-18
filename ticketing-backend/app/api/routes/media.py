from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.services.object_storage_service import get_object


router = APIRouter(prefix="/media", tags=["media"])


@router.get("/{object_key:path}")
def get_media_object(object_key: str):
    if settings.object_storage_backend != "s3" or not object_key.startswith("events/"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Archivo no encontrado",
        )

    stored_object = get_object(object_key)
    headers = {
        "Cache-Control": stored_object.get(
            "CacheControl",
            "public, max-age=31536000, immutable",
        )
    }
    if stored_object.get("ETag"):
        headers["ETag"] = stored_object["ETag"]

    return StreamingResponse(
        stored_object["Body"].iter_chunks(),
        media_type=stored_object.get("ContentType", "application/octet-stream"),
        headers=headers,
    )
