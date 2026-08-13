"""hustvl/4DGaussians engine adapter — device detection, train command, gating.

The rasterizer (`depth-diff-gaussian-rasterization`) and `simple-knn` are
CUDA-only: there are no CPU/MPS kernels. So the engine is out of the base
requirements, installed by `scripts/setup_engine.sh` on a CUDA host and located
via `FOURDGS_REPO_DIR`. This adapter auto-detects the device (CUDA -> MPS ->
CPU, default CPU), emits the EXACT `train.py` command, and — when CUDA or the
repo is missing — raises `EngineUnavailableError` WITHOUT running anything. The
runner turns that into a "skipped (CUDA required)" stage; the trained splat is
never faked.
"""

from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

from app.config import settings
from app.types.sessions import QUALITY_ITERATIONS


class EngineUnavailableError(Exception):
    """Raised when 4DGaussians training cannot run on this host (no CUDA/repo).

    Carries the exact command that WOULD have run so the UI/manifest can show it
    and a CUDA host can copy-paste it.
    """

    def __init__(self, detail: str, command: str, device: str):
        self.detail = detail
        self.command = command
        self.device = device
        super().__init__(detail)


def detect_device() -> str:
    """First available of CUDA -> Apple MPS -> CPU, defaulting to CPU.

    torch is not in the base requirements, so import it lazily: on the default
    (CPU) path it simply isn't present and we report `cpu` — never an
    unconditional `.cuda()` or a GPU assert.
    """
    try:
        import torch
    except ImportError:
        return "cpu"
    try:
        if torch.cuda.is_available():
            return "cuda"
        mps = getattr(torch.backends, "mps", None)
        if mps is not None and mps.is_available():
            return "mps"
    except Exception:
        return "cpu"
    return "cpu"


def build_train_command(dataset_dir: str, expname: str, quality: str) -> list[str]:
    """The exact 4DGaussians `train.py` invocation for this session."""
    iterations = QUALITY_ITERATIONS.get(quality, QUALITY_ITERATIONS["draft"])
    return [
        "python",
        "train.py",
        "-s", dataset_dir,
        "--expname", f"multipleview/{expname}",
        "--configs", "arguments/multipleview/default.py",
        "--iterations", str(iterations),
    ]


def train_command_str(dataset_dir: str, expname: str, quality: str) -> str:
    return shlex.join(build_train_command(dataset_dir, expname, quality))


def engine_available() -> bool:
    return detect_device() == "cuda" and bool(settings.fourdgs_repo_dir)


def run_training(dataset_dir: str, expname: str, quality: str) -> dict:
    """Run 4DGaussians train.py in an isolated subprocess (CUDA hosts only).

    Raises EngineUnavailableError (never runs) on a non-CUDA host or when
    FOURDGS_REPO_DIR is unset. Returns run metadata on success.
    """
    device = detect_device()
    command = train_command_str(dataset_dir, expname, quality)
    repo_dir = settings.fourdgs_repo_dir

    if device != "cuda" or not repo_dir:
        raise EngineUnavailableError(
            "4DGaussians training requires a CUDA GPU and a local engine clone. "
            "Install it with scripts/setup_engine.sh and set FOURDGS_REPO_DIR, "
            "then run the emitted command on a CUDA host.",
            command=command,
            device=device,
        )

    repo = Path(repo_dir)
    if not (repo / "train.py").exists():
        raise EngineUnavailableError(
            f"FOURDGS_REPO_DIR={repo_dir} does not contain train.py — clone "
            "hustvl/4DGaussians there (scripts/setup_engine.sh).",
            command=command,
            device=device,
        )

    # Real invocation: isolated subprocess, the engine's own working directory.
    proc = subprocess.run(
        build_train_command(dataset_dir, expname, quality),
        cwd=str(repo),
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        tail = (proc.stderr or "").strip().splitlines()[-12:]
        raise RuntimeError("4DGaussians train.py failed: " + " | ".join(tail))
    return {"device": device, "command": command, "output_dir": f"output/multipleview/{expname}"}
