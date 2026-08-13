<!-- last_verified: 2026-08-13 -->
# Feature: 4D training (hustvl/4DGaussians)

## Purpose
Stage a 4DGaussians `multipleview` dataset on B2 and — on a CUDA host — train a real,
time-varying Gaussian-Splatting model with a temporal deformation field, uploading
checkpoints and the final splat `.ply` to B2. On a non-CUDA host the training tail
auto-gates and emits the exact command instead of ever faking a result.

## Used By
- UI: `/sessions/[id]` (Run, the stage timeline, the exact `train.py` command)
- API: `POST /sessions/{id}/run`

## Core Functions
- `service/fourdgs_runner.py` — device detection (CUDA → MPS → CPU, default CPU), the exact
  train command, `EngineUnavailableError` gating, and the isolated-subprocess invocation
- `repo/calibration.py` — known-pose synthetic camera calibration + a real init point cloud
  (`points3D.ply` via `plyfile`)
- `service/session_runner.py` — the stage + train/export orchestration

## Canonical Files
- Engine adapter: `services/api/app/service/fourdgs_runner.py`
- Engine bootstrap: `scripts/setup_engine.sh`

## Why it is dep-split (CUDA-only)
The 4DGaussians rasterizer (`depth-diff-gaussian-rasterization`) and `simple-knn` are
CUDA-only — there are no CPU or Apple-MPS kernels. So the engine (torch + the 4DGaussians
clone + the two CUDA submodules) is **out of the base install**, installed by
`scripts/setup_engine.sh` on a CUDA host and located via `FOURDGS_REPO_DIR`. The base
install runs every CPU stage for real everywhere.

## Inputs
- The staged `multipleview` dataset (frames + `cameras.json` + `points3D.ply`) on B2
- `quality` → iteration budget (`draft` 3000 / `balanced` 14000 / `high` 30000) + resolution
- `FOURDGS_REPO_DIR` (engine location) + runtime CUDA availability

## Outputs
- **On CUDA**: training checkpoints under `checkpoints/<id>/`, the final splat `.ply` (+
  per-timestamp export) under `models/<id>/`, `metrics.trained = true`
- **On non-CUDA**: the train/export stages are marked `skipped (CUDA required)`,
  `metrics.trained = false`, and `train_command` carries the exact invocation to run on a GPU

## Flow
- **Stage**: build the multipleview dataset descriptor + init cloud on B2, render the preview,
  and record the exact `train.py` command
- **Train/Export**: `run_training` detects the device; if not CUDA (or the engine is missing),
  it raises `EngineUnavailableError` **without spawning anything**; otherwise it runs
  `python train.py -s <dataset> --expname multipleview/<id> --configs
  arguments/multipleview/default.py --iterations <budget>` in an isolated subprocess whose
  working directory is the engine clone

## Edge Cases
- No CUDA / no `FOURDGS_REPO_DIR` → gated cleanly; POST never 500s; splat never faked
- `FOURDGS_REPO_DIR` set but missing `train.py` → gated with an actionable message
- Engine subprocess non-zero exit → the run is marked `failed` with a trimmed stderr tail

## Engine boundary
The subprocess talks only to local disk — it never touches B2. All B2 I/O stays in the
tagged boto3 client in `repo/`, so the boto3-only-in-`repo/` boundary holds with the engine present.

## Verification
- Test files: `services/api/tests/test_fourdgs_engine.py` (the gated-path regression)
- Required cases: device detection is valid, command uses the quality iterations, gating on
  non-CUDA and on unset repo (no subprocess), `engine_available()` false on CPU
- Focused verify command: `pnpm test:api`
- Default pre-PR verify command: `pnpm verify`
- Pass criteria: on a CPU host the engine never runs and the run stays green with a skipped tail

## Related Docs
- [README.md](../../README.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [Sessions](sessions.md), [Multi-view ingest](multiview-ingest.md)
