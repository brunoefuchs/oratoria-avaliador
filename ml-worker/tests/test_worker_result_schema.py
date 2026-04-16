"""Tests for contracts.worker_result — Story 8.1 Truth Contract Fundacao (T1).

Cobre vetos T1.1 (extra=forbid), T1.2 (Success rejeita score=None),
T1.3 (Failure rejeita score != None), discriminated union dispatch,
e validacao de score range.
"""

import pytest
from pydantic import TypeAdapter, ValidationError

from contracts.worker_result import (
    DimensionStatus,
    FailureReason,
    WorkerFailure,
    WorkerResult,
    WorkerSuccess,
)


# ---------- WorkerSuccess ----------


def test_success_happy_path():
    s = WorkerSuccess(dimension="variety", score=87, metrics={"cv_volume": 0.12})
    assert s.dimension == "variety"
    assert s.score == 87
    assert s.dimension_status == "ok"
    assert s.confidence == 1.0


def test_success_explicit_confidence():
    s = WorkerSuccess(
        dimension="voice", score=50, metrics={}, confidence=0.7
    )
    assert s.confidence == 0.7


def test_success_rejects_score_none():
    """Veto T1.2 — Success deve rejeitar score=None (type error)."""
    with pytest.raises(ValidationError):
        WorkerSuccess(dimension="voice", score=None, metrics={})


def test_success_rejects_score_above_100():
    with pytest.raises(ValidationError):
        WorkerSuccess(dimension="voice", score=150, metrics={})


def test_success_rejects_score_below_zero():
    with pytest.raises(ValidationError):
        WorkerSuccess(dimension="voice", score=-1, metrics={})


def test_success_rejects_invalid_dimension():
    """Literal type rejeita dimensao desconhecida."""
    with pytest.raises(ValidationError):
        WorkerSuccess(dimension="invalid_xyz", score=50, metrics={})


def test_success_rejects_extra_field():
    """Veto T1.1 — extra='forbid' bloqueia chaves desconhecidas."""
    with pytest.raises(ValidationError):
        WorkerSuccess(
            dimension="voice", score=50, metrics={}, unexpected_key="boom"
        )


def test_success_rejects_invalid_confidence():
    with pytest.raises(ValidationError):
        WorkerSuccess(dimension="voice", score=50, metrics={}, confidence=1.5)


def test_success_is_frozen():
    """Modelo eh imutavel apos construcao (model_config frozen=True)."""
    s = WorkerSuccess(dimension="voice", score=50, metrics={})
    with pytest.raises(ValidationError):
        s.score = 100


# ---------- WorkerFailure ----------


def test_failure_happy_path():
    f = WorkerFailure(
        dimension="facial",
        dimension_status="failed",
        failure_reason="video_too_short",
    )
    assert f.dimension == "facial"
    assert f.score is None
    assert f.failure_reason == "video_too_short"
    assert f.metrics == {}


def test_failure_with_metrics():
    f = WorkerFailure(
        dimension="voice",
        dimension_status="insufficient_data",
        failure_reason="audio under 5s",
        metrics={"audio_duration_s": 3.2},
    )
    assert f.metrics["audio_duration_s"] == 3.2


def test_failure_rejects_score_not_none():
    """Veto T1.3 — Failure deve rejeitar score != None (incoerencia)."""
    with pytest.raises(ValidationError):
        WorkerFailure(
            dimension="voice",
            dimension_status="failed",
            failure_reason="x",
            score=0,
        )
    with pytest.raises(ValidationError):
        WorkerFailure(
            dimension="voice",
            dimension_status="failed",
            failure_reason="x",
            score=50,
        )


def test_failure_rejects_empty_reason():
    """min_length=1 — failure_reason vazio mente sobre o motivo."""
    with pytest.raises(ValidationError):
        WorkerFailure(dimension="voice", dimension_status="failed", failure_reason="")


def test_failure_rejects_ok_status():
    """Failure nao pode ter status='ok' — esse e o discriminador do Success."""
    with pytest.raises(ValidationError):
        WorkerFailure(
            dimension="voice", dimension_status="ok", failure_reason="x"
        )


def test_failure_accepts_all_failure_statuses():
    for status in ("failed", "skipped", "insufficient_data", "crashed"):
        f = WorkerFailure(
            dimension="voice", dimension_status=status, failure_reason="reason"
        )
        assert f.dimension_status == status


def test_failure_rejects_extra_field():
    """Veto T1.1 — extra='forbid' tambem em Failure."""
    with pytest.raises(ValidationError):
        WorkerFailure(
            dimension="voice",
            dimension_status="failed",
            failure_reason="x",
            random_field="boom",
        )


# ---------- WorkerResult Discriminated Union ----------


def test_discriminated_union_dispatches_to_success():
    """Dispatch via dimension_status='ok' → WorkerSuccess."""
    adapter = TypeAdapter(WorkerResult)
    payload = {
        "dimension": "voice",
        "dimension_status": "ok",
        "score": 75,
        "metrics": {},
    }
    result = adapter.validate_python(payload)
    assert isinstance(result, WorkerSuccess)
    assert result.score == 75


def test_discriminated_union_dispatches_to_failure():
    """Dispatch via dimension_status='failed' → WorkerFailure."""
    adapter = TypeAdapter(WorkerResult)
    payload = {
        "dimension": "voice",
        "dimension_status": "failed",
        "failure_reason": "audio missing",
    }
    result = adapter.validate_python(payload)
    assert isinstance(result, WorkerFailure)
    assert result.score is None


def test_discriminated_union_rejects_unknown_status():
    adapter = TypeAdapter(WorkerResult)
    with pytest.raises(ValidationError):
        adapter.validate_python(
            {"dimension": "voice", "dimension_status": "unknown_status"}
        )


# ---------- DimensionStatus enum ----------


def test_dimension_status_values():
    assert DimensionStatus.OK.value == "ok"
    assert DimensionStatus.FAILED.value == "failed"
    assert DimensionStatus.SKIPPED.value == "skipped"
    assert DimensionStatus.INSUFFICIENT_DATA.value == "insufficient_data"
    assert DimensionStatus.CRASHED.value == "crashed"


# ---------- FailureReason enum ----------


def test_failure_reason_categories_present():
    """Categorias canonicas pra falhas comuns."""
    assert FailureReason.VIDEO_TOO_SHORT.value == "video_too_short"
    assert FailureReason.AUDIO_MISSING.value == "audio_missing"
    assert FailureReason.LLM_TIMEOUT.value == "llm_timeout"
    assert FailureReason.UNKNOWN_EXCEPTION.value == "unknown_exception"
