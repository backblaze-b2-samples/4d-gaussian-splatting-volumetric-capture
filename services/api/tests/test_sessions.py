"""Session lifecycle service + route tests — hermetic (the B2 store is mocked).

The Session manifest in B2 is the system of record, so these tests replace the
`session_store` repo boundary with an in-memory dict. That exercises the real
service rules (create defaults, edit-only-pre-run, scoped delete, storage +
stats aggregation) and the REST routes without any network.
"""

from __future__ import annotations

import pytest

from app.service import sessions as svc
from app.service.sessions import (
    SessionNotFoundError,
    SessionStateError,
    create_session,
    delete_session,
    get_storage,
    update_session,
)
from app.types.sessions import SessionCreate, SessionUpdate


@pytest.fixture
def store(monkeypatch):
    """In-memory replacement for the B2-backed session_store."""
    manifests: dict[str, dict] = {}

    def put_manifest(session_id: str, manifest: dict):
        manifests[session_id] = manifest
        return None

    def get_manifest(session_id: str):
        return manifests.get(session_id)

    def list_manifests():
        return list(manifests.values())

    def delete_session_objects(session_id: str):
        manifests.pop(session_id, None)
        return 7

    monkeypatch.setattr(svc, "put_manifest", put_manifest)
    monkeypatch.setattr(svc, "get_manifest", get_manifest)
    monkeypatch.setattr(svc, "list_manifests", list_manifests)
    monkeypatch.setattr(svc, "delete_session_objects", delete_session_objects)
    return manifests


def test_create_sets_draft_defaults(store):
    session = create_session(
        SessionCreate(name="  Studio take 1  ", scene_preset="orbit-dancer",
                      num_cameras=4, frames_per_camera=12, quality="draft")
    )
    assert session.status == "draft"
    assert session.name == "Studio take 1"  # trimmed
    assert session.params.num_cameras == 4
    # Every pipeline stage is present and pending.
    assert [s.name for s in session.stages] == [
        "ingest", "extract", "calibrate", "stage", "train", "export"
    ]
    assert all(s.status == "pending" for s in session.stages)
    assert session.metrics.num_cameras == 4
    assert session.id in store


def test_edit_allowed_pre_run(store):
    session = create_session(
        SessionCreate(name="A", scene_preset="orbit-dancer", num_cameras=4,
                      frames_per_camera=12, quality="draft")
    )
    updated = update_session(session.id, SessionUpdate(num_cameras=8, quality="high"))
    assert updated.params.num_cameras == 8
    assert updated.params.quality == "high"
    assert updated.metrics.num_cameras == 8


def test_edit_locked_after_run(store):
    session = create_session(
        SessionCreate(name="A", scene_preset="orbit-dancer", num_cameras=4,
                      frames_per_camera=12, quality="draft")
    )
    # Simulate a completed run.
    session.status = "done"
    svc.put_manifest(session.id, session.model_dump(mode="json"))

    with pytest.raises(SessionStateError):
        update_session(session.id, SessionUpdate(num_cameras=20))


def test_delete_unknown_is_not_found(store):
    with pytest.raises(SessionNotFoundError):
        delete_session("does-not-exist")


def test_delete_returns_object_count(store):
    session = create_session(
        SessionCreate(name="A", scene_preset="orbit-dancer", num_cameras=4,
                      frames_per_camera=12, quality="draft")
    )
    removed = delete_session(session.id)
    assert removed == 7
    assert session.id not in store


def test_storage_write_amplification(store, monkeypatch):
    session = create_session(
        SessionCreate(name="A", scene_preset="orbit-dancer", num_cameras=4,
                      frames_per_camera=12, quality="draft")
    )
    rows = [
        {"stage": "source video", "prefix": "captures/x/", "object_count": 4, "bytes": 1000},
        {"stage": "frames", "prefix": "frames/x/", "object_count": 48, "bytes": 4000},
        {"stage": "model", "prefix": "models/x/", "object_count": 1, "bytes": 1000},
    ]
    monkeypatch.setattr(svc, "storage_breakdown", lambda sid: rows)

    storage = get_storage(session.id)
    assert storage.source_bytes == 1000
    assert storage.total_bytes == 6000
    assert storage.derived_bytes == 5000
    # Canonical write-amplification = derived / source = 5000 / 1000 = 5.0
    # (the source→derived fan-out multiplier). Same formula the runner records
    # in metrics.write_amplification, so the detail card and dashboard agree.
    assert storage.write_amplification == 5.0
    assert storage.total_objects == 53


def test_finalize_and_storage_write_amplification_agree(store, monkeypatch):
    """The per-session detail card (get_storage) and the dashboard cards/avg
    (metrics.write_amplification, set by the runner's _finalize) must compute
    write-amplification the SAME way: derived / source."""
    from app.service.session_runner import _finalize
    from app.types.sessions import SessionArtifact

    session = create_session(
        SessionCreate(name="A", scene_preset="orbit-dancer", num_cameras=4,
                      frames_per_camera=12, quality="draft")
    )
    # source = 1000; derived = frames(4000) + one dataset artifact(1000) = 5000.
    session.metrics.source_bytes = 1000
    session.metrics.frame_bytes = 4000
    session.artifacts = [SessionArtifact(kind="dataset", key="k", bytes=1000)]
    _finalize(session)
    # derived / source = 5000 / 1000 = 5.0 — matches get_storage above.
    assert session.metrics.write_amplification == 5.0


@pytest.mark.asyncio
async def test_create_and_list_via_routes(client, store):
    resp = await client.post(
        "/sessions",
        json={"name": "Route session", "scene_preset": "orbit-dancer",
              "num_cameras": 4, "frames_per_camera": 12, "quality": "draft"},
    )
    assert resp.status_code == 201
    created = resp.json()
    assert created["status"] == "draft"

    listed = await client.get("/sessions")
    assert listed.status_code == 200
    assert any(s["id"] == created["id"] for s in listed.json())


@pytest.mark.asyncio
async def test_get_missing_session_404(client, store):
    resp = await client.get("/sessions/nope")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_rejects_bad_enum(client, store):
    resp = await client.post(
        "/sessions",
        json={"name": "Bad", "scene_preset": "orbit-dancer",
              "num_cameras": 5, "frames_per_camera": 12, "quality": "draft"},
    )
    # 5 is not one of the finite NumCameras Literals — validated at the boundary.
    assert resp.status_code == 422
