"""ml-worker repositories — camada de persistencia tipada.

Story 8.1 (Truth Contract — Fundacao).
"""

from repositories.analysis_result_repo import (
    save_analysis_result,
    save_analysis_result_legacy,
)

__all__ = [
    "save_analysis_result",
    "save_analysis_result_legacy",
]
