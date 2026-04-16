"""Dimension — fonte unica de verdade dos analyzers do pipeline ML.

Story 8.1 (Truth Contract — Fundacao).

Pre-Flight discovery (2026-04-15): existem 13 analyzers reais em
ml-worker/workers/, nao 10 como o draft inicial supos. Inclui:

- 10 scoring dimensions (compoem overall_score via aggregator)
- 3 augmentation dimensions (consumidas pelo report_generator mas nao
  entram diretamente no overall_score):
    - storytelling: estrutura narrativa
    - temporal: arco temporal por terco
    - congruence: cruzamento entre canais

OBS: congruence ESTA listada como augmentation aqui pq o aggregator
atualmente trata-a como dimensao paralela (nao tem peso no overall_score
do contexto principal). Decisao revisitada na Story 8.4 (Aggregator
Truth Contract).
"""

from typing import Literal

# 10 scoring dimensions — compoem overall_score via aggregator
SCORING_DIMENSIONS: tuple[str, ...] = (
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

# 3 augmentation dimensions — analise complementar pro report_generator
AUGMENTATION_DIMENSIONS: tuple[str, ...] = (
    "storytelling",
    "temporal",
    "congruence",
)

# Conjunto completo: 13 dimensoes que workers podem produzir
ALL_DIMENSIONS: tuple[str, ...] = SCORING_DIMENSIONS + AUGMENTATION_DIMENSIONS

# Literal type — fonte unica de verdade pra type-checker e Pydantic
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
]

# Mapa para discovery dinamico (modulo onde cada analyzer vive)
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
}
