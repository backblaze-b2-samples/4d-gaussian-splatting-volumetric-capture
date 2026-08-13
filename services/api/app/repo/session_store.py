"""B2 persistence for Sessions — manifest CRUD, scoped delete, storage stats.

The Session manifest at `sessions/<id>/manifest.json` is the system of record
(no database). boto3/botocore stay confined to this repo/ layer; the shared S3
client is reused from `b2_client` for connection pooling.

Every user-facing prefix is named for the use case so the bucket reads like the
pipeline: source video under `captures/`, extracted frames under `frames/`, and
so on. All of a session's objects hang off its id, which is how the scoped
delete stays strictly inside one session.
"""

from __future__ import annotations

import json

from botocore.exceptions import ClientError

from app.config import settings
from app.repo.b2_client import get_s3_client
from app.repo.list_cache import invalidate as _invalidate_list_cache


def manifest_key(session_id: str) -> str:
    return f"sessions/{session_id}/manifest.json"


def captures_prefix(session_id: str) -> str:
    return f"captures/{session_id}/"


def frames_prefix(session_id: str) -> str:
    return f"frames/{session_id}/"


def calibration_prefix(session_id: str) -> str:
    return f"calibration/{session_id}/"


def dataset_prefix(session_id: str) -> str:
    return f"dataset/{session_id}/"


def checkpoints_prefix(session_id: str) -> str:
    return f"checkpoints/{session_id}/"


def models_prefix(session_id: str) -> str:
    return f"models/{session_id}/"


def previews_prefix(session_id: str) -> str:
    return f"previews/{session_id}/"


# (stage label shown in the scoped storage explorer, prefix builder). Ordered
# to read as the pipeline fan-out: source video -> frames -> ... -> model.
STAGE_PREFIXES: tuple[tuple[str, object], ...] = (
    ("source video", captures_prefix),
    ("frames", frames_prefix),
    ("calibration", calibration_prefix),
    ("dataset", dataset_prefix),
    ("checkpoints", checkpoints_prefix),
    ("model", models_prefix),
    ("preview", previews_prefix),
)

# Everything owned by one session — used by the strictly-scoped delete.
def _all_session_prefixes(session_id: str) -> list[str]:
    return [
        captures_prefix(session_id),
        frames_prefix(session_id),
        calibration_prefix(session_id),
        dataset_prefix(session_id),
        checkpoints_prefix(session_id),
        models_prefix(session_id),
        previews_prefix(session_id),
        f"sessions/{session_id}/",
    ]


def list_captures(session_id: str) -> list[dict]:
    """Every source-video object already ingested for a session."""
    return _list_prefix(captures_prefix(session_id))


def _list_prefix(prefix: str) -> list[dict]:
    """Every object under `prefix` (paginated). Raises RuntimeError on failure."""
    client = get_s3_client()
    contents: list[dict] = []
    kwargs: dict = {"Bucket": settings.b2_bucket_name, "Prefix": prefix, "MaxKeys": 1000}
    try:
        while True:
            response = client.list_objects_v2(**kwargs)
            contents.extend(response.get("Contents", []))
            if not response.get("IsTruncated"):
                break
            kwargs["ContinuationToken"] = response["NextContinuationToken"]
    except ClientError as e:
        raise RuntimeError(f"B2 list failed for '{prefix}': {e}") from e
    return contents


def put_manifest(session_id: str, manifest: dict) -> str | None:
    """Write the session manifest JSON to B2. Returns its version id if any."""
    client = get_s3_client()
    body = json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8")
    try:
        response = client.put_object(
            Bucket=settings.b2_bucket_name,
            Key=manifest_key(session_id),
            Body=body,
            ContentType="application/json",
        )
    except ClientError as e:
        raise RuntimeError(f"B2 manifest write failed for '{session_id}': {e}") from e
    _invalidate_list_cache()
    return response.get("VersionId")


def get_manifest(session_id: str) -> dict | None:
    """Read a session manifest, or None if it does not exist."""
    client = get_s3_client()
    try:
        response = client.get_object(
            Bucket=settings.b2_bucket_name, Key=manifest_key(session_id)
        )
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchKey"):
            return None
        raise RuntimeError(f"B2 manifest read failed for '{session_id}': {e}") from e
    return json.loads(response["Body"].read())


def list_manifests() -> list[dict]:
    """Every session manifest in the bucket (one GET per manifest object)."""
    client = get_s3_client()
    manifests: list[dict] = []
    for obj in _list_prefix("sessions/"):
        if not obj["Key"].endswith("/manifest.json"):
            continue
        try:
            response = client.get_object(Bucket=settings.b2_bucket_name, Key=obj["Key"])
            manifests.append(json.loads(response["Body"].read()))
        except (ClientError, ValueError):
            # A malformed or racing-deleted manifest must not sink the list.
            continue
    return manifests


def delete_session_objects(session_id: str) -> int:
    """Delete EVERY object under this one session's prefixes. Returns the count.

    Strictly scoped: only keys under `<prefix>/<session_id>/` are touched, so a
    session delete can never reach another session's or another app's data.
    """
    client = get_s3_client()
    deleted = 0
    for prefix in _all_session_prefixes(session_id):
        keys = [{"Key": o["Key"]} for o in _list_prefix(prefix)]
        for i in range(0, len(keys), 1000):
            batch = keys[i : i + 1000]
            if not batch:
                continue
            try:
                client.delete_objects(
                    Bucket=settings.b2_bucket_name, Delete={"Objects": batch}
                )
            except ClientError as e:
                raise RuntimeError(f"B2 delete failed for '{prefix}': {e}") from e
            deleted += len(batch)
    _invalidate_list_cache()
    return deleted


def storage_breakdown(session_id: str) -> list[dict]:
    """Per-stage object counts + bytes for the scoped storage explorer."""
    rows: list[dict] = []
    for label, prefix_fn in STAGE_PREFIXES:
        prefix = prefix_fn(session_id)  # type: ignore[operator]
        objs = _list_prefix(prefix)
        rows.append(
            {
                "stage": label,
                "prefix": prefix,
                "object_count": len(objs),
                "bytes": sum(o["Size"] for o in objs),
            }
        )
    return rows
