"""
evolve_dimension.py
───────────────────
Playbook determinístico para adicionar nova dimensão ao pipeline SEM quebrar
o que já funciona.

Epic 6 — Story 6.1.

Classifica mudança:
- additive → MINOR bump (1.0.0 → 1.1.0). Backward compat preservada.
- breaking → MAJOR bump (1.0.0 → 2.0.0). Migração obrigatória.

Steps do playbook:
  1. classify_change(old_schema, new_schema) → "additive" | "breaking"
  2. compute_version_bump()
  3. ensure_scorer_exists(dimension_name)
  4. ensure_adapter_mapping(dimension_name)
  5. run_backward_compat_test(old_fixture)
  6. run_new_dimension_test(new_fixture)
  7. record_evolution_precedent() (via calibration-keeper)

Violações bloqueiam. Nunca força release de evolução sem G_EVOLVE PASS.
"""

from __future__ import annotations

from typing import Any


def classify_change(
    old_dimensions: dict[str, Any],
    new_dimensions: dict[str, Any],
) -> dict[str, Any]:
    """Compara sets de dimensões. Determina additive vs breaking."""
    old_keys = set(old_dimensions.keys())
    new_keys = set(new_dimensions.keys())

    added = new_keys - old_keys
    removed = old_keys - new_keys
    kept = old_keys & new_keys

    # Verificar renames/restructs em kept
    restructured: list[str] = []
    for k in kept:
        if isinstance(old_dimensions[k], dict) and isinstance(new_dimensions[k], dict):
            old_sub = set((old_dimensions[k].get("properties") or {}).keys()) if isinstance(old_dimensions[k], dict) else set()
            new_sub = set((new_dimensions[k].get("properties") or {}).keys()) if isinstance(new_dimensions[k], dict) else set()
            # Remoção de sub-field = breaking
            if old_sub - new_sub:
                restructured.append(k)

    if removed or restructured:
        return {
            "classification": "breaking",
            "added": sorted(added),
            "removed": sorted(removed),
            "restructured": sorted(restructured),
            "version_bump": "major",
            "requires_migration": True,
        }
    if added:
        return {
            "classification": "additive",
            "added": sorted(added),
            "removed": [],
            "restructured": [],
            "version_bump": "minor",
            "requires_migration": False,
        }
    return {
        "classification": "none",
        "added": [],
        "removed": [],
        "restructured": [],
        "version_bump": None,
        "requires_migration": False,
    }


def bump_version(current: str, bump_type: str) -> str:
    """Semver bump: major reseta minor e patch; minor reseta patch."""
    try:
        major, minor, patch = (int(x) for x in current.split("."))
    except ValueError:
        return current
    if bump_type == "major":
        return f"{major + 1}.0.0"
    if bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    if bump_type == "patch":
        return f"{major}.{minor}.{patch + 1}"
    return current


def ensure_scorer_registered(dimension: str, score_functions_map: dict[str, Any]) -> dict[str, Any]:
    """Verifica se existe scorer registrado em SCORE_FUNCTIONS para a dimensão."""
    has_scorer = dimension in score_functions_map
    return {
        "dimension": dimension,
        "has_scorer": has_scorer,
        "action_if_missing": (
            f"Adicionar _score_{dimension}() em tasks/scoring_engine.py e "
            f"registrar em SCORE_FUNCTIONS dict. Default peso 0.0 em PESOS_DEFAULT "
            f"(neutro até calibração)."
        ) if not has_scorer else None,
    }


def run_backward_compat(
    validate_fn: Any,
    old_fixture_payload: dict[str, Any],
) -> dict[str, Any]:
    """Valida que payload antigo ainda passa G1 após evolução do schema."""
    result = validate_fn(old_fixture_payload)
    return {
        "gate": "G_EVOLVE_BACKWARD_COMPAT",
        "result": result.get("result"),
        "payload_version": old_fixture_payload.get("schema_version"),
        "violations": result.get("violations", []),
        "note": "Payload v1.0.0 deve continuar passando após evolução aditiva",
    }


def run_evolution_playbook(
    *,
    dimension_name: str,
    old_schema_version: str,
    new_schema_version: str,
    old_dimensions: dict[str, Any],
    new_dimensions: dict[str, Any],
    score_functions_map: dict[str, Any],
    validate_fn: Any,
    old_fixture_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Executa playbook completo. Retorna relatório com PASS/FAIL por step."""
    report: dict[str, Any] = {
        "gate": "G_EVOLVE",
        "dimension": dimension_name,
        "old_schema_version": old_schema_version,
        "proposed_new_version": new_schema_version,
        "steps": {},
        "overall_result": "PASS",
    }

    # Step 1-2: classify + bump
    change = classify_change(old_dimensions, new_dimensions)
    expected_version = bump_version(old_schema_version, change["version_bump"] or "patch")
    version_match = expected_version == new_schema_version

    report["steps"]["classify_change"] = {
        "result": "PASS" if change["classification"] != "none" else "NOOP",
        **change,
    }
    report["steps"]["version_bump"] = {
        "result": "PASS" if version_match else "FAIL",
        "expected": expected_version,
        "received": new_schema_version,
        "detail": "version bump consistent" if version_match else f"esperado {expected_version}, proposto {new_schema_version}",
    }
    if not version_match:
        report["overall_result"] = "FAIL"

    # Step 3: scorer presente
    scorer = ensure_scorer_registered(dimension_name, score_functions_map)
    report["steps"]["ensure_scorer"] = {
        "result": "PASS" if scorer["has_scorer"] else "FAIL",
        **scorer,
    }
    if not scorer["has_scorer"]:
        report["overall_result"] = "FAIL"

    # Step 4: backward compat (se payload fornecido)
    if old_fixture_payload is not None:
        bc = run_backward_compat(validate_fn, old_fixture_payload)
        report["steps"]["backward_compat"] = bc
        if bc["result"] != "PASS":
            report["overall_result"] = "FAIL"

    # Step 5: breaking change requer migração manual
    if change["classification"] == "breaking":
        report["steps"]["migration_required"] = {
            "result": "WARN",
            "detail": "Breaking change detectado. Migração manual necessária + bump MAJOR + comunicação para @data-engineer.",
        }

    # next_action humano-legível
    if report["overall_result"] == "PASS":
        report["next_action"] = (
            f"Gravar precedent via calibration-keeper: "
            f"record_precedent(change_type='new_rule', target='schema.dimensions.{dimension_name}', "
            f"before=null, after='dimension_added', why='...', who='...', mentor_signoff=True)"
        )
    else:
        report["next_action"] = "CORRIGIR FAILs antes de aplicar evolução."

    return report
