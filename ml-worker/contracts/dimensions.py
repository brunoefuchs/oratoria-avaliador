"""Dimension — fonte unica de verdade dos analyzers do pipeline ML.

Story 9.1 (Epic 9 — State of the Art, 2026-04-16):
Reorganiza o universo de dimensoes em 3 conjuntos semanticamente distintos:

1. SCORING_DIMENSIONS (6): entram no `overall_score` via pesos contextuais.
   Representam medicoes 🟢 Alta confianca (>85%) — backbone ML confiavel.
2. SECONDARY_DIMENSIONS (7): exibidas como "analise complementar" no report
   com badge de confidence. Nao pesam no `overall_score`. Em calibracao com
   mentor Gui (Story 7.7 / Gate 3).
3. AUGMENTATION_DIMENSIONS (3): subset de SECONDARY consumido internamente
   pelo `report_generator` para enriquecer prompt LLM. Preservado como alias
   para compat com pipeline existente.

v0.6.0 legacy (Epic 8 Truth Contract): SCORING_DIMENSIONS_V060 preserva a
lista de 10 dimensoes que pesavam no aggregator quando feature flag
`STATE_OF_ART_ENABLED=false`. Permite rollback instantaneo.

Story 8.1 prehistory: existem 13 analyzers reais em ml-worker/workers/
(10 scoring + 3 augmentation).
"""

from typing import Literal

# ─────────────────────────────────────────────────────────────────────────────
# V0.7.0 CANONICAL (flag ON — Epic 9 active)
# ─────────────────────────────────────────────────────────────────────────────

# 6 scoring dimensions — compoem overall_score via aggregator com pesos novos.
# Todas sao 🟢 Alta confianca (>85%). variety entra como meta-dim sobre outputs 🟢.
# NOTA (2026-04-30): articulation removida do SCORING. Smoke test mobile mostrou
# spectral_clarity 0.003 pra Gui E aluna (codec corta 4-8kHz). Nao discrimina.
# Mantida em SECONDARY pra coleta passiva ate validar com audio studio-grade.
SCORING_DIMENSIONS: tuple[str, ...] = (
    "posture",
    "gesture",
    "voice",
    "fillers",
    "variety",
    "facial",
)

# 7 secondary dimensions — "analise complementar" no report, sem peso no score.
# Em calibracao com mentor (Gate 3). Promocao → scoring requer Gate 3 PASS.
SECONDARY_DIMENSIONS: tuple[str, ...] = (
    "archetypes",
    "tonality",
    "opening",
    "identity",
    "storytelling",
    "temporal",
    "congruence",
    "gesture_semantic",  # Story 9.6 — Gemini Vision gesto semantico (LLM)
    "articulation",  # 2026-04-30 — coleta passiva ate audio studio validar
)

# ─────────────────────────────────────────────────────────────────────────────
# FAMILY GROUPS (2026-04-29) — esqueleto pedagogico Tecnica vs Narrativa
# ─────────────────────────────────────────────────────────────────────────────
# Decisao arquitetural: separar overall em 2 family_scores pra:
# 1. Isolar calibracao (tecnica nao afeta narrativa e vice-versa)
# 2. Cliente ve 2 verdades (ferramenta vs uso)
# 3. Espelha pedagogia Vinh Giang (5 Foundations vs Storytelling/Archetypes)
#
# TECNICA_DIMENSIONS = SCORING_DIMENSIONS (calibradas, ja entram em overall_score)
# NARRATIVA_DIMENSIONS = subset SECONDARY pendente calibracao Gate 3
# congruence permanece como modificador separado (Look-Feel-Sound triangle)

TECNICA_DIMENSIONS: tuple[str, ...] = (
    "voice",
    "variety",
    "fillers",
)

PRESENCA_DIMENSIONS: tuple[str, ...] = (
    "gesture",
    "posture",
    "facial",
)

NARRATIVA_DIMENSIONS: tuple[str, ...] = (
    "storytelling",
    "archetypes",
    "tonality",
    "identity",
)

# 3 augmentation dimensions — subset de SECONDARY consumido pelo report_generator
# como contexto interno (storytelling structure, temporal arc, congruence checks).
# Preservado como alias para nao quebrar consumers existentes.
AUGMENTATION_DIMENSIONS: tuple[str, ...] = (
    "storytelling",
    "temporal",
    "congruence",
)

# ─────────────────────────────────────────────────────────────────────────────
# V0.6.0 LEGACY (flag OFF — comportamento pre-Epic 9 preservado)
# ─────────────────────────────────────────────────────────────────────────────

# 10 scoring dimensions da v0.6.0 — usadas quando STATE_OF_ART_ENABLED=false.
# NAO remover: aggregate_metrics_legacy depende desta lista.
SCORING_DIMENSIONS_V060: tuple[str, ...] = (
    "posture",
    "gesture",
    "voice",
    "fillers",
    "variety",
    "archetypes",
    "facial",
    "tonality",
    "opening",
    "identity",
)

# ─────────────────────────────────────────────────────────────────────────────
# CONJUNTO COMPLETO (invariante — todas as 13 dims produziveis pelos workers)
# ─────────────────────────────────────────────────────────────────────────────

ALL_DIMENSIONS: tuple[str, ...] = tuple(
    dict.fromkeys(SCORING_DIMENSIONS + SECONDARY_DIMENSIONS + AUGMENTATION_DIMENSIONS)
)

# Literal type — fonte unica de verdade pra type-checker e Pydantic.
Dimension = Literal[
    "posture",
    "gesture",
    "voice",
    "fillers",
    "variety",
    "archetypes",
    "facial",
    "tonality",
    "opening",
    "identity",
    "storytelling",
    "temporal",
    "congruence",
    "gesture_semantic",
    "articulation",
]

# ─────────────────────────────────────────────────────────────────────────────
# CONFIDENCE MAPPING (hardcoded — propriedade do metodo de medicao)
# ─────────────────────────────────────────────────────────────────────────────
# Story 9.1 AC5: badges visuais no report UI.
# Mudar confidence = mudar codigo = code review obrigatorio.

ConfidenceLevel = Literal["alta", "media", "baixa"]

DIMENSION_CONFIDENCE: dict[str, ConfidenceLevel] = {
    # 🟢 Alta (>85%) — ML estado-da-arte validado
    "posture": "alta",
    "gesture": "alta",
    "voice": "alta",
    "fillers": "alta",
    "facial": "alta",
    # 🟡 Media (60-85%) — heuristicas sobre features confiaveis
    "variety": "media",
    "archetypes": "media",
    "tonality": "media",
    "temporal": "media",
    # 🔴 Baixa (<60%) — regex PT-BR ou regras if-then
    "opening": "baixa",
    "identity": "baixa",
    "storytelling": "baixa",
    "congruence": "baixa",
    # 🟡 Media — Story 9.6 LLM structured output, em calibracao (Gemini Vision)
    "gesture_semantic": "media",
    # 🔴 Baixa — articulation em mobile (codec corta 4-8kHz, AGC infla jitter)
    "articulation": "baixa",
}

# ─────────────────────────────────────────────────────────────────────────────
# SCHEMA VERSIONING (Story 9.1 AC7)
# ─────────────────────────────────────────────────────────────────────────────

SCHEMA_VERSION_V060 = "1.1.0"  # baseline — flag OFF mantem este schema
SCHEMA_VERSION_V070 = "1.2.0"  # Epic 9 — flag ON emite este schema

# ─────────────────────────────────────────────────────────────────────────────
# WORKER MODULE MAP (para discovery dinamico)
# ─────────────────────────────────────────────────────────────────────────────

DIMENSION_TO_WORKER_MODULE: dict[str, str] = {
    "posture": "workers.posture_analyzer",
    "gesture": "workers.gesture_analyzer",
    "voice": "workers.voice_analyzer",
    "fillers": "workers.filler_detector",
    "variety": "workers.variety_analyzer",
    "archetypes": "workers.archetype_classifier",
    "facial": "workers.facial_analyzer",
    "tonality": "workers.tonality_analyzer",
    "opening": "workers.opening_analyzer",
    "identity": "workers.identity_analyzer",
    "storytelling": "workers.storytelling_analyzer",
    "temporal": "workers.temporal_analyzer",
    "congruence": "workers.congruence_analyzer",
    "gesture_semantic": "workers.gesture_semantic_analyzer",
}
