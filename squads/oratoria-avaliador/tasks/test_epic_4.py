"""
test_epic_4.py
──────────────
Smoke tests Epic 4: quality_gate_keeper, calibration_keeper, audit_outlier,
dashboard_generator, pipeline_end_to_end.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from quality_gate_keeper import aggregate_gates  # noqa: E402
from calibration_keeper import (  # noqa: E402
    record_precedent, read_log, audit_trail, verify_current_state_traceable, LOG_PATH,
)
from audit_outlier import audit  # noqa: E402
from dashboard_generator import generate_dashboard  # noqa: E402
from pipeline_end_to_end import run_pipeline  # noqa: E402


def _load_fixture(name: str) -> dict:
    with open(_HERE.parent / "data" / "fixtures" / name, encoding="utf-8") as f:
        return json.load(f)


def test_gate_pass_all_green():
    print("=== TEST_E4_01: gate PASS com tudo verde ===")
    decision = aggregate_gates(
        evaluation_id="test-pass",
        contract_result={"result": "PASS", "violations": []},
        scoring_result={"incomplete_dimensions": []},
        congruence_result={"result": "PASS", "critical_count": 0, "warning_count": 0, "violations": []},
        hierarchy_result={"top_n": 3, "problems": [
            {"rank": 1, "why": "x", "evidence": []},
            {"rank": 2, "why": "y", "evidence": []},
            {"rank": 3, "why": "z", "evidence": []},
        ]},
        fidelity_result={"result": "PASS", "fidelity_pct": 92, "threshold_pct": 85, "mentor": "gui-reginatto"},
        exercise_plan={"g6_exercise_linkage_pass": True, "exercises_by_problem": [
            {"rank": 1, "has_exercise": True}, {"rank": 2, "has_exercise": True}, {"rank": 3, "has_exercise": True}
        ]},
    )
    assert decision["verdict"] == "PASS", decision
    assert decision["release_to_user"] is True
    print(f"  verdict: {decision['verdict']}, next: {decision['next_action']}")
    print("PASS\n")


def test_gate_fail_contract():
    print("=== TEST_E4_02: G1 FAIL → verdict FAIL ===")
    decision = aggregate_gates(
        evaluation_id="test-g1-fail",
        contract_result={"result": "FAIL", "violations": [{"rule": "schema_version_required"}]},
    )
    assert decision["verdict"] == "FAIL"
    assert decision["release_to_user"] is False
    assert "G1_CONTRACT_VALIDITY" in decision["critical_fails"]
    print(f"  verdict: {decision['verdict']}, critical_fails: {decision['critical_fails']}")
    print("PASS\n")


def test_gate_waived():
    print("=== TEST_E4_03: FAIL com waiver → WAIVED (release) ===")
    decision = aggregate_gates(
        evaluation_id="test-waive",
        contract_result={"result": "PASS"},
        scoring_result={"incomplete_dimensions": []},
        congruence_result={"result": "PASS", "critical_count": 0, "warning_count": 0, "violations": []},
        hierarchy_result={"top_n": 3, "problems": [
            {"rank": 1, "why": "x", "evidence": []},
            {"rank": 2, "why": "y", "evidence": []},
            {"rank": 3, "why": "z", "evidence": []},
        ]},
        fidelity_result={"result": "FAIL", "fidelity_pct": 70, "threshold_pct": 85, "mentor": "gui-reginatto"},
        exercise_plan={"g6_exercise_linkage_pass": True, "exercises_by_problem": [
            {"rank": 1, "has_exercise": True}, {"rank": 2, "has_exercise": True}, {"rank": 3, "has_exercise": True}
        ]},
        waiver={"waiver_reason": "mentor humano validou manualmente", "signed_by": "bruno"},
    )
    assert decision["verdict"] == "WAIVED"
    assert decision["release_to_user"] is True
    print(f"  verdict: {decision['verdict']}, waiver: {decision['waiver']['signed_by']}")
    print("PASS\n")


def test_calibration_append_and_read():
    print("=== TEST_E4_04: calibration append-only ===")
    if LOG_PATH.exists():
        LOG_PATH.unlink()  # reset for test
    entry1 = record_precedent(
        change_type="weight_adjust",
        target="scoring.weights.vendas.voice",
        before=0.25,
        after=0.28,
        why="Feedback mentor: vendas deveria pesar voz mais",
        who="bruno",
        mentor_signoff=True,
    )
    entry2 = record_precedent(
        change_type="threshold_adjust",
        target="congruence.CONG_02.threshold_critical",
        before=40.0,
        after=35.0,
        why="Falso positivo em 3 casos reais",
        who="@mentor:gui",
        mentor_signoff=True,
    )
    log = read_log()
    assert len(log) == 2, log
    assert log[0]["precedent_id"].startswith("CAL-")
    assert log[1]["target"] == "congruence.CONG_02.threshold_critical"
    print(f"  log entries: {len(log)}")
    print(f"  first: {entry1['precedent_id']}")
    print("PASS\n")


def test_calibration_audit_trail_g7():
    print("=== TEST_E4_05: G7 traceability ===")
    verify = verify_current_state_traceable(
        target="scoring.weights.vendas.voice",
        current_value=0.28,
    )
    assert verify["result"] == "PASS", verify
    verify_drift = verify_current_state_traceable(
        target="scoring.weights.vendas.voice",
        current_value=0.50,  # drift!
    )
    assert verify_drift["result"] == "FAIL", verify_drift
    print(f"  match: {verify['result']}, drift: {verify_drift['result']}")
    print("PASS\n")


def test_calibration_warning_without_signoff():
    print("=== TEST_E4_06: G7 warn sem signoff ===")
    entry = record_precedent(
        change_type="weight_adjust",
        target="test.no.signoff",
        before=1,
        after=2,
        why="teste",
        who="dev",
        mentor_signoff=False,
    )
    assert "_warning" in entry, entry
    print(f"  warning: {entry.get('_warning')}")
    print("PASS\n")


def test_audit_pass_trivial():
    print("=== TEST_E4_07: audit em PASS → trivial ===")
    decision = {"verdict": "PASS", "evaluation_id": "p1", "critical_fails": [], "gate_states": {}}
    report = audit(decision)
    assert report["escalation_needed"] is False
    assert report["trigger"] == "none"
    print(f"  action: {report['action_items']}")
    print("PASS\n")


def test_audit_fail_g1():
    print("=== TEST_E4_08: audit G1 FAIL → escalate @data-engineer ===")
    decision = {
        "verdict": "FAIL",
        "evaluation_id": "f1",
        "critical_fails": ["G1_CONTRACT_VALIDITY"],
        "gate_states": {
            "G1_CONTRACT_VALIDITY": {"result": "FAIL", "violations": [{"rule": "schema_version_required"}]}
        },
    }
    report = audit(decision)
    assert report["escalation_needed"] is True
    assert report["escalate_to"] == "@data-engineer"
    assert report["hypotheses"], report
    print(f"  escalate_to: {report['escalate_to']}, hypotheses: {len(report['hypotheses'])}")
    print("PASS\n")


def test_audit_fail_g3():
    print("=== TEST_E4_09: audit G3 FAIL → escalate mentor ===")
    decision = {
        "verdict": "FAIL",
        "evaluation_id": "f3",
        "critical_fails": ["G3_CONGRUENCE"],
        "gate_states": {
            "G3_CONGRUENCE": {
                "result": "FAIL",
                "violations": [{"rule": "CONG_01", "severity": "critical"}]
            }
        },
    }
    report = audit(decision)
    assert report["escalate_to"] == "human_mentor"
    print(f"  escalate_to: {report['escalate_to']}")
    print("PASS\n")


def test_dashboard_empty():
    print("=== TEST_E4_10: dashboard vazio ===")
    md = generate_dashboard([])
    assert "Nenhuma decisão" in md
    print("PASS\n")


def test_dashboard_mixed():
    print("=== TEST_E4_11: dashboard agrega métricas ===")
    decisions = [
        {"verdict": "PASS", "critical_fails": [], "gate_states": {"G4_VOICE_DNA_FIDELITY": {"fidelity_pct": 92, "mentor": "gui-reginatto"}}},
        {"verdict": "PASS", "critical_fails": [], "gate_states": {"G4_VOICE_DNA_FIDELITY": {"fidelity_pct": 88, "mentor": "gui-reginatto"}}},
        {"verdict": "FAIL", "critical_fails": ["G3_CONGRUENCE"], "gate_states": {}},
        {"verdict": "PASS", "critical_fails": [], "gate_states": {"G4_VOICE_DNA_FIDELITY": {"fidelity_pct": 91, "mentor": "vinh-giang"}}},
    ]
    md = generate_dashboard(decisions)
    assert "PASS" in md
    assert "gui-reginatto" in md
    assert "vinh-giang" in md
    assert "G3_CONGRUENCE" in md
    print(f"  dashboard generated, {len(md)} chars")
    print("PASS\n")


def test_pipeline_end_to_end_happy():
    print("=== TEST_E4_12: pipeline end-to-end (fixture válida) ===")
    features = _load_fixture("features_valid_v1.json")
    result = run_pipeline(
        features,
        evaluation_context={"motivacao": ["vender_mais"], "desejo_melhorar": ["autoridade"]},
    )
    assert result["pipeline_result"] == "COMPLETE", result["pipeline_result"]
    decision = result["gate_decision"]
    print(f"  verdict: {decision['verdict']}, release: {decision['release_to_user']}")
    print(f"  mentor: {result['artifacts']['router_result']['mentor']}")
    print(f"  fidelity: {result['artifacts']['fidelity_result']['fidelity_pct']}%")
    assert decision["verdict"] in ("PASS", "WAIVED"), decision
    assert result["artifacts"]["router_result"]["mentor"] == "gui-reginatto"
    print("PASS\n")


def test_pipeline_end_to_end_abort_g1():
    print("=== TEST_E4_13: pipeline aborta em G1 FAIL ===")
    features = _load_fixture("features_invalid_missing_required.json")
    result = run_pipeline(features)
    assert result["pipeline_result"] == "ABORTED_AT_PHASE_1", result
    assert result["gate_decision"]["verdict"] == "FAIL"
    print(f"  aborted at phase 1 — {result['gate_decision']['next_action']}")
    print("PASS\n")


def test_pipeline_to_dashboard_integration():
    print("=== TEST_E4_14: pipeline × dashboard integration ===")
    features = _load_fixture("features_valid_v1.json")
    # roda 2 avaliações — uma pt-BR vendas, uma EN
    r1 = run_pipeline(features, evaluation_context={"motivacao": ["vender_mais"]})
    r2 = run_pipeline(features, user_profile={"language": "en"})
    r3 = run_pipeline(_load_fixture("features_invalid_missing_required.json"))
    decisions = [r1["gate_decision"], r2["gate_decision"], r3["gate_decision"]]
    md = generate_dashboard(decisions)
    assert "PASS" in md
    assert "FAIL" in md
    assert "gui-reginatto" in md or "vinh-giang" in md
    print(f"  3 runs → dashboard OK ({len(md)} chars)")
    print("PASS\n")


def run() -> int:
    test_gate_pass_all_green()
    test_gate_fail_contract()
    test_gate_waived()
    test_calibration_append_and_read()
    test_calibration_audit_trail_g7()
    test_calibration_warning_without_signoff()
    test_audit_pass_trivial()
    test_audit_fail_g1()
    test_audit_fail_g3()
    test_dashboard_empty()
    test_dashboard_mixed()
    test_pipeline_end_to_end_happy()
    test_pipeline_end_to_end_abort_g1()
    test_pipeline_to_dashboard_integration()
    print("ALL EPIC 4 TESTS PASSED (14/14)")
    # cleanup calibration log
    if LOG_PATH.exists():
        LOG_PATH.unlink()
    return 0


if __name__ == "__main__":
    sys.exit(run())
