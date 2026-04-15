"""
process_evaluation.py
─────────────────────
Entrypoint ÚNICO que ml-worker chama ao terminar captura de features.

Liga tudo: ml_worker_adapter → validate_contract → pipeline_end_to_end.

Uso no ml-worker (exemplo após `_run_pipeline` coletar todos os workers):

    from squads.oratoria_avaliador.tasks.process_evaluation import process

    result = process(
        evaluation_id=req.evaluation_id,
        storage_path=video_url,
        duration_seconds=video_duration,
        worker_outputs={
            "voice_analyzer": voice_result,
            "filler_detector": filler_result,
            "posture_analyzer": posture_result,
            "gesture_analyzer": gesture_result,
            "facial_analyzer": facial_result,
            "opening_analyzer": opening_result,
            "tonality_analyzer": tonality_result,  # v1.1.0
        },
        evaluation_context={
            "motivacao": ["vender_mais"],
            "desejo_melhorar": ["autoridade"],
        },
    )

    if result["gate_decision"]["release_to_user"]:
        # Persistir narrativa + entregar ao usuário
        save_report(result["artifacts"]["narrative"], result["artifacts"]["exercise_plan"])
    else:
        # Rodar audit + escalar
        audit_report = audit(result["gate_decision"])
        notify_bruno(audit_report)

O retorno é o mesmo de pipeline_end_to_end.run_pipeline, com o adapter já
aplicado. É a API estável do squad — mantenha backward compat.
"""

from __future__ import annotations

import logging
from typing import Any

from ml_worker_adapter import to_features_canonical
from pipeline_end_to_end import run_pipeline
from audit_outlier import audit

logger = logging.getLogger(__name__)


def process(
    *,
    evaluation_id: str,
    storage_path: str,
    duration_seconds: float,
    worker_outputs: dict[str, dict | None],
    evaluation_context: dict[str, Any] | None = None,
    user_profile: dict[str, Any] | None = None,
    fps: float | None = None,
    audio_sample_rate: int | None = None,
    processing_time_ms: int | None = None,
    warnings: list[str] | None = None,
    fallbacks_applied: list[str] | None = None,
    mode: str = "template",
    include_audit_on_fail: bool = True,
) -> dict[str, Any]:
    """Entrypoint público. Single-call: worker outputs → release decision.

    Retorno sempre contém:
        {
            "pipeline_result": "COMPLETE" | "ABORTED_AT_PHASE_1",
            "features_canonical": {...},   # convertido via adapter
            "gate_decision": {...},         # PASS / FAIL / WAIVED / INCOMPLETE
            "artifacts": {...},
            "audit_report": {...} | None,   # presente se FAIL e include_audit_on_fail
        }
    """
    # Step 1 — Adapt raw worker outputs to canonical contract
    features = to_features_canonical(
        evaluation_id=evaluation_id,
        storage_path=storage_path,
        duration_seconds=duration_seconds,
        worker_outputs=worker_outputs,
        fps=fps,
        audio_sample_rate=audio_sample_rate,
        processing_time_ms=processing_time_ms,
        warnings=warnings,
        fallbacks_applied=fallbacks_applied,
    )

    # Step 2 — Run full pipeline (6 phases + all gates)
    pipeline_output = run_pipeline(
        features,
        evaluation_context=evaluation_context,
        user_profile=user_profile,
        mode=mode,
    )

    # Step 3 — If FAIL, auto-run audit_outlier
    audit_report: dict[str, Any] | None = None
    if include_audit_on_fail and pipeline_output["gate_decision"]["verdict"] == "FAIL":
        audit_report = audit(pipeline_output["gate_decision"])

    return {
        **pipeline_output,
        "features_canonical": features,
        "audit_report": audit_report,
    }


def process_minimal(
    evaluation_id: str,
    worker_outputs: dict,
    storage_path: str = "",
    duration_seconds: float = 0.0,
) -> dict:
    """Atalho para casos simples — usa defaults."""
    return process(
        evaluation_id=evaluation_id,
        storage_path=storage_path or f"evaluations/{evaluation_id}/video.mp4",
        duration_seconds=duration_seconds,
        worker_outputs=worker_outputs,
    )
