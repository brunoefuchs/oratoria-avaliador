"""
audit_outlier.py
────────────────
Investigação automática de FAIL ou outlier. Gera audit report com
root cause hypothesis + action items.

Epic 4 — Story 4.4 (wf-audit-outlier implementation).

Triggers:
- quality-gate-keeper emite verdict=FAIL
- congruence-auditor emite FAIL_CRITICAL
- scoring-engine emite outlier (score 0 ou 100 em todas dims)

Output: audit_report.json
    {
      "evaluation_id": "...",
      "trigger": "G3_FAIL | G4_FAIL | OUTLIER_ALL_MAX | ...",
      "hypotheses": [ { hypothesis, likelihood, investigation_steps } ],
      "action_items": [ "recomendação humana-legível" ],
      "escalation_needed": bool,
      "escalate_to": "@data-engineer | @architect | human_mentor | none"
    }
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def audit(gate_decision: dict[str, Any]) -> dict[str, Any]:
    """Recebe output de quality-gate-keeper e gera audit report.

    Se verdict=PASS → audit é trivial (nada a investigar).
    Se verdict=FAIL → investiga cada gate que falhou.
    """
    evaluation_id = gate_decision.get("evaluation_id")
    verdict = gate_decision.get("verdict")
    critical_fails = gate_decision.get("critical_fails", [])
    gate_states = gate_decision.get("gate_states", {})

    hypotheses: list[dict[str, Any]] = []
    action_items: list[str] = []
    escalate_to = "none"

    if verdict == "PASS":
        return {
            "schema_version": "1.0.0",
            "evaluation_id": evaluation_id,
            "trigger": "none",
            "verdict_audited": verdict,
            "hypotheses": [],
            "action_items": ["Nenhuma ação necessária — gate PASS"],
            "escalation_needed": False,
            "escalate_to": "none",
            "timestamp": _iso_now(),
        }

    # Investigação por gate
    for gate_id in critical_fails:
        _investigate_gate(gate_id, gate_states, hypotheses, action_items)

    # Escalation heurística
    if any("G1" in g for g in critical_fails):
        escalate_to = "@data-engineer"  # contract/schema é responsabilidade dele
    elif any("G3" in g or "G4" in g for g in critical_fails):
        escalate_to = "human_mentor"  # congruência/fidelity pedem olhar humano
    elif any("G5" in g or "G6" in g for g in critical_fails):
        escalate_to = "@architect"  # ranking/exercise logic é design

    return {
        "schema_version": "1.0.0",
        "evaluation_id": evaluation_id,
        "trigger": ",".join(critical_fails) or "UNKNOWN",
        "verdict_audited": verdict,
        "hypotheses": hypotheses,
        "action_items": action_items,
        "escalation_needed": True,
        "escalate_to": escalate_to,
        "timestamp": _iso_now(),
    }


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _investigate_gate(
    gate_id: str,
    gate_states: dict[str, Any],
    hypotheses: list[dict[str, Any]],
    action_items: list[str],
) -> None:
    state = gate_states.get(gate_id, {})

    if gate_id == "G1_CONTRACT_VALIDITY":
        violations = state.get("violations", [])
        hypotheses.append({
            "hypothesis": "ml-worker emitiu payload não-conforme ao contract v1.0.0",
            "likelihood": "high" if violations else "medium",
            "investigation_steps": [
                "Checar ml-worker versions no payload",
                "Comparar com schema features_canonical.schema.json",
                "Ver se há rollout recente de worker",
            ],
            "violations_sample": violations[:3],
        })
        action_items.append("Bloquear pipeline até ml-worker output conformar")
        action_items.append("Se schema mudou: bump major version + migração")

    elif gate_id == "G3_CONGRUENCE":
        violations = state.get("violations", [])
        hypotheses.append({
            "hypothesis": "Contradição entre dimensões indica erro em captura OU scoring",
            "likelihood": "high",
            "investigation_steps": [
                "Ver rule_id violado em cada violation",
                "Cruzar com evidence do scoring para dimensões envolvidas",
                "Se CONG_01 (voice flat + story rich): revisar transcript + prosódia raw",
                "Se CONG_02 (body-face disconnect): rodar captura de novo se possível",
            ],
            "violations_sample": violations[:3],
        })
        action_items.append("Revisar features raw do ml-worker para dims contraditórias")
        action_items.append("Se padrão se repete: abrir calibration precedent")

    elif gate_id == "G4_VOICE_DNA_FIDELITY":
        fid = state.get("fidelity_pct")
        hypotheses.append({
            "hypothesis": f"Narrativa não atingiu threshold (atual: {fid}%, alvo: ≥85%)",
            "likelihood": "high",
            "investigation_steps": [
                "Verificar se mentor foi carregado corretamente (router output)",
                "Checar voice_dna.yaml do mentor (signatures vazias? yaml corrompido?)",
                "Se usou LLM: revisar system prompt construction",
                "Re-render em template mode como sanity check",
            ],
        })
        action_items.append("Re-generate narrativa em template mode para validar baseline")
        action_items.append("Se template PASS mas LLM FAIL: problema é prompt engineering")

    elif gate_id == "G5_HIERARCHY_VALIDITY":
        hypotheses.append({
            "hypothesis": "Ranking emitido sem rank/evidence/why completos",
            "likelihood": "medium",
            "investigation_steps": [
                "Ver scoring_output: todas dims têm score?",
                "Ver applied_weights: soma dá ~1.0?",
            ],
        })
        action_items.append("Re-run hierarchy_ranker com scoring_output completo")

    elif gate_id == "G6_EXERCISE_LINKAGE":
        coverage = state.get("coverage", [])
        missing = [c for c in coverage if not c.get("has_exercise")]
        hypotheses.append({
            "hypothesis": f"Biblioteca de exercícios sem cobertura para {len(missing)} problema(s)",
            "likelihood": "high" if missing else "low",
            "investigation_steps": [
                "Ver EXERCISES dict em exercise_prescriber.py",
                "Verificar se mentor foi adicionado a todas as 4 dims",
            ],
            "missing_coverage": missing,
        })
        action_items.append("Adicionar exercício em EXERCISES dict + teste + calibration precedent")
