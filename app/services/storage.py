"""사진 스토리지 추상화 — 설정(storage_backend)으로 local/S3 전환.

원칙:
- 비밀키는 설정(.env)로만. 코드 하드코딩 금지.
- 기본은 local(앱이 /uploads 로 정적 서빙). 운영은 s3(또는 S3 호환: MinIO 등).
- boto3 는 s3 사용 시에만 lazy import → local 환경에선 미설치여도 동작.
"""
import os
import uuid

from app.core.config import get_settings

ALLOWED = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}
_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def _ext(content_type: str, filename: str) -> str:
    if content_type in ALLOWED:
        return ALLOWED[content_type]
    e = os.path.splitext(filename or "")[1].lower()
    return e if e in _EXTS else ".jpg"


def save_image(data: bytes, content_type: str = "", filename: str = "") -> str:
    """이미지 바이트를 저장하고 공개 URL을 반환한다."""
    s = get_settings()
    key = f"listings/{uuid.uuid4().hex}{_ext(content_type, filename)}"
    if s.storage_backend == "s3":
        return _save_s3(s, key, data, content_type)
    return _save_local(s, key, data)


def _save_local(s, key: str, data: bytes) -> str:
    path = os.path.join(s.upload_dir, key)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)
    return f"{s.upload_public_base.rstrip('/')}/{key}"


def _save_s3(s, key: str, data: bytes, content_type: str) -> str:
    import boto3  # s3 사용 시에만 필요

    kwargs = {}
    if s.s3_region:
        kwargs["region_name"] = s.s3_region
    if s.s3_endpoint_url:
        kwargs["endpoint_url"] = s.s3_endpoint_url
    if s.s3_access_key:
        kwargs["aws_access_key_id"] = s.s3_access_key
        kwargs["aws_secret_access_key"] = s.s3_secret_key
    client = boto3.client("s3", **kwargs)
    client.put_object(
        Bucket=s.s3_bucket, Key=key, Body=data,
        ContentType=content_type or "application/octet-stream",
    )
    if s.s3_public_base_url:
        return f"{s.s3_public_base_url.rstrip('/')}/{key}"
    if s.s3_endpoint_url:
        return f"{s.s3_endpoint_url.rstrip('/')}/{s.s3_bucket}/{key}"
    return f"https://{s.s3_bucket}.s3.{s.s3_region}.amazonaws.com/{key}"
