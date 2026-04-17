"""Tests for Story 9.1 — Aggregator Refactor + Confidence Badges.

Exercita path v0.7.0 (STATE_OF_ART_ENABLED=true):
- SCORING_DIMENSIONS reduz para 6 → overall_score usa PESOS_DEFAULT novos
- SECONDARY_DIMENSIONS (7) em detailed_metrics, nao em dimension_scores
- dimension_confidence no payload
- schema_version = "1.2.0"
- PESOS_POR_CONTEXTO ajustado para 6 dims × 6 contextos, cada um soma 1.00
"""

import importlib
import math

import pytest

from contracts import WorkerSuccess
from contracts.dimensions import (
    ALL_DIMENSIONS,
    DIMENSION_CONFIDENCE,
    SECONDARY_DIMENSIONS,
)


@pytest.fixture
def state_of_art_on(monkeypatch):
    """Ativa STATE_OF_ART_ENABLED=true + recarrega aggregator para pegar flag."""
    monkeypatch.setenv("STATE_OF_ART_ENABLED", "true")
    import workers.aggregator as agg_module

    importlib.reload(agg_module)
    return agg_module


@pytest.fixture
def state_of_art_off(monkeypatch):
    monkeypatch.setenv("STATE_OF_ART_ENABLED", "false")
    import workers.aggregator as agg_module

    importlib.reload(agg_module)
    return agg_module


def _all_success(score: int = 80) -> dict:
    return {
        dim: WorkerSuccess(dimension=dim, score=score, metrics={"k": score}, confidence=1.0)
        for dim in ALL_DIMENSIONS
    }


VIDEO_META = {"duration_seconds": 120.0}


# ─────────────────────────────────────────────────────────────
# AC1 + AC2 — Pesos somam 1.0
# ─────────────────────────────────────────────────────────────


def test_ac1_pesos_default_v070_sum_to_one(state_of_art_on):
    pesos = state_of_art_on.PESOS_DEFAULT
    assert math.isclose(sum(pesos.values()), 1.0, abs_tol=1e-6)
    assert set(pesos.keys()) == {"voice", "variety", "gesture", "facial", "posture", "fillers"}


def test_ac2_pesos_por_contexto_all_sum_to_one(state_of_art_on):
    for ctx, pesos in state_of_art_on.PESOS_POR_CONTEXTO.items():
        assert math.isclose(sum(pesos.values()), 1.0, abs_tol=1e-6), (
            f"contexto {ctx} soma {sum(pesos.values())}, esperado 1.0"
        )
        assert set(pesos.keys()) == {"voice", "variety", "gesture", "facial", "posture", "fillers"}


def test_ac2_six_contexts_defined(state_of_art_on):
    assert set(state_of_art_on.PESOS_POR_CONTEXTO.keys()) == {
        "palco",
        "podcast",
        "vendas",
        "rede_social",
        "reuniao",
        "aula",
    }


# ─────────────────────────────────────────────────────────────
# AC3 + AC4 — Secondary dims em detailed_metrics, nao em dimension_scores
# ─────────────────────────────────────────────────────────────


def test_ac4_secondary_dims_not_in_dimension_scores(state_of_art_on):
    results = _all_success(score=75)
    agg = state_of_art_on.aggregate_metrics("eval-9.1", results, VIDEO_META)

    for dim in SECONDARY_DIMENSIONS:
        assert dim not in agg["dimension_scores"], (
            f"secondary dim {dim} nao deveria estar em dimension_scores"
        )


def test_ac4_secondary_dims_in_detailed_metrics(state_of_art_on):
    results = _all_success(score=75)
    agg = state_of_art_on.aggregate_metrics("eval-9.1", results, VIDEO_META)

    for dim in SECONDARY_DIMENSIONS:
        assert dim in agg["detailed_metrics"], (
            f"secondary dim {dim} deveria estar em detailed_metrics"
        )


def test_ac4_only_six_scoring_dims_counted(state_of_art_on):
    results = _all_success(score=75)
    agg = state_of_art_on.aggregate_metrics("eval-9.1", results, VIDEO_META)

    assert set(agg["dimension_scores"].keys()) == {
        "voice",
        "variety",
        "gesture",
        "facial",
        "posture",
        "fillers",
    }


def test_ac4_overall_score_uses_only_scoring_dims(state_of_art_on):
    """Score uniforme 80 → overall_score = 80 (pesos somam 1.0)."""
    results = _all_success(score=80)
    agg = state_of_art_on.aggregate_metrics("eval-9.1", results, VIDEO_META)
    assert agg["overall_score"] == 80


# ─────────────────────────────────────────────────────────────
# AC5 — Confidence badges
# ─────────────────────────────────────────────────────────────


def test_ac5_dimension_confidence_present_when_flag_on(state_of_art_on):
    results = _all_success()
    agg = state_of_art_on.aggregate_metrics("eval-9.1", results, VIDEO_META)

    assert "dimension_confidence" in agg
    confidence = agg["dimension_confidence"]

    for dim in ALL_DIMENSIONS:
        assert dim in confidence
        assert confidence[dim] == DIMENSION_CONFIDENCE[dim]


def test_ac5_scoring_dims_are_alta_or_variety_media(state_of_art_on):
    results = _all_success()
    agg = state_of_art_on.aggregate_metrics("eval-9.1", results, VIDEO_META)
    conf = agg["dimension_confidence"]

    for dim in agg["dimension_scores"]:
        if dim == "variety":
            assert conf[dim] == "media"
        else:
            assert conf[dim] == "alta", f"{dim} deveria ser alta, e {conf[dim]}"


# ─────────────────────────────────────────────────────────────
# AC7 — Feature flag rollback safety
# ─────────────────────────────────────────────────────────────


def test_ac7_flag_off_preserves_v060_schema(state_of_art_off):
    results = _all_success()
    agg = state_of_art_off.aggregate_metrics("eval-9.1", results, VIDEO_META)

    assert agg["schema_version"] == "1.1.0"
    assert "dimension_confidence" not in agg


def test_ac7_flag_on_emits_v070_schema(state_of_art_on):
    results = _all_success()
    agg = state_of_art_on.aggregate_metrics("eval-9.1", results, VIDEO_META)

    assert agg["schema_version"] == "1.2.0"
    assert "dimension_confidence" in agg


def test_ac7_flag_off_uses_v060_weights(state_of_art_off):
    """Flag OFF: pesos V060 (5 dims: variety, voice, gesture, posture, fillers)."""
    pesos = state_of_art_off.PESOS_DEFAULT_V060
    assert math.isclose(sum(pesos.values()), 1.0, abs_tol=1e-6)
    assert "facial" not in pesos
    assert set(pesos.keys()) == {"variety", "voice", "gesture", "posture", "fillers"}


# ─────────────────────────────────────────────────────────────
# AC8 — Legacy path intocado
# ─────────────────────────────────────────────────────────────


def test_ac8_legacy_path_unchanged(state_of_art_off):
    """aggregate_metrics_legacy preservado — assinatura e comportamento."""
    result_dict = {"score": 70, "confidence": 1.0, "metrics": {}}
    agg = state_of_art_off.aggregate_metrics_legacy(
        "eval",
        result_dict,
        result_dict,
        result_dict,
        result_dict,
        result_dict,
        result_dict,
        VIDEO_META,
    )
    assert agg["overall_score"] == 70
    # Legacy path aceita 6 dicts — todos viram dimension_scores
    assert len(agg["dimension_scores"]) == 6
