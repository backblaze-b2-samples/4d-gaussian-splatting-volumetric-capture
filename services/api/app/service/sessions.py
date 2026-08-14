"""Session lifecycle service — manifest CRUD, dashboard stats, scoped storage.

The Session manifest in B2 is the system of record; this layer validates the
lifecycle rules (edit only pre-run, etc.) and shapes the dashboard/storage
aggregates. It calls the repo layer for all B2 I/O and holds no boto3 itself.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.repo.session_store import (
    delete_session_objects,
    get_manifest,
    list_manifests,
    put_manifest,
    storage_breakdown,
)
from app.types.formatting import humanize_bytes
from app.types.sessions import (
    PIPELINE_STAGES,
    Session,
    SessionCreate,
    SessionParams,
    SessionStage,
    SessionStats,
    SessionStorage,
    SessionUpdate,
    StageStorage,
)

# Params fixed once a run has started (they change the dataset that was staged).
_PRE_RUN_STATES = {"draft", "ready"}


class SessionNotFoundError(Exception):
    def __init__(self, detail: str = "Session not found"):
        self.detail = detail
        super().__init__(detail)


class SessionStateError(Exception):
    """Raised when an operation is illegal for the session's current status."""

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


def _now() -> datetime:
    return datetime.now(UTC)


def load_session(session_id: str) -> Session | None:
    data = get_manifest(session_id)
    return Session.model_validate(data) if data else None


def save_session(session: Session) -> None:
    session.updated_at = _now()
    put_manifest(session.id, session.model_dump(mode="json"))


def get_session(session_id: str) -> Session:
    session = load_session(session_id)
    if session is None:
        raise SessionNotFoundError()
    return session


def list_sessions() -> list[Session]:
    sessions = [Session.model_validate(m) for m in list_manifests()]
    sessions.sort(key=lambda s: s.created_at, reverse=True)
    return sessions


def create_session(payload: SessionCreate) -> Session:
    now = _now()
    params = SessionParams(
        scene_preset=payload.scene_preset,
        num_cameras=payload.num_cameras,
        frames_per_camera=payload.frames_per_camera,
        quality=payload.quality,
    )
    session = Session(
        id=uuid.uuid4().hex[:12],
        name=payload.name.strip(),
        status="draft",
        params=params,
        created_at=now,
        updated_at=now,
        stages=[SessionStage(name=name) for name in PIPELINE_STAGES],
    )
    session.metrics.num_cameras = params.num_cameras
    session.metrics.frames_per_camera = params.frames_per_camera
    put_manifest(session.id, session.model_dump(mode="json"))
    return session


def update_session(session_id: str, patch: SessionUpdate) -> Session:
    session = get_session(session_id)
    if session.status not in _PRE_RUN_STATES:
        raise SessionStateError(
            "Capture parameters are locked once a session has run. "
            "Create a new session to change them."
        )
    data = patch.model_dump(exclude_none=True)
    if "name" in data:
        session.name = data.pop("name").strip()
    if data:
        session.params = session.params.model_copy(update=data)
        session.metrics.num_cameras = session.params.num_cameras
        session.metrics.frames_per_camera = session.params.frames_per_camera
    save_session(session)
    return session


def delete_session(session_id: str) -> int:
    # Confirm it exists so a delete of an unknown id is a clean 404, not a no-op.
    get_session(session_id)
    return delete_session_objects(session_id)


def get_storage(session_id: str) -> SessionStorage:
    """Per-stage B2 footprint + the write-amplification breakdown for one session."""
    get_session(session_id)
    rows = storage_breakdown(session_id)
    stages = [
        StageStorage(
            stage=r["stage"],
            prefix=r["prefix"],
            object_count=r["object_count"],
            bytes=r["bytes"],
            bytes_human=humanize_bytes(r["bytes"]),
        )
        for r in rows
    ]
    source_bytes = next(
        (r["bytes"] for r in rows if r["stage"] == "source video"), 0
    )
    total_bytes = sum(r["bytes"] for r in rows)
    total_objects = sum(r["object_count"] for r in rows)
    derived_bytes = total_bytes - source_bytes
    # Canonical write-amplification = derived / source (the source→derived
    # fan-out multiplier). This is the SAME formula the runner records in
    # `metrics.write_amplification` (session_runner._finalize) and that drives
    # the dashboard cards + average, so the detail card and dashboard agree.
    amp = (derived_bytes / source_bytes) if source_bytes else 0.0
    return SessionStorage(
        session_id=session_id,
        stages=stages,
        source_bytes=source_bytes,
        derived_bytes=derived_bytes,
        total_bytes=total_bytes,
        total_objects=total_objects,
        write_amplification=round(amp, 2),
    )


def get_stats() -> SessionStats:
    sessions = list_sessions()
    total_source = sum(s.metrics.source_bytes for s in sessions)
    total_derived = sum(
        s.metrics.frame_bytes + s.metrics.checkpoint_bytes + s.metrics.model_bytes
        for s in sessions
    )
    amps = [s.metrics.write_amplification for s in sessions if s.metrics.write_amplification]
    total_bytes = total_source + total_derived
    return SessionStats(
        total_sessions=len(sessions),
        trained_sessions=sum(1 for s in sessions if s.metrics.trained),
        running_sessions=sum(1 for s in sessions if s.status == "running"),
        total_frames=sum(s.metrics.total_frames for s in sessions),
        total_source_bytes=total_source,
        total_derived_bytes=total_derived,
        total_bytes=total_bytes,
        total_bytes_human=humanize_bytes(total_bytes),
        avg_write_amplification=round(sum(amps) / len(amps), 2) if amps else 0.0,
    )
