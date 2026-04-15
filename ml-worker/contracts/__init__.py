"""Truth Contract — schemas validados que workers e aggregator consomem.

Story 8.1: Truth Contract — Fundacao.
"""

from contracts.dimensions import Dimension
from contracts.worker_result import (
    DimensionStatus,
    FailureReason,
    WorkerFailure,
    WorkerResult,
    WorkerSuccess,
)

__all__ = [
    "Dimension",
    "DimensionStatus",
    "FailureReason",
    "WorkerFailure",
    "WorkerResult",
    "WorkerSuccess",
]
