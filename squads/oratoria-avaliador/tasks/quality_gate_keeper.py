"""
quality_gate_keeper.py
──────────────────────
Gate final de release. Combina G1-G6 em decisão determinística.

Epic 4 — Story 4.1.

Entrada: artefatos de todas as fases (contract, scoring, congruence,
hierarchy, narrative, exercise_plan, fidelity).
Saída: quality_gate_decision.json — PASS / FAIL / WAIVED + razão por gate.

Política:
- PASS: todos G1-G6 em PASS
- FAIL: qualquer G1/G3/G5/G6 em FAIL OU G4 abaixo de threshold
- WAIVED: FAIL mas com waiver humano registrado (campo waiver_reason)

O gate é o único autorizado a emitir release. Ninguém "bypassa" — se vai pra
usuário, passou aqui.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

GATE_ORDER = [
    "G1_CONTRACT_VALIDITY",
    "G2_COMPLETUDE",
    "G3_CONGRUENCE",
    "G5_HIERARCHY_VALIDITY",
    "G4_VOICE_DNA_FIDELITY",
    "G6_EXERCISE_LINKAGE",
]


def aggregate_gates(
    *,
    evaluation_id: str,
    contract_result: dict[str, Any] | None = None,
    scoring_result: dict[str, Any] | None = None,
    congruence_result: dict[str, Any] | None = None,
    hierarchy_result: dict[str, Any] | None = None,
    fidelity_result: dict[str, Any] | None = None,
    exercise_plan: dict[str, Any] | None = None,
    waiver: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Constrói gate_states a partir dos artefatos das fases."""
    gate_states: dict[str, dict[str, Any]] = {}

    # G1 — Contract Validity
    if contract_result:
        gate_states["G1_CONTRACT_VALIDITY"] = {
            "result": contract_result.get("result", "UNKNOWN"),
            "violations": contract_result.get("violations", []),
        }
    else:
        gate_states["G1_CONTRACT_VALIDITY"] = {"result": "UNKNOWN", "violations": ["G1 missing"]}

    # G2 — Completude (informativo no Epic 4, não bloqueia)
    if scoring_result:
        incomplete = scoring_result.get("incomplete_dimensions", [])
        gate_states["G2_COMPLETUDE"] = {
            "result": "PASS" if not incomplete else "PASS_WITH_WARNINGS",
            "incomplete_dimensions": incomplete,
        }
    else:
        gate_states["G2_COMPLETUDE"] = {"result": "UNKNOWN"}

    # G3 — Congruence
    if congruence_result:
        c = congruence_result.get("result", "UNKNOWN")
        gate_states["G3_CONGRUENCE"] = {
            "result": "PASS" if c in ("PASS", "PASS_WITH_WARNINGS") else "FAIL",
            "raw_result": c,
            "critical_count": congruence_result.get("critical_count", 0),
            "warning_count": congruence_result.get("warning_count", 0),
            "violations": congruence_result.get("violations", []),
        }
    else:
        gate_states["G3_CONGRUENCE"] = {"result": "UNKNOWN"}

    # G5 — Hierarchy Validity
    if hierarchy_result:
        problems = hierarchy_result.get("problems", [])
        valid = all(
            "rank" in p and p.get("why") and "evidence" in p
            for p in problems
        )
        gate_states["G5_HIERARCHY_VALIDITY"] = {
            "result": "PASS" if valid else "FAIL",
            "top_n": hierarchy_result.get("top_n", 0),
            "problems_count": len(problems),
        }
    else:
        gate_states["G5_HIERARCHY_VALIDITY"] = {"result": "UNKNOWN"}

    # G4 — Voice DNA Fidelity
    if fidelity_result:
        gate_states["G4_VOICE_DNA_FIDELITY"] = {
            "result": fidelity_result.get("result", "UNKNOWN"),
            "fidelity_pct": fidelity_result.get("fidelity_pct"),
            "threshold_pct": fidelity_result.get("threshold_pct"),
            "mentor": fidelity_result.get("mentor"),
        }
    else:
        gate_states["G4_VOICE_DNA_FIDELITY"] = {"result": "UNKNOWN"}

    # G6 — Exercise Linkage
    if exercise_plan:
        gate_states["G6_EXERCISE_LINKAGE"] = {
            "result": "PASS" if exercise_plan.get("g6_exercise_linkage_pass") else "FAIL",
            "coverage": [
                {"rank": i["rank"], "has_exercise": i["has_exercise"]}
                for i in exercise_plan.get("exercises_by_problem", [])
            ],
        }
    else:
        gate_states["G6_EXERCISE_LINKAGE"] = {"result": "UNKNOWN"}

    # ─── Verdict ────────────────────────────────────────────────────────────
    critical_fails: list[str] = []
    for gate_id in ["G1_CONTRACT_VALIDITY", "G3_CONGRUENCE", "G4_VOICE_DNA_FIDELITY",
                    "G5_HIERARCHY_VALIDITY", "G6_EXERCISE_LINKAGE"]:
        gs = gate_states.get(gate_id, {})
        if gs.get("result") == "FAIL":
            critical_fails.append(gate_id)

    unknowns = [g for g, s in gate_states.items() if s.get("result") == "UNKNOWN"]

    if critical_fails:
        if waiver and waiver.get("waiver_reason"):
            verdict = "WAIVED"
            release = True
        else:
            verdict = "FAIL"
            release = False
    elif unknowns:
        verdict = "INCOMPLETE"
        release = False
    else:
        verdict = "PASS"
        release = True

    return {
        "gate": "G_FINAL_RELEASE",
        "schema_version": "1.0.0",
        "evaluation_id": evaluation_id,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "verdict": verdict,
        "release_to_user": release,
        "gate_states": gate_states,
        "critical_fails": critical_fails,
        "unknowns": unknowns,
        "waiver": waiver,
        "next_action": _next_action(verdict, critical_fails),
    }


def _next_action(verdict: str, critical_fails: list[str]) -> str:
    if verdict == "PASS":
        return "RELEASE → entregar evaluation_report ao usuário"
    if verdict == "WAIVED":
        return "RELEASE_COM_WAIVER → entregar + registrar precedent"
    if verdict == "FAIL":
        gates = ", ".join(critical_fails) or "múltiplos"
        return f"BLOCK + ESCALATE → wf-audit-outlier para {gates}"
    if verdict == "INCOMPLETE":
        return "WAIT → artefatos faltando, pipeline não terminou"
    return "UNKNOWN"
