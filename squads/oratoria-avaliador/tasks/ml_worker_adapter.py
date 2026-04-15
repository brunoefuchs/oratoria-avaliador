"""
ml_worker_adapter.py
────────────────────
Adapter que converte o output atual do ml-worker (formato legado que mistura
features brutas + scores agregados) para o contract canônico v1.0.0 do
squad oratoria-avaliador.

Uso:
    from squads.oratoria_avaliador.tasks.ml_worker_adapter import to_features_canonical

    payload = to_features_canonical(
        evaluation_id="uuid",
        storage_path="evaluations/uuid/video.mp4",
        duration_seconds=180.5,
        worker_outputs={
            "voice_analyzer": {...},
            "filler_detector": {...},
            "posture_analyzer": {...},
            ...
        },
    )

Contract de saída: data/features_canonical.schema.json (v1.0.0)

Convenções:
- Worker ausente → campo correspondente omitido (contract permite dimensões parciais)
- Worker com "confidence": "failed" → campo omitido + warning registrado
- Scores agregados do aggregator.py NÃO entram no canonical — aqui só vão features
- schema_version é fixado em "1.0.0"; mudança exige bump MAJOR + migração

Story 1.3 — Epic 1. Este arquivo NÃO importa dependências do ml-worker
(mantém o squad desacoplado). Contratos são os únicos acoplamentos.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.1.0"  # inclui tonality (aditivo)
SCHEMA_PATH = Path(__file__).parent.parent / "data" / "features_canonical.schema.json"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_get(d: dict[str, Any] | None, *keys: str, default: Any = None) -> Any:
    """Navega chave a chave. Retorna default se qualquer nível faltar ou for None."""
    if not d:
        return default
    current: Any = d
    for k in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(k)
        if current is None:
            return default
    return current


def _extract_voice(voice_out: dict | None, filler_out: dict | None) -> dict | None:
    """Monta dimensions.voice a partir de voice_analyzer + filler_detector."""
    if not voice_out and not filler_out:
        return None

    voice: dict[str, Any] = {}

    prosody = voice_out.get("metrics", voice_out) if voice_out else {}
    if prosody:
        voice["prosody"] = {
            k: v
            for k, v in {
                "pitch_mean_hz": _safe_get(prosody, "pitch_mean_hz"),
                "pitch_std_hz": _safe_get(prosody, "pitch_std_hz"),
                "pitch_range_hz": _safe_get(prosody, "pitch_range_hz"),
                "volume_mean_db": _safe_get(prosody, "volume_mean_db"),
                "volume_std_db": _safe_get(prosody, "volume_std_db"),
                "speaking_rate_wpm": _safe_get(prosody, "speaking_rate_wpm")
                or _safe_get(prosody, "wpm"),
            }.items()
            if v is not None
        }

    if filler_out:
        fm = filler_out.get("metrics", filler_out)
        voice["filler_words"] = {
            k: v
            for k, v in {
                "count": _safe_get(fm, "count"),
                "per_minute": _safe_get(fm, "per_minute")
                or _safe_get(fm, "fillers_per_minute"),
                "timestamps": _safe_get(fm, "timestamps", default=[]),
            }.items()
            if v is not None
        }

    vad = _safe_get(voice_out, "vad") or _safe_get(voice_out, "metrics", "vad")
    if vad:
        voice["vad"] = vad

    return voice or None


def _extract_body(posture_out: dict | None, gesture_out: dict | None) -> dict | None:
    if not posture_out and not gesture_out:
        return None
    body: dict[str, Any] = {}
    if posture_out and posture_out.get("confidence") != "failed":
        pm = posture_out.get("metrics", posture_out)
        score = posture_out.get("score") or _safe_get(pm, "score")
        if score is not None:
            body["posture_score"] = score
    if gesture_out and gesture_out.get("confidence") != "failed":
        gm = gesture_out.get("metrics", gesture_out)
        for src, dst in (
            ("amplitude", "gesture_amplitude"),
            ("variety", "gesture_variety"),
            ("movement_std", "movement_std"),
        ):
            v = _safe_get(gm, src)
            if v is not None:
                body[dst] = v
    return body or None


def _extract_face(facial_out: dict | None) -> dict | None:
    if not facial_out or facial_out.get("confidence") == "failed":
        return None
    fm = facial_out.get("metrics", facial_out)
    face = {
        k: v
        for k, v in {
            "aus_active_pct": _safe_get(fm, "aus_active_pct"),
            "smile_frequency": _safe_get(fm, "smile_frequency"),
            "gaze_variance": _safe_get(fm, "gaze_variance"),
            "expression_entropy": _safe_get(fm, "expression_entropy"),
        }.items()
        if v is not None
    }
    return face or None


def _extract_tonality(tonality_out: dict | None) -> dict | None:
    """Extrai features de tonality (schema v1.1.0)."""
    if not tonality_out or tonality_out.get("confidence") == "failed":
        return None
    tm = tonality_out.get("metrics", tonality_out)
    tonality = {
        k: v
        for k, v in {
            "valence_mean": _safe_get(tm, "valence_mean"),
            "arousal_mean": _safe_get(tm, "arousal_mean"),
            "dominance_mean": _safe_get(tm, "dominance_mean"),
            "emotion_variety": _safe_get(tm, "emotion_variety"),
            "dominant_emotion": _safe_get(tm, "dominant_emotion"),
        }.items()
        if v is not None
    }
    return tonality or None


def _extract_storytelling(
    voice_out: dict | None, opening_out: dict | None
) -> dict | None:
    transcript = _safe_get(voice_out, "transcript", "full_text") or _safe_get(
        voice_out, "full_text"
    )
    if not transcript and not opening_out:
        return None
    story: dict[str, Any] = {}
    if transcript:
        story["transcript"] = transcript
    if opening_out and opening_out.get("confidence") != "failed":
        om = opening_out.get("metrics", opening_out)
        hints = {
            "has_opening_hook": _safe_get(om, "has_hook"),
            "has_personal_story": _safe_get(om, "has_personal_story"),
            "has_call_to_action": _safe_get(om, "has_cta"),
        }
        hints = {k: v for k, v in hints.items() if v is not None}
        if hints:
            story["narrative_structure_hints"] = hints
    return story or None


def to_features_canonical(
    *,
    evaluation_id: str,
    storage_path: str,
    duration_seconds: float,
    worker_outputs: dict[str, dict | None],
    fps: float | None = None,
    audio_sample_rate: int | None = None,
    processing_time_ms: int | None = None,
    warnings: list[str] | None = None,
    fallbacks_applied: list[str] | None = None,
) -> dict[str, Any]:
    """
    Converte output do ml-worker legado para features_canonical v1.0.0.

    worker_outputs deve ter chaves como:
      voice_analyzer, filler_detector, posture_analyzer,
      gesture_analyzer, facial_analyzer, opening_analyzer

    Retorna dict pronto para validação contra features_canonical.schema.json.
    """
    voice = _extract_voice(
        worker_outputs.get("voice_analyzer"), worker_outputs.get("filler_detector")
    )
    body = _extract_body(
        worker_outputs.get("posture_analyzer"), worker_outputs.get("gesture_analyzer")
    )
    face = _extract_face(worker_outputs.get("facial_analyzer"))
    storytelling = _extract_storytelling(
        worker_outputs.get("voice_analyzer"), worker_outputs.get("opening_analyzer")
    )
    tonality = _extract_tonality(worker_outputs.get("tonality_analyzer"))

    dimensions = {
        k: v
        for k, v in {
            "voice": voice,
            "body": body,
            "face": face,
            "storytelling": storytelling,
            "tonality": tonality,
        }.items()
        if v is not None
    }

    ml_worker_versions = {
        name: (out.get("version") if isinstance(out, dict) else None) or "unknown"
        for name, out in worker_outputs.items()
        if out is not None
    }

    video_ref: dict[str, Any] = {
        "storage_path": storage_path,
        "duration_seconds": duration_seconds,
    }
    if fps is not None:
        video_ref["fps"] = fps
    if audio_sample_rate is not None:
        video_ref["audio_sample_rate"] = audio_sample_rate

    metadata: dict[str, Any] = {}
    if processing_time_ms is not None:
        metadata["processing_time_ms"] = processing_time_ms
    if warnings:
        metadata["warnings"] = warnings
    if fallbacks_applied:
        metadata["fallbacks_applied"] = fallbacks_applied

    payload: dict[str, Any] = {
        "evaluation_id": evaluation_id,
        "schema_version": SCHEMA_VERSION,
        "extracted_at": _iso_now(),
        "video_ref": video_ref,
        "ml_worker_versions": ml_worker_versions,
        "dimensions": dimensions,
    }
    if metadata:
        payload["metadata"] = metadata

    return payload


def load_schema() -> dict[str, Any]:
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)
