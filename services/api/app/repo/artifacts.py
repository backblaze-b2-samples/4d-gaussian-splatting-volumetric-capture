"""Write and presign derived session artifacts on B2.

Kept apart from `session_store` (manifest CRUD) to stay under the 300-line file
ceiling. boto3 lives only in repo/, so both modules belong here. Large objects
(source video, multi-GB checkpoints) go through boto3's managed multipart
`upload_fileobj` + `TransferConfig`; small objects use a plain `put_object`.
"""

from __future__ import annotations

import io

from boto3.s3.transfer import TransferConfig
from botocore.exceptions import ClientError

from app.config import settings
from app.repo.b2_client import get_s3_client
from app.repo.list_cache import invalidate as _invalidate_list_cache

# Objects at or above this size use boto3's managed multipart upload. Matches
# boto3's own default multipart threshold; documented in ARCHITECTURE.md as the
# large-object path for source video and training checkpoints.
_MULTIPART_THRESHOLD = 8 * 1024 * 1024
_TRANSFER = TransferConfig(multipart_threshold=_MULTIPART_THRESHOLD)


def put_bytes(key: str, data: bytes, content_type: str) -> dict:
    """Upload derived bytes to B2. Returns {key, bytes, version_id, content_type}.

    Routes large objects through managed multipart so a multi-GB checkpoint
    streams in parts instead of buffering a single giant PUT.
    """
    client = get_s3_client()
    try:
        if len(data) >= _MULTIPART_THRESHOLD:
            client.upload_fileobj(
                io.BytesIO(data),
                settings.b2_bucket_name,
                key,
                ExtraArgs={"ContentType": content_type},
                Config=_TRANSFER,
            )
            version_id = _head_version(client, key)
        else:
            response = client.put_object(
                Bucket=settings.b2_bucket_name,
                Key=key,
                Body=data,
                ContentType=content_type,
            )
            version_id = response.get("VersionId")
    except ClientError as e:
        raise RuntimeError(f"B2 artifact write failed for '{key}': {e}") from e
    _invalidate_list_cache()
    return {
        "key": key,
        "bytes": len(data),
        "version_id": version_id,
        "content_type": content_type,
    }


def put_text(key: str, text: str, content_type: str = "application/json") -> dict:
    return put_bytes(key, text.encode("utf-8"), content_type)


def _head_version(client, key: str) -> str | None:
    try:
        return client.head_object(
            Bucket=settings.b2_bucket_name, Key=key
        ).get("VersionId")
    except ClientError:
        return None


def presign_get(key: str, expires_in: int = 900) -> str:
    """Short-lived presigned GET so a rendering client can pull an artifact."""
    client = get_s3_client()
    try:
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.b2_bucket_name, "Key": key},
            ExpiresIn=expires_in,
        )
    except ClientError as e:
        raise RuntimeError(f"B2 presign failed for '{key}': {e}") from e
