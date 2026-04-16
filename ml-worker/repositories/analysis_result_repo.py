"""analysis_result_repo — camada tipada de persistencia pra analysis_results.

Story 8.1 (Truth Contract — Fundacao) T5.

Substitui _save_analysis() em app.py pelo pattern de repo:
- save_analysis_result(supabase, eval_id, result: WorkerResult) — flag ON
- save_analysis_result_legacy(supabase, eval_id, dim, result_dict) — flag OFF

Truth Contract vs Legacy:

Truth Contract (WorkerResult → DB):
    WorkerSuccess → score int, dimension_status='ok', failure_reason=None
    WorkerFailure → score=None, dimension_status=status, failure_reason=reason

Legacy (dict → DB):
    Escreve score=0 em fallback (comportamento documentado no audit Epic 8.0).
    Usado enquanto feature flag TRUTH_CONTRACT_ENABLED=false.
"""

from typing import Any

from contracts import WorkerFailure, WorkerResult, WorkerSuccess


def save_analysis_result(
    supabase: Any, evaluation_id: str, result: WorkerResult
) -> dict:
    """Persistir WorkerResult em analysis_results (Truth Contract path).

    Args:
        supabase: cliente Supabase (duck-typed — precisa ter .table().upsert().execute())
        evaluation_id: UUID da evaluation-pai
        result: WorkerResult validado pelo Pydantic

    Returns:
        Row persistida (dict), ou o payload construido se Supabase retornar vazio.

    Raises:
        TypeError: se `result` nao eh WorkerSuccess nem WorkerFailure (veto T5.1).
    """
    if isinstance(result, WorkerSuccess):
        row = {
            "evaluation_id": evaluation_id,
            "dimension": result.dimension,
            "score": result.score,
            "metrics": result.metrics,
            # confidence legacy — mantido pra consumers antigos conseguirem ler
            # (frontend, aggregator legacy). Story 8.4 removera.
            "confidence": "high",
            "dimension_status": "ok",
            "failure_reason": None,
        }
    elif isinstance(result, WorkerFailure):
        row = {
            "evaluation_id": evaluation_id,
            "dimension": result.dimension,
            "score": None,
            "metrics": result.metrics,
            # confidence legacy: 'failed' permite que aggregator antigo
            # ainda reconheca falha durante migration window
            "confidence": "failed",
            "dimension_status": result.dimension_status,
            "failure_reason": result.failure_reason,
        }
    else:
        # Veto T5.1: save_analysis_result DEVE aceitar apenas WorkerResult.
        # Chamada com dict solto indica caller esqueceu de migrar pro novo
        # contrato OU o worker ainda retorna legacy — nesse caso usar
        # save_analysis_result_legacy().
        raise TypeError(
            f"save_analysis_result requer WorkerResult "
            f"(WorkerSuccess | WorkerFailure); recebeu {type(result).__name__}. "
            f"Use save_analysis_result_legacy() se worker ainda nao foi migrado."
        )

    response = supabase.table("analysis_results").upsert(row).execute()
    if response.data:
        return response.data[0]
    return row


def save_analysis_result_legacy(
    supabase: Any,
    evaluation_id: str,
    dimension: str,
    result_dict: dict,
) -> dict:
    """Persistir dict legacy em analysis_results (pre-Truth-Contract path).

    Usado enquanto `TRUTH_CONTRACT_ENABLED=false` e workers nao migrados.
    Replica o comportamento problematico documentado em Epic 8.0:
    - score fallback 0 quando ausente (mentira documentada)
    - metrics fallback pro dict inteiro
    - confidence fallback 'high'

    Migrar worker → usar save_analysis_result() + WorkerResult.
    """
    row = {
        "evaluation_id": evaluation_id,
        "dimension": dimension,
        "score": result_dict.get("score", 0),  # veto documentado, nao corrigir aqui
        "metrics": result_dict.get("metrics", result_dict),
        "confidence": result_dict.get("confidence", "high"),
        # dimension_status/failure_reason ficam nos defaults do DB
        # (dimension_status='ok' + failure_reason=NULL)
    }
    response = supabase.table("analysis_results").upsert(row).execute()
    if response.data:
        return response.data[0]
    return row
