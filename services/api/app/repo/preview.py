"""Always-works preview PNG: a multi-view contact sheet + init-cloud scatter.

matplotlib's Agg backend is the PRIMARY renderer (no GPU on the default path).
If it ever fails, a plain PIL contact sheet is the last-resort fallback, so the
preview never hard-fails. Wrapped in repo/ per the layering rules.
"""

from __future__ import annotations

import io
import math

import matplotlib

matplotlib.use("Agg")  # headless — must precede pyplot import
import matplotlib.pyplot as plt
import mpl_toolkits.mplot3d  # noqa: F401  (registers the 3d projection)
import numpy as np
from PIL import Image


def _pil_contact_sheet(frames_by_cam: dict[str, bytes]) -> bytes:
    thumbs = [Image.open(io.BytesIO(b)).convert("RGB") for b in frames_by_cam.values()]
    if not thumbs:
        return _blank_png()
    tw, th = 160, 100
    cols = min(4, len(thumbs))
    rows = math.ceil(len(thumbs) / cols)
    sheet = Image.new("RGB", (cols * tw, rows * th), (18, 18, 22))
    for i, thumb in enumerate(thumbs):
        sheet.paste(thumb.resize((tw, th)), ((i % cols) * tw, (i // cols) * th))
    buf = io.BytesIO()
    sheet.save(buf, format="PNG")
    return buf.getvalue()


def _blank_png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (320, 200), (18, 18, 22)).save(buf, format="PNG")
    return buf.getvalue()


def render_preview(
    frames_by_cam: dict[str, bytes],
    init_xyz: np.ndarray | None = None,
    init_rgb: np.ndarray | None = None,
) -> bytes:
    """Contact sheet of one frame per camera plus a 3D scatter of the init cloud."""
    try:
        cams = list(frames_by_cam.items())
        n = max(len(cams), 1)
        cols = min(4, n)
        thumb_rows = math.ceil(n / cols)
        has_cloud = init_xyz is not None and len(init_xyz) > 0
        total_rows = thumb_rows + (1 if has_cloud else 0)
        fig = plt.figure(figsize=(cols * 2.3, thumb_rows * 1.7 + (2.8 if has_cloud else 0.4)))
        gs = fig.add_gridspec(total_rows, cols)

        for i, (cam_id, jpg) in enumerate(cams):
            ax = fig.add_subplot(gs[i // cols, i % cols])
            ax.imshow(Image.open(io.BytesIO(jpg)))
            ax.set_title(cam_id, fontsize=8)
            ax.axis("off")

        if has_cloud:
            pts = np.asarray(init_xyz)[:30000]
            ax3d = fig.add_subplot(gs[thumb_rows, :], projection="3d")
            colors = None
            if init_rgb is not None and len(init_rgb) >= len(pts):
                colors = np.asarray(init_rgb)[: len(pts)] / 255.0
            ax3d.scatter(
                pts[:, 0], pts[:, 2], pts[:, 1], c=colors, s=2, depthshade=True
            )
            ax3d.set_title("init point cloud", fontsize=9)
            ax3d.set_xticks([])
            ax3d.set_yticks([])
            ax3d.set_zticks([])

        fig.suptitle("Synchronized multi-view capture", fontsize=11)
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
        plt.close(fig)
        return buf.getvalue()
    except Exception:
        # Never let a preview crash the run — fall back to a plain PIL sheet.
        return _pil_contact_sheet(frames_by_cam)
