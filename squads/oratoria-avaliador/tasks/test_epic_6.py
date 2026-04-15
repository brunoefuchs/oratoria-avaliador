"""
test_epic_6.py
──────────────
Smoke tests Epic 6: evolve_dimension playbook + tonality integration +
backward compat de v1.0.0 após bump para v1.1.0.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from validate_contract import validate_payload  # noqa: E402
from scoring_engine import SCORE_FUNCTIONS, score_evaluation, PESOS_DEFAULT  # noqa: E402
from evolve_dimension import (  # noqa: E402
    classify_change, bump_version, run_evolution_playbook,
)
from pipeline_end_to_end import run_pipeline  # noqa: E402


def _load_fixture(name: str) -> dict:
    with open(_HERE.parent / "data" / "fixtures" / name, encoding="utf-8") as f:
        return json.load(f)


def test_classify_additive():
    print("=== TEST_E6_01: classify_change additive ===")
    old = {"voice": {}, "body": {}}
    new = {"voice": {}, "body": {}, "tonality": {}}
    c = classify_change(old, new)
    assert c["classification"] == "additive", c
    assert c["added"] == ["tonality"]
    assert c["version_bump"] == "minor"
    print(f"  added: {c['added']}, bump: {c['version_bump']}")
    print("PASS\n")


def test_classify_breaking_removal():
    print("=== TEST_E6_02: classify_change breaking (removal) ===")
    old = {"voice": {}, "body": {}, "face": {}}
    new = {"voice": {}, "body": {}}
    c = classify_change(old, new)
    assert c["classification"] == "breaking"
    assert c["version_bump"] == "major"
    assert "face" in c["removed"]
    print(f"  removed: {c['removed']}")
    print("PASS\n")


def test_bump_version():
    print("=== TEST_E6_03: semver bumps ===")
    assert bump_version("1.0.0", "minor") == "1.1.0"
    assert bump_version("1.0.0", "major") == "2.0.0"
    assert bump_version("1.2.3", "patch") == "1.2.4"
    assert bump_version("1.1.0", "minor") == "1.2.0"
    print("  all semver bumps OK")
    print("PASS\n")


def test_backward_compat_v1_0_0_still_valid():
    print("=== TEST_E6_04: v1.0.0 payload continua passando G1 após bump do squad para 1.1.0 ===")
    old_payload = _load_fixture("features_valid_v1.json")
    assert old_payload["schema_version"] == "1.0.0"
    result = validate_payload(old_payload)
    assert result["result"] == "PASS", result
    print(f"  v1.0.0 → PASS (backward compat OK)")
    print("PASS\n")


def test_new_v1_1_0_payload_valid():
    print("=== TEST_E6_05: v1.1.0 payload com tonality passa G1 ===")
    new_payload = _load_fixture("features_valid_v1_1.json")
    assert new_payload["schema_version"] == "1.1.0"
    assert "tonality" in new_payload["dimensions"]
    result = validate_payload(new_payload)
    assert result["result"] == "PASS", result
    print(f"  v1.1.0 com tonality → PASS")
    print("PASS\n")


def test_tonality_scorer_integrated():
    print("=== TEST_E6_06: scorer de tonality produz score válido ===")
    assert "tonality" in SCORE_FUNCTIONS, "scorer não registrado"
    assert "tonality" in PESOS_DEFAULT, "peso não declarado"
    assert PESOS_DEFAULT["tonality"] == 0.0, "peso default deve ser 0.0 (neutro até calibração)"

    new_payload = _load_fixture("features_valid_v1_1.json")
    scoring = score_evaluation(new_payload)
    assert "tonality" in scoring["dimension_scores"], scoring
    tonality_entry = scoring["dimension_scores"]["tonality"]
    assert 0 <= tonality_entry["score"] <= 100
    assert tonality_entry["evidence"]
    print(f"  tonality score: {tonality_entry['score']}")
    print(f"  overall (peso tonality=0): {scoring['overall_score']}")
    print("PASS\n")


def test_pipeline_end_to_end_v1_1_0():
    print("=== TEST_E6_07: pipeline end-to-end com payload v1.1.0 ===")
    payload = _load_fixture("features_valid_v1_1.json")
    result = run_pipeline(payload, evaluation_context={"motivacao": ["palestrar"]})
    assert result["pipeline_result"] == "COMPLETE"
    decision = result["gate_decision"]
    print(f"  verdict: {decision['verdict']}, release: {decision['release_to_user']}")
    assert decision["verdict"] in ("PASS", "WAIVED"), decision
    # Tonality deve aparecer no scoring
    dims = result["artifacts"]["scoring_result"]["dimension_scores"]
    assert "tonality" in dims
    print(f"  dims scored: {list(dims.keys())}")
    print("PASS\n")


def test_playbook_executor_pass():
    print("=== TEST_E6_08: playbook executor PASS com classificação correta ===")
    old_dims = {"voice": {}, "body": {}, "face": {}, "storytelling": {}}
    new_dims = {**old_dims, "tonality": {}}
    old_payload = _load_fixture("features_valid_v1.json")

    report = run_evolution_playbook(
        dimension_name="tonality",
        old_schema_version="1.0.0",
        new_schema_version="1.1.0",
        old_dimensions=old_dims,
        new_dimensions=new_dims,
        score_functions_map=SCORE_FUNCTIONS,
        validate_fn=validate_payload,
        old_fixture_payload=old_payload,
    )
    assert report["overall_result"] == "PASS", report
    assert report["steps"]["classify_change"]["classification"] == "additive"
    assert report["steps"]["version_bump"]["result"] == "PASS"
    assert report["steps"]["ensure_scorer"]["has_scorer"] is True
    assert report["steps"]["backward_compat"]["result"] == "PASS"
    print(f"  overall: {report['overall_result']}")
    print(f"  steps: {list(report['steps'].keys())}")
    print("PASS\n")


def test_playbook_executor_fail_missing_scorer():
    print("=== TEST_E6_09: playbook FAIL quando scorer ausente ===")
    old_dims = {"voice": {}}
    new_dims = {"voice": {}, "hypothetical_dim": {}}
    report = run_evolution_playbook(
        dimension_name="hypothetical_dim",
        old_schema_version="1.0.0",
        new_schema_version="1.1.0",
        old_dimensions=old_dims,
        new_dimensions=new_dims,
        score_functions_map=SCORE_FUNCTIONS,  # não tem hypothetical_dim
        validate_fn=validate_payload,
    )
    assert report["overall_result"] == "FAIL"
    assert report["steps"]["ensure_scorer"]["has_scorer"] is False
    assert "action_if_missing" in report["steps"]["ensure_scorer"]
    print(f"  action: {report['steps']['ensure_scorer']['action_if_missing']}")
    print("PASS\n")


def test_playbook_executor_fail_wrong_version_bump():
    print("=== TEST_E6_10: playbook FAIL com version bump inconsistente ===")
    old_dims = {"voice": {}}
    new_dims = {"voice": {}, "tonality": {}}
    report = run_evolution_playbook(
        dimension_name="tonality",
        old_schema_version="1.0.0",
        new_schema_version="2.0.0",  # deveria ser 1.1.0 (additive=minor)
        old_dimensions=old_dims,
        new_dimensions=new_dims,
        score_functions_map=SCORE_FUNCTIONS,
        validate_fn=validate_payload,
    )
    assert report["overall_result"] == "FAIL"
    assert report["steps"]["version_bump"]["result"] == "FAIL"
    assert report["steps"]["version_bump"]["expected"] == "1.1.0"
    print(f"  detail: {report['steps']['version_bump']['detail']}")
    print("PASS\n")


def run() -> int:
    test_classify_additive()
    test_classify_breaking_removal()
    test_bump_version()
    test_backward_compat_v1_0_0_still_valid()
    test_new_v1_1_0_payload_valid()
    test_tonality_scorer_integrated()
    test_pipeline_end_to_end_v1_1_0()
    test_playbook_executor_pass()
    test_playbook_executor_fail_missing_scorer()
    test_playbook_executor_fail_wrong_version_bump()
    print("ALL EPIC 6 TESTS PASSED (10/10)")
    return 0


if __name__ == "__main__":
    sys.exit(run())
