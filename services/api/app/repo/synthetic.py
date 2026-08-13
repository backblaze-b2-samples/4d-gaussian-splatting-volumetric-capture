"""Fully procedural synthetic dynamic scenes (numpy + PIL) — never real people.

A moving, textured subject rendered from each calibrated camera, so the demo
input is a genuinely consistent synchronized multi-view capture that needs no
download, no license review and no second key. License-clean by construction.
Wrapped in repo/ like every third-party client per the layering rules.
"""

from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw

_N_POINTS = 650


def _base_subject(seed: int = 11) -> tuple[np.ndarray, np.ndarray]:
    """A blobby humanoid point cloud + per-point colors, generated once."""
    rng = np.random.default_rng(seed)
    theta = rng.uniform(0, 2 * np.pi, _N_POINTS)
    height = rng.uniform(-1.0, 1.0, _N_POINTS)
    radius = 0.45 * (1.0 - 0.35 * np.abs(height)) * np.sqrt(rng.uniform(0, 1, _N_POINTS))
    xyz = np.stack(
        [radius * np.cos(theta), height, radius * np.sin(theta)], axis=1
    ).astype(np.float32)
    hue = (theta / (2 * np.pi) + 0.5 * (height + 1)) % 1.0
    rgb = _hsv_to_rgb(hue, 0.55, 0.95)
    return xyz, rgb


def _hsv_to_rgb(h: np.ndarray, s: float, v: float) -> np.ndarray:
    i = np.floor(h * 6).astype(int)
    f = h * 6 - i
    p, q, t = v * (1 - s), v * (1 - f * s), v * (1 - (1 - f) * s)
    i = i % 6
    r = np.choose(i, [v, q, p, p, t, v])
    g = np.choose(i, [t, v, v, q, p, p])
    b = np.choose(i, [p, p, t, v, v, q])
    return np.clip(np.stack([r, g, b], axis=1) * 255, 0, 255).astype(np.uint8)


def _roty(angle: float) -> np.ndarray:
    c, s = np.cos(angle), np.sin(angle)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], dtype=np.float32)


def scene_points(preset: str, t01: float) -> tuple[np.ndarray, np.ndarray]:
    """Animate the subject for a normalized timestamp t01 in [0, 1]."""
    xyz, rgb = _base_subject()
    if preset == "orbit-dancer":
        xyz = xyz @ _roty(2 * np.pi * t01).T
        xyz = xyz + np.array([0, 0.15 * np.sin(2 * np.pi * t01), 0], dtype=np.float32)
    elif preset == "bouncing-prims":
        phase = (xyz[:, 1] > 0).astype(np.float32)
        bounce = 0.4 * np.abs(np.sin(2 * np.pi * (t01 + 0.25 * phase)))
        xyz = xyz.copy()
        xyz[:, 1] = xyz[:, 1] + bounce
    else:  # rotating-bust
        xyz = xyz @ _roty(0.5 * np.pi * t01).T
    return xyz.astype(np.float32), rgb


def _background(width: int, height: int) -> Image.Image:
    grad = np.linspace(38, 14, height, dtype=np.uint8)[:, None]
    arr = np.repeat(grad, width, axis=1)
    rgb = np.stack([arr, arr, np.clip(arr + 10, 0, 255)], axis=2)
    return Image.fromarray(rgb, "RGB")


def _project(xyz: np.ndarray, camera: dict) -> tuple[np.ndarray, np.ndarray]:
    """World points -> pixel coords + depth (OpenCV pinhole)."""
    rot = np.asarray(camera["R"], dtype=np.float32)
    trans = np.asarray(camera["T"], dtype=np.float32)
    cam = xyz @ rot.T + trans
    z = cam[:, 2]
    x = camera["fx"] * cam[:, 0] / z + camera["cx"]
    y = camera["fy"] * cam[:, 1] / z + camera["cy"]
    return np.stack([x, y], axis=1), z


def render_frame(preset: str, camera: dict, t01: float) -> Image.Image:
    width, height = int(camera["width"]), int(camera["height"])
    img = _background(width, height)
    draw = ImageDraw.Draw(img)
    xyz, rgb = scene_points(preset, t01)
    uv, z = _project(xyz, camera)
    order = np.argsort(-z)  # painter's algorithm: far first
    for idx in order:
        if z[idx] <= 0.05:
            continue
        px, py = float(uv[idx, 0]), float(uv[idx, 1])
        if px < -8 or px > width + 8 or py < -8 or py > height + 8:
            continue
        r = max(1.5, 3.2 / z[idx] * (width / 256))
        color = (int(rgb[idx, 0]), int(rgb[idx, 1]), int(rgb[idx, 2]))
        draw.ellipse([px - r, py - r, px + r, py + r], fill=color)
    return img


def render_scene(
    preset: str, cameras: list[dict], frames_per_camera: int
) -> dict[str, list[Image.Image]]:
    """Per-camera frame sequences of the animated subject."""
    out: dict[str, list[Image.Image]] = {}
    for cam in cameras:
        frames: list[Image.Image] = []
        for f in range(frames_per_camera):
            t01 = f / max(frames_per_camera - 1, 1)
            frames.append(render_frame(preset, cam, t01))
        out[cam["id"]] = frames
    return out
