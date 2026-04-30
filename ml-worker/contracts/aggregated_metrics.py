"""AggregatedMetrics — contrato Pydantic para saida do aggregator.

Story 8.5 (Truth Contract — Report Generator Rewrite): define o schema
tipado que generate_report() recebe. Garante que score=None nao seja
escondido silenciosamente como 0 no prompt ao LLM.

V8 do audit: generate_report recebia dict sem contrato. Esta class fecha.
"""

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class AggregatedMetrics(BaseModel):
    """Resultado agregado tipado com overall_score honesto.

    Campos obrigatorios refletem exatamente o que aggregate_metrics() retorna
    quando TRUTH_CONTRACT_ENABLED=true (Story 8.4).

    overall_score: int valido [0,100] quando ha dimensoes de scoring com sucesso.
                   None quando TODAS as dimensoes de scoring falharam.
    partial_aggregation: True quando alguma dimensao falhou mas ha score parcial.
    """

    model_config = ConfigDict(extra="allow")  # aggregator retorna campos extras

    overall_score: int | None
    # Family scores (2026-04-29) — esqueleto pedagogico Tecnica vs Narrativa.
    # tecnica = overall_score (mesmas dims/pesos). narrativa = subset SECONDARY.
    family_scores: dict[str, int | None] = Field(default_factory=dict)
    dimension_scores: dict[str, int] = Field(default_factory=dict)
    detailed_metrics: dict[str, Any] = Field(default_factory=dict)
    incomplete_dimensions: list[str] = Field(default_factory=list)
    partial_aggregation: bool = False
    contexto: str | None = None
    pesos_utilizados: dict[str, float] = Field(default_factory=dict)
    video_metadata: dict[str, Any] = Field(default_factory=dict)

    # Augmentation dims (opcionais)
    identity: Optional[dict] = None
    opening: Optional[dict] = None
    storytelling: Optional[dict] = None
    temporal: Optional[dict] = None
    congruence: Optional[dict] = None

    # Story 9.1 (Epic 9 — State of the Art): confidence badges + schema version.
    # Populados apenas quando STATE_OF_ART_ENABLED=true. Optional garante
    # backward compat com payloads v0.6.0 (sem estes campos).
    dimension_confidence: Optional[dict[str, str]] = None
    schema_version: Optional[str] = None
