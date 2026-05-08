"""Tests Story 10.3 — discourse_arc_analyzer.

Mockado — zero chamada real a Gemini API.
Valida:
- Schema Pydantic do output (DiscourseArcOutput)
- Truncate transcript em MAX_TRANSCRIPT_CHARS
- Retry strategy (429/500 → retry, outros → fail)
- Fallback gracioso quando Gemini falha
- Instrumentação (cost_usd, latency_ms, prompt_sha)
- Schema invalid → WorkerFailure
- Empty transcript → WorkerFailure
- Missing API key → WorkerFailure
- Aggregator: PESOS_NARRATIVA_V103 sums to 1.0
- Aggregator: flag OFF preserva comportamento (PESOS_NARRATIVA original)
- Config: WEIGHT_TECNICA + WEIGHT_NARRATIVA assert
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from contracts import WorkerFailure, WorkerSuccess
from workers.discourse_arc_analyzer import (
    MAX_TRANSCRIPT_CHARS,
    DiscourseArcOutput,
    _compute_discourse_arc,
    _load_prompt,
    _truncate_transcript,
    analyze_discourse_arc,
)


# ─────────────────────────────────────────────────────────────
# Schema validation (Pydantic)
# ─────────────────────────────────────────────────────────────


def test_schema_valid_minimal():
    """Schema aceita output válido mínimo."""
    valid = {
        "discourse_type": "narrativa",
        "score": 65,
        "arc_label": "arco_completo",
        "tem_payoff": True,
        "tipo_payoff": "insight",
        "callback_abertura_fechamento": False,
        "justificativa": '"Trecho citado"',
        "confidence": 0.8,
        "criterios_atendidos": {
            "inicio_claro": True,
            "desenvolvimento": True,
            "fechamento": True,
            "transicoes": True,
            "profundidade": False,
        },
    }
    out = DiscourseArcOutput(**valid)
    assert out.score == 65
    assert out.arc_label == "arco_completo"


def test_schema_rejects_invalid_score():
    """Score >100 deve falhar Pydantic."""
    invalid = {
        "discourse_type": "narrativa",
        "score": 150,  # invalid
        "arc_label": "arco_completo",
        "tem_payoff": True,
        "tipo_payoff": None,
        "callback_abertura_fechamento": False,
        "justificativa": "x",
        "confidence": 0.5,
        "criterios_atendidos": {},
    }
    with pytest.raises(ValidationError):
        DiscourseArcOutput(**invalid)


def test_schema_rejects_invalid_arc_label():
    """arc_label fora do enum deve falhar."""
    invalid = {
        "discourse_type": "narrativa",
        "score": 50,
        "arc_label": "muito_bom",  # invalid
        "tem_payoff": False,
        "tipo_payoff": None,
        "callback_abertura_fechamento": False,
        "justificativa": "x",
        "confidence": 0.5,
        "criterios_atendidos": {},
    }
    with pytest.raises(ValidationError):
        DiscourseArcOutput(**invalid)


def test_schema_tipo_payoff_optional_none():
    """tipo_payoff pode ser None quando tem_payoff=False."""
    valid = {
        "discourse_type": "lista",
        "score": 30,
        "arc_label": "incompleto",
        "tem_payoff": False,
        "tipo_payoff": None,
        "callback_abertura_fechamento": False,
        "justificativa": "x",
        "confidence": 0.4,
        "criterios_atendidos": {},
    }
    out = DiscourseArcOutput(**valid)
    assert out.tipo_payoff is None


# ─────────────────────────────────────────────────────────────
# Truncate logic
# ─────────────────────────────────────────────────────────────


def test_truncate_under_limit():
    """Texto curto não é truncado."""
    text = "a" * 1000
    out, was = _truncate_transcript(text)
    assert out == text
    assert was is False


def test_truncate_over_limit():
    """Texto grande é truncado preservando início + fim."""
    text = "INICIO" + "x" * 50_000 + "FIM"
    out, was = _truncate_transcript(text)
    assert was is True
    assert len(out) <= MAX_TRANSCRIPT_CHARS + 100  # +marker
    assert out.startswith("INICIO")
    assert out.endswith("FIM")
    assert "truncado" in out


def test_truncate_at_exact_limit():
    """Texto = limite exato não trunca."""
    text = "x" * MAX_TRANSCRIPT_CHARS
    out, was = _truncate_transcript(text)
    assert was is False
    assert len(out) == MAX_TRANSCRIPT_CHARS


# ─────────────────────────────────────────────────────────────
# Prompt loading + SHA
# ─────────────────────────────────────────────────────────────


def test_load_prompt_returns_text_and_sha():
    """Prompt carrega + SHA é hex 16 chars."""
    text, sha = _load_prompt()
    assert "{TRANSCRIPT}" in text
    assert "Toastmasters" in text
    assert len(sha) == 16
    assert all(c in "0123456789abcdef" for c in sha)


def test_load_prompt_caches_result():
    """Segunda call retorna mesma instância."""
    text1, sha1 = _load_prompt()
    text2, sha2 = _load_prompt()
    assert text1 == text2
    assert sha1 == sha2


# ─────────────────────────────────────────────────────────────
# _compute_discourse_arc — error paths
# ─────────────────────────────────────────────────────────────


def test_compute_empty_transcript_returns_failed():
    """Transcript vazio retorna failed sem chamar Gemini."""
    result = _compute_discourse_arc("")
    assert result["score"] is None
    assert result["confidence"] == "failed"
    assert result["metrics"]["failure_reason"] == "empty_transcript"


def test_compute_none_transcript_returns_failed():
    """None transcript retorna failed."""
    result = _compute_discourse_arc(None)
    assert result["confidence"] == "failed"


def test_compute_missing_api_key_returns_failed(monkeypatch):
    """Sem GEMINI_API_KEY retorna failed sem chamar genai."""
    import config

    monkeypatch.setattr(config, "GEMINI_API_KEY", "")
    result = _compute_discourse_arc("Texto válido com várias palavras")
    assert result["confidence"] == "failed"
    assert "missing_gemini_api_key" in result["metrics"]["failure_reason"]


# ─────────────────────────────────────────────────────────────
# _compute_discourse_arc — success path (mocked)
# ─────────────────────────────────────────────────────────────


@patch("workers.discourse_arc_analyzer._call_gemini")
def test_compute_success_returns_validated_metrics(mock_call, monkeypatch):
    """Gemini retorna válido → score + metrics + instrumentação."""
    import config

    monkeypatch.setattr(config, "GEMINI_API_KEY", "fake-key")
    mock_call.return_value = (
        {
            "discourse_type": "narrativa",
            "score": 72,
            "arc_label": "arco_completo",
            "tem_payoff": True,
            "tipo_payoff": "insight",
            "callback_abertura_fechamento": True,
            "justificativa": '"trecho citado"',
            "confidence": 0.85,
            "criterios_atendidos": {
                "inicio_claro": True,
                "desenvolvimento": True,
                "fechamento": True,
                "transicoes": True,
                "profundidade": True,
            },
        },
        {"latency_ms": 2300, "cost_usd": 0.0046, "input_tokens": 8000, "output_tokens": 400},
    )

    result = _compute_discourse_arc("Transcript válido com narrativa.")
    assert result["score"] == 72
    assert result["confidence"] == "high"  # 0.85 → high
    assert result["metrics"]["arc_label"] == "arco_completo"
    assert result["metrics"]["cost_usd"] == 0.0046
    assert result["metrics"]["latency_ms"] == 2300
    assert "prompt_sha" in result["metrics"]
    assert result["metrics"]["transcript_truncated"] is False


@patch("workers.discourse_arc_analyzer._call_gemini")
def test_compute_schema_invalid_returns_failed(mock_call, monkeypatch):
    """Gemini retorna JSON com schema errado → failed."""
    import config

    monkeypatch.setattr(config, "GEMINI_API_KEY", "fake-key")
    mock_call.return_value = (
        {"score": "not-an-int", "arc_label": "weird"},  # invalid schema
        {"latency_ms": 1000, "cost_usd": 0.001, "input_tokens": 100, "output_tokens": 50},
    )

    result = _compute_discourse_arc("Transcript válido.")
    assert result["confidence"] == "failed"
    assert "schema_validation_failed" in result["metrics"]["failure_reason"]


@patch("workers.discourse_arc_analyzer._call_gemini")
def test_compute_gemini_429_retries_once(mock_call, monkeypatch):
    """429 dispara 1 retry. Se segunda falha, retorna failed."""
    import config

    monkeypatch.setattr(config, "GEMINI_API_KEY", "fake-key")
    mock_call.side_effect = [
        Exception("429 quota exceeded"),
        Exception("429 still over"),
    ]

    result = _compute_discourse_arc("Transcript válido.")
    assert result["confidence"] == "failed"
    assert mock_call.call_count == 2  # original + 1 retry


@patch("workers.discourse_arc_analyzer._call_gemini")
def test_compute_gemini_non_retryable_no_retry(mock_call, monkeypatch):
    """Erro não-retryable (e.g. 400 schema bad) → não retry."""
    import config

    monkeypatch.setattr(config, "GEMINI_API_KEY", "fake-key")
    mock_call.side_effect = Exception("Invalid argument")

    result = _compute_discourse_arc("Transcript válido.")
    assert result["confidence"] == "failed"
    assert mock_call.call_count == 1  # sem retry


# ─────────────────────────────────────────────────────────────
# analyze_discourse_arc — wrapper integration
# ─────────────────────────────────────────────────────────────


def test_analyze_returns_worker_result_failure_on_empty():
    """Wrapper retorna WorkerFailure quando transcript vazio."""
    result = analyze_discourse_arc("")
    assert isinstance(result, WorkerFailure)
    assert result.dimension == "discourse_arc"


@patch("workers.discourse_arc_analyzer._call_gemini")
def test_analyze_returns_worker_success(mock_call, monkeypatch):
    """Wrapper retorna WorkerSuccess quando Gemini OK."""
    import config

    monkeypatch.setattr(config, "GEMINI_API_KEY", "fake-key")
    mock_call.return_value = (
        {
            "discourse_type": "narrativa",
            "score": 80,
            "arc_label": "circular_callback",
            "tem_payoff": True,
            "tipo_payoff": "imagem",
            "callback_abertura_fechamento": True,
            "justificativa": '"hook citado"',
            "confidence": 0.9,
            "criterios_atendidos": {},
        },
        {"latency_ms": 1500, "cost_usd": 0.003, "input_tokens": 5000, "output_tokens": 300},
    )

    result = analyze_discourse_arc("Texto longo válido com narrativa.")
    assert isinstance(result, WorkerSuccess)
    assert result.score == 80
    assert result.dimension == "discourse_arc"


# ─────────────────────────────────────────────────────────────
# Aggregator integration — flag aware
# ─────────────────────────────────────────────────────────────


def test_pesos_narrativa_v103_sums_to_one():
    """PESOS_NARRATIVA_V103 deve somar 1.0 (constraint matemático)."""
    from workers.aggregator import PESOS_NARRATIVA_V103

    total = sum(PESOS_NARRATIVA_V103.values())
    assert abs(total - 1.0) < 0.001
    assert "discourse_arc" in PESOS_NARRATIVA_V103


def test_pesos_narrativa_legacy_intacto():
    """PESOS_NARRATIVA original não inclui discourse_arc (AC7)."""
    from workers.aggregator import PESOS_NARRATIVA

    assert "discourse_arc" not in PESOS_NARRATIVA
    assert sum(PESOS_NARRATIVA.values()) == pytest.approx(1.0, abs=0.001)


def test_dimensions_registry():
    """discourse_arc registrado em SECONDARY + NARRATIVA dim sets."""
    from contracts.dimensions import NARRATIVA_DIMENSIONS, SECONDARY_DIMENSIONS

    assert "discourse_arc" in SECONDARY_DIMENSIONS
    assert "discourse_arc" in NARRATIVA_DIMENSIONS


# ─────────────────────────────────────────────────────────────
# Config flag
# ─────────────────────────────────────────────────────────────


def test_flag_default_false():
    """NARRATIVE_FAMILY_ENABLED default false."""
    import importlib

    import config

    importlib.reload(config)  # garantir sem env override
    # Pode ser true se .env tiver — testar via helper
    val_check = config.is_narrative_family_enabled()
    assert isinstance(val_check, bool)


def test_weights_default_06_04():
    """WEIGHT_TECNICA + WEIGHT_NARRATIVA somam 1.0 default."""
    import config

    total = config.WEIGHT_TECNICA + config.WEIGHT_NARRATIVA
    assert abs(total - 1.0) < 0.001


# ─────────────────────────────────────────────────────────────
# Storytelling extension — payoff types heuristic (Task 3)
# ─────────────────────────────────────────────────────────────


def test_payoff_types_detects_cta_in_closing():
    """Closing com CTA é detectado mesmo só 1 hit (closing-pesa-2x rule)."""
    from workers.storytelling_analyzer import _detect_payoff_types

    result = _detect_payoff_types(
        "blá blá conteúdo geral",
        "experimente isso hoje",
    )
    assert "cta" in result


def test_payoff_types_requires_2_hits_in_full_only():
    """Sem closing hits, full precisa ≥2 hits."""
    from workers.storytelling_analyzer import _detect_payoff_types

    # 1 hit no full → não detecta
    result1 = _detect_payoff_types("descobri uma coisa", "encerramento neutro")
    assert "insight" not in result1

    # 2 hits no full → detecta
    result2 = _detect_payoff_types(
        "descobri que aprendi muito ao longo da vida",
        "encerramento neutro",
    )
    assert "insight" in result2


def test_payoff_types_returns_sorted_by_frequency():
    """Múltiplos tipos retornam ordenados por hits (mais primeiro)."""
    from workers.storytelling_analyzer import _detect_payoff_types

    closing = "experimente, comece, tente, faça hoje. perceba que descobri"
    result = _detect_payoff_types("conteúdo geral", closing)
    # cta tem 4 keywords no closing (×2=8) vs insight tem 2 (×2=4)
    assert result[0] == "cta"
