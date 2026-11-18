from functools import lru_cache

import boto3
from botocore.client import BaseClient
from botocore.exceptions import ClientError
from fastapi import HTTPException, status

from app.core.config import settings


@lru_cache(maxsize=1)
def get_s3_client() -> BaseClient:
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
        use_ssl=settings.s3_use_ssl,
    )


def ensure_s3_bucket() -> None:
    client = get_s3_client()
    try:
        client.head_bucket(Bucket=settings.s3_bucket)
    except ClientError:
        client.create_bucket(Bucket=settings.s3_bucket)


def put_object(key: str, contents: bytes, content_type: str) -> None:
    ensure_s3_bucket()
    get_s3_client().put_object(
        Bucket=settings.s3_bucket,
        Key=key,
        Body=contents,
        ContentType=content_type,
        CacheControl="public, max-age=31536000, immutable",
    )


def delete_object(key: str) -> None:
    get_s3_client().delete_object(Bucket=settings.s3_bucket, Key=key)


def get_object(key: str):
    try:
        return get_s3_client().get_object(Bucket=settings.s3_bucket, Key=key)
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code")
        if error_code in {"NoSuchKey", "404"}:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Archivo no encontrado",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El almacenamiento de archivos no está disponible",
        ) from exc
