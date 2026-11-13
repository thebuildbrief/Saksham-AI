"""Shared S3-compatible and local development object storage for private resumes."""
from pathlib import Path
from typing import BinaryIO
from app.core.config import secret_value, settings
from app.core.exceptions import SakshamException


def _s3_client():
    if not settings.STORAGE_S3_BUCKET:
        raise SakshamException(503, "Persistent object storage is not configured")
    try:
        import boto3
        return boto3.client(
            "s3", region_name=settings.STORAGE_S3_REGION or None,
            endpoint_url=settings.STORAGE_S3_ENDPOINT_URL or None,
            aws_access_key_id=secret_value(settings.STORAGE_S3_ACCESS_KEY_ID) or None,
            aws_secret_access_key=secret_value(settings.STORAGE_S3_SECRET_ACCESS_KEY) or None,
        )
    except Exception as exc:
        raise SakshamException(503, "Persistent object storage is unavailable") from exc


def put_object(key: str, content: bytes, content_type: str) -> None:
    provider = settings.STORAGE_PROVIDER.lower()
    if provider == "s3":
        try:
            # R2 encrypts objects at rest by default and rejects the S3 SSE header.
            _s3_client().put_object(Bucket=settings.STORAGE_S3_BUCKET, Key=key, Body=content, ContentType=content_type)
        except SakshamException:
            raise
        except Exception as exc:
            raise SakshamException(503, "Could not store the uploaded document") from exc
        return
    if provider != "local":
        raise SakshamException(503, "Configured storage provider is unsupported")
    root = Path(settings.STORAGE_LOCAL_DIR).resolve()
    path = (root / key).resolve()
    if root not in path.parents:
        raise SakshamException(400, "Invalid object key")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    except OSError as exc:
        raise SakshamException(503, "Could not store the uploaded document") from exc


def get_object(key: str) -> bytes:
    if settings.STORAGE_PROVIDER.lower() == "s3":
        try:
            return _s3_client().get_object(Bucket=settings.STORAGE_S3_BUCKET, Key=key)["Body"].read(settings.MAX_RESUME_SIZE_BYTES + 1)
        except SakshamException:
            raise
        except Exception as exc:
            raise SakshamException(404, "Stored document was not found") from exc
    path = (Path(settings.STORAGE_LOCAL_DIR).resolve() / key).resolve()
    if Path(settings.STORAGE_LOCAL_DIR).resolve() not in path.parents:
        raise SakshamException(400, "Invalid object key")
    try:
        return path.read_bytes()
    except OSError as exc:
        raise SakshamException(404, "Stored document was not found") from exc


def delete_object(key: str) -> None:
    if settings.STORAGE_PROVIDER.lower() == "s3":
        try:
            _s3_client().delete_object(Bucket=settings.STORAGE_S3_BUCKET, Key=key)
        except Exception as exc:
            raise SakshamException(503, "Could not delete stored document") from exc
        return
    path = (Path(settings.STORAGE_LOCAL_DIR).resolve() / key).resolve()
    if Path(settings.STORAGE_LOCAL_DIR).resolve() not in path.parents:
        raise SakshamException(400, "Invalid object key")
    try:
        path.unlink(missing_ok=True)
    except OSError as exc:
        raise SakshamException(503, "Could not delete stored document") from exc
