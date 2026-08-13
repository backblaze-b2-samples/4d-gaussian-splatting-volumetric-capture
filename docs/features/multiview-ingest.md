<!-- last_verified: 2026-08-13 -->
# Feature: Synchronized multi-view ingest

## Purpose
Turn synchronized multi-camera video into the per-camera frames a 4D reconstruction needs —
either from real uploaded footage or from a fully synthetic, license-clean seed — and stage
every input and derived frame in B2.

## Used By
- UI: `/upload` and `/sessions/[id]` (Run), plus `scripts/seed_demo.py`
- API: `POST /sessions/{id}/ingest` (presign a per-camera source-video PUT), `POST /sessions/{id}/run`

## Core Functions
- `repo/synthetic.py` — procedural dynamic scene rendered from each calibrated camera (numpy + PIL)
- `repo/frames.py` — video encode + frame extraction via the bundled ffmpeg
  (`imageio_ffmpeg.get_ffmpeg_exe()`), not a bare PATH `ffmpeg`
- `service/session_runner.py` — the ingest + extract stages

## Canonical Files
- ffmpeg wrapper: `services/api/app/repo/frames.py`
- Synthetic renderer: `services/api/app/repo/synthetic.py`

## Inputs
- Real: one source video per camera, uploaded to `captures/<id>/<cam>/` (presigned PUT)
- Synthetic: `scene_preset`, `num_cameras`, `frames_per_camera` from the session params

## Outputs
- Per-camera source MP4s under `captures/<id>/<cam>/`
- Extracted frames under `frames/<id>/<cam>/frame_NNNN.jpg` (thousands of small JPEGs at scale)
- Side effects: PutObject for each video and frame; metrics record source + frame bytes

## Flow
- **Ingest**: if source video already exists under `captures/<id>/`, it is pulled back for
  extraction; otherwise a synthetic multi-view capture is rendered and per-camera MP4s uploaded
- **Extract**: each camera's video is decoded to `frames_per_camera` JPEGs and uploaded

## Edge Cases
- No source video and no synthetic render → nothing to extract (guarded)
- Homebrew's slim ffmpeg lacks filters → the bundled full build is pinned for reproducibility
- ffmpeg failure surfaces a trimmed stderr tail and fails the stage cleanly (no 500 to the UI)

## UX States
- The extract stage advances live on the detail page's timeline with a frame count

## Sensitive-content guard
Demo/seed/screenshot assets are **fully procedural synthetic renders** — never real people,
never a downloaded academic/research dataset.

## Verification
- Test files: covered by `services/api/tests/test_sessions.py` (pipeline stages) and the
  structural `boto3-only-in-repo` test
- Focused verify command: `pnpm test:api`
- Default pre-PR verify command: `pnpm verify`
- Pass criteria: ingest/extract stages produce frames and record byte counts

## Related Docs
- [README.md](../../README.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [Sessions](sessions.md), [4D training](fourd-training.md)
