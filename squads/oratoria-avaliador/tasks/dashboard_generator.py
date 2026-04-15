"""
dashboard_generator.py
──────────────────────
Gera dashboard markdown de decisões de gate (Story 4.2).

Lê logs de quality_gate_decision.json persistidos (se existirem) e agrega:
- Taxa PASS/FAIL por período
- Top razões de FAIL
- Mentor routing distribution
- Fidelity distribution

Para Epic 4, implementação simplificada: recebe lista de decisões em memória
(não persiste em DB ainda — isso seria Epic 4b). Foco em função pura que
transforma decisões → markdown.
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import Any

logger = logging.getLogger(__name__)


def generate_dashboard(decisions: list[dict[str, Any]]) -> str:
    """Gera dashboard markdown a partir de lista de quality_gate_decision."""
    if not decisions:
        return "# Gate Dashboard\n\n_Nenhuma decisão registrada ainda._\n"

    total = len(decisions)
    verdicts = Counter(d.get("verdict", "UNKNOWN") for d in decisions)
    pass_count = verdicts.get("PASS", 0)
    fail_count = verdicts.get("FAIL", 0)
    waived = verdicts.get("WAIVED", 0)
    incomplete = verdicts.get("INCOMPLETE", 0)

    pass_rate = round(pass_count / total * 100, 1)

    # Top razões de FAIL
    fail_gates = Counter()
    for d in decisions:
        for g in d.get("critical_fails", []):
            fail_gates[g] += 1

    # Fidelity distribution
    fidelity_values = [
        d.get("gate_states", {}).get("G4_VOICE_DNA_FIDELITY", {}).get("fidelity_pct")
        for d in decisions
    ]
    fidelity_values = [f for f in fidelity_values if isinstance(f, (int, float))]

    # Mentor routing
    mentors = Counter(
        d.get("gate_states", {}).get("G4_VOICE_DNA_FIDELITY", {}).get("mentor")
        for d in decisions
    )
    mentors.pop(None, None)

    lines: list[str] = []
    lines.append("# 📊 Gate Dashboard — Oratória Avaliador")
    lines.append("")
    lines.append(f"**Total avaliações processadas:** {total}")
    lines.append("")
    lines.append("## Verdicts")
    lines.append("")
    lines.append("| Status | Count | % |")
    lines.append("|--------|-------|---|")
    lines.append(f"| ✅ PASS | {pass_count} | {pass_rate}% |")
    lines.append(f"| ❌ FAIL | {fail_count} | {round(fail_count/total*100,1)}% |")
    lines.append(f"| ⚠️ WAIVED | {waived} | {round(waived/total*100,1)}% |")
    lines.append(f"| ⏳ INCOMPLETE | {incomplete} | {round(incomplete/total*100,1)}% |")
    lines.append("")

    lines.append("## Top razões de FAIL")
    lines.append("")
    if fail_gates:
        lines.append("| Gate | FAIL count |")
        lines.append("|------|-----------|")
        for g, c in fail_gates.most_common():
            lines.append(f"| `{g}` | {c} |")
    else:
        lines.append("_Nenhum FAIL registrado._")
    lines.append("")

    lines.append("## Voice DNA Fidelity")
    lines.append("")
    if fidelity_values:
        avg = round(sum(fidelity_values) / len(fidelity_values), 1)
        min_f = round(min(fidelity_values), 1)
        max_f = round(max(fidelity_values), 1)
        below_threshold = sum(1 for f in fidelity_values if f < 85)
        lines.append(f"- Amostra: {len(fidelity_values)} narrativas")
        lines.append(f"- Fidelity médio: **{avg}%**")
        lines.append(f"- Range: {min_f}% → {max_f}%")
        lines.append(f"- Abaixo do threshold 85%: **{below_threshold}** ({round(below_threshold/len(fidelity_values)*100,1)}%)")
    else:
        lines.append("_Sem medições de fidelity._")
    lines.append("")

    lines.append("## Mentor Routing")
    lines.append("")
    if mentors:
        lines.append("| Mentor | Count | % |")
        lines.append("|--------|-------|---|")
        m_total = sum(mentors.values())
        for m, c in mentors.most_common():
            lines.append(f"| {m} | {c} | {round(c/m_total*100,1)}% |")
    else:
        lines.append("_Sem dados de routing._")
    lines.append("")

    lines.append("## Health Check")
    lines.append("")
    health_issues: list[str] = []
    if pass_rate < 85 and total >= 10:
        health_issues.append(f"⚠️ PASS rate {pass_rate}% abaixo do alvo 85% (PRD 11.1)")
    if fail_gates.get("G4_VOICE_DNA_FIDELITY", 0) > total * 0.15 and total >= 10:
        health_issues.append("⚠️ G4 Fidelity FAIL >15% — investigar drift no Voice DNA")
    if fail_gates.get("G1_CONTRACT_VALIDITY", 0) > 0:
        health_issues.append("🚨 G1 FAIL presente — ml-worker contract misalignment")

    if health_issues:
        for issue in health_issues:
            lines.append(f"- {issue}")
    else:
        lines.append("✅ Nenhum problema detectado.")
    lines.append("")

    return "\n".join(lines)
