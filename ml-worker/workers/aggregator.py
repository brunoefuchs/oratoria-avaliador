import structlog

logger = structlog.get_logger()

# Pesos default (sem contexto ou contexto "outro")
PESOS_DEFAULT = {
    "variety": 0.29,
    "voice": 0.24,
    "gesture": 0.18,
    "posture": 0.18,
    "fillers": 0.11,
}

# Pesos contextuais por tipo de apresentacao
PESOS_POR_CONTEXTO = {
    "palco": {"variety": 0.25, "voice": 0.20, "gesture": 0.18, "posture": 0.22, "fillers": 0.15},
    "podcast": {"variety": 0.30, "voice": 0.35, "gesture": 0.10, "posture": 0.05, "fillers": 0.20},
    "vendas": {"variety": 0.20, "voice": 0.25, "gesture": 0.20, "posture": 0.15, "fillers": 0.20},
    "rede_social": {
        "variety": 0.25,
        "voice": 0.20,
        "gesture": 0.20,
        "posture": 0.15,
        "fillers": 0.20,
    },
    "reuniao": {"variety": 0.20, "voice": 0.25, "gesture": 0.15, "posture": 0.20, "fillers": 0.20},
    "aula": {"variety": 0.25, "voice": 0.25, "gesture": 0.20, "posture": 0.15, "fillers": 0.15},
}


# Mapeamento motivacao (questionario V2) → pesos contextuais
MOTIVACAO_TO_CONTEXTO = {
    "redes_sociais": "rede_social",
    "vender_mais": "vendas",
    "carreira": "reuniao",
    "palestrar": "palco",
    "satisfacao_pessoal": None,  # usa default
    "outro": None,
}


def _get_pesos(contexto: str | None = None, motivacao: list | None = None) -> dict:
    """Retorna pesos baseados no contexto ou motivacao.

    Prioridade: contexto direto > primeira motivacao com mapeamento > default.
    """
    # Backward compat: contexto direto (V1 do questionario)
    if contexto and contexto in PESOS_POR_CONTEXTO:
        return PESOS_POR_CONTEXTO[contexto]

    # V2: mapear motivacao para contexto
    if motivacao:
        for m in motivacao:
            mapped = MOTIVACAO_TO_CONTEXTO.get(m)
            if mapped and mapped in PESOS_POR_CONTEXTO:
                return PESOS_POR_CONTEXTO[mapped]

    return PESOS_DEFAULT


def aggregate_metrics(
    evaluation_id: str,
    posture_result: dict,
    gesture_result: dict,
    voice_result: dict,
    filler_result: dict,
    variety_result: dict,
    archetype_result: dict,
    video_metadata: dict,
    contexto: str | None = None,
    motivacao: list | None = None,
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

    # Score geral PONDERADO com pesos contextuais
    pesos = _get_pesos(contexto=contexto, motivacao=motivacao)
    overall_score = 0.0
    peso_total = 0.0

    for dimension, peso in pesos.items():
        if dimension in dimension_scores:
            overall_score += dimension_scores[dimension] * peso
            peso_total += peso

    # Normalizar se alguma dimensao falhou
    if peso_total > 0:
        overall_score = round(overall_score / peso_total)
    else:
        overall_score = 0

    # Diagnostico rapido: dimensoes fortes e fracas
    dimensoes_fortes = [dim for dim, score in dimension_scores.items() if score >= 70]
    dimensoes_fracas = [dim for dim, score in dimension_scores.items() if score < 50]

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
        "contexto": contexto,
        "pesos_utilizados": pesos,
        "video_metadata": video_metadata,
    }
