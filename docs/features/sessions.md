<!-- last_verified: 2026-08-13 -->
# Feature: Sessions & lifecycle

## Purpose
A **Session** is the app's primary entity — a 4D volumetric capture. Its system of record is
a JSON manifest in B2 (`sessions/<id>/manifest.json`), so the full lifecycle runs against
object storage with no database.

## Used By
- UI: `/sessions` (library grid), `/sessions/new` (create), `/sessions/[id]` (detail),
  `/sessions/[id]/edit` (edit)
- API: `POST /sessions`, `GET /sessions`, `GET /sessions/stats`, `GET /sessions/{id}`,
  `PATCH /sessions/{id}`, `DELETE /sessions/{id}`, `POST /sessions/{id}/run`,
  `GET /sessions/{id}/storage`, `POST /sessions/{id}/ingest`

## Core Functions
- `service/sessions.py` — manifest CRUD, edit-only-pre-run rule, storage + stats aggregation
- `service/session_runner.py` — background run pipeline (stage orchestration + B2 I/O)
- `repo/session_store.py` — B2 manifest read/write, scoped delete, per-stage listing
- `types/sessions.py` — finite `Literal` params, stages, artifacts, metrics, storage models

## Canonical Files
- Routes: `services/api/app/runtime/sessions.py`
- Service: `services/api/app/service/sessions.py`
- Store: `services/api/app/repo/session_store.py`
- Form: `apps/web/src/components/sessions/session-form.tsx`

## Inputs
- `name`: string (create/edit)
- `scene_preset`: `orbit-dancer | bouncing-prims | rotating-bust` (selector)
- `num_cameras`: `4 | 8 | 12 | 20` (selector)
- `frames_per_camera`: `12 | 24 | 48` (selector)
- `quality`: `draft | balanced | high` (selector)

## Outputs
- A `Session` manifest in B2 with `status` (`draft | ready | running | done | failed`),
  ordered stages, artifacts, metrics (incl. `write_amplification`), `preview_key`, and the
  exact `train_command`
- Side effects: writes/deletes objects under the session's B2 prefixes

## Flow
- **Create** → writes a `draft` manifest to B2
- **Read** → library grid + detail (preview, stage timeline, metrics, storage breakdown,
  train command)
- **Edit** → PATCH tunable params + name while `draft`/`ready`; locked after a run (409)
- **Delete** → removes the manifest + every object under the session's prefixes (scoped)
- **Run** → executes ingest → extract → calibrate → stage → train/export (re-runnable)

## Edge Cases
- Edit after run → `SessionStateError` → HTTP 409, and the edit page shows a locked notice
- Unknown id → `SessionNotFoundError` → HTTP 404
- Invalid finite param (e.g. `num_cameras=5`) → 422 at the API boundary
- Run of an already-running session → 409

## UX States
- Empty: "No sessions yet" with a create prompt
- Loading: skeleton cards / detail skeleton
- Error: inline `ErrorState` with retry
- Running: stage timeline polls the manifest every 2s and advances live

## Verification
- Test files: `services/api/tests/test_sessions.py`
- Required cases: create defaults, edit pre-run, edit-locked-after-run, scoped delete,
  storage write-amplification, route create/list, 404, 422
- Focused verify command: `pnpm test:api`
- Default pre-PR verify command: `pnpm verify`
- Pass criteria: session CRUD + storage math green; routes return the documented codes

## Related Docs
- [README.md](../../README.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [docs/app-workflows.md](../app-workflows.md)
- [Multi-view ingest](multiview-ingest.md), [4D training](fourd-training.md),
  [Write amplification](write-amplification.md)
