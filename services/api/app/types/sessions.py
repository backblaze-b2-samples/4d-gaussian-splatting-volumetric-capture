"""Domain types for a 4D volumetric capture Session.

A Session is the app's primary entity. Its system of record is a JSON manifest
in B2 at `sessions/<id>/manifest.json` — there is no database. These models both
validate the REST boundary (finite params are `Literal`s) and serialize straight
to the manifest.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# --- Finite option sets (selectors on the UI, Literals at the boundary) ------
ScenePreset = Literal["orbit-dancer", "bouncing-prims", "rotating-bust"]
NumCameras = Literal[4, 8, 12, 20]
FramesPerCamera = Literal[12, 24, 48]
Quality = Literal["draft", "balanced", "high"]

SCENE_PRESETS: tuple[ScenePreset, ...] = (
    "orbit-dancer",
    "bouncing-prims",
    "rotating-bust",
)
NUM_CAMERAS_OPTIONS: tuple[int, ...] = (4, 8, 12, 20)
FRAMES_PER_CAMERA_OPTIONS: tuple[int, ...] = (12, 24, 48)
QUALITY_OPTIONS: tuple[Quality, ...] = ("draft", "balanced", "high")

# Iteration budget the CUDA training tail would run per quality preset. Emitted
# in the train command; never executed on a non-CUDA host.
QUALITY_ITERATIONS: dict[str, int] = {"draft": 3000, "balanced": 14000, "high": 30000}
# Per-quality render resolution (kept deliberately small so the default demo is
# fast and its B2 footprint stays tiny).
QUALITY_RESOLUTION: dict[str, tuple[int, int]] = {
    "draft": (256, 160),
    "balanced": (384, 240),
    "high": (512, 320),
}

SessionStatus = Literal["draft", "ready", "running", "done", "failed"]
StageName = Literal["ingest", "extract", "calibrate", "stage", "train", "export"]
StageStatus = Literal["pending", "running", "done", "skipped", "failed"]
ArtifactKind = Literal[
    "video",
    "frames",
    "calibration",
    "init_cloud",
    "checkpoint",
    "model",
    "manifest",
    "preview",
    "dataset",
]

# Ordered pipeline. The train/export tail is CUDA-only and auto-gated.
PIPELINE_STAGES: tuple[StageName, ...] = (
    "ingest",
    "extract",
    "calibrate",
    "stage",
    "train",
    "export",
)


class SessionStage(BaseModel):
    name: StageName
    status: StageStatus = "pending"
    message: str = ""
    object_count: int = 0
    bytes: int = 0
    started_at: datetime | None = None
    finished_at: datetime | None = None


class SessionArtifact(BaseModel):
    kind: ArtifactKind
    key: str
    bytes: int = 0
    object_count: int = 1
    content_type: str = "application/octet-stream"
    version_id: str | None = None


class SessionMetrics(BaseModel):
    num_cameras: int = 0
    frames_per_camera: int = 0
    total_frames: int = 0
    duration_seconds: float = 0.0
    init_points: int = 0
    model_points: int = 0
    source_bytes: int = 0
    frame_bytes: int = 0
    checkpoint_bytes: int = 0
    model_bytes: int = 0
    # Derived: total derived bytes / source bytes (the write-amplification story).
    write_amplification: float = 0.0
    device: str = "cpu"
    trained: bool = False


class SessionParams(BaseModel):
    """The tunable, finite-option capture parameters shared by create/edit."""

    scene_preset: ScenePreset = "orbit-dancer"
    num_cameras: NumCameras = 4
    frames_per_camera: FramesPerCamera = 12
    quality: Quality = "draft"


class SessionCreate(SessionParams):
    name: str = Field(min_length=1, max_length=120)


class SessionUpdate(BaseModel):
    """PATCH body — every field optional. Only allowed pre-run (draft/ready)."""

    name: str | None = Field(default=None, min_length=1, max_length=120)
    scene_preset: ScenePreset | None = None
    num_cameras: NumCameras | None = None
    frames_per_camera: FramesPerCamera | None = None
    quality: Quality | None = None


class Session(BaseModel):
    id: str
    name: str
    status: SessionStatus = "draft"
    params: SessionParams
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    stages: list[SessionStage] = Field(default_factory=list)
    artifacts: list[SessionArtifact] = Field(default_factory=list)
    metrics: SessionMetrics = Field(default_factory=SessionMetrics)
    preview_key: str | None = None
    train_command: str = ""
    error: str | None = None


class StageStorage(BaseModel):
    """Per-pipeline-stage B2 footprint for the scoped storage explorer."""

    stage: str
    prefix: str
    object_count: int = 0
    bytes: int = 0
    bytes_human: str = ""


class SessionStorage(BaseModel):
    session_id: str
    stages: list[StageStorage] = Field(default_factory=list)
    source_bytes: int = 0
    derived_bytes: int = 0
    total_bytes: int = 0
    total_objects: int = 0
    write_amplification: float = 0.0


class SessionStats(BaseModel):
    """Dashboard aggregates across every session."""

    total_sessions: int = 0
    trained_sessions: int = 0
    running_sessions: int = 0
    total_frames: int = 0
    total_source_bytes: int = 0
    total_derived_bytes: int = 0
    total_bytes: int = 0
    total_bytes_human: str = ""
    avg_write_amplification: float = 0.0
