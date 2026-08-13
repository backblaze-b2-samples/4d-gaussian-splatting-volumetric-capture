"""REST routes for the Session lifecycle: create/read/update/delete/run + ingest.

Sync `def` handlers so blocking B2 work runs in Starlette's threadpool (see
runtime/files.py). The run route kicks the pipeline onto a background thread and
returns immediately; the client polls the detail endpoint for live progress.

SECURITY: like the rest of the starter these routes are UNAUTHENTICATED and
bucket-wide (single-tenant demo stance — see docs/SECURITY.md). A multi-tenant
clone must add auth AND scope every session to its owner.
"""

from __future__ import annotations

import logging
import threading

from fastapi import APIRouter, HTTPException

from app.config import settings
from app.repo import generate_presigned_upload
from app.service.session_runner import run_session
from app.service.sessions import (
    SessionNotFoundError,
    SessionStateError,
    create_session,
    delete_session,
    get_session,
    get_stats,
    get_storage,
    list_sessions,
    update_session,
)
from app.service.upload import sanitize_filename
from app.types import (
    PresignUploadResponse,
    Session,
    SessionCreate,
    SessionStats,
    SessionStorage,
    SessionUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter()

_VIDEO_TYPES = {"video/mp4", "video/quicktime", "video/webm"}


def _spawn(session_id: str) -> None:
    """Run the pipeline on a daemon thread (patched out in unit tests)."""
    threading.Thread(target=run_session, args=(session_id,), daemon=True).start()


@router.post("/sessions", response_model=Session, status_code=201)
def create_session_endpoint(payload: SessionCreate):
    return create_session(payload)


@router.get("/sessions", response_model=list[Session])
def list_sessions_endpoint():
    return list_sessions()


@router.get("/sessions/stats", response_model=SessionStats)
def session_stats_endpoint():
    return get_stats()


@router.get("/sessions/{session_id}", response_model=Session)
def get_session_endpoint(session_id: str):
    try:
        return get_session(session_id)
    except SessionNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail) from None


@router.patch("/sessions/{session_id}", response_model=Session)
def update_session_endpoint(session_id: str, patch: SessionUpdate):
    try:
        return update_session(session_id, patch)
    except SessionNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail) from None
    except SessionStateError as e:
        raise HTTPException(status_code=409, detail=e.detail) from None


@router.delete("/sessions/{session_id}")
def delete_session_endpoint(session_id: str):
    try:
        deleted = delete_session(session_id)
    except SessionNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail) from None
    except RuntimeError:
        raise HTTPException(status_code=502, detail="Failed to delete session") from None
    logger.info("Session deleted: id=%s objects=%d", session_id, deleted)
    return {"deleted": True, "id": session_id, "objects_removed": deleted}


@router.post("/sessions/{session_id}/run", response_model=Session)
def run_session_endpoint(session_id: str):
    try:
        session = get_session(session_id)
    except SessionNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail) from None
    if session.status == "running":
        raise HTTPException(status_code=409, detail="Session is already running")
    _spawn(session_id)
    session.status = "running"
    return session


@router.get("/sessions/{session_id}/storage", response_model=SessionStorage)
def session_storage_endpoint(session_id: str):
    try:
        return get_storage(session_id)
    except SessionNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail) from None


@router.post("/sessions/{session_id}/ingest", response_model=PresignUploadResponse)
def ingest_session_endpoint(session_id: str, req: dict):
    """Presign a direct-to-B2 PUT for one camera's source video (supporting verb).

    The browser uploads bytes straight to `captures/<id>/<camera>/<file>`; the
    run pipeline then extracts frames from whatever source video is present.
    """
    try:
        get_session(session_id)
    except SessionNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail) from None

    camera_id = str(req.get("camera_id", "")).strip()
    filename = sanitize_filename(str(req.get("filename", "")))
    content_type = str(req.get("content_type", ""))
    size_bytes = int(req.get("size_bytes", 0) or 0)
    if not camera_id or not filename:
        raise HTTPException(status_code=400, detail="camera_id and filename are required")
    if content_type not in _VIDEO_TYPES:
        raise HTTPException(status_code=415, detail="Source must be an MP4/MOV/WebM video")
    if size_bytes <= 0:
        raise HTTPException(status_code=400, detail="Empty file")

    key = f"captures/{session_id}/{camera_id}/{filename}"
    expires_in = settings.presign_upload_expiry_seconds
    url = generate_presigned_upload(key, content_type, size_bytes, expires_in)
    return PresignUploadResponse(
        key=key,
        url=url,
        method="PUT",
        content_type=content_type,
        headers={"Content-Type": content_type},
        expires_in=expires_in,
    )
