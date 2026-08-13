"""ffmpeg-backed video encode + frame extraction.

Uses the bundled full ffmpeg build from `imageio_ffmpeg.get_ffmpeg_exe()`, not a
bare PATH `ffmpeg` — a Homebrew slim build lacks filters/encoders, and pinning
the bundled binary keeps extraction reproducible across hosts. Wrapped in repo/
like every third-party client.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import imageio_ffmpeg
from PIL import Image

_FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


def _run(args: list[str]) -> None:
    """Run ffmpeg, surfacing a trimmed stderr tail on failure (contained here)."""
    proc = subprocess.run(
        [_FFMPEG, "-hide_banner", "-loglevel", "error", "-y", *args],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        tail = (proc.stderr or "").strip().splitlines()[-8:]
        raise RuntimeError("ffmpeg failed: " + " | ".join(tail))


def encode_video(frames: list[Image.Image], fps: int = 12) -> bytes:
    """Encode PIL frames into an H.264 MP4 and return its bytes."""
    if not frames:
        raise ValueError("encode_video requires at least one frame")
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        for i, frame in enumerate(frames):
            frame.convert("RGB").save(tmp_dir / f"frame_{i + 1:04d}.png")
        out = tmp_dir / "out.mp4"
        _run(
            [
                "-framerate", str(fps),
                "-i", str(tmp_dir / "frame_%04d.png"),
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                str(out),
            ]
        )
        return out.read_bytes()


def extract_frames(video_bytes: bytes, max_frames: int) -> list[bytes]:
    """Decode an MP4 back into up to `max_frames` JPEG frames (bytes)."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        src = tmp_dir / "in.mp4"
        src.write_bytes(video_bytes)
        _run(
            [
                "-i", str(src),
                "-frames:v", str(max_frames),
                "-vsync", "0",
                "-q:v", "3",
                str(tmp_dir / "frame_%04d.jpg"),
            ]
        )
        return [p.read_bytes() for p in sorted(tmp_dir.glob("frame_*.jpg"))]
