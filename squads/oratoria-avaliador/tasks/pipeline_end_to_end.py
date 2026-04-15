"""
pipeline_end_to_end.py
──────────────────────
Execução full-pipeline: features_canonical → quality_gate_decision.

Este é o runner de produção — não existia antes de Epic 4 porque faltava o
gate final. Agora todas as 6 fases têm implementação.

Uso:
    from pipeline_end_to_end import run_pipeline
    decision = run_pipeline(features_canonical, evaluation_context)
    if decision["release_to_user"]:
        return decision  # deliver to user
    else:
        audit = audit(decision)  # investigate
"""

from __future__ import annotations

from typing import Any

from validate_contract import validate_payload
from scoring_engine import score_evaluation
from congruence_auditor import audit_congruence
from hierarchy_ranker import rank_problems
from mentor_router import route_mentor
from exercise_prescriber import prescribe
from mentor_narrator import render_template_narrative
from fidelity_checker import measure_fidelity
from quality_gate_keeper import aggregate_gates


def run_pipeline(
    features_canonical: dict[str, Any],
    evaluation_context: dict[str, Any] | None = None,
    user_profile: dict[str, Any] | None = None,
    mode: str = "template",  # "template" | "llm" (llm = Epic 3b)
) -> dict[str, Any]:
    """Executa pipeline fase 1-6 e retorna quality_gate_decision + artefatos."""
    evaluation_id = features_canonical.get("evaluation_id", "unknown")

    # Phase 1 — Contract Validity (G1)
    contract_result = validate_payload(features_canonical)
    if contract_result["result"] == "FAIL":
        # Aborta cedo — não vale rodar resto
        return {
            "pipeline_result": "ABORTED_AT_PHASE_1",
            "evaluation_id": evaluation_id,
            "gate_decision": aggregate_gates(
                evaluation_id=evaluation_id,
                contract_result=contract_result,
            ),
            "artifacts": {"contract_result": contract_result},
        }

    # Phase 2 — Scoring
    scoring_result = score_evaluation(features_canonical, evaluation_context)

    # Phase 3 — Congruence (G3)
    congruence_result = audit_congruence(scoring_result)

    # Phase 4 — Hierarchy (G5)
    hierarchy_result = rank_problems(scoring_result, top_n=3)

    # Phase 5 — Mentor Narrative + Exercises (G4 + G6)
    router_result = route_mentor(evaluation_context, user_profile)
    mentor = router_result["mentor"]
    exercise_plan = prescribe(hierarchy_result, mentor)

    if mode == "template":
        narrative = render_template_narrative(mentor, hierarchy_result, exercise_plan)
    else:
        # Epic 3b: LLM call aqui. Por ora, delega ao template.
        narrative = render_template_narrative(mentor, hierarchy_result, exercise_plan)

    fidelity_result = measure_fidelity(narrative, mentor)

    # Phase 6 — Quality Gate (G_FINAL)
    gate_decision = aggregate_gates(
        evaluation_id=evaluation_id,
        contract_result=contract_result,
        scoring_result=scoring_result,
        congruence_result=congruence_result,
        hierarchy_result=hierarchy_result,
        fidelity_result=fidelity_result,
        exercise_plan=exercise_plan,
    )

    return {
        "pipeline_result": "COMPLETE",
        "evaluation_id": evaluation_id,
        "gate_decision": gate_decision,
        "artifacts": {
            "contract_result": contract_result,
            "scoring_result": scoring_result,
            "congruence_result": congruence_result,
            "hierarchy_result": hierarchy_result,
            "router_result": router_result,
            "exercise_plan": exercise_plan,
            "narrative": narrative,
            "fidelity_result": fidelity_result,
        },
    }
