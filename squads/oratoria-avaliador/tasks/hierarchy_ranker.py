"""
hierarchy_ranker.py
───────────────────
Rankeia problemas por impacto estimado para emitir top-N que o usuário deve
atacar primeiro (Epic 6.2 do produto + story 3.3 do PRD do squad).

Entrada: scoring_output (do scoring-engine) + evaluation_context (6.Q).
Saída: problem_hierarchy.json
    {
      "schema_version": "1.0.0",
      "evaluation_id": "...",
      "top_n": 3,
      "problems": [
        {
          "rank": 1,
          "dimension": "voice",
          "score": 68.5,
          "gap_from_target": 21.5,
          "weight": 0.25,
          "weighted_impact": 5.375,
          "evidence": [...],
          "why": "motivo humano-legível"
        },
        ...
      ]
    }

Fórmula de impacto:
  weighted_impact = gap_from_target * weight
  onde gap_from_target = max(0, TARGET_SCORE - score)
  e weight vem do scoring_output.applied_weights.

Racional: dimensão pior + mais pesada no contexto do usuário = prioridade 1.
Epic 3 — Determinístico.
"""

from __future__ import annotations

from typing import Any

TARGET_SCORE = 85.0  # Score "ideal" que um bom speaker atinge


def rank_problems(
    scoring_output: dict[str, Any],
    top_n: int = 3,
) -> dict[str, Any]:
    evaluation_id = scoring_output.get("evaluation_id")
    dimension_scores = scoring_output.get("dimension_scores") or {}
    weights = scoring_output.get("applied_weights") or {}

    candidates: list[dict[str, Any]] = []

    for dim, entry in dimension_scores.items():
        score = entry.get("score", 50.0)
        weight = weights.get(dim, 0.0)
        gap = max(0.0, TARGET_SCORE - score)
        weighted_impact = round(gap * weight, 3)

        if gap < 1:
            continue  # dimensão já está ótima — não entra no ranking

        why = _explain(dim, entry, weight)
        candidates.append({
            "dimension": dim,
            "score": score,
            "gap_from_target": round(gap, 1),
            "weight": weight,
            "weighted_impact": weighted_impact,
            "evidence": entry.get("evidence", []),
            "why": why,
        })

    candidates.sort(key=lambda c: c["weighted_impact"], reverse=True)
    top = candidates[:top_n]

    for i, item in enumerate(top, start=1):
        item["rank"] = i

    return {
        "schema_version": "1.0.0",
        "evaluation_id": evaluation_id,
        "top_n": top_n,
        "problems": top,
        "total_candidates": len(candidates),
    }


def _explain(dim: str, entry: dict, weight: float) -> str:
    score = entry.get("score", 0)
    ev = entry.get("evidence", [])
    base_why = {
        "voice": "voz é o canal primário; variação de pitch/WPM/fillers impacta atenção",
        "body": "corpo ancora credibilidade visual; postura + gesto comunicam antes das palavras",
        "face": "face transmite emoção; expressão e olhar conectam ou desconectam",
        "storytelling": "estrutura narrativa decide se a audiência LEMBRA da mensagem",
    }.get(dim, "dimensão relevante do discurso")

    weight_pct = int(round(weight * 100))
    gap = max(0.0, TARGET_SCORE - score)

    # Evidência mais específica (pega primeira evidence não-note)
    specific = ""
    for e in ev:
        if "note" not in e:
            feat = e.get("feature") or e.get("rule")
            val = e.get("value")
            if feat:
                specific = f" Sinal: {feat}={val}."
            break

    return (
        f"{base_why}. Score atual: {score}/100 (gap {gap:.0f} pro ideal). "
        f"Peso contextual: {weight_pct}%.{specific}"
    )
