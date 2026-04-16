"""Analise de congruencia — detecta contradicoes entre canais de comunicacao.

Roda APOS todos os outros workers. Nao afeta overall_score (informativo).
"""

import structlog

logger = structlog.get_logger()

# Regras de contradicao entre canais
CONTRADICOES = [
    {
        "id": "entusiasmo_vs_postura",
        "descricao": "Voz entusiasmada mas postura fechada",
        "canal_1": ("voice", "pitch_range_semitones", ">=", 10),
        "canal_2": ("posture", "open_posture_pct", "<", 50),
        "penalidade": 15,
    },
    {
        "id": "confianca_vs_olhar",
        "descricao": "Volume alto mas olhar para baixo",
        "canal_1": ("voice", "intensity_mean_db", ">=", 65),
        "canal_2": ("gesture", "olhar_baixo_pct", ">", 20),
        "penalidade": 12,
    },
    {
        "id": "abertura_vs_volume",
        "descricao": "Gestos amplos mas volume baixo",
        "canal_1": ("gesture", "gesticulation_pct", ">=", 50),
        "canal_2": ("voice", "intensity_mean_db", "<", 55),
        "penalidade": 10,
    },
    {
        "id": "urgencia_vs_parado",
        "descricao": "Velocidade alta mas gesticulacao parada",
        "canal_1": ("voice", "wpm", ">=", 170),
        "canal_2": ("gesture", "gesticulation_pct", "<", 20),
        "penalidade": 8,
    },
]


def _check_condition(
    metrics: dict, dimension: str, metric_key: str, op: str, threshold: float
) -> bool:
    """Verifica se uma condicao e atendida nas metricas."""
    dim_metrics = metrics.get(dimension, {})
    value = dim_metrics.get(metric_key)
    if value is None:
        return False

    if op == ">=":
        return value >= threshold
    elif op == ">":
        return value > threshold
    elif op == "<=":
        return value <= threshold
    elif op == "<":
        return value < threshold
    return False


def _compute_congruence_metrics(detailed_metrics: dict) -> dict:
    """Analisa congruencia entre canais de comunicacao."""
    contradicoes_detectadas = []
    total_penalidade = 0

    for regra in CONTRADICOES:
        c1_dim, c1_key, c1_op, c1_thresh = regra["canal_1"]
        c2_dim, c2_key, c2_op, c2_thresh = regra["canal_2"]

        c1_match = _check_condition(detailed_metrics, c1_dim, c1_key, c1_op, c1_thresh)
        c2_match = _check_condition(detailed_metrics, c2_dim, c2_key, c2_op, c2_thresh)

        if c1_match and c2_match:
            contradicoes_detectadas.append(
                {
                    "id": regra["id"],
                    "descricao": regra["descricao"],
                    "penalidade": regra["penalidade"],
                }
            )
            total_penalidade += regra["penalidade"]

    score = max(0, min(100, 100 - total_penalidade))

    if score >= 80:
        diagnostico = "alta_congruencia"
    elif score >= 60:
        diagnostico = "congruencia_moderada"
    elif score >= 40:
        diagnostico = "incongruencia_parcial"
    else:
        diagnostico = "incongruencia_significativa"

    logger.info(
        "congruence_analysis_complete",
        score=score,
        contradicoes=len(contradicoes_detectadas),
        diagnostico=diagnostico,
    )

    return {
        "score": score,
        "diagnostico": diagnostico,
        "contradicoes": contradicoes_detectadas,
        "total_contradicoes": len(contradicoes_detectadas),
    }


# Story 8.3 — Truth Contract
from contracts import WorkerFailure, WorkerResult, WorkerSuccess  # noqa: E402


def analyze_congruence_legacy(detailed_metrics: dict) -> dict:
    """Legacy path (TRUTH_CONTRACT_ENABLED=false)."""
    return _compute_congruence_metrics(detailed_metrics)


def analyze_congruence(detailed_metrics: dict) -> "WorkerResult":
    """Truth Contract path — retorna WorkerResult (Pydantic).

    Congruence nao usa disponivel pattern — retorna score diretamente.
    - score presente → WorkerSuccess
    - Exception → WorkerFailure(crashed)
    """
    try:
        result = _compute_congruence_metrics(detailed_metrics)
        score = result.get("score")
        if score is None:
            return WorkerFailure(
                dimension="congruence",
                dimension_status="insufficient_data",
                failure_reason="score is None after congruence analysis",
            )
        metrics = {k: v for k, v in result.items() if k != "score"}
        return WorkerSuccess(
            dimension="congruence",
            score=max(0, min(100, int(score))),
            metrics=metrics,
            confidence=1.0,
        )
    except Exception as e:
        logger.error("congruence_crashed", error_type=type(e).__name__, error=str(e), exc_info=True)
        return WorkerFailure(
            dimension="congruence",
            dimension_status="crashed",
            failure_reason=f"{type(e).__name__}: {str(e)}",
        )
