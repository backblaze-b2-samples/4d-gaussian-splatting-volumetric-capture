# Build plan — `4d-gaussian-splatting-volumetric-capture`

Source of truth for the starter kit: `.claude/scratch/vcsk-92a83c23-ca41-412c-9cb0-891ca24c9c46/`.
Build target: `./4d-gaussian-splatting-volumetric-capture`.

> **Near-neighbour warning.** A sibling `colmap-gaussian-splatting-pipeline` exists in
> `../` and is architecturally close. It is a **reference for structure only** (entity
> shape, dep-split, CUDA-tail gating, synthetic seed). **Do NOT re-skin it.** The domain
> here is different: **dynamic 4D reconstruction from synchronized MULTI-CAMERA video**
> using **hustvl/4DGaussians** (temporal deformation field), not static single-camera
> COLMAP SfM. Do not clone it, do not read it as source, do not substitute its engine.
> Build fresh from the starter kit tree only.

## 1. Purpose

A capture-to-B2 **volumetric (4D) reconstruction pipeline** for VFX / volumetric-capture
labs. A user creates a **Session** from synchronized multi-view video (dozens of cameras
filming the same dynamic scene), the app extracts per-frame images and camera calibration,
stages a **4DGaussians**-ready `multipleview` dataset on B2, and — on a CUDA host — trains a
4D Gaussian Splatting scene (a time-varying set of Gaussians with a deformation field),
writing intermediate checkpoints and the final `.ply` splat model back to B2. Every input
and derived artifact is versioned under the session's own prefix. The sample's headline
story is **extreme data volume with write amplification**: one session fans out into source
video → thousands of extracted frames → multi-GB checkpoints → a final splat model, all
landing in **Backblaze B2** over the S3-compatible API. Runs on local OSS only — 4DGaussians
is keyless; the only secret is B2 credentials. No second API key.

Audience: volumetric-capture / VFX engineers and AI/3D practitioners who need durable,
cheap, S3-compatible object storage for the huge intermediate + final artifacts of a
4D-GS reconstruction pipeline, and AI coding agents scaffolding one.

## 2. Architecture delta from vibe-coding-starter-kit

The starter kit is the ceiling — strip what this app doesn't need; keep the layered
FastAPI + Next.js shell, the boto3 `repo/` containment, the full-bucket explorer, upload,
settings, design system, and structural tests.

### KEEP (as-is or lightly adapted)
- Monorepo shell: `apps/web` (Next.js 16 / React 19 / Tailwind v4 / shadcn/ui),
  `services/api` (FastAPI, strict layered `repo`/`service`/`runtime`/`types`/`config`),
  `packages/shared`, `scripts/`, `infra/`, pnpm workspace, `pnpm run setup|dev|doctor`.
- **Full-bucket File Explorer** (`/files`) + drag-and-drop **Upload** (`/upload`) — the
  starter's bucket explorer is **non-negotiable KEEP** (full-bucket browse/preview/
  download/delete, presigned PUT upload).
- `repo/b2_client.py` boto3 client with `user_agent_extra` (retarget the UA value),
  `list_cache.py`, `counter.py`, `b2_object.py`, `b2_upload.py`; health/metrics/ratelimit
  runtime; settings shell; `/settings` and `/design` pages; error/loading/not-found;
  structural tests, dependency-lock test, openapi-contract test, vercel-entrypoint test.

### TRIM (remove from starter)
- The generic "file metadata extraction" feature framing and its dashboard copy — replace
  with the Sessions domain. Delete `service/metadata.py`'s generic-upload framing only if
  unused after rewire; keep any helper the explorer still needs.
- Starter README / feature docs about "vibe coding" / generic uploads (rewrite, see §5).
- Any starter dashboard widgets that assume "recent uploads" as the primary object — re-aim
  at Sessions + B2 write-amplification.
- `docs/features/metadata-extraction.md`, `file-upload.md`, `file-browser.md`,
  `dashboard.md`, `settings.md` → rewrite/replace per §5 (explorer + upload docs stay,
  retargeted).

### ADD (new for this sample)
- **Primary entity `Session`** (a 4D capture session) — full lifecycle (§4). System of
  record is a JSON manifest in B2 at `sessions/<id>/manifest.json` — **no database**
  (mirror the sibling's B2-manifest pattern). NOTE: keep the user-facing B2 prefixes named
  per the use case — `captures/<id>/<camera_id>/`, `frames/<id>/`, `checkpoints/<id>/`,
  `models/<id>/`, plus `sessions/<id>/manifest.json` for the record. (A session id ties them
  together.)
- Backend: `types/sessions.py`, `service/sessions.py` (manifest CRUD, ingest, stats),
  `service/session_runner.py` (background run: stage orchestration + B2 I/O),
  `service/fourdgs_runner.py` (isolated-subprocess engine invocation, CUDA-gated),
  `repo/frames.py` (ffmpeg frame extraction via imageio-ffmpeg), `repo/calibration.py`
  (known-pose synthetic calibration + real init point cloud `.ply` via `plyfile`),
  `repo/preview.py` (matplotlib preview PNG: multi-view contact sheet / init-cloud render),
  `repo/artifacts.py` (write derived objects under the session prefix, capture version ids),
  `runtime/sessions.py` (REST routes).
- **Sample-specific asset explorer** (mandatory ADD, distinct from the full-bucket
  explorer): a per-session **"Artifacts / Storage"** view scoped to that one session's
  prefixes, grouped by pipeline stage (source video / frames / calibration / checkpoints /
  model) with per-stage object counts + bytes and the **write-amplification breakdown**
  (bytes and object-count multiplier from source → derived). This is the sample's own
  scoped explorer; the full-bucket `/files` explorer stays as well.
- Frontend pages: `/sessions` (library grid), `/sessions/new` (create form),
  `/sessions/[id]` (detail: stage timeline, multi-view thumbnails, 4D metrics, the exact
  4DGaussians `train.py` command for the CUDA tail, per-stage artifacts + storage
  breakdown), `/sessions/[id]/edit` (edit form). Dashboard (`/`) re-aimed at Sessions +
  B2 write-amplification stats.
- `scripts/seed_demo.py` — renders a tiny SYNTHETIC dynamic multi-camera capture (a moving
  textured object orbited/observed by N virtual pinhole cameras over T timestamps) fully in
  numpy/PIL, encodes per-camera short MP4s via bundled ffmpeg, uploads under
  `captures/<id>/<cam>/`, then runs the real CPU-side pipeline (extract → calibrate → stage
  `multipleview` dataset + init cloud → emit train command). No binary assets shipped;
  keyless; reproducible; prefix-scoped; NOT run by `pnpm verify`.
- `scripts/setup_engine.sh` — documented CUDA-only engine bootstrap: clones
  `https://github.com/hustvl/4DGaussians`, installs its requirements + the two CUDA
  submodules `depth-diff-gaussian-rasterization` and `simple-knn`, sets `FOURDGS_REPO_DIR`.
- New feature docs (§5).

**Explorer tension note (required by skill):** none — both explorers coexist cleanly. The
full-bucket `/files` explorer is kept; the per-session scoped "Artifacts/Storage" view is
the added sample-specific explorer.

## 3. B2 surface (S3-compatible only — NO b2-native)

All I/O through boto3 in `repo/`, S3 API, `user_agent_extra="b2ai-4d-gaussian-splatting-volumetric-capture"`.

| S3 operation | Where |
|---|---|
| `PutObject` | ingest video, extracted frames (thousands of small JPEG/PNG), calibration JSON, init point cloud `.ply`, training checkpoints, final splat `.ply` + metadata, `sessions/<id>/manifest.json`, preview PNG |
| `list_objects_v2` (paginated) | full-bucket explorer, dashboard stats, per-session artifact/storage listing |
| `HeadObject` | per-object metadata, version ids |
| presigned `get_object` | download models/checkpoints; "serve to rendering client" story; detail-view artifact links |
| presigned `put_object` | browser direct upload of source video (kept starter upload flow) |
| `DeleteObject` | delete a session (scoped strictly to that session's prefixes) |
| multipart upload (boto3 `upload_fileobj` + `TransferConfig`) | large source video / multi-GB checkpoints — note it in ARCHITECTURE.md as the large-object path |

No b2-native API anywhere. UA carried on boto3 (the only S3 client). Document in
`ARCHITECTURE.md` that boto3 carries the UA and that the 4DGaussians subprocess never talks
to B2 — the app stages data to/from local disk and does all B2 I/O through the tagged boto3
client.

## 4. Key features + primary-entity lifecycle

**Primary entity: `Session`** (a 4D volumetric capture session). DEFAULT = all lifecycle
verbs in the UI:

- **create** — `/sessions/new`: name + finite-option params (selectors, see Form UX).
  Creates a `draft` manifest in B2.
- **read** — `/sessions` library grid + `/sessions/[id]` detail (stage timeline, multi-view
  contact-sheet thumbnail, 4D metrics, per-stage storage breakdown, artifact download links,
  the exact train command).
- **edit** — `/sessions/[id]/edit`: PATCH the tunable params + name while `draft`/`ready`
  (pre-run). Immutable-after-run params are disabled with a hint.
- **delete** — delete the session + every B2 object under its prefixes (scoped).
- **run** — POST `/sessions/{id}/run`: execute the pipeline (extract → calibrate → stage →
  train/export). Re-runnable.

Plus **ingest** (POST frames/video to a session) — supporting verb, not a CRUD verb.

No verbs omitted → `omitted_ui_verbs` is empty.

### Feature bullets (seed README + `docs/features/*`)
1. **Sessions library + lifecycle** — create/browse/edit/delete/run 4D capture sessions;
   manifest-in-B2, no DB.
2. **Synchronized multi-view ingest** — upload per-camera video (or seed synthetic), frames
   extracted per camera via bundled ffmpeg, stored under `captures/<id>/<cam>/`.
3. **4DGaussians dataset staging + real 4D training** — build the `multipleview` dataset
   layout (`cam01/frame_*.jpg` + calibration + downsampled init `points3D.ply`) on B2, then
   invoke **hustvl/4DGaussians** `train.py` in an isolated subprocess on a CUDA host,
   uploading checkpoints + the final splat `.ply` (+ per-timestamp export) to B2. On a
   non-CUDA host the stage is auto-gated and the exact `train.py` command is emitted — the
   trained splat is **never faked**.
4. **B2 write-amplification dashboard + per-session storage explorer** — visualize the data
   fan-out (source bytes/objects → frame bytes/objects → checkpoint/model bytes) and total
   B2 footprint per session and across the bucket.
5. **Full-bucket File Explorer + Upload** — kept from the starter.
6. **Serve/query** — session manifest JSON links video, frames, checkpoints, models;
   presigned URLs let a rendering client pull the splat model directly from B2.

### External API provider
**None.** The headline capability (4D Gaussian Splatting training) is **on-device / local
OSS** (`deployment: local`, no external provider, no second key — B2 credentials only).
- Provider/model: **hustvl/4DGaussians** (local, keyless).
- deployment: **local**.
- Estimated cost per full demo run: **$0** (no external API; only B2 storage of demo
  artifacts, kept tiny — see below).
- Env var for key: **none** (no provider key). Engine location via `FOURDGS_REPO_DIR`.

**Device rule (`deployment: local`):** auto-detect CUDA → MPS → CPU, default CPU. The
4DGaussians rasterizer (`depth-diff-gaussian-rasterization`) and `simple-knn` are
**CUDA-only** (no MPS/CPU kernels). So: the **CPU/MPS-runnable stages** (ingest, frame
extraction, calibration, init-cloud, dataset staging, manifest, preview, all B2 I/O,
explorer, dashboard, serve) run **for real everywhere**; the **train/export stages require
CUDA** and are auto-gated. This is the documented **dep-split** recipe, not a simulation.

**No Genblaze** — the description does not mention Genblaze/`genblaze-*`; use plain boto3.

### Form UX conventions (create/edit `Session` forms)
Finite-option fields → **selectors** (Select/RadioGroup/segmented), never free text, on both
create and edit; validated at the API boundary as `Literal`s:
- `scene_preset` — the synthetic demo scene (e.g. `orbit-dancer` | `bouncing-prims` |
  `rotating-bust`) [synthetic, license-clean]. Select.
- `num_cameras` — small finite set (e.g. `4 | 8 | 12 | 20`). Select/segmented.
- `frames_per_camera` (temporal length) — finite set (e.g. `12 | 24 | 48`). Select.
- `quality` / training preset — `draft | balanced | high` (maps to 4DGaussians iteration
  budget + resolution). Select.

CREATE-form safe defaults as placeholder / `FormDescription` guidance (never an autofill
button), sized for a fast, sound test run: `scene_preset=orbit-dancer`, `num_cameras=4`,
`frames_per_camera=12`, `quality=draft`. Edit form opens pre-filled from the real manifest;
post-run-immutable params disabled with a hint. Exemplar to match:
`apps/web/src/components/settings/settings-form.tsx`.

**Sensitive-content guard:** volumetric capture implies people. The demo/seed/screenshot
assets MUST be **verified-license synthetic footage** — here fully procedural synthetic
renders (numpy/PIL), never real people. No downloaded academic/research datasets bundled.

## 5. Doc transforms
- **Rewrite** `README.md` — new title "4D Gaussian Splatting Volumetric Capture", the
  Session lifecycle, the synchronized multi-view + 4DGaussians + write-amplification story,
  standardized `B2_*` setup, CUDA-tail note ("no GPU needed to stage the dataset & exercise
  B2; 4D training is CUDA-only and auto-gated"), UTM `b2ai-4d-gaussian-splatting-volumetric-capture`.
- **Rewrite** `ARCHITECTURE.md` — layered backend, manifest-in-B2, dep-split (base vs
  `requirements-engine`), isolated-subprocess engine, boto3-carries-UA, prefix layout.
- **Replace** `docs/features/*`: new `sessions.md`, `multiview-ingest.md`,
  `fourd-training.md` (engine + CUDA gating + exact commands), `write-amplification.md`
  (dashboard + per-session storage explorer); **keep + retarget** `file-browser.md`
  (full-bucket explorer) and `file-upload.md` (upload). Delete `metadata-extraction.md`,
  `dashboard.md` (fold into the new dashboard/write-amplification doc).
- Update `PRODUCT.md`, `docs/app-workflows.md`, `AGENTS.md`/`CLAUDE.md`/`GEMINI.md` app
  name + domain. Keep `docs/RELIABILITY.md` / `docs/SECURITY.md`, retargeting app name.
- `docs/exec-plans/completed/initial-scaffold.md` — this plan lands here on PASS (skill
  Phase 5).

## 6. Rename table

| Kind | vibe-coding-starter-kit | 4d-gaussian-splatting-volumetric-capture |
|---|---|---|
| kebab slug / repo | `vibe-coding-starter-kit` | `4d-gaussian-splatting-volumetric-capture` |
| Title Case | Vibe Coding Starter Kit | 4D Gaussian Splatting Volumetric Capture |
| snake / pkg | `vibe_coding_starter_kit` | `fourd_gaussian_splatting` (Python-safe: no leading digit) |
| web pkg name | `web` (workspace) | keep `web` (internal) / app title "4D Gaussian Splatting Volumetric Capture" |
| user agent (`user_agent_extra`) | `b2ai-oss-start` | `b2ai-4d-gaussian-splatting-volumetric-capture` |
| UTM `utm_content` | `b2ai-oss-start` | `b2ai-4d-gaussian-splatting-volumetric-capture` |
| APP_NAME constant | (starter) | `4D Gaussian Splatting Volumetric Capture` — single source in `lib/app-config.ts`, referenced by `layout.tsx` metadata, `app-sidebar.tsx` brand, and `header.tsx` breadcrumb (fix the known starter breadcrumb/`pageTitles` "Page" fallback: derive title from pathname) |
| env vars | `B2_ENDPOINT`,`B2_KEY_ID`,`B2_APPLICATION_KEY`,`B2_BUCKET_NAME`,`B2_PUBLIC_URL` | **standardize** → `B2_APPLICATION_KEY_ID`,`B2_APPLICATION_KEY`,`B2_BUCKET_NAME`,`B2_REGION`,`B2_PUBLIC_URL_BASE` (+ optional `B2_ENDPOINT` override derived from region). Match the sibling's settings shape. |

## 7. Standards & constraints checklist (from repo CLAUDE.md + build-constraints)
- **S3 API default** (no b2-native); **custom UA** on the boto3 client
  (`b2ai-4d-gaussian-splatting-volumetric-capture`); **standardized `B2_*`** env names (rename from starter's
  `B2_KEY_ID`/`B2_ENDPOINT`; grep the tree — none may remain, a *derived* `b2_endpoint`
  settings property is fine). `B2_PUBLIC_URL_BASE` is **optional** — must not be in any
  boot-required list.
- **Primary feature is real** — 4DGaussians is genuinely invoked (real subprocess, real
  artifacts to B2) on CUDA; never mocked/simulated. Non-CUDA path stages the real dataset +
  init cloud + emits the real command and marks train/export **skipped (CUDA required)** —
  the POST never 500s.
- **Dep-split** (build-constraints "No wheel"): base `requirements.txt`/`.lock` = baseline
  clean CPU deps installed by setup/verify/CI (fastapi, uvicorn[standard], python-multipart,
  python-dotenv, pydantic, pydantic-settings, boto3, `numpy<2`, Pillow, imageio,
  imageio-ffmpeg, plyfile, matplotlib, + dev). Engine (torch + 4DGaussians + CUDA submodules)
  is **out of base**, installed by `scripts/setup_engine.sh` on a CUDA host, gated behind
  `FOURDGS_REPO_DIR` + CUDA detection. Lazy-import / subprocess guard raises a clear
  `EngineUnavailableError`; add a regression test for the gated path (mirror
  `test_sfm_engine.py`).
- **Device auto-detect** CUDA→MPS→CPU, default CPU; MPS unsupported by the rasterizer → note
  it, fall back to gated. No unconditional `.cuda()` / GPU assert on the default path.
- **Contain third-party clients in `repo/`** — boto3 only in `repo/`; structural test
  asserts it (keep the starter's). The 4DGaussians subprocess is spawned from `service/`
  and touches only local disk (no B2), so containment stays clean.
- **ffmpeg** — use `imageio_ffmpeg.get_ffmpeg_exe()` (bundled full build) for frame
  extraction / encoding, not a bare PATH `ffmpeg` (Homebrew slim build lacks filters);
  frame extraction (`-i in.mp4 out_%04d.jpg`) needs no special filter but pin the bundled
  binary for reproducibility.
- **numpy<2** (torch/arm64 + plyfile/matplotlib compat); pin `imageio-ffmpeg>=0.5`,
  `plyfile>=1.0`, `Pillow>=11`, `matplotlib>=3.8`. `>=`-only in `requirements.txt` with the
  dependency-lock test; exact pins in `requirements.lock`. Recreate the venv from the lock
  to prove no false-green.
- **Keep the default seed tiny** (~a handful of cameras × ~12 frames, small resolution) so
  verify + screenshots stay fast and B2 footprint stays small; offer a larger preset for the
  scale story.
- **Headless render never hard-fails** — the preview PNG (matplotlib `Agg`) is the
  always-works renderer for the init-cloud / multi-view contact sheet; no GPU render on the
  default path.
- **Rename hygiene** — one `APP_NAME` source; fix breadcrumb/`pageTitles`; after any rename
  clear `.next`/`.turbo` and re-probe routes.

## 8. Session type sketch (mirror sibling shape, 4D domain)
`types/sessions.py` — `ScenePreset`, `Quality`, finite `Literal`s + tuples; `SessionStage`
(`ingest|extract|calibrate|stage|train|export`), `SessionArtifact` (kind:
`video|frames|calibration|init_cloud|checkpoint|model|manifest|preview`), `SessionMetrics`
(`num_cameras`, `frames_per_camera`, `total_frames`, `duration_seconds`, `init_points`,
`model_points`, `source_bytes`, `frame_bytes`, `checkpoint_bytes`, `model_bytes`,
`write_amplification` (derived ratio), `device`, `trained: bool`), `SessionParams` (shared),
`SessionCreate`, `SessionUpdate` (all-optional), `Session` (id, status
`draft|ready|running|done|failed`, timestamps, `started_at`, stages, artifacts, metrics,
`preview_key`, `train_command`), `SessionStats` (dashboard aggregates incl. write-amp).

## 9. Definition of done (green gates)
`pnpm lint`, `pnpm build`, `pnpm test:api`, `pnpm check:structure`, `pnpm contract:export`
green in a **fresh** venv from `requirements.lock`; `pnpm dev` boots and every route
(`/`, `/sessions`, `/sessions/new`, `/sessions/[id]`, `/sessions/[id]/edit`, `/files`,
`/upload`, `/settings`, `/design`) returns 200; headline feature reachable from the UI;
tree grep (excl. node_modules/.next/.git/lockfiles) for
`vibe.coding.starter|oss-start|B2_KEY_ID|B2_ENDPOINT` is clean (derived `b2_endpoint`
property excepted); no real secrets; boto3 only in `repo/`; engine-gated regression test
passes on CPU.
