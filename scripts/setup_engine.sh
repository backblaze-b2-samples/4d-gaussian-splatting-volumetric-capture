#!/usr/bin/env bash
#
# setup_engine.sh — bootstrap the CUDA-only hustvl/4DGaussians training engine.
#
# The 4D Gaussian Splatting rasterizer (depth-diff-gaussian-rasterization) and
# simple-knn are CUDA-only: there are NO CPU or Apple-MPS kernels. So the engine
# lives OUT of the base requirements. Everything the CPU-runnable pipeline needs
# (ingest, ffmpeg frame extraction, calibration, init cloud, dataset staging,
# preview, all B2 I/O, the explorer and dashboard) installs with `pnpm run setup`
# and runs everywhere. Only the train/export tail needs this script, and only on
# a CUDA host.
#
# What it does:
#   1. Clones hustvl/4DGaussians into ${FOURDGS_REPO_DIR:-engines/4DGaussians}.
#   2. Installs its Python requirements plus the two CUDA submodules
#      (depth-diff-gaussian-rasterization, simple-knn) into the ACTIVE Python
#      environment — activate the API venv first if you want them there.
#   3. Prints the FOURDGS_REPO_DIR line to add to your .env.
#
# Usage (on a CUDA host):
#   source services/api/.venv/bin/activate        # optional but recommended
#   FOURDGS_REPO_DIR=engines/4DGaussians bash scripts/setup_engine.sh
#
# This script is intentionally NOT invoked by `pnpm run setup`, `pnpm verify`, or
# CI — those must stay CPU-clean and keyless.

set -euo pipefail

REPO_URL="https://github.com/hustvl/4DGaussians"
TARGET_DIR="${FOURDGS_REPO_DIR:-engines/4DGaussians}"

echo "==> 4DGaussians engine bootstrap (CUDA-only)"

if ! command -v nvidia-smi >/dev/null 2>&1; then
  echo "WARNING: nvidia-smi not found — 4DGaussians training requires an NVIDIA"
  echo "         CUDA GPU. The CPU pipeline (dataset staging + all B2 I/O) works"
  echo "         without this engine; only train/export need it. Continuing so"
  echo "         the clone still works, but training will not run on this host."
fi

if [ -d "${TARGET_DIR}/.git" ]; then
  echo "==> Engine already present at ${TARGET_DIR} — pulling latest"
  git -C "${TARGET_DIR}" pull --ff-only || true
else
  echo "==> Cloning ${REPO_URL} (with submodules) into ${TARGET_DIR}"
  git clone --recursive "${REPO_URL}" "${TARGET_DIR}"
fi

echo "==> Installing engine Python requirements into the active environment"
if [ -f "${TARGET_DIR}/requirements.txt" ]; then
  pip install -r "${TARGET_DIR}/requirements.txt"
fi

echo "==> Building the two CUDA submodules (rasterizer + simple-knn)"
pip install "${TARGET_DIR}/submodules/depth-diff-gaussian-rasterization"
pip install "${TARGET_DIR}/submodules/simple-knn"

ABS_DIR="$(cd "${TARGET_DIR}" && pwd)"
echo ""
echo "==> Done. Add this line to your .env so the app can locate the engine:"
echo ""
echo "    FOURDGS_REPO_DIR=${ABS_DIR}"
echo ""
echo "Then run a session: the train/export stages will invoke ${TARGET_DIR}/train.py"
echo "in an isolated subprocess and upload checkpoints + the final .ply splat to B2."
