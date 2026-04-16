"""Helpers DRY pra migracao Truth Contract — Story 8.2.

Generic wrapper que converte output dict de qualquer worker pra WorkerResult.
Evita duplicar boilerplate em cada um dos 12 workers.
"""

import structlog

from contracts import WorkerFailure, WorkerResult, WorkerSuccess

logger = structlog.get_logger()

# Mapa confidence string → float (backwards compat)
_CONFIDENCE_MAP = {"high": 1.0, "medium": 0.7, "low": 0.4, "failed": 0.0}


def upstream_failed(result) -> bool:
    """Detecta falha upstream em qualquer schema (legacy/novo/truth-contract)."""
    if not result:
        return True
    if not isinstance(result, dict):
        return True
    if result.get("confidence") == "failed":
        return True
    if result.get("disponivel") is False:
        return True
    status = result.get("dimension_status")
    if status and status != "ok":
        return True
    return False


def wrap_worker_result(
    dimension: str,
    compute_fn,
    *args,
    upstream_checks: list | None = None,
    **kwargs,
) -> WorkerResult:
    """Chama compute_fn e converte retorno dict → WorkerResult.

    Args:
        dimension: nome canonico da dimensao (ex: "posture")
        compute_fn: funcao que retorna dict com score/metrics/confidence
        *args: argumentos pra compute_fn
        upstream_checks: lista de dicts upstream pra verificar antes de computar
        **kwargs: keyword args pra compute_fn

    Pattern:
        1. Checa upstream dependencies (se fornecidas)
        2. Chama compute_fn(*args, **kwargs)
        3. Se resultado tem confidence="failed" → WorkerFailure
        4. Se score None → WorkerFailure(insufficient_data)
        5. Extrai metrics (nested ou flat) → WorkerSuccess
        6. Exception → WorkerFailure(crashed)
    """
    try:
        # Check upstream deps
        if upstream_checks:
            for dep in upstream_checks:
                if upstream_failed(dep):
                    return WorkerFailure(
                        dimension=dimension,
                        dimension_status="skipped",
                        failure_reason=f"upstream_dependency_failed: input data unavailable",
                    )

        result = compute_fn(*args, **kwargs)

        # Null/empty result
        if not result or not isinstance(result, dict):
            return WorkerFailure(
                dimension=dimension,
                dimension_status="failed",
                failure_reason="compute returned None or non-dict",
            )

        # Legacy "failed" signal
        if result.get("confidence") == "failed":
            return WorkerFailure(
                dimension=dimension,
                dimension_status="failed",
                failure_reason=result.get("failure_reason", "analysis returned confidence=failed"),
                metrics=result.get("metrics", {}),
            )

        # Score extraction
        score = result.get("score")
        if score is None:
            return WorkerFailure(
                dimension=dimension,
                dimension_status="insufficient_data",
                failure_reason="score is None after analysis",
            )

        # Metrics: prefer nested "metrics" key, fallback to flat dict minus score/confidence
        metrics = result.get("metrics")
        if metrics is None:
            metrics = {k: v for k, v in result.items() if k not in ("score", "confidence")}

        # Confidence: map string → float
        conf_str = result.get("confidence", "high")
        confidence = _CONFIDENCE_MAP.get(conf_str, 0.5) if isinstance(conf_str, str) else 0.5

        return WorkerSuccess(
            dimension=dimension,
            score=max(0, min(100, int(score))),
            metrics=metrics,
            confidence=confidence,
        )

    except Exception as e:
        logger.error(
            f"{dimension}_analysis_crashed",
            error_type=type(e).__name__,
            error=str(e),
            exc_info=True,
        )
        return WorkerFailure(
            dimension=dimension,
            dimension_status="crashed",
            failure_reason=f"{type(e).__name__}: {str(e)}",
        )
