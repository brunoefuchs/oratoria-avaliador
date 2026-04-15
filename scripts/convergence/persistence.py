"""Supabase persistence — AC-5, AC-6 of Story 7.6.

Scaffold: uses supabase-py if available. Tables created by
supabase/migrations/010_convergence_runs.sql and 011_convergence_alerts.sql.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .correlator import ConvergenceReport
    from .llm_client import EvaluationResult


def _get_supabase():
    try:
        from supabase import create_client  # type: ignore
    except ImportError as exc:
        raise RuntimeError("supabase-py not installed. pip install supabase") from exc
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not (url and key):
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY required")
    return create_client(url, key)


def persist_runs(
    video_id: str,
    prompt_version: str,
    evaluations: "dict[str, EvaluationResult]",
) -> list[dict]:
    """Insert one row per LLM into convergence_runs. Unique (video_id, llm, prompt_version)."""
    client = _get_supabase()
    rows = [
        {
            "video_id": video_id,
            "llm": llm,
            "score_geral": ev.score_geral,
            "scores_por_dimensao": ev.scores_por_dimensao,
            "pontos_fortes_top3": ev.pontos_fortes,
            "pontos_fracos_top3": ev.pontos_fracos,
            "raw_response": ev.raw_response,
            "prompt_version": prompt_version,
            "model_version": ev.model_version,
        }
        for llm, ev in evaluations.items()
    ]
    result = client.table("convergence_runs").upsert(
        rows, on_conflict="video_id,llm,prompt_version"
    ).execute()
    return result.data or []


def persist_alerts(video_id: str, report: "ConvergenceReport") -> list[dict]:
    """Insert one row per alert into convergence_alerts."""
    if not report.alerts:
        return []
    client = _get_supabase()
    rows = [
        {
            "video_id": video_id,
            "dimensao": a["dimensao"],
            "r_calculado": float(a["r_calculado"]),
            "r_esperado": float(a["r_esperado"]),
            "severidade": a["severidade"],
            "detalhes": a["detalhes"],
        }
        for a in report.alerts
    ]
    result = client.table("convergence_alerts").insert(rows).execute()
    return result.data or []
