"""
calibration_keeper.py
─────────────────────
Append-only log de calibração. Cada mudança de peso contextual (ou de
threshold de gate) precisa de precedent gravado aqui.

Epic 4 — Story 4.3. G7_CALIBRATION_AUDIT_TRAIL gate.

Política:
- Append-only. NUNCA delete. NUNCA modifique entrada existente.
- Cada precedent requer: who, when, why, change (before/after), mentor_signoff.
- Arquivo canônico: data/calibration_log.jsonl (JSON lines, append).

Se alguém tentar alterar peso sem passar por aqui → violação (detectada em
runtime comparing applied_weights vs last calibrated state).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LOG_PATH = Path(__file__).parent.parent / "data" / "calibration_log.jsonl"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def record_precedent(
    *,
    change_type: str,  # "weight_adjust" | "threshold_adjust" | "new_rule"
    target: str,       # "scoring.weights.vendas.voice" | "congruence.CONG_02.threshold" | etc.
    before: Any,
    after: Any,
    why: str,          # rationale humano
    who: str,          # "bruno" | "@mentor:gui" | "@aqaa:quinn" | etc.
    mentor_signoff: bool = False,
    evidence_refs: list[str] | None = None,
) -> dict[str, Any]:
    """Grava precedent em append-only log. Retorna entry criada."""
    entry = {
        "precedent_id": f"CAL-{_iso_now().replace(':', '-').replace('.', '-')}",
        "timestamp": _iso_now(),
        "change_type": change_type,
        "target": target,
        "before": before,
        "after": after,
        "why": why,
        "who": who,
        "mentor_signoff": mentor_signoff,
        "evidence_refs": evidence_refs or [],
    }

    # Validação: change_type válido
    if change_type not in ("weight_adjust", "threshold_adjust", "new_rule", "rollback"):
        entry["_validation_error"] = f"change_type inválido: {change_type}"
        return entry

    # Gate G7: sem signoff + mudança crítica = warning (mas ainda grava)
    if change_type in ("weight_adjust", "threshold_adjust") and not mentor_signoff:
        entry["_warning"] = "G7 warn: mudança sem mentor_signoff — risco de drift"

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return entry


def read_log(limit: int | None = None) -> list[dict[str, Any]]:
    """Lê o log. Se limit=N, retorna últimas N entries."""
    if not LOG_PATH.exists():
        return []
    entries: list[dict[str, Any]] = []
    with open(LOG_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    if limit is not None:
        return entries[-limit:]
    return entries


def audit_trail(target: str) -> list[dict[str, Any]]:
    """Retorna todas entries para um target específico (para revisar evolução)."""
    return [e for e in read_log() if e.get("target") == target]


def verify_current_state_traceable(
    *,
    target: str,
    current_value: Any,
) -> dict[str, Any]:
    """G7 gate: valor atual tem que bater com último precedent (ou ser default)."""
    trail = audit_trail(target)
    if not trail:
        return {
            "gate": "G7_CALIBRATION_AUDIT_TRAIL",
            "target": target,
            "result": "PASS_DEFAULT",
            "detail": "sem precedent (valor default)",
            "current_value": current_value,
        }
    last = trail[-1]
    match = last["after"] == current_value
    return {
        "gate": "G7_CALIBRATION_AUDIT_TRAIL",
        "target": target,
        "result": "PASS" if match else "FAIL",
        "current_value": current_value,
        "last_precedent_value": last["after"],
        "last_precedent_id": last["precedent_id"],
        "detail": "match" if match else "valor atual divergente do último precedent — drift não auditado",
    }
