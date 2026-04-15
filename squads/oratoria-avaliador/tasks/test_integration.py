"""
test_integration.py
───────────────────
Integration test: simula shape real de output do ml-worker (como aparece em
ml-worker/workers/*.py) e passa pelo entrypoint `process()`.

Valida que:
1. Adapter converte corretamente formato legado ml-worker
2. Pipeline completo roda end-to-end
3. Release decision é emitido
4. Auto-audit é invocado em FAIL
"""

from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from process_evaluation import process, process_minimal  # noqa: E402


def _realistic_ml_worker_outputs() -> dict:
    """Shape que ml-worker/workers/*.py realmente emitem hoje.

    Baseado em inspeção de aggregator.py + voice_analyzer.py + filler_detector.py.
    """
    return {
        "voice_analyzer": {
            "version": "0.3.1",
            "confidence": "high",
            "full_text": "Hoje quero falar sobre comunicação...",
            "metrics": {
                "pitch_mean_hz": 142.5,
                "pitch_std_hz": 29.8,
                "pitch_range_hz": 98.0,
                "volume_mean_db": -18.5,
                "volume_std_db": 4.2,
                "wpm": 151.0,
            },
        },
        "filler_detector": {
            "version": "0.2.0",
            "confidence": "high",
            "score": 72.0,
            "metrics": {
                "count": 9,
                "fillers_per_minute": 3.0,
                "timestamps": [
                    {"word": "né", "start_s": 14.5, "end_s": 14.7},
                    {"word": "tipo", "start_s": 47.2, "end_s": 47.5},
                ],
            },
        },
        "posture_analyzer": {
            "version": "0.3.0",
            "confidence": "high",
            "score": 70.0,
            "metrics": {"score": 70.0},
        },
        "gesture_analyzer": {
            "version": "0.2.1",
            "confidence": "high",
            "score": 65.0,
            "metrics": {"amplitude": 0.55, "variety": 0.48, "movement_std": 0.11},
        },
        "facial_analyzer": {
            "version": "0.1.0",
            "confidence": "high",
            "metrics": {
                "aus_active_pct": 44.0,
                "smile_frequency": 0.20,
                "gaze_variance": 0.33,
                "expression_entropy": 1.85,
            },
        },
        "opening_analyzer": {
            "version": "0.1.0",
            "confidence": "high",
            "metrics": {
                "has_hook": True,
                "has_personal_story": True,
                "has_cta": False,
            },
        },
        "tonality_analyzer": {
            "version": "0.1.0",
            "confidence": "high",
            "metrics": {
                "valence_mean": 0.58,
                "arousal_mean": 0.62,
                "dominance_mean": 0.68,
                "emotion_variety": 0.55,
            },
        },
    }


def test_integration_happy_path():
    print("=== TEST_INT_01: process() happy path com ml-worker output realista ===")
    outputs = _realistic_ml_worker_outputs()
    result = process(
        evaluation_id="int-test-001",
        storage_path="evaluations/int-test-001/video.mp4",
        duration_seconds=180.0,
        fps=30,
        audio_sample_rate=44100,
        worker_outputs=outputs,
        evaluation_context={"motivacao": ["vender_mais"], "desejo_melhorar": ["autoridade"]},
        processing_time_ms=48000,
    )
    assert result["pipeline_result"] == "COMPLETE"
    decision = result["gate_decision"]
    print(f"  schema_version: {result['features_canonical']['schema_version']}")
    print(f"  verdict: {decision['verdict']}")
    print(f"  mentor: {result['artifacts']['router_result']['mentor']}")
    dims_scored = list(result["artifacts"]["scoring_result"]["dimension_scores"].keys())
    print(f"  dims scored: {dims_scored}")
    print(f"  top-3: {[p['dimension'] for p in result['artifacts']['hierarchy_result']['problems']]}")
    assert result["features_canonical"]["schema_version"] == "1.1.0"
    assert "tonality" in result["features_canonical"]["dimensions"], "tonality deveria entrar via adapter"
    assert "tonality" in dims_scored
    assert decision["release_to_user"] in (True, False)
    assert "narrative" in result["artifacts"]
    print("PASS\n")


def test_integration_incomplete_workers():
    print("=== TEST_INT_02: worker failures → fallbacks_applied ===")
    outputs = _realistic_ml_worker_outputs()
    outputs["facial_analyzer"] = {"version": "0.1.0", "confidence": "failed"}
    outputs["gesture_analyzer"] = {"version": "0.2.1", "confidence": "failed"}

    result = process(
        evaluation_id="int-test-002",
        storage_path="evaluations/int-test-002/video.mp4",
        duration_seconds=120.0,
        worker_outputs=outputs,
        warnings=["facial failed", "gesture failed"],
        fallbacks_applied=["face omitted", "body partial"],
    )
    # Pipeline ainda roda, mas com dims incompletos
    features = result["features_canonical"]
    print(f"  dims em features_canonical: {list(features['dimensions'].keys())}")
    print(f"  warnings propagadas: {features['metadata']['warnings']}")
    assert "face" not in features["dimensions"]
    assert features["metadata"]["warnings"]
    print("PASS\n")


def test_integration_auto_audit_on_fail():
    print("=== TEST_INT_03: auto-audit dispara em FAIL ===")
    # Força G1 FAIL com output incompleto
    bad_outputs = {"voice_analyzer": {"version": "0.3.1", "confidence": "failed"}}
    result = process(
        evaluation_id="int-test-003",
        storage_path="evaluations/int-test-003/video.mp4",
        duration_seconds=60.0,
        worker_outputs=bad_outputs,
    )
    # G1 passa (schema v1.1.0 aceita dimensions vazio), mas outros gates falham
    verdict = result["gate_decision"]["verdict"]
    print(f"  verdict: {verdict}")
    if verdict == "FAIL":
        assert result["audit_report"] is not None
        print(f"  audit escalate_to: {result['audit_report']['escalate_to']}")
    else:
        print(f"  no audit triggered (verdict={verdict})")
    print("PASS\n")


def test_process_minimal():
    print("=== TEST_INT_04: process_minimal shortcut ===")
    outputs = _realistic_ml_worker_outputs()
    result = process_minimal(
        evaluation_id="int-test-004",
        worker_outputs=outputs,
        duration_seconds=180.0,
    )
    assert result["pipeline_result"] == "COMPLETE"
    print(f"  verdict: {result['gate_decision']['verdict']}")
    print("PASS\n")


def test_integration_en_routing():
    print("=== TEST_INT_05: user_profile.language=en → vinh narra ===")
    outputs = _realistic_ml_worker_outputs()
    result = process(
        evaluation_id="int-test-005",
        storage_path="evaluations/int-test-005/video.mp4",
        duration_seconds=150.0,
        worker_outputs=outputs,
        user_profile={"language": "en"},
    )
    mentor = result["artifacts"]["router_result"]["mentor"]
    assert mentor == "vinh-giang"
    narrative = result["artifacts"]["narrative"]
    assert "vinh-giang" in narrative
    print(f"  mentor: {mentor}, narrative: {len(narrative)} chars")
    print("PASS\n")


def run() -> int:
    test_integration_happy_path()
    test_integration_incomplete_workers()
    test_integration_auto_audit_on_fail()
    test_process_minimal()
    test_integration_en_routing()
    print("ALL INTEGRATION TESTS PASSED (5/5)")
    return 0


if __name__ == "__main__":
    sys.exit(run())
