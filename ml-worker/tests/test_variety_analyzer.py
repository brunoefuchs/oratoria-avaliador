"""Tests for workers.variety_analyzer — Story 8.1 Truth Contract (T3).

Cobre vetos T3.1 (retorna WorkerResult), T3.2 (zero score=0 fake),
T3.3 (exception captura em WorkerFailure crashed).
"""

import pytest

from contracts import WorkerFailure, WorkerSuccess
from workers.variety_analyzer import (
    _upstream_failed,
    analyze_variety,
    analyze_variety_legacy,
)


# ---------- Fixtures ----------


@pytest.fixture
def voice_ok() -> dict:
    return {
        "audio_duration_seconds": 60,
        "wpm_por_janela": [120, 140, 160, 130, 150],
        "pitch_por_janela": [100, 120, 110, 130, 105],
        "volume_por_janela": [-20, -22, -18, -25, -20],
        "cv_velocidade": 0.15,
        "cv_pitch": 0.12,
        "cv_volume": 0.10,
        "janela_size_seconds": 12,
    }


@pytest.fixture
def gesture_ok() -> dict:
    return {"metrics": {"gesticulation_pct": 50, "vocabulario_gestos": 6}}


# ---------- Happy path ----------


def test_analyze_variety_returns_worker_success(voice_ok, gesture_ok):
    """Veto T3.1: retorna WorkerResult (nao dict)."""
    result = analyze_variety(voice_ok, gesture_ok)
    assert isinstance(result, WorkerSuccess)
    assert result.dimension == "variety"
    assert 0 <= result.score <= 100
    assert result.dimension_status == "ok"
    assert result.confidence == 0.95


def test_analyze_variety_success_has_rich_metrics(voice_ok, gesture_ok):
    result = analyze_variety(voice_ok, gesture_ok)
    assert "diagnostico_geral" in result.metrics
    assert "sub_scores" in result.metrics
    assert "trechos_monotonos" in result.metrics


# ---------- Upstream failure detection (veto T3.2) ----------


def test_voice_legacy_failed_returns_failure(voice_ok, gesture_ok):
    voice_failed = {"confidence": "failed", "score": 0}
    result = analyze_variety(voice_failed, gesture_ok)
    assert isinstance(result, WorkerFailure)
    assert result.dimension_status == "skipped"
    assert result.score is None  # veto T3.2: nunca score=0 fake
    assert "voice_analyzer" in result.failure_reason


def test_voice_new_schema_unavailable_returns_failure(voice_ok, gesture_ok):
    """Workers novos (facial/tonality/opening) usam disponivel: bool."""
    voice_unavail = {"disponivel": False}
    result = analyze_variety(voice_unavail, gesture_ok)
    assert isinstance(result, WorkerFailure)
    assert result.dimension_status == "skipped"


def test_voice_worker_failure_schema_returns_failure(voice_ok, gesture_ok):
    """Schema novissimo: outro worker ja retornou WorkerFailure como dict."""
    voice_failure = {
        "dimension": "voice",
        "dimension_status": "failed",
        "failure_reason": "audio missing",
    }
    result = analyze_variety(voice_failure, gesture_ok)
    assert isinstance(result, WorkerFailure)
    assert result.dimension_status == "skipped"


def test_gesture_failed_returns_failure(voice_ok, gesture_ok):
    gesture_failed = {"confidence": "failed"}
    result = analyze_variety(voice_ok, gesture_failed)
    assert isinstance(result, WorkerFailure)
    assert "gesture_analyzer" in result.failure_reason


def test_none_inputs_return_failure(gesture_ok):
    result = analyze_variety(None, gesture_ok)
    assert isinstance(result, WorkerFailure)


# ---------- Insufficient data ----------


def test_missing_audio_duration_returns_insufficient_data(gesture_ok):
    voice_no_duration = {"wpm_por_janela": [120, 140]}
    result = analyze_variety(voice_no_duration, gesture_ok)
    assert isinstance(result, WorkerFailure)
    assert result.dimension_status == "insufficient_data"


def test_zero_audio_duration_returns_insufficient_data(gesture_ok):
    voice_zero = {"audio_duration_seconds": 0}
    result = analyze_variety(voice_zero, gesture_ok)
    assert isinstance(result, WorkerFailure)
    assert result.dimension_status == "insufficient_data"


# ---------- Crashed (veto T3.3) ----------


def test_invalid_type_returns_crashed(voice_ok):
    """Veto T3.3: excecao durante compute → WorkerFailure(crashed), nao propaga."""
    result = analyze_variety(voice_ok, "not_a_dict")
    assert isinstance(result, WorkerFailure)
    # "not_a_dict" nao passa em isinstance check de _upstream_failed → cai em skipped
    assert result.dimension_status in ("skipped", "crashed")


def test_exception_in_compute_captured(monkeypatch, voice_ok, gesture_ok):
    """Forca excecao dentro de _compute_variety_metrics → WorkerFailure(crashed)."""
    from workers import variety_analyzer

    def boom(*args, **kwargs):
        raise RuntimeError("simulated boom during compute")

    monkeypatch.setattr(variety_analyzer, "_compute_variety_metrics", boom)
    result = analyze_variety(voice_ok, gesture_ok)
    assert isinstance(result, WorkerFailure)
    assert result.dimension_status == "crashed"
    assert "RuntimeError" in result.failure_reason
    assert "simulated boom" in result.failure_reason


# ---------- Legacy path (feature flag OFF) ----------


def test_analyze_variety_legacy_returns_dict(voice_ok, gesture_ok):
    result = analyze_variety_legacy(voice_ok, gesture_ok)
    assert isinstance(result, dict)
    assert "score" in result
    assert "metrics" in result
    assert result["confidence"] == "high"


def test_legacy_matches_new_success_score(voice_ok, gesture_ok):
    """Migracao nao muda score de happy path."""
    legacy = analyze_variety_legacy(voice_ok, gesture_ok)
    new = analyze_variety(voice_ok, gesture_ok)
    assert isinstance(new, WorkerSuccess)
    assert legacy["score"] == new.score


# ---------- _upstream_failed helper ----------


def test_upstream_failed_none():
    assert _upstream_failed(None) is True


def test_upstream_failed_empty_dict():
    assert _upstream_failed({}) is True


def test_upstream_failed_legacy_confidence_failed():
    assert _upstream_failed({"confidence": "failed"}) is True


def test_upstream_failed_disponivel_false():
    assert _upstream_failed({"disponivel": False}) is True


def test_upstream_failed_dimension_status_failed():
    assert _upstream_failed({"dimension_status": "failed"}) is True


def test_upstream_failed_dimension_status_ok():
    assert _upstream_failed({"dimension_status": "ok"}) is False


def test_upstream_failed_non_dict():
    assert _upstream_failed("not a dict") is True
    assert _upstream_failed(42) is True


def test_upstream_not_failed_when_valid():
    assert _upstream_failed({"score": 80, "confidence": "high"}) is False
