<!-- last_verified: 2026-08-13 -->
# Architecture

## Components

- **apps/web/** — Next.js 16 frontend (App Router, Tailwind v4, shadcn/ui)
  - Sessions library + lifecycle (`/sessions`, `/sessions/new`, `/sessions/[id]`, `/sessions/[id]/edit`)
  - Dashboard re-aimed at Sessions + the B2 write-amplification chart
  - Per-session **Artifacts / Storage** explorer (fan-out by pipeline stage)
  - Full-bucket **File Explorer** and drag-and-drop **Upload** (kept from the starter)
  - Dark mode via `next-themes`
- **services/api/** — FastAPI backend (strict layered architecture)
  - Session manifest CRUD, ingest, run orchestration, dashboard/storage stats
  - Synchronized multi-view ingest, ffmpeg frame extraction, synthetic calibration + init cloud
  - 4DGaussians dataset staging and the CUDA-gated training tail (isolated subprocess)
  - B2 S3 integration via boto3; health, metrics, rate-limit runtime
- **packages/shared/** — TypeScript type definitions mirroring the Pydantic models

## Primary entity: Session (manifest in B2, no database)

A **Session** is a 4D volumetric capture. Its system of record is a JSON manifest at
`sessions/<id>/manifest.json` in B2 — there is **no database**. The manifest carries the
session's params, ordered pipeline stages, artifacts, metrics (including the derived
write-amplification ratio), the preview key, and the exact `train.py` command. Every
lifecycle verb (create, read, edit, delete, run) reads and writes that manifest.

### B2 prefix layout

Objects are named for the use case so the bucket reads like the pipeline. A session id
ties them together, and a session delete is strictly scoped to these prefixes:

```
sessions/<id>/manifest.json     the session record (system of record)
captures/<id>/<cam>/            source video per camera
frames/<id>/<cam>/              extracted frames (thousands of small JPEGs)
calibration/<id>/               cameras.json + points3D.ply (sparse init cloud)
dataset/<id>/                   the 4DGaussians multipleview dataset descriptor
checkpoints/<id>/               training checkpoints (CUDA tail, multi-GB)
models/<id>/                    the final splat .ply + per-timestamp export (CUDA tail)
previews/<id>/                  matplotlib contact-sheet / init-cloud preview PNG
```

## Backend Layering

The API follows a strict layered architecture:

```
types/     Pydantic models — no logic, no imports from other layers
  |
config/    Settings (pydantic-settings) — depends only on types
  |
repo/      Data access (boto3 B2 client, ffmpeg, numpy/plyfile, matplotlib) — no business logic
  |
service/   Business logic (session lifecycle, run orchestration, engine adapter) — calls repo
  |
runtime/   FastAPI routes — calls service, never repo directly
```

### Layering Rules

1. Dependencies flow downward only: `types` → `config` → `repo` → `service` → `runtime`
2. No backward imports (e.g., service must not import from runtime)
3. `boto3` only allowed in `repo/` layer
4. All boundary data uses Pydantic models (finite params are `Literal`s, validated at the boundary)
5. Authored Python files under `services/api/app/` stay under 300 lines

### Directory Structure

```
services/api/
  main.py                  App entrypoint, middleware, router registration
  app/
    types/                 Pydantic models (sessions.py, files.py, upload.py, …)
    config/                Settings loaded from environment (region-derived endpoint)
    repo/                  B2 client + session_store, frames, synthetic, calibration,
                           preview, artifacts (all third-party clients live here)
    service/               sessions, session_runner, fourdgs_runner, files, upload
    runtime/               FastAPI route handlers (sessions, files, upload, health, metrics)
  tests/                   pytest tests (structural + integration + engine-gating)
scripts/
  seed_demo.py             synthetic multi-camera seed + real CPU pipeline
  setup_engine.sh          CUDA-only 4DGaussians engine bootstrap (out of base install)
```

## Dependency split (base vs. engine)

The 4DGaussians rasterizer (`depth-diff-gaussian-rasterization`) and `simple-knn` are
**CUDA-only** — there are no CPU or Apple-MPS kernels — so the engine is deliberately
**out of the base install**:

- **Base** (`services/api/requirements.txt` / `.lock`, installed by `pnpm run setup` and CI):
  only baseline-clean CPU deps the default path needs — fastapi, boto3, `numpy<2`, Pillow,
  imageio-ffmpeg, plyfile, matplotlib. These run the CPU-runnable stages for real everywhere.
- **Engine** (installed by `scripts/setup_engine.sh` on a CUDA host): torch + a
  hustvl/4DGaussians clone + the two CUDA submodules, located via `FOURDGS_REPO_DIR`.

`service/fourdgs_runner.py` auto-detects the device (CUDA → MPS → CPU, defaulting to CPU),
lazily imports torch, and — when CUDA or the engine clone is missing — raises
`EngineUnavailableError` **without running anything**, carrying the exact command. The
run marks the train/export stages "skipped (CUDA required)"; the POST never 500s and the
trained splat is never faked. `services/api/tests/test_fourdgs_engine.py` pins that gate.

## Engine subprocess boundary

4DGaussians training runs in an **isolated subprocess** spawned from `service/` with the
engine repo as its working directory. The subprocess talks only to **local disk** — it
never touches B2. The app stages data to/from local disk and does **all** B2 I/O through
the tagged boto3 client in `repo/`, so the boto3-only-in-`repo/` boundary stays clean even
with the engine present.

## Data Stores

- **Backblaze B2** — object storage (S3-compatible API); the sole data store (no database)
  - Session records, source video, frames, calibration, checkpoints, models, previews
  - Listing/metadata via S3 `list_objects_v2` / `head_object`; downloads via presigned GET
  - **Large objects** (source video, multi-GB checkpoints) use boto3's managed multipart
    upload (`upload_fileobj` + `TransferConfig`) — see `repo/artifacts.py`

## B2 access & the custom user agent

All B2 I/O is S3-compatible (no b2-native API) and flows through the single boto3 client in
`repo/b2_client.py`, which carries `user_agent_extra="b2ai-4d-gaussian-splatting-volumetric-capture"`.
The S3 endpoint is **derived from `B2_REGION`** (`https://s3.<region>.backblazeb2.com`), so
no region string is hardcoded in source. Env var names are standardized: `B2_APPLICATION_KEY_ID`,
`B2_APPLICATION_KEY`, `B2_BUCKET_NAME`, `B2_REGION`, and the optional `B2_PUBLIC_URL_BASE`
(never required at boot).

## Boundary Invariants

- **No external SDK leakage**: `boto3` is only imported in `app/repo/`. The 4DGaussians
  subprocess is spawned from `service/` and touches only local disk.
- **No raw dicts at boundaries**: all data crossing layer boundaries uses typed Pydantic models.
- **No cross-layer mutable state**: configuration is read-only after init; intra-layer
  caches/counters (the listing cache, B2 connectivity cache, download counter, rate-limit and
  metrics state) are module-local and guarded by a `threading.Lock`. The listing cache owns
  the app's only background thread (stale-while-revalidate), warmed once at startup.
- **Validated inputs**: all HTTP inputs validated by FastAPI/Pydantic; finite session params
  are `Literal`s so the selectors and the API boundary cannot drift.

## Deployment

- **Local dev** — `pnpm dev` runs both services via `concurrently` (web `:3000`, API `:8000`).
- **Railway** — two services from the same repo: `web` builds from the root (it consumes
  `packages/shared`); `api` builds from `services/api`. Each service's versioned config sits at
  its own root. The 4D training engine is not installed on Railway; the CPU pipeline runs there.
- **Vercel** — one project: the `web` and `api` services share one origin (web at `/`, API under
  `/api`). Uploads go directly from the browser to B2 via presigned PUT, bypassing the Function's
  4.5 MB payload ceiling; the bucket must allow the deploy origin in its CORS. Native ML does not
  run on Vercel serverless, so training stays on a self-hosted CUDA host. Full contract in
  [infra/vercel/README.md](infra/vercel/README.md).

External provisioning and deployment remain explicit user-approved actions.

## Trust Boundaries

See [docs/SECURITY.md](docs/SECURITY.md) for full security documentation.

- **Frontend → API** — CORS-restricted to configured origins. `CORSMiddleware` is outermost in
  `main.py` so it wraps every response, including uncaught-exception 500s. A per-IP rate-limit
  middleware sits inner to CORS.
- **API → B2** — authenticated via application keys, signature v4.
- **Client → B2** — presigned URLs for upload (PUT) and download (GET), short-lived.

## Data Flows

- **Create**: Browser → `POST /sessions` → service writes `sessions/<id>/manifest.json` to B2
- **Run**: Browser → `POST /sessions/{id}/run` → background thread runs ingest → extract →
  calibrate → stage → train/export, persisting the manifest after every stage (the detail page
  polls it live)
- **Storage**: Browser → `GET /sessions/{id}/storage` → per-stage `list_objects_v2` → the
  write-amplification breakdown
- **List/Download (explorer)**: Browser → `GET /files` / presigned GET → full-bucket browse
- **Delete**: Browser → `DELETE /sessions/{id}` → every object under the session's prefixes removed

## Observability

- Structured JSON logging on all requests with `request_id`
- Request timing middleware (also the catch-all that converts uncaught exceptions to a typed 500)
- `/metrics` (Prometheus format) and `/health` (B2 connectivity check)

## API Contract

- Checked-in OpenAPI artifact: `docs/api/openapi.json`
- Export/check command: `pnpm contract:export` / `pnpm contract:check`
- FastAPI freshness test: `services/api/tests/test_openapi_contract.py`
- Frontend route drift test: `apps/web/src/lib/api-contract.test.ts`

## Canonical Files

- Session routes: `services/api/app/runtime/sessions.py`
- Session lifecycle service: `services/api/app/service/sessions.py`
- Run pipeline: `services/api/app/service/session_runner.py`
- Engine adapter (CUDA gating): `services/api/app/service/fourdgs_runner.py`
- B2 manifest store: `services/api/app/repo/session_store.py`
- B2 data access (UA carrier): `services/api/app/repo/b2_client.py`
- Session Pydantic models: `services/api/app/types/sessions.py`
- Config (pydantic-settings, region-derived endpoint): `services/api/app/config/settings.py`
- Structural tests: `services/api/tests/test_structure.py`

## Core Features

- [Sessions & lifecycle](docs/features/sessions.md)
- [Multi-view ingest](docs/features/multiview-ingest.md)
- [4D training](docs/features/fourd-training.md)
- [Write amplification](docs/features/write-amplification.md)
- [File Browser](docs/features/file-browser.md)
- [File Upload](docs/features/file-upload.md)

## References

- [docs/SECURITY.md](docs/SECURITY.md) — security principles and implementation
- [docs/RELIABILITY.md](docs/RELIABILITY.md) — reliability expectations
- [AGENTS.md](AGENTS.md) — architectural invariants and agent instructions
