"""
congruence_auditor.py
─────────────────────
Detecta contradições entre dimensões em um scores_by_dimension.json.
Aplica G3_CONGRUENCE — bloqueia release se contradição crítica detectada.

Epic 2 — Story 2.3.

Heurísticas de contradição (CONGRUENCE_RULES):
Cada rule é uma função (scores) → violation|None.
Violação tem severity: "critical" (bloqueia) ou "warning" (passa com flag).

Retorno padronizado:
    {
      "gate": "G3_CONGRUENCE",
      "evaluation_id": "...",
      "result": "PASS" | "FAIL_CRITICAL" | "PASS_WITH_WARNINGS",
      "violations": [ { rule, severity, detail, dimensions_involved } ],
      "critical_count": int,
      "warning_count": int
    }
"""

from __future__ import annotations

from typing import Any


# ─────────────────────────────────────────────────────────────────────────────
# REGRAS DE CONGRUÊNCIA
# ─────────────────────────────────────────────────────────────────────────────

DELTA_CRITICAL = 40.0  # diferença absoluta que dispara contradição crítica
DELTA_WARNING = 25.0


def _s(scores: dict, dim: str) -> float | None:
    entry = scores.get(dim)
    if isinstance(entry, dict):
        return entry.get("score")
    return None


def rule_voice_vs_storytelling_range(scores: dict) -> dict | None:
    """Voz monótona + storytelling com arco emocional rico = contradição.

    Se voice < 40 E storytelling > 80 → crítico (discurso dramático
    com entrega plana é implausível).
    """
    v = _s(scores, "voice")
    s = _s(scores, "storytelling")
    if v is None or s is None:
        return None
    if v < 40 and s > 80:
        return {
            "rule": "CONG_01_voice_flat_vs_narrative_rich",
            "severity": "critical",
            "detail": f"Voz avaliada como plana (score={v}) mas storytelling rico (score={s}). Contradição implausível — revisar captura ou scoring.",
            "dimensions_involved": ["voice", "storytelling"],
        }
    return None


def rule_body_vs_face_disconnect(scores: dict) -> dict | None:
    """Corpo alto + face baixa (ou vice-versa) com grande delta."""
    b = _s(scores, "body")
    f = _s(scores, "face")
    if b is None or f is None:
        return None
    delta = abs(b - f)
    if delta >= DELTA_CRITICAL:
        return {
            "rule": "CONG_02_body_face_disconnect",
            "severity": "critical",
            "detail": f"Corpo (score={b}) e face (score={f}) divergem em {delta:.1f} pontos. Sinal de inconsistência presencial.",
            "dimensions_involved": ["body", "face"],
        }
    if delta >= DELTA_WARNING:
        return {
            "rule": "CONG_02_body_face_disconnect",
            "severity": "warning",
            "detail": f"Corpo vs face: delta {delta:.1f} — vale investigar",
            "dimensions_involved": ["body", "face"],
        }
    return None


def rule_voice_vs_body_disconnect(scores: dict) -> dict | None:
    v = _s(scores, "voice")
    b = _s(scores, "body")
    if v is None or b is None:
        return None
    delta = abs(v - b)
    if delta >= DELTA_CRITICAL:
        return {
            "rule": "CONG_03_voice_body_disconnect",
            "severity": "critical",
            "detail": f"Voz (score={v}) e corpo (score={b}) divergem em {delta:.1f} pontos.",
            "dimensions_involved": ["voice", "body"],
        }
    if delta >= DELTA_WARNING:
        return {
            "rule": "CONG_03_voice_body_disconnect",
            "severity": "warning",
            "detail": f"Voz vs corpo: delta {delta:.1f}",
            "dimensions_involved": ["voice", "body"],
        }
    return None


def rule_all_high_but_overall_low(scores: dict, overall: float | None) -> dict | None:
    """Se TODAS dimensões > 70 mas overall < 50, há bug no peso."""
    if overall is None:
        return None
    values = [_s(scores, d) for d in scores]
    values = [v for v in values if v is not None]
    if not values:
        return None
    if all(v > 70 for v in values) and overall < 50:
        return {
            "rule": "CONG_04_weight_math_error",
            "severity": "critical",
            "detail": f"Todas dimensões > 70 mas overall={overall}. Provável bug no cálculo de pesos.",
            "dimensions_involved": list(scores.keys()),
        }
    return None


def rule_incomplete_coverage_critical(scores: dict, incomplete: list[str]) -> dict | None:
    """Se faltam 2+ dimensões, relatório não é releasable sem flag."""
    if len(incomplete) >= 2:
        return {
            "rule": "CONG_05_insufficient_coverage",
            "severity": "warning",
            "detail": f"{len(incomplete)} dimensões ausentes: {incomplete}. Relatório é parcial.",
            "dimensions_involved": incomplete,
        }
    return None


RULES_SCORES_ONLY = [
    rule_voice_vs_storytelling_range,
    rule_body_vs_face_disconnect,
    rule_voice_vs_body_disconnect,
]


def audit_congruence(scoring_output: dict[str, Any]) -> dict[str, Any]:
    """Aplica regras de congruência sobre output do scoring_engine."""
    evaluation_id = scoring_output.get("evaluation_id")
    dimension_scores = scoring_output.get("dimension_scores") or {}
    incomplete = scoring_output.get("incomplete_dimensions") or []
    overall = scoring_output.get("overall_score")

    violations: list[dict] = []

    for rule in RULES_SCORES_ONLY:
        v = rule(dimension_scores)
        if v is not None:
            violations.append(v)

    v = rule_all_high_but_overall_low(dimension_scores, overall)
    if v is not None:
        violations.append(v)

    v = rule_incomplete_coverage_critical(dimension_scores, incomplete)
    if v is not None:
        violations.append(v)

    critical = [v for v in violations if v["severity"] == "critical"]
    warnings_ = [v for v in violations if v["severity"] == "warning"]

    if critical:
        result = "FAIL_CRITICAL"
    elif warnings_:
        result = "PASS_WITH_WARNINGS"
    else:
        result = "PASS"

    return {
        "gate": "G3_CONGRUENCE",
        "evaluation_id": evaluation_id,
        "result": result,
        "violations": violations,
        "critical_count": len(critical),
        "warning_count": len(warnings_),
    }
