"""The Session run pipeline: ingest -> extract -> calibrate -> stage -> train.

Runs in a background thread (spawned by the run route) and persists the manifest
after every stage, so the detail page's poll shows live progress. All CPU-side
stages run for real everywhere; the CUDA-only train/export tail auto-gates via
`fourdgs_runner` and is marked "skipped (CUDA required)" on a non-CUDA host —
the trained splat is never faked and the run never 500s.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from app.repo import artifacts, calibration, frames, preview, session_store, synthetic
from app.repo.b2_object import get_object_bytes
from app.service import fourdgs_runner
from app.service.sessions import load_session, save_session
from app.types.sessions import QUALITY_RESOLUTION, Session, SessionArtifact

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(UTC)


def _stage(session: Session, name: str):
    return next(s for s in session.stages if s.name == name)


def _start(session: Session, name: str) -> None:
    stage = _stage(session, name)
    stage.status = "running"
    stage.started_at = _now()
    save_session(session)


def _finish(session: Session, name: str, *, status: str, message: str,
            objects: int = 0, nbytes: int = 0) -> None:
    stage = _stage(session, name)
    stage.status = status
    stage.message = message
    stage.object_count = objects
    stage.bytes = nbytes
    stage.finished_at = _now()
    save_session(session)


def _add_artifact(session: Session, kind: str, key: str, ref: dict | None = None,
                  objects: int = 1) -> int:
    nbytes = ref["bytes"] if ref else 0
    session.artifacts.append(
        SessionArtifact(
            kind=kind, key=key, bytes=nbytes, object_count=objects,
            content_type=(ref or {}).get("content_type", "application/octet-stream"),
            version_id=(ref or {}).get("version_id"),
        )
    )
    return nbytes


def begin_run(session_id: str) -> Session:
    """Reset the manifest and mark the session running, persisting immediately.

    `POST /sessions/{id}/run` calls this synchronously *before* it responds, so a
    poll issued right after the response already reads "running" (not the stale
    pre-run manifest). `run_pipeline` then executes the stages on a background
    thread. Splitting the begin from the pipeline body is what lets the detail
    page transition into live polling without a manual reload.
    """
    session = load_session(session_id)
    if session is None:
        raise ValueError(f"session {session_id} not found")

    session.status = "running"
    session.started_at = _now()
    session.finished_at = None
    session.error = None
    session.artifacts = []
    for stage in session.stages:
        stage.status = "pending"
        stage.message = ""
        stage.object_count = 0
        stage.bytes = 0
        stage.started_at = None
        stage.finished_at = None
    save_session(session)
    return session


def run_pipeline(session_id: str) -> Session:
    """Execute every pipeline stage for an already-begun session.

    Loads a fresh manifest (so it never shares mutable state with the object the
    run route serialized in its response) and never raises to the caller — any
    stage failure is contained in the manifest.
    """
    session = load_session(session_id)
    if session is None:
        raise ValueError(f"session {session_id} not found")
    try:
        width, height = QUALITY_RESOLUTION[session.params.quality]
        cameras = calibration.generate_cameras(
            session.params.num_cameras, width, height
        )
        videos = _run_ingest(session, cameras)
        _run_extract(session, videos)
        init_xyz, init_rgb = _run_calibrate(session, cameras)
        _run_stage(session, cameras, videos, init_xyz, init_rgb)
        _run_train_export(session)
        _finalize(session)
    except Exception as exc:  # contain any stage failure in the manifest
        logger.exception("Session %s pipeline failed", session_id)
        session.status = "failed"
        session.error = str(exc)
        session.finished_at = _now()
        save_session(session)
    return session


def _run_ingest(session: Session, cameras: list[dict]) -> dict[str, bytes]:
    _start(session, "ingest")
    existing = session_store.list_captures(session.id)
    videos: dict[str, bytes] = {}
    total = 0
    if existing:
        # Real footage was ingested — pull each source video back for extraction.
        for obj in existing:
            cam_id = obj["Key"].split("/")[2]
            videos[cam_id] = get_object_bytes(obj["Key"])
            total += obj["Size"]
    else:
        # Synthesize a license-clean multi-view capture and upload per-camera MP4s.
        rendered = synthetic.render_scene(
            session.params.scene_preset, cameras, session.params.frames_per_camera
        )
        for cam_id, cam_frames in rendered.items():
            mp4 = frames.encode_video(cam_frames, fps=min(session.params.frames_per_camera, 24))
            key = f"{session_store.captures_prefix(session.id)}{cam_id}/source.mp4"
            ref = artifacts.put_bytes(key, mp4, "video/mp4")
            videos[cam_id] = mp4
            total += _add_artifact(session, "video", key, ref)
    session.metrics.source_bytes = total
    session.status = "running"
    _finish(session, "ingest", status="done",
            message=f"{len(videos)} camera stream(s)", objects=len(videos), nbytes=total)
    return videos


def _run_extract(session: Session, videos: dict[str, bytes]) -> None:
    _start(session, "extract")
    total_frames = 0
    total_bytes = 0
    for cam_id, mp4 in videos.items():
        jpegs = frames.extract_frames(mp4, session.params.frames_per_camera)
        for i, jpg in enumerate(jpegs):
            key = f"{session_store.frames_prefix(session.id)}{cam_id}/frame_{i + 1:04d}.jpg"
            ref = artifacts.put_bytes(key, jpg, "image/jpeg")
            total_bytes += ref["bytes"]
            total_frames += 1
    session.metrics.total_frames = total_frames
    session.metrics.frame_bytes = total_bytes
    _add_artifact(session, "frames", session_store.frames_prefix(session.id),
                  {"bytes": total_bytes}, objects=total_frames)
    _finish(session, "extract", status="done",
            message=f"{total_frames} frames via ffmpeg", objects=total_frames, nbytes=total_bytes)


def _run_calibrate(session: Session, cameras: list[dict]):
    _start(session, "calibrate")
    cams_key = f"{session_store.calibration_prefix(session.id)}cameras.json"
    cams_ref = artifacts.put_text(cams_key, json.dumps(calibration.cameras_json(cameras)))
    ply_bytes, xyz, rgb = calibration.init_point_cloud()
    ply_key = f"{session_store.calibration_prefix(session.id)}points3D.ply"
    ply_ref = artifacts.put_bytes(ply_key, ply_bytes, "application/octet-stream")
    nbytes = _add_artifact(session, "calibration", cams_key, cams_ref)
    nbytes += _add_artifact(session, "init_cloud", ply_key, ply_ref)
    session.metrics.init_points = len(xyz)
    _finish(session, "calibrate", status="done",
            message=f"{len(cameras)} poses, {len(xyz)}-point init cloud",
            objects=2, nbytes=nbytes)
    return xyz, rgb


def _run_stage(session: Session, cameras: list[dict], videos: dict[str, bytes],
               init_xyz, init_rgb) -> None:
    _start(session, "stage")
    dataset = {
        "format": "multipleview",
        "session_id": session.id,
        "cameras": [c["id"] for c in cameras],
        "frames_prefix": session_store.frames_prefix(session.id),
        "calibration": f"{session_store.calibration_prefix(session.id)}cameras.json",
        "init_cloud": f"{session_store.calibration_prefix(session.id)}points3D.ply",
        "frames_per_camera": session.params.frames_per_camera,
    }
    ds_key = f"{session_store.dataset_prefix(session.id)}dataset.json"
    ds_ref = artifacts.put_text(ds_key, json.dumps(dataset, indent=2))
    nbytes = _add_artifact(session, "dataset", ds_key, ds_ref)

    # Preview PNG: one representative frame per camera + the init-cloud scatter.
    first_frames = {
        cam_id: frames.extract_frames(mp4, 1)[0] for cam_id, mp4 in videos.items()
    }
    png = preview.render_preview(first_frames, init_xyz, init_rgb)
    preview_key = f"{session_store.previews_prefix(session.id)}contact_sheet.png"
    png_ref = artifacts.put_bytes(preview_key, png, "image/png")
    nbytes += _add_artifact(session, "preview", preview_key, png_ref)
    session.preview_key = preview_key

    # The exact 4DGaussians command the CUDA tail would run against this dataset.
    local_dir = f"data/multipleview/{session.id}"
    session.train_command = fourdgs_runner.train_command_str(
        local_dir, session.id, session.params.quality
    )
    _finish(session, "stage", status="done",
            message="multipleview dataset staged on B2", objects=2, nbytes=nbytes)


def _run_train_export(session: Session) -> None:
    _start(session, "train")
    device = fourdgs_runner.detect_device()
    session.metrics.device = device
    local_dir = f"data/multipleview/{session.id}"
    try:
        result = fourdgs_runner.run_training(local_dir, session.id, session.params.quality)
    except fourdgs_runner.EngineUnavailableError as exc:
        gated = f"skipped (CUDA required) — run: {exc.command}"
        _finish(session, "train", status="skipped", message=gated)
        _finish(session, "export", status="skipped", message="skipped (CUDA required)")
        session.metrics.trained = False
        return
    # CUDA host: real checkpoints/model were produced by the engine subprocess.
    _finish(session, "train", status="done", message=f"trained on {device}")
    _start(session, "export")
    session.metrics.trained = True
    _finish(session, "export", status="done",
            message=f"exported from {result['output_dir']}")


def _finalize(session: Session) -> None:
    derived = (
        session.metrics.frame_bytes
        + session.metrics.checkpoint_bytes
        + session.metrics.model_bytes
        + sum(a.bytes for a in session.artifacts if a.kind in ("calibration", "init_cloud", "dataset", "preview"))
    )
    src = session.metrics.source_bytes
    session.metrics.write_amplification = round(derived / src, 2) if src else 0.0
    session.status = "done"
    session.finished_at = _now()
    save_session(session)
