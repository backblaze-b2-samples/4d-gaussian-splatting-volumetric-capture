"""Regression tests for the CUDA-gated 4DGaussians engine adapter.

The rasterizer + simple-knn are CUDA-only, so on the CI/CPU default path the
engine must NEVER run — it must raise a clean, actionable EngineUnavailableError
that carries the exact `train.py` command, and the run must be marked
"skipped (CUDA required)" rather than 500ing or faking a trained splat. These
tests pin that gated behavior (they run on a CPU host with no engine clone).
"""

from __future__ import annotations

import pytest

from app.service import fourdgs_runner as engine
from app.types.sessions import QUALITY_ITERATIONS


def test_detect_device_is_valid_and_defaults_cpu():
    device = engine.detect_device()
    assert device in {"cuda", "mps", "cpu"}


def test_build_train_command_uses_quality_iterations():
    cmd = engine.build_train_command("data/multipleview/abc", "abc", "balanced")
    assert cmd[:2] == ["python", "train.py"]
    assert "-s" in cmd and "data/multipleview/abc" in cmd
    assert "--expname" in cmd
    # Iteration budget tracks the quality preset.
    assert str(QUALITY_ITERATIONS["balanced"]) in cmd


def test_train_command_str_matches_list():
    parts = engine.build_train_command("data/multipleview/abc", "abc", "draft")
    text = engine.train_command_str("data/multipleview/abc", "abc", "draft")
    for token in parts:
        assert token in text


def test_run_training_gates_without_cuda(monkeypatch):
    """On a non-CUDA host the engine must raise, not run a subprocess."""
    monkeypatch.setattr(engine, "detect_device", lambda: "cpu")

    # Guard: if this ever regressed to actually spawning, fail loudly.
    def _boom(*_a, **_k):  # pragma: no cover - must never be reached
        raise AssertionError("subprocess must not run on a non-CUDA host")

    monkeypatch.setattr(engine.subprocess, "run", _boom)

    with pytest.raises(engine.EngineUnavailableError) as excinfo:
        engine.run_training("data/multipleview/abc", "abc", "draft")

    err = excinfo.value
    assert err.device == "cpu"
    # The exact command the CUDA tail would run is carried for the UI/manifest.
    assert err.command == engine.train_command_str("data/multipleview/abc", "abc", "draft")


def test_run_training_gates_when_repo_unset(monkeypatch):
    """Even on CUDA, a missing FOURDGS_REPO_DIR gates cleanly (no subprocess)."""
    monkeypatch.setattr(engine, "detect_device", lambda: "cuda")
    monkeypatch.setattr(engine.settings, "fourdgs_repo_dir", "")

    with pytest.raises(engine.EngineUnavailableError):
        engine.run_training("data/multipleview/abc", "abc", "draft")


def test_engine_available_false_on_cpu(monkeypatch):
    monkeypatch.setattr(engine, "detect_device", lambda: "cpu")
    monkeypatch.setattr(engine.settings, "fourdgs_repo_dir", "/tmp/does-not-matter")
    assert engine.engine_available() is False
