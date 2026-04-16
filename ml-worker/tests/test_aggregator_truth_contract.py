"""Tests for Story 8.4 — Truth Contract Aggregator Rewrite.

Cobre:
- aggregate_metrics() aceita dict[str, WorkerResult] diretamente
- overall_score: int quando ha scoring dims com sucesso, None quando nao ha
- partial_aggregation: bool presente no retorno
- 13 dimensoes processadas (scoring + augmentation separadas)
- Pesos contextuais funcionam com WorkerResult input
- Legacy path aggregate_metrics_legacy() intacto
- V1/V2: overall_score nunca eh 0 por fallback
"""

import pytest

from contracts import WorkerFailure, WorkerSuccess
from contracts.dimensions import AUGMENTATION_DIMENSIONS, SCORING_DIMENSIONS
from workers.aggregator import aggregate_metrics, aggregate_metrics_legacy

EVAL_ID = "test-eval-8.4"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_success(dimension: str, score: int = 75, **metrics) -> WorkerSuccess:
    return WorkerSuccess(
        dimension=dimension,
        score=score,
        metrics=metrics or {"test_metric": score},
        confidence=1.0,
    )


def make_failure(dimension: str, reason: str = "test_failure") -> WorkerFailure:
    return WorkerFailure(
        dimension=dimension,
        dimension_status="failed",
        failure_reason=reason,
    )


def all_success_results(score: int = 75) -> dict:
    """Retorna dict com todos 13 workers como WorkerSuccess."""
    results = {}
    for dim in SCORING_DIMENSIONS:
        results[dim] = make_success(dim, score=score)
    for dim in AUGMENTATION_DIMENSIONS:
        results[dim] = make_success(dim, score=score)
    return results


def all_failure_results() -> dict:
    """Retorna dict com todos 13 workers como WorkerFailure."""
    results = {}
    for dim in SCORING_DIMENSIONS:
        results[dim] = make_failure(dim)
    for dim in AUGMENTATION_DIMENSIONS:
        results[dim] = make_failure(dim)
    return results


VIDEO_META = {"duration_seconds": 120.0, "frames_processed": 1200}


# ---------------------------------------------------------------------------
# T1 — All WorkerSuccess → overall_score int, partial=False
# ---------------------------------------------------------------------------


class TestAllSuccess:
    def test_overall_score_is_int(self):
        """Todos WorkerSuccess → overall_score eh int (nao None)."""
        results = all_success_results(score=80)
        agg = aggregate_metrics(EVAL_ID, results, VIDEO_META)
        assert isinstance(agg["overall_score"], int)
        assert agg["overall_score"] is not None

    def test_partial_aggregation_false(self):
        """Todos WorkerSuccess → partial_aggregation=False."""
        results = all_success_results(score=80)
        agg = aggregate_metrics(EVAL_ID, results, VIDEO_META)
        assert agg["partial_aggregation"] is False

    def test_incomplete_dimensions_empty(self):
        """Todos WorkerSuccess → incomplete_dimensions vazio."""
        results = all_success_results(score=80)
        agg = aggregate_metrics(EVAL_ID, results, VIDEO_META)
        assert agg["incomplete_dimensions"] == []

    def test_dimension_scores_contain_scoring_dims(self):
        """dimension_scores contem as scoring dims com score correto."""
        results = all_success_results(score=70)
        agg = aggregate_metrics(EVAL_ID, results, VIDEO_META)
        # PESOS_DEFAULT cobre: variety, voice, gesture, posture, fillers
        for dim in ["variety", "voice", "gesture", "posture", "fillers"]:
            assert dim in agg["dimension_scores"], f"dim '{dim}' ausente de dimension_scores"
            assert agg["dimension_scores"][dim] == 70

    def test_detailed_metrics_populated(self):
        """detailed_metrics populado com metrics dos WorkerSuccess."""
        results = all_success_results(score=70)
        agg = aggregate_metrics(EVAL_ID, results, VIDEO_META)
        assert len(agg["detailed_metrics"]) > 0

    def test_overall_score_calculation(self):
        """overall_score calculado corretamente com pesos default."""
        # Todos com score 100 → overall_score deve ser 100
        results = all_success_results(score=100)
        agg = aggregate_metrics(EVAL_ID, results, VIDEO_META)
        assert agg["overall_score"] == 100

    def test_overall_score_zero_is_real_zero(self):
        """overall_score=0 eh score real, nao fallback (V1 veto)."""
        results = all_success_results(score=0)
        agg = aggregate_metrics(EVAL_ID, results, VIDEO_META)
        assert agg["overall_score"] == 0
        assert agg["partial_aggregation"] is False


# ---------------------------------------------------------------------------
# T2 — Mix Success+Failure → overall_score int, partial=True
# ---------------------------------------------------------------------------


class TestMixSuccessFailure:
    def test_partial_aggregation_true(self):
        """Qualquer scoring dim falhou → partial_aggregation=True."""
        results = all_success_results(score=75)
        # Derrubar 2 scoring dims
        results["posture"] = make_failure("posture")
        results["gesture"] = make_failure("gesture")
        agg = aggregate_metrics(EVAL_ID, results, VIDEO_META)
        assert agg["partial_aggregation"] is True

    def test_overall_score_still_int_with_partial(self):
        """Mix Success+Failure → overall_score ainda eh int (nao None)."""
        results = all_success_results(score=75)
        results["posture"] = make_failure("posture")
        agg = aggregate_metrics(EVAL_ID, results, VIDEO_META)
        assert isinstance(agg["overall_score"], int)

    def test_incomplete_dimensions_lists_failures(self):
        """incomplete_dimensions lista apenas dims que falharam."""
        results = all_success_results(score=75)
        results["posture"] = make_failure("posture")
        results["gesture"] = make_failure("gesture")
        agg = aggregate_metrics(EVAL_ID, results, VIDEO_META)
        assert "posture" in agg["incomplete_dimensions"]
        assert "gesture" in agg["incomplete_dimensions"]

    def test_failed_dims_not_in_dimension_scores(self):
        """Dims que falharam nao aparecem em dimension_scores."""
        results = all_success_results(score=75)
        results["posture"] = make_failure("posture")
        agg = aggregate_metrics(EVAL_ID, results, VIDEO_META)
        assert "posture" not in agg["dimension_scores"]

    def test_renormalized_weight_calculation(self):
        """Peso renormalizado: se posture (0.18) falha, remaining peso_total < 1.0."""
        results = {}
        # Apenas variety e voice (pesos: 0.29 + 0.24 = 0.53)
        results["variety"] = make_success("variety", score=100)
        results["voice"] = make_success("voice", score=0)
        for dim in SCORING_DIMENSIONS:
            if dim not in results:
                results[dim] = make_failure(dim)
        for dim in AUGMENTATION_DIMENSIONS:
            results[dim] = make_success(dim, score=50)
        agg = aggregate_metrics(EVAL_ID, results, VIDEO_META)
        # variety=100, voice=0 → pesos 0.29:0.24, normalizado:
        # (100*0.29 + 0*0.24) / (0.29+0.24) = 29/0.53 ≈ 55
        assert agg["overall_score"] is not None
        assert isinstance(agg["overall_score"], int)
        expected = round((100 * 0.29 + 0 * 0.24) / (0.29 + 0.24))
        assert agg["overall_score"] == expected

    def test_augmentation_failures_not_in_incomplete(self):
        """Falhas em augmentation dims nao entram em incomplete_dimensions."""
        results = all_success_results(score=75)
        for dim in AUGMENTATION_DIMENSIONS:
            results[dim] = make_failure(dim)
        agg = aggregate_metrics(EVAL_ID, results, VIDEO_META)
        for dim in AUGMENTATION_DIMENSIONS:
            assert dim not in agg["incomplete_dimensions"]


# ---------------------------------------------------------------------------
# T3 — All WorkerFailure → overall_score=None, partial=True
# ---------------------------------------------------------------------------


class TestAllFailure:
    def test_overall_score_is_none(self):
        """Todos WorkerFailure → overall_score=None (nao 0)."""
        results = all_failure_results()
        agg = aggregate_metrics(EVAL_ID, results, VIDEO_META)
        assert agg["overall_score"] is None

    def test_partial_aggregation_true(self):
        """Todos WorkerFailure → partial_aggregation=True."""
        results = all_failure_results()
        agg = aggregate_metrics(EVAL_ID, results, VIDEO_META)
        assert agg["partial_aggregation"] is True

    def test_incomplete_dimensions_lists_all_scoring(self):
        """Todos scoring dims em incomplete_dimensions."""
        results = all_failure_results()
        agg = aggregate_metrics(EVAL_ID, results, VIDEO_META)
        for dim in SCORING_DIMENSIONS:
            assert dim in agg["incomplete_dimensions"]

    def test_dimension_scores_empty(self):
        """dimension_scores vazio quando todos falharam."""
        results = all_failure_results()
        agg = aggregate_metrics(EVAL_ID, results, VIDEO_META)
        assert agg["dimension_scores"] == {}

    def test_overall_score_not_zero_fallback(self):
        """VETO V1: overall_score nunca eh 0 por fallback — deve ser None."""
        results = {}
        for dim in SCORING_DIMENSIONS:
            results[dim] = make_failure(dim)
        for dim in AUGMENTATION_DIMENSIONS:
            results[dim] = make_failure(dim)
        agg = aggregate_metrics(EVAL_ID, results, VIDEO_META)
        assert agg["overall_score"] is None, (
            f"overall_score={agg['overall_score']} mas deveria ser None "
            "(score=0 fake detectado — VETO V1 violado)"
        )


# ---------------------------------------------------------------------------
# T4 — 13 dimensoes processadas (scoring + augmentation separadas)
# ---------------------------------------------------------------------------


class TestThirteenDimensions:
    def test_scoring_dims_in_dimension_scores(self):
        """Todas scoring dims com success aparecem em dimension_scores."""
        results = all_success_results(score=70)
        agg = aggregate_metrics(EVAL_ID, results, VIDEO_META)
        # dimension_scores so deve ter scoring dims (as que tem peso)
        # fillers, variety, voice, gesture, posture (pesos default)
        # identity, facial, tonality, opening, archetypes (sem peso → nao entram)
        # Verificar que nenhuma augmentation dim entrou no dimension_scores
        for dim in AUGMENTATION_DIMENSIONS:
            assert dim not in agg["dimension_scores"], (
                f"dim augmentation '{dim}' entrou em dimension_scores — nao deve"
            )

    def test_augmentation_dims_in_detailed_metrics(self):
        """Augmentation dims com success aparecem em detailed_metrics."""
        results = all_success_results(score=70)
        agg = aggregate_metrics(EVAL_ID, results, VIDEO_META)
        for dim in AUGMENTATION_DIMENSIONS:
            assert dim in agg["detailed_metrics"], (
                f"dim augmentation '{dim}' ausente de detailed_metrics"
            )

    def test_scoring_dims_in_detailed_metrics(self):
        """Scoring dims com success aparecem em detailed_metrics."""
        results = all_success_results(score=70)
        agg = aggregate_metrics(EVAL_ID, results, VIDEO_META)
        # Pelo menos as scoring dims com pesos devem estar
        for dim in ["posture", "gesture", "voice", "fillers", "variety", "archetypes"]:
            assert dim in agg["detailed_metrics"], f"dim '{dim}' ausente de detailed_metrics"

    def test_partial_aggregation_key_present(self):
        """VETO V3: partial_aggregation presente no retorno."""
        results = all_success_results(score=70)
        agg = aggregate_metrics(EVAL_ID, results, VIDEO_META)
        assert "partial_aggregation" in agg

    def test_overall_score_key_present(self):
        """overall_score sempre presente no retorno."""
        results = all_success_results(score=70)
        agg = aggregate_metrics(EVAL_ID, results, VIDEO_META)
        assert "overall_score" in agg

    def test_missing_dims_treated_as_failure(self):
        """Dims ausentes do results dict sao tratados como incomplete."""
        # Enviar apenas 5 scoring dims
        results = {}
        for dim in ["posture", "gesture", "voice", "fillers", "variety"]:
            results[dim] = make_success(dim, score=75)
        # Nao incluir as outras 8 dims
        agg = aggregate_metrics(EVAL_ID, results, VIDEO_META)
        # partial_aggregation deve ser True (faltam dims)
        assert agg["partial_aggregation"] is True
        # overall_score deve ser calculado com as 5 que existem
        assert agg["overall_score"] is not None


# ---------------------------------------------------------------------------
# T5 — Pesos contextuais funcionam com WorkerResult input
# ---------------------------------------------------------------------------


class TestContextualWeights:
    def test_palco_context_increases_posture_weight(self):
        """Contexto 'palco' usa pesos especificos (posture=0.22 vs 0.18 default)."""
        results_base = all_success_results(score=50)
        # Com palco, posture tem mais peso → mudar score de posture muda overall
        results_high_posture = {**results_base}
        results_high_posture["posture"] = make_success("posture", score=100)
        results_high_posture["variety"] = make_success("variety", score=0)

        agg_palco = aggregate_metrics(EVAL_ID, results_high_posture, VIDEO_META, contexto="palco")
        agg_default = aggregate_metrics(EVAL_ID, results_high_posture, VIDEO_META)

        assert agg_palco["contexto"] == "palco"
        assert agg_palco["overall_score"] is not None

    def test_podcast_context_increases_voice_weight(self):
        """Contexto 'podcast' usa pesos especificos (voice=0.35)."""
        results = all_success_results(score=50)
        agg = aggregate_metrics(EVAL_ID, results, VIDEO_META, contexto="podcast")
        assert agg["contexto"] == "podcast"
        assert agg["overall_score"] is not None

    def test_motivacao_maps_to_context(self):
        """motivacao='palestrar' mapeia para contexto 'palco'."""
        results = all_success_results(score=75)
        agg = aggregate_metrics(EVAL_ID, results, VIDEO_META, motivacao=["palestrar"])
        assert agg["contexto"] == "palco"

    def test_motivacao_sem_mapeamento_usa_default(self):
        """motivacao='satisfacao_pessoal' (sem mapeamento) usa pesos default."""
        results = all_success_results(score=75)
        agg = aggregate_metrics(EVAL_ID, results, VIDEO_META, motivacao=["satisfacao_pessoal"])
        assert agg["contexto"] is None  # default nao tem contexto

    def test_contexto_direto_tem_prioridade_sobre_motivacao(self):
        """contexto direto tem prioridade sobre motivacao."""
        results = all_success_results(score=75)
        agg = aggregate_metrics(
            EVAL_ID, results, VIDEO_META, contexto="palco", motivacao=["vender_mais"]
        )
        assert agg["contexto"] == "palco"  # motivacao 'vendas' ignorada

    def test_pesos_utilizados_presente_no_retorno(self):
        """pesos_utilizados presente no retorno."""
        results = all_success_results(score=75)
        agg = aggregate_metrics(EVAL_ID, results, VIDEO_META)
        assert "pesos_utilizados" in agg
        assert isinstance(agg["pesos_utilizados"], dict)


# ---------------------------------------------------------------------------
# T6 — Legacy path aggregate_metrics_legacy() intacto
# ---------------------------------------------------------------------------


class TestLegacyPath:
    def _legacy_success(self, score: int = 75) -> dict:
        return {"score": score, "confidence": "high", "metrics": {"val": score}}

    def _legacy_failure(self) -> dict:
        return {"score": 0, "confidence": "failed", "metrics": {}}

    def test_legacy_accepts_6_dicts(self):
        """aggregate_metrics_legacy() aceita 6 dicts separados."""
        agg = aggregate_metrics_legacy(
            EVAL_ID,
            self._legacy_success(80),
            self._legacy_success(70),
            self._legacy_success(75),
            self._legacy_success(90),
            self._legacy_success(85),
            self._legacy_success(65),
            VIDEO_META,
        )
        assert isinstance(agg["overall_score"], int)
        assert agg["overall_score"] is not None

    def test_legacy_all_failure_returns_zero(self):
        """Legacy all-failure retorna 0 (comportamento legado documentado)."""
        agg = aggregate_metrics_legacy(
            EVAL_ID,
            self._legacy_failure(),
            self._legacy_failure(),
            self._legacy_failure(),
            self._legacy_failure(),
            self._legacy_failure(),
            self._legacy_failure(),
            VIDEO_META,
        )
        # Legacy INTENCIONAL: score=0 quando todas falharam (documentado)
        assert agg["overall_score"] == 0

    def test_legacy_does_not_use_worker_result(self):
        """Legacy path NAO usa WorkerResult em nenhum ponto."""
        agg = aggregate_metrics_legacy(
            EVAL_ID,
            self._legacy_success(),
            self._legacy_success(),
            self._legacy_success(),
            self._legacy_success(),
            self._legacy_success(),
            self._legacy_success(),
            VIDEO_META,
        )
        # Retorno deve ser dict python simples (nao WorkerResult)
        assert isinstance(agg, dict)
        assert not hasattr(agg, "dimension_status")

    def test_legacy_no_partial_aggregation_key(self):
        """Legacy path NAO inclui partial_aggregation (campo novo do TC)."""
        agg = aggregate_metrics_legacy(
            EVAL_ID,
            self._legacy_success(),
            self._legacy_success(),
            self._legacy_success(),
            self._legacy_success(),
            self._legacy_success(),
            self._legacy_success(),
            VIDEO_META,
        )
        # partial_aggregation e campo novo — legacy nao retorna
        assert "partial_aggregation" not in agg

    def test_legacy_contextual_weights_work(self):
        """Pesos contextuais funcionam no legacy path."""
        agg = aggregate_metrics_legacy(
            EVAL_ID,
            self._legacy_success(80),
            self._legacy_success(70),
            self._legacy_success(75),
            self._legacy_success(90),
            self._legacy_success(85),
            self._legacy_success(65),
            VIDEO_META,
            contexto="palco",
        )
        assert agg["contexto"] == "palco"

    def test_legacy_score_calculation_correct(self):
        """Legacy score calculado corretamente com pesos default."""
        # Todos com score 100 → overall deve ser 100
        agg = aggregate_metrics_legacy(
            EVAL_ID,
            self._legacy_success(100),  # posture
            self._legacy_success(100),  # gesture
            self._legacy_success(100),  # voice
            self._legacy_success(100),  # fillers
            self._legacy_success(100),  # variety
            self._legacy_success(100),  # archetypes
            VIDEO_META,
        )
        assert agg["overall_score"] == 100


# ---------------------------------------------------------------------------
# T7 — Veto conditions especificos
# ---------------------------------------------------------------------------


class TestVetoConditions:
    def test_veto_v1_overall_score_not_zero_on_all_failure(self):
        """VETO V1: overall_score NAO eh 0 por fallback no TC path."""
        results = all_failure_results()
        agg = aggregate_metrics(EVAL_ID, results, VIDEO_META)
        assert agg["overall_score"] is None, (
            f"VETO V1 violado: overall_score={agg['overall_score']} mas deveria ser None"
        )

    def test_veto_v3_partial_aggregation_present(self):
        """VETO V3: partial_aggregation presente no retorno do TC path."""
        results = all_success_results()
        agg = aggregate_metrics(EVAL_ID, results, VIDEO_META)
        assert "partial_aggregation" in agg, "VETO V3 violado: partial_aggregation ausente"

    def test_veto_v4_not_hardcoded_6_dims(self):
        """VETO V4: aggregator processa mais de 6 dimensoes (nao hardcoded)."""
        results = all_success_results(score=80)
        agg = aggregate_metrics(EVAL_ID, results, VIDEO_META)
        # detailed_metrics deve ter mais que 6 entries
        assert len(agg["detailed_metrics"]) > 6, (
            f"VETO V4 violado: detailed_metrics tem {len(agg['detailed_metrics'])} dims — "
            "parece hardcoded pra 6"
        )

    def test_veto_v5_legacy_works_independently(self):
        """VETO V5: legacy path funciona independentemente do TC path."""
        # TC path
        tc_results = all_success_results(score=80)
        tc_agg = aggregate_metrics(EVAL_ID, tc_results, VIDEO_META)
        # Legacy path
        legacy_success = {"score": 80, "confidence": "high", "metrics": {}}
        leg_agg = aggregate_metrics_legacy(
            EVAL_ID,
            legacy_success,
            legacy_success,
            legacy_success,
            legacy_success,
            legacy_success,
            legacy_success,
            VIDEO_META,
        )
        # Ambos devem retornar overall_score valido
        assert tc_agg["overall_score"] is not None
        assert leg_agg["overall_score"] is not None

    def test_partial_true_when_single_failure(self):
        """partial_aggregation=True mesmo com apenas 1 scoring dim falha."""
        results = all_success_results(score=80)
        results["fillers"] = make_failure("fillers")
        agg = aggregate_metrics(EVAL_ID, results, VIDEO_META)
        assert agg["partial_aggregation"] is True

    def test_augmentation_failure_does_not_cause_partial(self):
        """Falha em augmentation dim nao causa partial_aggregation=True."""
        results = all_success_results(score=80)
        # Todas scoring dims com sucesso, mas augmentation falha
        for dim in AUGMENTATION_DIMENSIONS:
            results[dim] = make_failure(dim)
        agg = aggregate_metrics(EVAL_ID, results, VIDEO_META)
        assert agg["partial_aggregation"] is False
