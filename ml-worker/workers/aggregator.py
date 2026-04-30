"""Aggregator — combina outputs dos workers em payload unico.

Story 9.1 (Epic 9 — State of the Art): refatora fluxo de agregacao:
- Path v0.7.0 (STATE_OF_ART_ENABLED=true): usa SCORING_DIMENSIONS (6 dims)
  com PESOS_DEFAULT novos + SECONDARY_DIMENSIONS em detailed_metrics +
  dimension_confidence no payload.
- Path v0.6.0 (flag OFF): usa SCORING_DIMENSIONS_V060 (10 dims) e mantem
  comportamento pre-Epic 9 bit-identico (incluindo "scoring fantasma" das 5
  dims sem peso).

aggregate_metrics_legacy preservado intocado para consumers que chamam path
pre-Epic 8 (dict sem WorkerResult).
"""

import structlog

from config import is_state_of_art_enabled
from contracts import WorkerFailure, WorkerSuccess
from contracts.dimensions import (
    AUGMENTATION_DIMENSIONS,
    DIMENSION_CONFIDENCE,
    SCHEMA_VERSION_V060,
    SCHEMA_VERSION_V070,
    SCORING_DIMENSIONS,
    SCORING_DIMENSIONS_V060,
    SECONDARY_DIMENSIONS,
)

logger = structlog.get_logger()

# ─────────────────────────────────────────────────────────────────────────────
# V0.7.0 PESOS (STATE_OF_ART_ENABLED=true) — Cenario B aprovado @po 2026-04-16
# ─────────────────────────────────────────────────────────────────────────────
# HEURISTIC_V1 — calibrar via Story 9.7 post-Gate 3 (ground truth Gui Reginatto).
# Valores derivam do diagnostico Vinh + principios de "variety como meta-dim".
# NAO editar sem Story 9.7 aprovada.

PESOS_DEFAULT: dict[str, float] = {
    "voice": 0.22,
    "variety": 0.20,
    "gesture": 0.18,
    "facial": 0.16,
    "posture": 0.14,
    "fillers": 0.10,
}

PESOS_POR_CONTEXTO: dict[str, dict[str, float]] = {
    # HEURISTIC_V1 — calibrar via Story 9.7 post-Gate 3
    "palco": {
        "voice": 0.18,
        "variety": 0.22,
        "gesture": 0.20,
        "facial": 0.14,
        "posture": 0.18,
        "fillers": 0.08,
    },
    "podcast": {
        "voice": 0.28,
        "variety": 0.25,
        "gesture": 0.08,
        "facial": 0.15,
        "posture": 0.06,
        "fillers": 0.18,
    },
    "vendas": {
        "voice": 0.22,
        "variety": 0.20,
        "gesture": 0.18,
        "facial": 0.16,
        "posture": 0.12,
        "fillers": 0.12,
    },
    "rede_social": {
        "voice": 0.20,
        "variety": 0.18,
        "gesture": 0.18,
        "facial": 0.20,
        "posture": 0.10,
        "fillers": 0.14,
    },
    "reuniao": {
        "voice": 0.22,
        "variety": 0.18,
        "gesture": 0.14,
        "facial": 0.16,
        "posture": 0.18,
        "fillers": 0.12,
    },
    "aula": {
        "voice": 0.22,
        "variety": 0.22,
        "gesture": 0.18,
        "facial": 0.14,
        "posture": 0.14,
        "fillers": 0.10,
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# V0.6.0 PESOS (STATE_OF_ART_ENABLED=false) — rollback preservation
# ─────────────────────────────────────────────────────────────────────────────
# Pesos originais pre-Epic 9. Soma 1.00 sobre 5 dims (archetypes/facial/tonality/
# opening/identity ficam fora — "scoring fantasma" documentado).
# NAO editar — this is load-bearing legacy.

PESOS_DEFAULT_V060: dict[str, float] = {
    "variety": 0.29,
    "voice": 0.24,
    "gesture": 0.18,
    "posture": 0.18,
    "fillers": 0.11,
}

# ─────────────────────────────────────────────────────────────────────────────
# FAMILY SCORES (2026-04-29) — Look-Feel-Sound Triangle de Vinh Giang
# ─────────────────────────────────────────────────────────────────────────────
# 3 familias pedagogicas mapeadas em 1-pra-1 com o triangle:
#   TECNICA VOCAL    (Sound) — voz como instrumento
#   PRESENCA FISICA  (Look)  — corpo paralelo a fala
#   NARRATIVA        (Feel)  — mensagem que conecta
# Pesos iniciais HEURISTIC — calibracao real virá apos Vinh validar primeira
# leva. overall_score continua usando PESOS_DEFAULT (todas dims) por compat.

PESOS_TECNICA: dict[str, float] = {
    "voice": 0.40,
    "variety": 0.40,
    "fillers": 0.20,
}

PESOS_PRESENCA: dict[str, float] = {
    "gesture": 0.35,
    "posture": 0.30,
    "facial": 0.35,
}

PESOS_NARRATIVA: dict[str, float] = {
    "storytelling": 0.35,  # Bridge/hook/chemicals — coracao da mensagem
    "archetypes": 0.25,  # Cycling de 4 personas (anti-default)
    "tonality": 0.25,  # VAD emocional (arousal/valence/dominance)
    "identity": 0.15,  # Coerencia da persona ao longo do video
}

PESOS_POR_CONTEXTO_V060: dict[str, dict[str, float]] = {
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


# ─────────────────────────────────────────────────────────────────────────────
# MOTIVACAO → CONTEXTO (invariante entre versions)
# ─────────────────────────────────────────────────────────────────────────────

MOTIVACAO_TO_CONTEXTO: dict[str, str | None] = {
    "redes_sociais": "rede_social",
    "vender_mais": "vendas",
    "carreira": "reuniao",
    "palestrar": "palco",
    "satisfacao_pessoal": None,
    "outro": None,
}


def _get_pesos(
    contexto: str | None = None,
    motivacao: list | None = None,
    force_v060: bool = False,
) -> tuple[dict[str, float], str | None]:
    """Seleciona pesos (flag-aware) + contexto resolvido pra badge UI.

    Prioridade: contexto direto > primeira motivacao com mapeamento > default.

    Story 9.1 QA fix (C2): parametro `force_v060=True` permite que callers
    (ex: aggregate_metrics_legacy) garantam pesos V060 INDEPENDENTE da
    feature flag. Preserva guarantee "legacy intocado" do Epic 8.
    """
    if force_v060 or not is_state_of_art_enabled():
        pesos_contexto = PESOS_POR_CONTEXTO_V060
        pesos_default = PESOS_DEFAULT_V060
    else:
        pesos_contexto = PESOS_POR_CONTEXTO
        pesos_default = PESOS_DEFAULT

    if contexto and contexto in pesos_contexto:
        return pesos_contexto[contexto], contexto

    if motivacao:
        for m in motivacao:
            mapped = MOTIVACAO_TO_CONTEXTO.get(m)
            if mapped and mapped in pesos_contexto:
                return pesos_contexto[mapped], mapped

    return pesos_default, None


def _active_scoring_dims() -> tuple[str, ...]:
    """Retorna scoring dims conforme feature flag."""
    return SCORING_DIMENSIONS if is_state_of_art_enabled() else SCORING_DIMENSIONS_V060


def _active_schema_version() -> str:
    """Retorna schema version conforme feature flag."""
    return SCHEMA_VERSION_V070 if is_state_of_art_enabled() else SCHEMA_VERSION_V060


def aggregate_metrics(
    evaluation_id: str,
    results: dict,
    video_metadata: dict,
    contexto: str | None = None,
    motivacao: list | None = None,
) -> dict:
    """Agrega metricas de todas as dimensoes em um payload unico.

    Story 9.1 path (flag ON):
    - SCORING_DIMENSIONS (6): entram no overall_score via PESOS_DEFAULT novo.
    - SECONDARY_DIMENSIONS (7): entram em detailed_metrics, NAO em dimension_scores.
    - dimension_confidence no payload (AC5).
    - schema_version = "1.2.0".

    V0.6.0 path (flag OFF):
    - SCORING_DIMENSIONS_V060 (10): comportamento pre-Epic 9 preservado.
    - AUGMENTATION_DIMENSIONS (3): em detailed_metrics (igual v0.6.0).
    - Sem dimension_confidence, schema_version = "1.1.0".
    - overall_score: int | None; None quando nenhuma scoring dim teve sucesso.
    - partial_aggregation: True quando qualquer scoring dim falhou.
    """
    state_of_art = is_state_of_art_enabled()
    scoring_dims = _active_scoring_dims()
    dimension_scores: dict[str, int] = {}
    detailed_metrics: dict = {}
    incomplete_dimensions: list[str] = []

    # --- Processar scoring dimensions ---
    for dim in scoring_dims:
        result = results.get(dim)
        if result is None:
            incomplete_dimensions.append(dim)
            logger.warning(
                "dimension_missing",
                evaluation_id=evaluation_id,
                dimension=dim,
            )
        elif isinstance(result, WorkerSuccess):
            dimension_scores[dim] = result.score
            # N5 fix: inclui score no metrics dict pro UI renderizar (WorkerSuccess
            # separa score/metrics, mas UI cards como IdentityCard leem data.score)
            detailed_metrics[dim] = {**result.metrics, "score": result.score}
        elif isinstance(result, WorkerFailure):
            incomplete_dimensions.append(dim)
            logger.warning(
                "dimension_incomplete",
                evaluation_id=evaluation_id,
                dimension=dim,
                status=result.dimension_status,
                reason=result.failure_reason,
            )
        else:
            # Fallback defensivo: result eh dict (legacy)
            if result and result.get("confidence") != "failed":
                dimension_scores[dim] = result["score"]
                detailed_metrics[dim] = result.get("metrics", result)
            else:
                incomplete_dimensions.append(dim)

    # --- Processar secondary / augmentation dimensions ---
    # Flag ON: SECONDARY (7). Flag OFF: AUGMENTATION (3) igual v0.6.0.
    complementary_dims = SECONDARY_DIMENSIONS if state_of_art else AUGMENTATION_DIMENSIONS
    for dim in complementary_dims:
        result = results.get(dim)
        if result is None:
            continue
        if isinstance(result, WorkerSuccess):
            detailed_metrics[dim] = {**result.metrics, "score": result.score}
        elif isinstance(result, WorkerFailure):
            logger.info(
                "secondary_dimension_failed",
                evaluation_id=evaluation_id,
                dimension=dim,
                status=result.dimension_status,
            )
        elif isinstance(result, dict):
            if result and result.get("confidence") != "failed":
                detailed_metrics[dim] = result.get("metrics", result)

    # --- Score geral PONDERADO ---
    pesos, contexto_resolvido = _get_pesos(contexto=contexto, motivacao=motivacao)
    overall_score_float = 0.0
    peso_total = 0.0

    for dimension, peso in pesos.items():
        if dimension in dimension_scores:
            overall_score_float += dimension_scores[dimension] * peso
            peso_total += peso

    if peso_total > 0:
        overall_score: int | None = round(overall_score_float / peso_total)
    else:
        overall_score = None

    # ─────────────────────────────────────────────────────────────────
    # FAMILY SCORES (2026-04-29) — Look-Feel-Sound Triangle
    # ─────────────────────────────────────────────────────────────────
    # 3 familias com pesos proprios. Quando uma dim falha, peso ignorado e
    # os restantes renormalizam. Score family = None se nenhuma dim sucesso.
    def _compute_family_score(pesos: dict[str, float]) -> int | None:
        total = 0.0
        peso_acum = 0.0
        for dim, peso in pesos.items():
            score_dim = (
                dimension_scores.get(dim)
                if dim in dimension_scores
                else (detailed_metrics.get(dim) or {}).get("score")
            )
            if isinstance(score_dim, (int, float)):
                total += float(score_dim) * peso
                peso_acum += peso
        return round(total / peso_acum) if peso_acum > 0 else None

    tecnica_score = _compute_family_score(PESOS_TECNICA)
    presenca_score = _compute_family_score(PESOS_PRESENCA)
    narrativa_score = _compute_family_score(PESOS_NARRATIVA)

    family_scores = {
        "tecnica": tecnica_score,
        "presenca": presenca_score,
        "narrativa": narrativa_score,
    }

    partial_aggregation = len(incomplete_dimensions) > 0

    dimensoes_fortes = [dim for dim, score in dimension_scores.items() if score >= 70]
    dimensoes_fracas = [dim for dim, score in dimension_scores.items() if score < 50]

    logger.info(
        "metrics_aggregated",
        evaluation_id=evaluation_id,
        overall_score=overall_score,
        tecnica_score=tecnica_score,
        presenca_score=presenca_score,
        narrativa_score=narrativa_score,
        dimensions_complete=len(dimension_scores),
        incomplete=incomplete_dimensions,
        partial=partial_aggregation,
        fortes=dimensoes_fortes,
        fracas=dimensoes_fracas,
        state_of_art=state_of_art,
    )

    payload: dict = {
        "overall_score": overall_score,
        "family_scores": family_scores,
        "partial_aggregation": partial_aggregation,
        "dimension_scores": dimension_scores,
        "detailed_metrics": detailed_metrics,
        "incomplete_dimensions": incomplete_dimensions,
        "dimensoes_fortes": dimensoes_fortes,
        "dimensoes_fracas": dimensoes_fracas,
        "contexto": contexto_resolvido,
        "pesos_utilizados": pesos,
        "video_metadata": video_metadata,
        "schema_version": _active_schema_version(),
    }

    # Story 9.1 AC5: confidence badges apenas no path v0.7.0
    if state_of_art:
        payload["dimension_confidence"] = {
            dim: DIMENSION_CONFIDENCE[dim]
            for dim in set(dimension_scores.keys()) | set(detailed_metrics.keys())
            if dim in DIMENSION_CONFIDENCE
        }

    return payload


def aggregate_metrics_legacy(
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
    """Agrega metricas de todas as 6 dimensoes em um payload unico.

    LEGACY PATH — preservado 100% intacto para TRUTH_CONTRACT_ENABLED=false
    (Story 8.4). Aceita 6 dicts separados (comportamento pre-Epic 8.0).
    Inclui score=0 fallback documentado — eh legacy, nao bug.
    NAO usa WorkerResult em nenhum ponto.

    Story 9.1 NAO altera este path — usa PESOS_DEFAULT_V060 via _get_pesos
    quando flag OFF (default).
    """
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

    # Story 9.1 QA C2 fix: force_v060=True garante pesos v0.6.0 independente
    # da feature flag STATE_OF_ART_ENABLED. Preserva guarantee legacy intocado.
    pesos, contexto_resolvido = _get_pesos(contexto=contexto, motivacao=motivacao, force_v060=True)
    overall_score = 0.0
    peso_total = 0.0

    for dimension, peso in pesos.items():
        if dimension in dimension_scores:
            overall_score += dimension_scores[dimension] * peso
            peso_total += peso

    if peso_total > 0:
        overall_score = round(overall_score / peso_total)
    else:
        overall_score = 0  # legacy: score=0 quando todas dimensoes falharam

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
        "contexto": contexto_resolvido,
        "pesos_utilizados": pesos,
        "video_metadata": video_metadata,
    }
