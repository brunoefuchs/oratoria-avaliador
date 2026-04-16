"""Truth Contract — schemas validados que workers e aggregator consomem.

Story 8.1: Truth Contract — Fundacao.
Story 8.5: AggregatedMetrics adicionado (Pydantic input pro report_generator).
"""

from contracts.aggregated_metrics import AggregatedMetrics
from contracts.dimensions import Dimension
from contracts.worker_result import (
    DimensionStatus,
    FailureReason,
    WorkerFailure,
    WorkerResult,
    WorkerSuccess,
)

__all__ = [
    "AggregatedMetrics",
    "Dimension",
    "DimensionStatus",
    "FailureReason",
    "WorkerFailure",
    "WorkerResult",
    "WorkerSuccess",
]
