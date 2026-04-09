import structlog

logger = structlog.get_logger()

# Pesos de cada dimensao no score geral
# Arquetipos removidos do score principal (extra a ser desbloqueado)
# Pesos redistribuidos proporcionalmente entre as 5 dimensoes restantes
PESOS_DIMENSOES = {
    "variety": 0.29,     # Variedade e o mais importante — o meta-principio
    "voice": 0.24,       # Voz e diccao
    "gesture": 0.18,     # Presenca visual (gestual + contato visual)
    "posture": 0.18,     # Postura e presenca fisica
    "fillers": 0.11,     # Clareza verbal
}


def aggregate_metrics(
    evaluation_id: str,
    posture_result: dict,
    gesture_result: dict,
    voice_result: dict,
    filler_result: dict,
    variety_result: dict,
    archetype_result: dict,
    video_metadata: dict,
) -> dict:
    """Agrega metricas de todas as 6 dimensoes em um payload unico."""
    dimension_scores = {}
    detailed_metrics = {}
    incomplete_dimensions = []

    for dimension, result in [
        ("posture", posture_result),
        ("gesture", gesture_result),
        ("voice", voice_result),
        ("fillers", filler_result),
        ("variety", variety_result),
        ("archetypes", archetype_result),
    ]:
        if result and result.get("confidence") != "failed":
            dimension_scores[dimension] = result["score"]
            detailed_metrics[dimension] = result.get("metrics", result)
        else:
            incomplete_dimensions.append(dimension)
            logger.warning(
                "dimension_incomplete",
                evaluation_id=evaluation_id,
                dimension=dimension,
            )

    # Score geral PONDERADO (nao mais media simples)
    overall_score = 0.0
    peso_total = 0.0

    for dimension, peso in PESOS_DIMENSOES.items():
        if dimension in dimension_scores:
            overall_score += dimension_scores[dimension] * peso
            peso_total += peso

    # Normalizar se alguma dimensao falhou
    if peso_total > 0:
        overall_score = round(overall_score / peso_total)
    else:
        overall_score = 0

    # Diagnostico rapido: dimensoes fortes e fracas
    dimensoes_fortes = [
        dim for dim, score in dimension_scores.items() if score >= 70
    ]
    dimensoes_fracas = [
        dim for dim, score in dimension_scores.items() if score < 50
    ]

    logger.info(
        "metrics_aggregated",
        evaluation_id=evaluation_id,
        overall_score=overall_score,
        dimensions_complete=len(dimension_scores),
        incomplete=incomplete_dimensions,
        fortes=dimensoes_fortes,
        fracas=dimensoes_fracas,
    )

    return {
        "overall_score": overall_score,
        "dimension_scores": dimension_scores,
        "detailed_metrics": detailed_metrics,
        "incomplete_dimensions": incomplete_dimensions,
        "dimensoes_fortes": dimensoes_fortes,
        "dimensoes_fracas": dimensoes_fracas,
        "pesos_utilizados": PESOS_DIMENSOES,
        "video_metadata": video_metadata,
    }
