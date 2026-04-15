"""
test_adapter.py
───────────────
Smoke test do ml_worker_adapter.to_features_canonical().

Valida que payload gerado pelo adapter (a partir de output simulado do ml-worker)
passa pelo G1_CONTRACT_VALIDITY gate.

Roda sem pytest:
    python3 squads/oratoria-avaliador/tasks/test_adapter.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from ml_worker_adapter import to_features_canonical  # noqa: E402
from validate_contract import validate_payload  # noqa: E402


def _mock_worker_outputs() -> dict:
    """Simula output do ml-worker atual (formato legado)."""
    return {
        "voice_analyzer": {
            "version": "0.3.1",
            "confidence": "ok",
            "full_text": "Fala de teste do speaker.",
            "metrics": {
                "pitch_mean_hz": 145.0,
                "pitch_std_hz": 30.0,
                "pitch_range_hz": 100.0,
                "volume_mean_db": -17.5,
                "volume_std_db": 3.8,
                "wpm": 152.0,
            },
        },
        "filler_detector": {
            "version": "0.2.0",
            "confidence": "ok",
            "metrics": {
                "count": 8,
                "fillers_per_minute": 2.67,
                "timestamps": [
                    {"word": "né", "start_s": 15.0, "end_s": 15.2},
                ],
            },
        },
        "posture_analyzer": {
            "version": "0.3.0",
            "confidence": "ok",
            "score": 68.0,
            "metrics": {"score": 68.0},
        },
        "gesture_analyzer": {
            "version": "0.2.1",
            "confidence": "ok",
            "metrics": {"amplitude": 0.6, "variety": 0.5, "movement_std": 0.1},
        },
        "facial_analyzer": {
            "version": "0.1.0",
            "confidence": "ok",
            "metrics": {
                "aus_active_pct": 40.0,
                "smile_frequency": 0.15,
                "gaze_variance": 0.28,
                "expression_entropy": 1.7,
            },
        },
        "opening_analyzer": {
            "version": "0.1.0",
            "confidence": "ok",
            "metrics": {
                "has_hook": True,
                "has_personal_story": True,
                "has_cta": False,
            },
        },
    }


def _mock_failed_worker_outputs() -> dict:
    """Simula output parcial — worker de face falhou."""
    outs = _mock_worker_outputs()
    outs["facial_analyzer"] = {"version": "0.1.0", "confidence": "failed"}
    return outs


def run() -> int:
    print("=== TEST_ADAPTER_01: happy path ===")
    payload = to_features_canonical(
        evaluation_id="a1b2c3d4-9999-4000-8000-000000000099",
        storage_path="evaluations/test/video.mp4",
        duration_seconds=180.0,
        fps=30,
        audio_sample_rate=44100,
        worker_outputs=_mock_worker_outputs(),
        processing_time_ms=42000,
    )
    r1 = validate_payload(payload)
    print(json.dumps({"result": r1["result"], "violations": r1["violations"]}, indent=2))
    assert r1["result"] == "PASS", f"Expected PASS, got {r1}"
    assert set(payload["dimensions"].keys()) == {"voice", "body", "face", "storytelling"}, (
        f"Unexpected dimensions: {payload['dimensions'].keys()}"
    )
    print("PASS\n")

    print("=== TEST_ADAPTER_02: face worker failed (partial output) ===")
    payload2 = to_features_canonical(
        evaluation_id="a1b2c3d4-9999-4000-8000-000000000098",
        storage_path="evaluations/test/video2.mp4",
        duration_seconds=120.0,
        worker_outputs=_mock_failed_worker_outputs(),
        warnings=["facial_analyzer failed"],
        fallbacks_applied=["face dimension omitted"],
    )
    r2 = validate_payload(payload2)
    print(json.dumps({"result": r2["result"], "violations": r2["violations"]}, indent=2))
    assert r2["result"] == "PASS", f"Expected PASS (partial OK), got {r2}"
    assert "face" not in payload2["dimensions"], "face should be omitted when worker failed"
    assert payload2["metadata"]["warnings"] == ["facial_analyzer failed"]
    print("PASS\n")

    print("=== TEST_ADAPTER_03: empty worker outputs ===")
    payload3 = to_features_canonical(
        evaluation_id="a1b2c3d4-9999-4000-8000-000000000097",
        storage_path="evaluations/test/video3.mp4",
        duration_seconds=60.0,
        worker_outputs={},
    )
    r3 = validate_payload(payload3)
    print(json.dumps({"result": r3["result"], "violations": r3["violations"]}, indent=2))
    # Dimensions vazio ainda é object válido; schema permite parcial em Epic 1.
    assert r3["result"] == "PASS", f"Expected PASS (empty dims are object), got {r3}"
    assert payload3["dimensions"] == {}
    print("PASS\n")

    print("ALL ADAPTER TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(run())
