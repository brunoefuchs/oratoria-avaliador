"""WorkerResult — contrato universal de retorno dos analyzers.

Story 8.1 (Truth Contract — Fundacao).

Principio: dado no banco so existe se rastreavel ate fonte de verdade.
Workers retornam Success ou Failure como tipos discriminados.
Nunca score=0 em fallback. Nunca score=50 mentindo. Nunca dict solto.
"""

from enum import Enum
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

from contracts.dimensions import Dimension


class DimensionStatus(str, Enum):
    """Estado possivel de uma dimensao apos analise."""

    OK = "ok"
    FAILED = "failed"
    SKIPPED = "skipped"
    INSUFFICIENT_DATA = "insufficient_data"
    CRASHED = "crashed"


class FailureReason(str, Enum):
    """Categorias normalizadas de falha. Workers podem usar string livre se
    nao se encaixar — mas devem priorizar as categorias daqui."""

    VIDEO_TOO_SHORT = "video_too_short"
    VIDEO_CORRUPTED = "video_corrupted"
    AUDIO_MISSING = "audio_missing"
    AUDIO_TOO_QUIET = "audio_too_quiet"
    TRANSCRIPTION_FAILED = "transcription_failed"
    LLM_TIMEOUT = "llm_timeout"
    LLM_INVALID_RESPONSE = "llm_invalid_response"
    SCHEMA_INVALID = "schema_invalid"
    UPSTREAM_DEPENDENCY_FAILED = "upstream_dependency_failed"
    UNKNOWN_EXCEPTION = "unknown_exception"


class WorkerSuccess(BaseModel):
    """Worker concluiu com sucesso. Score eh int valido [0, 100]."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    dimension: Dimension
    dimension_status: Literal["ok"] = "ok"
    score: int = Field(ge=0, le=100)
    metrics: dict[str, Any]
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)


class WorkerFailure(BaseModel):
    """Worker nao produziu score utilizavel. Score eh None — nunca 0 ou 50.

    failure_reason eh string livre (nao Enum) para permitir contexto rico
    sem perder a normalizacao via FailureReason quando aplicavel.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    dimension: Dimension
    dimension_status: Literal["failed", "skipped", "insufficient_data", "crashed"]
    score: None = None
    failure_reason: str = Field(min_length=1)
    metrics: dict[str, Any] = Field(default_factory=dict)


WorkerResult = Annotated[
    Union[WorkerSuccess, WorkerFailure],
    Field(discriminator="dimension_status"),
]
"""Discriminated Union: Pydantic dispatcha pra Success ou Failure pelo
campo dimension_status. Use isinstance(result, WorkerSuccess) para
distinguir em runtime, ou pattern matching no dimension_status."""
