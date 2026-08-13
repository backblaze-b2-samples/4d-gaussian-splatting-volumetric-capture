"""Known-pose synthetic camera calibration and a real init point cloud.

Third-party numeric/format libs (numpy, plyfile) are wrapped here in repo/ per
the layering rules. The calibration is deterministic given the same inputs, so
the synthetic-capture renderer and the calibrate stage agree on the exact same
cameras — a genuinely consistent multi-view rig, not random noise per stage.
"""

from __future__ import annotations

import io

import numpy as np
from plyfile import PlyData, PlyElement

_RIG_RADIUS = 3.2
_RIG_ELEVATION = 0.6


def _normalize(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    return v / n if n > 0 else v


def _look_at(eye: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """World->camera rotation R and translation T for a camera at `eye` looking
    at the origin (OpenCV convention: +z forward, +x right, +y down)."""
    target = np.zeros(3)
    up = np.array([0.0, 1.0, 0.0])
    forward = _normalize(target - eye)
    right = _normalize(np.cross(forward, up))
    down = np.cross(forward, right)
    rot = np.stack([right, down, forward], axis=0)
    trans = -rot @ eye
    return rot, trans


def generate_cameras(
    num_cameras: int, width: int, height: int
) -> list[dict]:
    """A ring of `num_cameras` pinhole cameras encircling the scene origin."""
    focal = 1.2 * width
    cams: list[dict] = []
    for i in range(num_cameras):
        angle = 2.0 * np.pi * i / num_cameras
        eye = np.array(
            [
                _RIG_RADIUS * np.cos(angle),
                _RIG_ELEVATION,
                _RIG_RADIUS * np.sin(angle),
            ]
        )
        rot, trans = _look_at(eye)
        cams.append(
            {
                "id": f"cam{i + 1:02d}",
                "width": width,
                "height": height,
                "fx": focal,
                "fy": focal,
                "cx": width / 2.0,
                "cy": height / 2.0,
                "R": rot.tolist(),
                "T": trans.tolist(),
                "position": eye.tolist(),
            }
        )
    return cams


def cameras_json(cameras: list[dict]) -> dict:
    """Serializable calibration record for `calibration/<id>/cameras.json`."""
    return {
        "convention": "opencv",
        "count": len(cameras),
        "cameras": cameras,
    }


def init_point_cloud(
    num_points: int = 2000, seed: int = 7
) -> tuple[bytes, np.ndarray, np.ndarray]:
    """A real, downsampled COLMAP-style init cloud serialized as binary PLY.

    4DGaussians seeds training from a sparse `points3D.ply`; this stands in for
    it on the CPU path. Returns (ply_bytes, xyz[N,3], rgb[N,3]).
    """
    rng = np.random.default_rng(seed)
    # A rough humanoid/blob volume so the cloud reads as a subject, not a cube.
    theta = rng.uniform(0, 2 * np.pi, num_points)
    height = rng.uniform(-1.0, 1.0, num_points)
    radius = 0.5 * (1.0 - 0.35 * np.abs(height)) * np.sqrt(rng.uniform(0, 1, num_points))
    xyz = np.stack(
        [radius * np.cos(theta), height, radius * np.sin(theta)], axis=1
    ).astype(np.float32)
    rgb = np.clip(
        128 + 96 * np.stack([np.cos(theta), height, np.sin(theta)], axis=1),
        0,
        255,
    ).astype(np.uint8)

    vertex = np.zeros(
        num_points,
        dtype=[
            ("x", "f4"), ("y", "f4"), ("z", "f4"),
            ("red", "u1"), ("green", "u1"), ("blue", "u1"),
        ],
    )
    vertex["x"], vertex["y"], vertex["z"] = xyz[:, 0], xyz[:, 1], xyz[:, 2]
    vertex["red"], vertex["green"], vertex["blue"] = rgb[:, 0], rgb[:, 1], rgb[:, 2]

    buffer = io.BytesIO()
    PlyData([PlyElement.describe(vertex, "vertex")], text=False).write(buffer)
    return buffer.getvalue(), xyz, rgb
