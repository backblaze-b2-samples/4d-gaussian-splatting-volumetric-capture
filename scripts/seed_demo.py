#!/usr/bin/env python3
"""Seed a tiny, fully synthetic 4D volumetric capture session into Backblaze B2.

What it does (all real, no fakery):
  1. Creates a Session (manifest.json in B2 — the system of record).
  2. Renders a small SYNTHETIC dynamic multi-camera capture with numpy + PIL —
     a moving textured subject observed by N virtual pinhole cameras over T
     timestamps. Never real people, no downloaded dataset, no second API key.
  3. Encodes one short MP4 per camera with the bundled ffmpeg and uploads them
     under `captures/<id>/<cam>/source.mp4`.
  4. Runs the REAL CPU-side pipeline against those uploads: extract frames ->
     calibrate -> stage the 4DGaussians `multipleview` dataset + init point
     cloud -> emit the exact `train.py` command. The CUDA-only train/export
     tail auto-gates and is marked "skipped (CUDA required)" on a non-CUDA host.

Requirements: B2 credentials in `.env` (see `.env.example`). Keyless otherwise.
Reproducible and strictly prefix-scoped to the one session it creates. NOT run
by `pnpm verify` — it makes real network writes to your bucket.

Usage:
    python scripts/seed_demo.py                 # default tiny preset
    python scripts/seed_demo.py --name "Take 2" --cameras 8 --frames 24
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Make the API package importable and load the repo-root .env exactly like the
# server does, so the seed talks to the same bucket with the same tagged client.
_REPO_ROOT = Path(__file__).resolve().parents[1]
_API_ROOT = _REPO_ROOT / "services" / "api"
sys.path.insert(0, str(_API_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(_REPO_ROOT / ".env")

from app.config import settings  # noqa: E402
from app.repo import artifacts, calibration, frames, session_store, synthetic  # noqa: E402
from app.service.session_runner import run_session  # noqa: E402
from app.service.sessions import create_session  # noqa: E402
from app.types.sessions import QUALITY_RESOLUTION, SessionCreate  # noqa: E402

VALID_CAMERAS = (4, 8, 12, 20)
VALID_FRAMES = (12, 24, 48)


def _require_b2() -> None:
    missing = [
        name
        for name, val in (
            ("B2_APPLICATION_KEY_ID", settings.b2_application_key_id),
            ("B2_APPLICATION_KEY", settings.b2_application_key),
            ("B2_BUCKET_NAME", settings.b2_bucket_name),
            ("B2_REGION", settings.b2_region),
        )
        if not val
    ]
    if missing:
        raise SystemExit(
            "Missing B2 configuration: "
            + ", ".join(missing)
            + f".\nAdd them to {_REPO_ROOT / '.env'} (see .env.example) and retry."
        )


def _upload_synthetic_capture(session_id: str, preset: str, num_cameras: int,
                              frames_per_camera: int, quality: str) -> int:
    """Render + upload one MP4 per camera under captures/<id>/<cam>/. Returns bytes."""
    width, height = QUALITY_RESOLUTION[quality]
    cameras = calibration.generate_cameras(num_cameras, width, height)
    rendered = synthetic.render_scene(preset, cameras, frames_per_camera)
    total = 0
    for cam_id, cam_frames in rendered.items():
        mp4 = frames.encode_video(cam_frames, fps=min(frames_per_camera, 24))
        key = f"{session_store.captures_prefix(session_id)}{cam_id}/source.mp4"
        ref = artifacts.put_bytes(key, mp4, "video/mp4")
        total += ref["bytes"]
        print(f"  uploaded {key} ({ref['bytes'] / 1024:.0f} KiB)")
    return total


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", default="Synthetic demo capture")
    parser.add_argument("--preset", default="orbit-dancer",
                        choices=["orbit-dancer", "bouncing-prims", "rotating-bust"])
    parser.add_argument("--cameras", type=int, default=4, choices=VALID_CAMERAS)
    parser.add_argument("--frames", type=int, default=12, choices=VALID_FRAMES)
    parser.add_argument("--quality", default="draft",
                        choices=["draft", "balanced", "high"])
    args = parser.parse_args()

    _require_b2()

    print(f"Creating session '{args.name}' in bucket {settings.b2_bucket_name} ...")
    session = create_session(
        SessionCreate(
            name=args.name,
            scene_preset=args.preset,
            num_cameras=args.cameras,
            frames_per_camera=args.frames,
            quality=args.quality,
        )
    )
    print(f"  session id: {session.id}")

    print(f"Rendering + uploading {args.cameras} synthetic camera streams ...")
    _upload_synthetic_capture(
        session.id, args.preset, args.cameras, args.frames, args.quality
    )

    print("Running the CPU-side pipeline (extract -> calibrate -> stage) ...")
    result = run_session(session.id)

    print("\nDone. Session summary:")
    print(f"  status              : {result.status}")
    print(f"  device              : {result.metrics.device}")
    print(f"  frames extracted    : {result.metrics.total_frames}")
    print(f"  init cloud points   : {result.metrics.init_points}")
    print(f"  source bytes        : {result.metrics.source_bytes}")
    print(f"  write amplification : {result.metrics.write_amplification}x")
    print(f"  trained             : {result.metrics.trained} "
          "(train/export gated to CUDA hosts)")
    print(f"\n  4DGaussians train command:\n    {result.train_command}")
    print(f"\nOpen the app and visit /sessions/{result.id} to explore artifacts.")


if __name__ == "__main__":
    main()
