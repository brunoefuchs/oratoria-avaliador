"""Replay Eval — Story 9.1.1 Gate 2 smoke execution.

Lê aggregated_metrics salvo de evals do Supabase e re-executa aggregate_metrics
em ambos paths (flag OFF = V060, flag ON = V070) para comparar overall_score.

Uso:
    python ml-worker/scripts/replay_eval.py                # 5 evals mais recentes
    python ml-worker/scripts/replay_eval.py --limit 10     # N evals
    python ml-worker/scripts/replay_eval.py --eval-id X    # 1 eval especifico
    python ml-worker/scripts/replay_eval.py --json         # JSON output
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_ML_WORKER_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ML_WORKER_ROOT))


def _reconstruct_worker_results(detailed_metrics: dict) -> dict:
    """Transforma detailed_metrics (dict) → dict[str, WorkerSuccess]."""
    from contracts import WorkerSuccess

    results = {}
    for dim, metrics in detailed_metrics.items():
        if not isinstance(metrics, dict):
            continue
        # Score pode vir em metrics.score ou no dim_scores (nao temos aqui — reconstroi a partir)
        # Para replay, usamos score=70 default; aggregate_metrics usa dimension_scores separado
        # Mas AC1 do 9.1 foi testado via dict com score. Vamos reconstituir WorkerSuccess fiel.
        score = metrics.get("score")
        if score is None:
            # Sem score explícito no detailed_metrics — usa placeholder 70 (replay é relativo)
            score = 70

        results[dim] = WorkerSuccess(
            dimension=dim,
            score=int(round(score)),
            metrics=metrics,
            confidence=1.0,
        )
    return results


def _reconstruct_from_dimension_scores(dimension_scores: dict, detailed_metrics: dict) -> dict:
    """Versao fiel: usa dimension_scores (do aggregated_metrics row) pra WorkerSuccess."""
    from contracts import WorkerSuccess

    results = {}
    # Todas as dims scoring vem de dimension_scores
    for dim, score in dimension_scores.items():
        metrics = detailed_metrics.get(dim, {})
        if not isinstance(metrics, dict):
            metrics = {}
        results[dim] = WorkerSuccess(
            dimension=dim,
            score=int(round(score)),
            metrics=metrics,
            confidence=1.0,
        )

    # Secondary dims entram em detailed_metrics apenas
    from contracts.dimensions import ALL_DIMENSIONS

    for dim in ALL_DIMENSIONS:
        if dim in results:
            continue
        metrics = detailed_metrics.get(dim, {})
        if isinstance(metrics, dict) and metrics:
            # Score inferido do metrics.score se presente, senão 70 default
            s = metrics.get("score", 70)
            results[dim] = WorkerSuccess(
                dimension=dim,
                score=int(round(s)),
                metrics=metrics,
                confidence=1.0,
            )

    return results


def _run_aggregator(results: dict, contexto: str | None, flag_on: bool) -> dict:
    """Executa aggregate_metrics com flag toggle via env var."""
    if flag_on:
        os.environ["STATE_OF_ART_ENABLED"] = "true"
    else:
        os.environ["STATE_OF_ART_ENABLED"] = "false"

    # Reload aggregator pra pegar novo flag
    import importlib

    import workers.aggregator as agg_module

    importlib.reload(agg_module)

    return agg_module.aggregate_metrics(
        evaluation_id="replay",
        results=results,
        video_metadata={"duration_seconds": 120.0},
        contexto=contexto,
    )


def _explain_delta(v060_score: int | None, v070_score: int | None, dimension_scores: dict) -> str:
    """Gera explicacao rastreavel da diferenca baseado em pesos + dims presentes."""
    if v060_score is None or v070_score is None:
        return "score incompleto (partial_aggregation)"

    delta = v070_score - v060_score
    direction = "subiu" if delta > 0 else "desceu" if delta < 0 else "igual"

    # Identificar dims que mudaram de categoria
    v060_dims = {"variety", "voice", "gesture", "posture", "fillers"}  # pesos V060
    v070_dims = {"voice", "variety", "gesture", "facial", "posture", "fillers"}  # pesos V070

    scoring_dims_present = set(dimension_scores.keys())
    facial_entered = "facial" in (scoring_dims_present & v070_dims) and "facial" not in v060_dims
    facial_score = dimension_scores.get("facial", "?")

    parts = [f"score {direction} {abs(delta)}pt"]
    if facial_entered and facial_score != "?":
        parts.append(f"facial agora pesa 0.16 (era 0) com score={facial_score}")
    # Dims que sairam do V070 (archetypes)
    if "archetypes" in scoring_dims_present:
        parts.append(
            f"archetypes={dimension_scores['archetypes']} saiu do scoring (agora secondary)"
        )

    return " · ".join(parts)


def replay_eval(supabase_client, eval_id: str) -> dict | None:
    """Replay um eval especifico. Retorna dict com v060/v070/delta/explicacao ou None."""
    result = (
        supabase_client.table("aggregated_metrics")
        .select("*")
        .eq("evaluation_id", eval_id)
        .execute()
    )
    if not result.data:
        return None

    row = result.data[0]
    dimension_scores = row.get("dimension_scores") or {}
    detailed_metrics = row.get("detailed_metrics") or {}
    contexto = row.get("contexto")

    # Busca motivacao no eval (opcional)
    eval_row = supabase_client.table("evaluations").select("*").eq("id", eval_id).execute()
    created_at = eval_row.data[0].get("created_at", "")[:10] if eval_row.data else "?"

    if not dimension_scores:
        return None

    results = _reconstruct_from_dimension_scores(dimension_scores, detailed_metrics)

    # Path V060 (flag OFF)
    agg_v060 = _run_aggregator(results, contexto, flag_on=False)
    # Path V070 (flag ON)
    agg_v070 = _run_aggregator(results, contexto, flag_on=True)

    v060 = agg_v060.get("overall_score")
    v070 = agg_v070.get("overall_score")
    delta = (v070 - v060) if (v060 is not None and v070 is not None) else None
    explanation = _explain_delta(v060, v070, dimension_scores)

    return {
        "eval_id": eval_id,
        "created_at": created_at,
        "contexto": contexto or "default",
        "dimension_scores": dimension_scores,
        "overall_score_v060": v060,
        "overall_score_v070": v070,
        "delta": delta,
        "explanation": explanation,
        "dims_confidence": agg_v070.get("dimension_confidence", {}),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay eval — Gate 2 smoke Story 9.1.1")
    parser.add_argument("--limit", type=int, default=5, help="Num evals (default 5)")
    parser.add_argument("--eval-id", type=str, help="Eval especifico")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    try:
        from supabase import create_client

        import config

        client = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
    except Exception as e:
        print(f"Erro conectando ao Supabase: {e}", file=sys.stderr)
        return 1

    if args.eval_id:
        eval_ids = [args.eval_id]
    else:
        r = client.table("aggregated_metrics").select("evaluation_id").limit(args.limit).execute()
        eval_ids = [row["evaluation_id"] for row in r.data]

    results = []
    for eid in eval_ids:
        replay = replay_eval(client, eid)
        if replay:
            results.append(replay)

    # Summary
    max_delta = max((abs(r["delta"]) for r in results if r["delta"] is not None), default=0)
    verdict = "PASS" if max_delta <= 15 else "FAIL"

    summary = {
        "results": results,
        "max_delta": max_delta,
        "verdict": verdict,
        "criteria": "delta<=15pt + rastreabilidade (Story 9.1 PO-adjusted)",
        "n_evals": len(results),
    }

    if args.json:
        print(json.dumps(summary, indent=2, default=str))
    else:
        print("=" * 70)
        print(f"Gate 2 Smoke — {len(results)} evals")
        print("=" * 70)
        print(f"{'eval_id':<10} {'ctx':<10} {'v060':<6} {'v070':<6} {'delta':<8} explicação")
        print("-" * 70)
        for r in results:
            print(
                f"{r['eval_id'][:8]:<10} "
                f"{r['contexto'][:10]:<10} "
                f"{str(r['overall_score_v060']):<6} "
                f"{str(r['overall_score_v070']):<6} "
                f"{str(r['delta']):<8} "
                f"{r['explanation'][:50]}"
            )
        print("-" * 70)
        print(f"Max delta: {max_delta}pt · Verdict: {verdict}")

    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
