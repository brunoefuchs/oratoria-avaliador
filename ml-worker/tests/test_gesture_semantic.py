"""Tests for gesture_semantic_analyzer + _frame_sampler — Story 9.6.

Mockado — zero chamada real a Gemini API.
Valida:
- estimate_cost pricing
- Budget guard trigger
- JSON parse + retry
- WorkerSuccess / WorkerFailure schema compliance
- Dimension registry (gesture_semantic em SECONDARY_DIMENSIONS)
- Config flags
"""

from __future__ import annotations

import importlib
from unittest.mock import patch

from contracts import WorkerFailure, WorkerSuccess
from workers._frame_sampler import (
    GEMINI_FLASH_IMAGE_TOKENS,
    estimate_cost,
)

# ─────────────────────────────────────────────────────────────
# Frame sampler — cost estimation
# ─────────────────────────────────────────────────────────────


def test_estimate_cost_scales_linearly():
    cost_60 = estimate_cost(60)
    cost_120 = estimate_cost(120)
    assert cost_60 > 0
    assert cost_120 > cost_60
    # Approximadamente 2x (tokens de imagem dominam)
    assert 1.5 * cost_60 < cost_120 < 2.5 * cost_60


def test_estimate_cost_within_budget_for_3min_video():
    """3min @ 0.5fps = 90 frames. Deve caber em $0.10 budget (Flash)."""
    cost = estimate_cost(90)
    assert cost < 0.10


def test_estimate_cost_120_frames_hard_cap():
    """Max 120 frames ainda dentro do default budget $0.10."""
    cost = estimate_cost(120)
    assert cost < 0.10


def test_image_token_constant():
    assert GEMINI_FLASH_IMAGE_TOKENS == 258


# ─────────────────────────────────────────────────────────────
# Dimension registry
# ─────────────────────────────────────────────────────────────


def test_gesture_semantic_in_secondary_dimensions():
    from contracts.dimensions import SECONDARY_DIMENSIONS

    assert "gesture_semantic" in SECONDARY_DIMENSIONS


def test_gesture_semantic_confidence_media():
    from contracts.dimensions import DIMENSION_CONFIDENCE

    assert DIMENSION_CONFIDENCE["gesture_semantic"] == "media"


def test_gesture_semantic_in_worker_module_map():
    from contracts.dimensions import DIMENSION_TO_WORKER_MODULE

    assert DIMENSION_TO_WORKER_MODULE["gesture_semantic"] == "workers.gesture_semantic_analyzer"


def test_all_dimensions_count_16():
    """Story 9.6: 13 dims + gesture_semantic = 14.
    +articulation (2026-04-30) +discourse_arc (Story 10.3) = 16."""
    from contracts.dimensions import ALL_DIMENSIONS

    assert len(ALL_DIMENSIONS) == 16


# ─────────────────────────────────────────────────────────────
# analyze_gesture_semantic — missing API key
# ─────────────────────────────────────────────────────────────


def test_missing_api_key_returns_failure(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    import config
    import workers.gesture_semantic_analyzer as gsa

    importlib.reload(config)
    importlib.reload(gsa)

    result = gsa.analyze_gesture_semantic("/fake/video.mp4", [])
    assert isinstance(result, WorkerFailure)
    assert "GEMINI_API_KEY" in result.failure_reason


# ─────────────────────────────────────────────────────────────
# analyze_gesture_semantic — budget guard
# ─────────────────────────────────────────────────────────────


def test_budget_guard_triggers_when_over(monkeypatch):
    """Budget $0.001 + 90 frames → estimated cost excede → WorkerFailure."""
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.setenv("GESTURE_SEMANTIC_MAX_COST_PER_EVAL", "0.001")

    import config
    import workers.gesture_semantic_analyzer as gsa

    importlib.reload(config)
    importlib.reload(gsa)

    fake_frames = [{"timestamp_s": i * 2.0, "image_b64": "fake"} for i in range(90)]

    with patch("workers._frame_sampler.sample_frames_base64", return_value=fake_frames):
        result = gsa.analyze_gesture_semantic("/fake/video.mp4", [])

    assert isinstance(result, WorkerFailure)
    assert result.dimension_status == "skipped"
    assert "excede budget" in result.failure_reason


def test_budget_guard_passes_under_budget(monkeypatch):
    """Budget $1.0 + 30 frames → passa → chama Gemini."""
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.setenv("GESTURE_SEMANTIC_MAX_COST_PER_EVAL", "1.0")

    import config
    import workers.gesture_semantic_analyzer as gsa

    importlib.reload(config)
    importlib.reload(gsa)

    fake_frames = [{"timestamp_s": i * 2.0, "image_b64": "fake"} for i in range(30)]
    fake_response = {
        "per_frame": [
            {
                "timestamp_s": 0.0,
                "gesture_type": "open_palm",
                "reinforces_message": True,
                "distracts": False,
            }
        ],
        "global": {
            "gesture_narrative_coherence_score": 78,
            "rationale": "Gestos coerentes com tom do discurso",
        },
    }

    with patch("workers._frame_sampler.sample_frames_base64", return_value=fake_frames):
        with patch(
            "workers.gesture_semantic_analyzer._call_gemini_vision",
            return_value=fake_response,
        ):
            result = gsa.analyze_gesture_semantic("/fake/video.mp4", [])

    assert isinstance(result, WorkerSuccess)
    assert result.score == 78
    assert result.dimension == "gesture_semantic"
    assert "rationale" in result.metrics


# ─────────────────────────────────────────────────────────────
# Empty frames → WorkerFailure
# ─────────────────────────────────────────────────────────────


def test_empty_frames_returns_failure(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    import config
    import workers.gesture_semantic_analyzer as gsa

    importlib.reload(config)
    importlib.reload(gsa)

    with patch("workers._frame_sampler.sample_frames_base64", return_value=[]):
        result = gsa.analyze_gesture_semantic("/fake/video.mp4", [])

    assert isinstance(result, WorkerFailure)
    assert "zero frames" in result.failure_reason


# ─────────────────────────────────────────────────────────────
# Retry when JSON invalid
# ─────────────────────────────────────────────────────────────


def test_retry_on_invalid_json(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.setenv("GESTURE_SEMANTIC_MAX_COST_PER_EVAL", "1.0")

    import config
    import workers.gesture_semantic_analyzer as gsa

    importlib.reload(config)
    importlib.reload(gsa)

    fake_frames = [{"timestamp_s": 0.0, "image_b64": "fake"}]

    call_count = {"n": 0}

    def flaky_call(**kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return None  # primeira tentativa falha
        return {
            "per_frame": [],
            "global": {"gesture_narrative_coherence_score": 60, "rationale": "retry"},
        }

    with patch("workers._frame_sampler.sample_frames_base64", return_value=fake_frames):
        with patch("workers.gesture_semantic_analyzer._call_gemini_vision", side_effect=flaky_call):
            result = gsa.analyze_gesture_semantic("/fake/video.mp4", [])

    assert isinstance(result, WorkerSuccess)
    assert call_count["n"] == 2  # tentou 2x


def test_retry_exhausted_returns_failure(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.setenv("GESTURE_SEMANTIC_MAX_COST_PER_EVAL", "1.0")

    import config
    import workers.gesture_semantic_analyzer as gsa

    importlib.reload(config)
    importlib.reload(gsa)

    fake_frames = [{"timestamp_s": 0.0, "image_b64": "fake"}]

    with patch("workers._frame_sampler.sample_frames_base64", return_value=fake_frames):
        with patch("workers.gesture_semantic_analyzer._call_gemini_vision", return_value=None):
            result = gsa.analyze_gesture_semantic("/fake/video.mp4", [])

    assert isinstance(result, WorkerFailure)
    assert "JSON invalido" in result.failure_reason


# ─────────────────────────────────────────────────────────────
# Flag integration
# ─────────────────────────────────────────────────────────────


def test_flag_off_by_default(monkeypatch):
    monkeypatch.delenv("GESTURE_SEMANTIC_ENABLED", raising=False)
    import config

    importlib.reload(config)
    assert config.is_gesture_semantic_enabled() is False


def test_flag_on_with_env(monkeypatch):
    monkeypatch.setenv("GESTURE_SEMANTIC_ENABLED", "true")
    import config

    importlib.reload(config)
    assert config.is_gesture_semantic_enabled() is True


def test_budget_env_override(monkeypatch):
    monkeypatch.setenv("GESTURE_SEMANTIC_MAX_COST_PER_EVAL", "0.25")
    import config

    importlib.reload(config)
    assert config.GESTURE_SEMANTIC_MAX_COST_PER_EVAL == 0.25


# ─────────────────────────────────────────────────────────────
# Prompt building
# ─────────────────────────────────────────────────────────────


def test_prompt_includes_schema():
    from workers.gesture_semantic_analyzer import _build_prompt

    prompt = _build_prompt([])
    assert "per_frame" in prompt
    assert "gesture_narrative_coherence_score" in prompt


def test_prompt_samples_long_transcript():
    from workers.gesture_semantic_analyzer import _build_prompt

    long_transcript = [{"word": f"palavra{i}", "start": i * 0.5} for i in range(1000)]
    prompt = _build_prompt(long_transcript)
    # Nao deve colar 1000 palavras (seria prompt gigante)
    assert len(prompt) < 50000
