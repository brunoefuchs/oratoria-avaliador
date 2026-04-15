"""
validate_contract.py
────────────────────
Valida payload contra features_canonical v1.0.0.

Implementação de G1_CONTRACT_VALIDITY — o primeiro (e em Epic 1, único)
quality gate do pipeline.

Retorno padronizado:
    {
        "gate": "G1_CONTRACT_VALIDITY",
        "result": "PASS" | "FAIL",
        "violations": [ { "rule": str, "detail": str, "path": str } ],
        "schema_version_expected": "1.0.0",
        "schema_version_received": str | None,
    }

Exit codes (quando rodado via CLI):
    0 → PASS
    1 → FAIL
    2 → erro interno (schema não carrega, payload não é JSON, etc.)

Uso CLI:
    python -m squads.oratoria_avaliador.tasks.validate_contract \\
        squads/oratoria-avaliador/data/fixtures/features_valid_v1.json
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False

logger = logging.getLogger(__name__)

SCHEMA_PATH = Path(__file__).parent.parent / "data" / "features_canonical.schema.json"
SUPPORTED_VERSIONS = {"1.0.0", "1.1.0"}  # minor bumps são aditivos (backward compat)
EXPECTED_VERSION = "1.1.0"  # current canonical; 1.0.0 aceito mas não emitido


def _load_schema() -> dict[str, Any]:
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def validate_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Aplica G1_CONTRACT_VALIDITY ao payload. Retorna resultado estruturado."""
    violations: list[dict[str, str]] = []
    received_version = payload.get("schema_version") if isinstance(payload, dict) else None

    # Regra 1: schema_version deve existir e bater exatamente.
    if not isinstance(payload, dict):
        violations.append({
            "rule": "payload_must_be_object",
            "detail": f"Expected dict, got {type(payload).__name__}",
            "path": "$",
        })
        return _build_result("FAIL", violations, received_version)

    if "schema_version" not in payload:
        violations.append({
            "rule": "schema_version_required",
            "detail": "Campo schema_version é obrigatório (OAC_H04).",
            "path": "$.schema_version",
        })
    elif payload["schema_version"] not in SUPPORTED_VERSIONS:
        violations.append({
            "rule": "schema_version_mismatch",
            "detail": (
                f"Versão não suportada: {payload['schema_version']!r}. "
                f"Suportadas: {sorted(SUPPORTED_VERSIONS)}. "
                f"Bump major exige migração."
            ),
            "path": "$.schema_version",
        })

    # Regra 2: validação estrutural via JSON Schema (se biblioteca disponível).
    if HAS_JSONSCHEMA:
        try:
            schema = _load_schema()
            validator = Draft202012Validator(schema)
            for err in sorted(validator.iter_errors(payload), key=lambda e: list(e.absolute_path)):
                violations.append({
                    "rule": "jsonschema",
                    "detail": err.message,
                    "path": "$." + ".".join(str(p) for p in err.absolute_path) if err.absolute_path else "$",
                })
        except Exception as exc:
            violations.append({
                "rule": "schema_load_error",
                "detail": f"Não foi possível carregar/validar schema: {exc}",
                "path": "$",
            })
    else:
        # Fallback determinístico: valida mínimos obrigatórios sem jsonschema.
        required_top = ["evaluation_id", "video_ref", "schema_version", "extracted_at", "dimensions"]
        for field in required_top:
            if field not in payload:
                violations.append({
                    "rule": "required_field_missing_fallback",
                    "detail": f"Campo obrigatório ausente: {field}",
                    "path": f"$.{field}",
                })
        vref = payload.get("video_ref") or {}
        if not isinstance(vref, dict) or "storage_path" not in vref or "duration_seconds" not in vref:
            violations.append({
                "rule": "video_ref_invalid_fallback",
                "detail": "video_ref precisa de storage_path e duration_seconds",
                "path": "$.video_ref",
            })
        dims = payload.get("dimensions")
        if not isinstance(dims, dict):
            violations.append({
                "rule": "dimensions_must_be_object_fallback",
                "detail": "dimensions deve ser object",
                "path": "$.dimensions",
            })

    result = "PASS" if not violations else "FAIL"
    return _build_result(result, violations, received_version)


def _build_result(
    result: str, violations: list[dict[str, str]], received_version: str | None
) -> dict[str, Any]:
    return {
        "gate": "G1_CONTRACT_VALIDITY",
        "result": result,
        "violations": violations,
        "schema_version_expected": EXPECTED_VERSION,
        "schema_version_received": received_version,
        "jsonschema_available": HAS_JSONSCHEMA,
    }


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: python validate_contract.py <path_to_payload.json>", file=sys.stderr)
        return 2

    payload_path = Path(argv[1])
    if not payload_path.exists():
        print(f"File not found: {payload_path}", file=sys.stderr)
        return 2

    try:
        with open(payload_path, encoding="utf-8") as f:
            payload = json.load(f)
    except json.JSONDecodeError as exc:
        print(json.dumps({
            "gate": "G1_CONTRACT_VALIDITY",
            "result": "FAIL",
            "violations": [{"rule": "invalid_json", "detail": str(exc), "path": "$"}],
            "schema_version_expected": EXPECTED_VERSION,
            "schema_version_received": None,
        }, indent=2, ensure_ascii=False))
        return 1

    outcome = validate_payload(payload)
    print(json.dumps(outcome, indent=2, ensure_ascii=False))
    return 0 if outcome["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
