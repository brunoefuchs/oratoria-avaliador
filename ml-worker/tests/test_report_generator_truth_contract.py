"""Tests for Story 8.5 — Truth Contract Report Generator Rewrite.

Cobre:
- AggregatedMetrics validation (happy path, missing required fields)
- _build_prompt() tests:
  - overall_score=None → prompt contem "INDISPONIVEL", NAO "0/100"
  - dimension_scores missing → prompt diz "INDISPONIVEL" para dim faltante
  - Identity como WorkerFailure dict → secao identidade ausente do prompt
  - Identity como WorkerSuccess dict → secao identidade presente
- Mock Gemini JSON response → verify parsing sem markdown stripping
- Retry logic: mock primeiras 2 chamadas para falhar → temperature varia
- Legacy path: generate_report_legacy(dict) intacto
- Veto checks: sem "0/100" quando score None, sem "score != 50" no novo path
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from contracts.aggregated_metrics import AggregatedMetrics
from workers.report_generator import (
    _build_prompt,
    _score_label,
    generate_report,
    generate_report_legacy,
)


def make_metrics(
    overall_score=75,
    dimension_scores=None,
    incomplete_dimensions=None,
    partial_aggregation=False,
    identity=None,
    opening=None,
    temporal=None,
    congruence=None,
):
    """Factory para AggregatedMetrics de teste."""
    return AggregatedMetrics(
        overall_score=overall_score,
        dimension_scores=dimension_scores or {"variety": 70, "voice": 65, "gesture": 80, "posture": 75, "fillers": 60, "archetypes": 55},
        detailed_metrics={},
        incomplete_dimensions=incomplete_dimensions or [],
        partial_aggregation=partial_aggregation,
        identity=identity,
        opening=opening,
        temporal=temporal,
        congruence=congruence,
    )


def make_worker_success_dict(score=80, dimension="identity"):
    """Simula WorkerSuccess serializado (dimension_status='ok')."""
    return {
        "dimension": dimension,
        "dimension_status": "ok",
        "score": score,
        "metrics": {
            "diagnostico": "identidade_solida",
            "autoridade_count": 5,
            "autoridade_ratio": 0.6,
            "vitima_count": 1,
            "total_vicios": 0,
            "exemplos": [],
            "disponivel": True,
        },
        "confidence": 1.0,
    }


def make_worker_failure_dict(dimension="identity", reason="transcription_failed"):
    """Simula WorkerFailure serializado (dimension_status='failed')."""
    return {
        "dimension": dimension,
        "dimension_status": "failed",
        "score": None,
        "failure_reason": reason,
        "metrics": {},
    }


class TestAggregatedMetricsValidation:
    def test_happy_path_full(self):
        m = AggregatedMetrics(
            overall_score=75,
            dimension_scores={"variety": 70, "voice": 65},
            detailed_metrics={"voice": {"wpm": 150}},
            incomplete_dimensions=[],
            partial_aggregation=False,
            contexto="professor",
            pesos_utilizados={"variety": 0.25},
            video_metadata={"duration_seconds": 120},
        )
        assert m.overall_score == 75
        assert m.partial_aggregation is False

    def test_overall_score_none_is_valid(self):
        m = AggregatedMetrics(
            overall_score=None,
            incomplete_dimensions=["variety", "voice"],
            partial_aggregation=False,
        )
        assert m.overall_score is None

    def test_partial_aggregation_true(self):
        m = AggregatedMetrics(overall_score=60, incomplete_dimensions=["gesture"], partial_aggregation=True)
        assert m.partial_aggregation is True

    def test_extra_fields_allowed(self):
        m = AggregatedMetrics(overall_score=50, campo_extra="nao_definido")
        assert m.overall_score == 50

    def test_missing_required_raises(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            AggregatedMetrics()

    def test_dimension_scores_defaults_empty(self):
        m = AggregatedMetrics(overall_score=70)
        assert m.dimension_scores == {}

    def test_augmentation_fields_optional(self):
        m = AggregatedMetrics(overall_score=70)
        assert m.identity is None
        assert m.opening is None
        assert m.temporal is None
        assert m.congruence is None


class TestScoreLabel:
    def test_valid_score_returns_fraction(self):
        assert _score_label(75, "variety", []) == "75/100"

    def test_none_score_returns_indisponivel(self):
        result = _score_label(None, "variety", [])
        assert "INDISPONIVEL" in result
        assert "0/100" not in result

    def test_dim_in_incomplete_returns_indisponivel(self):
        result = _score_label(75, "variety", ["variety"])
        assert "INDISPONIVEL" in result

    def test_dim_not_in_incomplete_with_valid_score(self):
        result = _score_label(80, "voice", ["variety"])
        assert result == "80/100"


class TestBuildPromptHonestScores:
    def test_overall_score_none_prompt_says_indisponivel(self):
        """V9: overall_score=None → prompt NAO diz '0/100'."""
        m = make_metrics(
            overall_score=None,
            incomplete_dimensions=["variety", "voice", "gesture", "posture", "fillers", "archetypes"],
        )
        prompt = _build_prompt(m)
        assert "INDISPONIVEL" in prompt
        assert "Pontuacao Geral: 0/100" not in prompt
        assert "Pontuacao Geral: None" not in prompt

    def test_overall_score_valid_shows_number(self):
        m = make_metrics(overall_score=75)
        prompt = _build_prompt(m)
        assert "75/100" in prompt

    def test_dimension_none_in_incomplete_shows_indisponivel(self):
        """Dimensao faltante → INDISPONIVEL, NAO 0/100."""
        m = AggregatedMetrics(
            overall_score=60,
            dimension_scores={"voice": 65, "gesture": 80, "posture": 75, "fillers": 60, "archetypes": 55},
            incomplete_dimensions=["variety"],
            partial_aggregation=True,
        )
        prompt = _build_prompt(m)
        assert "INDISPONIVEL" in prompt
        assert "Pontuacao: 0/100" not in prompt

    def test_no_fake_zero_for_missing_dim_score(self):
        """V9 veto: nenhum '0/100' quando dim nao esta em dimension_scores."""
        m = AggregatedMetrics(
            overall_score=70,
            dimension_scores={},
            incomplete_dimensions=["variety", "voice", "gesture", "posture", "fillers", "archetypes"],
            partial_aggregation=True,
        )
        prompt = _build_prompt(m)
        assert "Pontuacao: 0/100" not in prompt

    def test_partial_aggregation_no_error(self):
        m = make_metrics(overall_score=55, partial_aggregation=True)
        prompt = _build_prompt(m)
        assert "55/100" in prompt


class TestIdentityCheckViaStatus:
    def test_identity_worker_failure_omits_section(self):
        """WorkerFailure de identity → secao identidade ausente."""
        m = make_metrics(identity=make_worker_failure_dict("identity"))
        prompt = _build_prompt(m)
        assert "IDENTIDADE COMUNICATIVA" not in prompt

    def test_identity_worker_success_includes_section(self):
        """WorkerSuccess de identity → secao identidade presente."""
        m = make_metrics(identity=make_worker_success_dict(score=80))
        prompt = _build_prompt(m)
        assert "IDENTIDADE COMUNICATIVA" in prompt

    def test_identity_none_omits_section(self):
        m = make_metrics(identity=None)
        prompt = _build_prompt(m)
        assert "IDENTIDADE COMUNICATIVA" not in prompt

    def test_identity_check_includes_score_50_if_ok_status(self):
        """V10: dimension_status='ok' com score=50 deve incluir secao."""
        identity_score_50 = make_worker_success_dict(score=50)
        m = make_metrics(identity=identity_score_50)
        prompt = _build_prompt(m)
        assert "IDENTIDADE COMUNICATIVA" in prompt

    def test_identity_crashed_omits_section(self):
        identity_crashed = {
            "dimension": "identity",
            "dimension_status": "crashed",
            "score": None,
            "failure_reason": "unknown",
            "metrics": {},
        }
        m = make_metrics(identity=identity_crashed)
        prompt = _build_prompt(m)
        assert "IDENTIDADE COMUNICATIVA" not in prompt


class TestGeminiJsonModeAndRetry:
    def _make_mock_response(self, content):
        mock = MagicMock()
        mock.text = json.dumps(content)
        mock.usage_metadata = MagicMock()
        mock.usage_metadata.prompt_token_count = 1000
        mock.usage_metadata.candidates_token_count = 500
        return mock

    def _make_valid_report(self):
        return {
            "resumo": "Resumo teste",
            "forcas": [{"titulo": "Forca 1", "descricao": "desc", "impacto": "impacto"}],
            "melhorias_80_20": [{"titulo": "Melhoria 1", "descricao": "desc", "exercicio": "ex", "prioridade": 1}],
            "dimensoes": {"variedade": {"label": "Bom", "feedback": "ok", "dica": "dica"}},
            "plano_12_semanas": [{"semana": "1-2", "foco": "foco", "exercicio": "ex", "meta": "meta"}],
            "mensagem_final": "Mensagem final",
        }

    @patch("workers.report_generator.genai.configure")
    @patch("workers.report_generator.genai.GenerativeModel")
    def test_json_mode_no_retrocompat_fields(self, mock_model_cls, mock_configure):
        """V11+V13: JSON mode, sem retrocompat fields no novo path."""
        mock_model = MagicMock()
        mock_model_cls.return_value = mock_model
        mock_model.generate_content.return_value = self._make_mock_response(self._make_valid_report())

        m = make_metrics()
        result = generate_report(m)

        assert result["resumo"] == "Resumo teste"
        assert "summary" not in result
        assert "dimension_feedback" not in result

    @patch("workers.report_generator.genai.configure")
    @patch("workers.report_generator.genai.GenerativeModel")
    def test_retry_varies_temperature(self, mock_model_cls, mock_configure):
        """V12: retry varia temperatura entre tentativas."""
        mock_model = MagicMock()
        mock_model_cls.return_value = mock_model

        call_count = [0]
        temperatures_used = []

        def side_effect(prompt, generation_config=None):
            call_count[0] += 1
            if generation_config:
                temperatures_used.append(generation_config.get("temperature"))
            if call_count[0] < 3:
                bad = MagicMock()
                bad.text = "not valid json {"
                bad.usage_metadata = None
                return bad
            return self._make_mock_response(self._make_valid_report())

        mock_model.generate_content.side_effect = side_effect

        m = make_metrics()
        result = generate_report(m)

        assert call_count[0] == 3
        assert len(temperatures_used) == 3
        assert temperatures_used[0] > temperatures_used[1]
        assert temperatures_used[1] > temperatures_used[2]

    @patch("workers.report_generator.genai.configure")
    @patch("workers.report_generator.genai.GenerativeModel")
    def test_all_retries_fail_raises(self, mock_model_cls, mock_configure):
        """3 falhas consecutivas → RuntimeError."""
        mock_model = MagicMock()
        mock_model_cls.return_value = mock_model
        bad = MagicMock()
        bad.text = "invalid json"
        bad.usage_metadata = None
        mock_model.generate_content.return_value = bad

        m = make_metrics()
        with pytest.raises(RuntimeError, match="tentativas"):
            generate_report(m)

    @patch("workers.report_generator.genai.configure")
    @patch("workers.report_generator.genai.GenerativeModel")
    def test_llm_cost_from_usage_metadata(self, mock_model_cls, mock_configure):
        """llm_cost_usd calculado via usage_metadata — nao 0.0 fake."""
        mock_model = MagicMock()
        mock_model_cls.return_value = mock_model
        mock_response = self._make_mock_response(self._make_valid_report())
        mock_response.usage_metadata.prompt_token_count = 10000
        mock_response.usage_metadata.candidates_token_count = 2000
        mock_model.generate_content.return_value = mock_response

        m = make_metrics()
        result = generate_report(m)
        assert result["llm_cost_usd"] > 0.0

    @patch("workers.report_generator.genai.configure")
    @patch("workers.report_generator.genai.GenerativeModel")
    def test_generation_config_has_json_mime_type(self, mock_model_cls, mock_configure):
        """V11: generation_config tem response_mime_type=application/json."""
        mock_model = MagicMock()
        mock_model_cls.return_value = mock_model
        mock_model.generate_content.return_value = self._make_mock_response(self._make_valid_report())

        m = make_metrics()
        generate_report(m)

        call_args = mock_model.generate_content.call_args
        generation_config = call_args.kwargs.get("generation_config") or {}
        assert generation_config.get("response_mime_type") == "application/json"


class TestLegacyPathIntact:
    def _make_legacy_aggregated(self, overall_score=75):
        return {
            "overall_score": overall_score,
            "dimension_scores": {"variety": 70, "voice": 65, "gesture": 80, "posture": 75, "fillers": 60, "archetypes": 55},
            "detailed_metrics": {},
            "incomplete_dimensions": [],
            "video_metadata": {},
            "identity": {"score": None, "diagnostico": "failed"},
            "opening": {"disponivel": False},
            "temporal": {"disponivel": False},
            "congruence": {},
        }

    @patch("workers.report_generator.genai.configure")
    @patch("workers.report_generator.genai.GenerativeModel")
    def test_legacy_accepts_dict(self, mock_model_cls, mock_configure):
        mock_model = MagicMock()
        mock_model_cls.return_value = mock_model
        valid_report = {"resumo": "Resumo legacy", "forcas": [], "melhorias_80_20": [], "dimensoes": {}, "plano_12_semanas": [], "mensagem_final": "msg"}
        mock_response = MagicMock()
        mock_response.text = json.dumps(valid_report)
        mock_model.generate_content.return_value = mock_response

        result = generate_report_legacy(self._make_legacy_aggregated())
        assert result["resumo"] == "Resumo legacy"

    @patch("workers.report_generator.genai.configure")
    @patch("workers.report_generator.genai.GenerativeModel")
    def test_legacy_has_retrocompat_fields(self, mock_model_cls, mock_configure):
        mock_model = MagicMock()
        mock_model_cls.return_value = mock_model
        valid_report = {"resumo": "Resumo", "forcas": [], "melhorias_80_20": [], "dimensoes": {"variedade": {"label": "Bom", "feedback": "ok", "dica": "d"}}, "plano_12_semanas": [], "mensagem_final": "msg"}
        mock_response = MagicMock()
        mock_response.text = json.dumps(valid_report)
        mock_model.generate_content.return_value = mock_response

        result = generate_report_legacy(self._make_legacy_aggregated())
        assert "summary" in result
        assert "dimension_feedback" in result

    @patch("workers.report_generator.genai.configure")
    @patch("workers.report_generator.genai.GenerativeModel")
    def test_legacy_cost_is_zero(self, mock_model_cls, mock_configure):
        mock_model = MagicMock()
        mock_model_cls.return_value = mock_model
        valid_report = {"resumo": "ok", "forcas": [], "melhorias_80_20": [], "dimensoes": {}, "plano_12_semanas": [], "mensagem_final": "ok"}
        mock_response = MagicMock()
        mock_response.text = json.dumps(valid_report)
        mock_model.generate_content.return_value = mock_response

        result = generate_report_legacy(self._make_legacy_aggregated())
        assert result["llm_cost_usd"] == 0.0


class TestVetoChecks:
    def test_veto_v9_no_fake_zero_score_in_prompt(self):
        """V9: nenhum 'Pontuacao: 0/100' quando score eh None."""
        m = AggregatedMetrics(
            overall_score=None,
            dimension_scores={},
            incomplete_dimensions=["variety", "voice", "gesture", "posture", "fillers", "archetypes"],
        )
        prompt = _build_prompt(m)
        lines_with_zero = [l for l in prompt.split("\n") if "Pontuacao" in l and "0/100" in l]
        assert len(lines_with_zero) == 0, f"Prompt contem '0/100' em: {lines_with_zero}"

    def test_veto_v10_identity_uses_dimension_status(self):
        """V10: _build_prompt usa dimension_status, nao score comparisons."""
        import inspect
        from workers import report_generator

        source = inspect.getsource(report_generator._build_prompt)
        assert "dimension_status" in source
        assert "_identity_ok" in source

    def test_veto_v11_json_mime_type_in_source(self):
        """V11: generate_report usa response_mime_type='application/json'."""
        import inspect
        from workers import report_generator

        source = inspect.getsource(report_generator.generate_report)
        assert "application/json" in source

    def test_veto_v13_no_retrocompat_in_new_path(self):
        """V13: generate_report nao retorna 'summary' ou 'dimension_feedback'."""
        import inspect
        from workers import report_generator

        source = inspect.getsource(report_generator.generate_report)
        assert '"summary"' not in source
        assert '"dimension_feedback"' not in source

    def test_veto_v12_retry_temperatures_distinct(self):
        """V12: retry usa temperaturas distintas."""
        import inspect
        from workers import report_generator

        source = inspect.getsource(report_generator.generate_report)
        assert "temperatures" in source
        assert "0.7" in source
        assert "0.5" in source
        assert "0.3" in source
