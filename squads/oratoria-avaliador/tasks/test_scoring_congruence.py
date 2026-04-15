"""
test_scoring_congruence.py
──────────────────────────
Smoke tests para scoring_engine + congruence_auditor (Epic 2 stories 2.1 + 2.3).

Roda sem pytest:
    python3 squads/oratoria-avaliador/tasks/test_scoring_congruence.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from scoring_engine import score_evaluation, resolve_weights  # noqa: E402
from congruence_auditor import audit_congruence  # noqa: E402


def _load_fixture(name: str) -> dict:
    p = _HERE.parent / "data" / "fixtures" / name
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def test_scoring_happy_path():
    print("=== TEST_SCORING_01: happy path (sem contexto, pesos default) ===")
    features = _load_fixture("features_valid_v1.json")
    result = score_evaluation(features, evaluation_context=None)
    assert result["weights_source"] == "default:no_context", result
    assert set(result["dimension_scores"].keys()) == {"voice", "body", "face", "storytelling"}
    for dim, entry in result["dimension_scores"].items():
        assert 0 <= entry["score"] <= 100, f"{dim} score out of range: {entry}"
        assert entry["evidence"], f"{dim} missing evidence"
    assert result["overall_score"] is not None
    assert 0 <= result["overall_score"] <= 100
    print(f"  dims: {[(d, s['score']) for d, s in result['dimension_scores'].items()]}")
    print(f"  overall: {result['overall_score']}")
    print("PASS\n")
    return result


def test_scoring_with_context():
    print("=== TEST_SCORING_02: contexto 'vender_mais' aplica pesos de vendas ===")
    features = _load_fixture("features_valid_v1.json")
    ctx = {"motivacao": ["vender_mais", "carreira"]}
    result = score_evaluation(features, evaluation_context=ctx)
    assert "vender_mais" in result["weights_source"], result["weights_source"]
    # pesos vendas: voice 0.25, body 0.25, face 0.20, storytelling 0.30
    assert result["applied_weights"]["storytelling"] == 0.30
    print(f"  source: {result['weights_source']}")
    print(f"  weights: {result['applied_weights']}")
    print("PASS\n")


def test_scoring_incomplete():
    print("=== TEST_SCORING_03: features parciais marca incomplete_dimensions ===")
    features = _load_fixture("features_valid_v1.json")
    # Remove face
    del features["dimensions"]["face"]
    result = score_evaluation(features)
    assert "face" in result["incomplete_dimensions"], result
    assert "face" not in result["dimension_scores"]
    print(f"  incomplete: {result['incomplete_dimensions']}")
    print("PASS\n")


def test_congruence_pass():
    print("=== TEST_CONGRUENCE_01: scores coerentes passam ===")
    features = _load_fixture("features_valid_v1.json")
    scoring = score_evaluation(features)
    audit = audit_congruence(scoring)
    print(f"  result: {audit['result']}, critical={audit['critical_count']}, warnings={audit['warning_count']}")
    assert audit["result"] in ("PASS", "PASS_WITH_WARNINGS"), audit
    print("PASS\n")


def test_congruence_fails_on_contradiction():
    print("=== TEST_CONGRUENCE_02: contradição crítica voice flat + story rico ===")
    # Construir scoring output artificial com contradição
    scoring = {
        "evaluation_id": "test-contradiction",
        "dimension_scores": {
            "voice": {"score": 30.0, "evidence": [], "confidence": "high"},
            "body": {"score": 70.0, "evidence": [], "confidence": "high"},
            "face": {"score": 65.0, "evidence": [], "confidence": "high"},
            "storytelling": {"score": 85.0, "evidence": [], "confidence": "high"},
        },
        "incomplete_dimensions": [],
        "overall_score": 62.5,
    }
    audit = audit_congruence(scoring)
    assert audit["result"] == "FAIL_CRITICAL", audit
    rule_ids = [v["rule"] for v in audit["violations"]]
    assert "CONG_01_voice_flat_vs_narrative_rich" in rule_ids, rule_ids
    print(f"  violations: {rule_ids}")
    print("PASS\n")


def test_congruence_body_face_disconnect():
    print("=== TEST_CONGRUENCE_03: body-face disconnect crítico ===")
    scoring = {
        "evaluation_id": "test-disconnect",
        "dimension_scores": {
            "body": {"score": 85.0, "evidence": [], "confidence": "high"},
            "face": {"score": 30.0, "evidence": [], "confidence": "high"},
            "voice": {"score": 65.0, "evidence": [], "confidence": "high"},
            "storytelling": {"score": 60.0, "evidence": [], "confidence": "high"},
        },
        "incomplete_dimensions": [],
        "overall_score": 60.0,
    }
    audit = audit_congruence(scoring)
    assert audit["result"] == "FAIL_CRITICAL", audit
    assert any("CONG_02" in v["rule"] for v in audit["violations"]), audit
    print(f"  violations: {[v['rule'] for v in audit['violations']]}")
    print("PASS\n")


def test_resolve_weights_default():
    print("=== TEST_WEIGHTS_01: sem contexto → default ===")
    w, src = resolve_weights(None)
    assert src == "default:no_context"
    assert abs(sum(w.values()) - 1.0) < 0.01, w
    print(f"  weights: {w}, source: {src}")
    print("PASS\n")


def test_resolve_weights_palco():
    print("=== TEST_WEIGHTS_02: motivacao='palestrar' → pesos de palco ===")
    w, src = resolve_weights({"motivacao": ["palestrar"]})
    assert "palco" in src
    assert w["body"] == 0.40, w
    print(f"  weights: {w}, source: {src}")
    print("PASS\n")


def run() -> int:
    test_scoring_happy_path()
    test_scoring_with_context()
    test_scoring_incomplete()
    test_congruence_pass()
    test_congruence_fails_on_contradiction()
    test_congruence_body_face_disconnect()
    test_resolve_weights_default()
    test_resolve_weights_palco()
    print("ALL EPIC 2 TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(run())
