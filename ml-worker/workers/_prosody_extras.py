"""Prosody Extras — Story 9.4 (Epic 9).

Duas funcoes CPU-only que enriquecem voice_analyzer:

1. extract_egemaps(audio_path) — 88 features acusticas padrao eGeMAPSv02
   (Eyben et al. 2016) via opensmile-python. Alimenta tonality com features
   academicamente validadas.

2. detect_pauses(audio_path) — Voice Activity Detection via pyannote.audio.
   Classifica pausas em micro/hesitation/retorical por duracao.
   Fallback librosa se HF_TOKEN ausente ou pyannote nao instalado.

Libs opcionais (pip install -e ".[prosody]"). Lazy import + graceful fallback
garantem pipeline nao quebra se deps nao instaladas.

Thresholds:
- Micro-pausa: <0.4s (natural de fala)
- Hesitacao: 0.4-1.2s (nervosismo)
- Pausa retorica: >1.2s (Vinh "highlighter verbal")
"""

from __future__ import annotations

import os

import structlog

logger = structlog.get_logger()

PAUSE_MICRO_MAX = 0.4
PAUSE_HESITATION_MAX = 1.2
EGEMAPS_FEATURE_COUNT = 88  # eGeMAPSv02 spec


# ─────────────────────────────────────────────────────────────────────────────
# openSMILE eGeMAPS
# ─────────────────────────────────────────────────────────────────────────────


def extract_egemaps(audio_path: str) -> dict[str, float] | None:
    """Extrai 88 features eGeMAPSv02 via opensmile-python.

    Returns:
        dict[str, float] com 88 chaves de features, ou None se lib ausente.
    """
    try:
        import opensmile
    except ImportError:
        logger.warning(
            "opensmile_not_installed",
            hint="pip install opensmile OR pip install -e '.[prosody]'",
        )
        return None

    try:
        smile = opensmile.Smile(
            feature_set=opensmile.FeatureSet.eGeMAPSv02,
            feature_level=opensmile.FeatureLevel.Functionals,
        )
        df = smile.process_file(audio_path)
        # df e DataFrame com 1 row × 88 cols. Retorna dict plano.
        return {col: float(df.iloc[0][col]) for col in df.columns}
    except Exception as e:  # noqa: BLE001 — qualquer erro de extracao vira None
        logger.warning(
            "opensmile_extraction_failed",
            audio_path=audio_path,
            error=str(e),
            error_type=type(e).__name__,
        )
        return None


# ─────────────────────────────────────────────────────────────────────────────
# pyannote VAD + fallback librosa
# ─────────────────────────────────────────────────────────────────────────────


def _classify_pause(duration_s: float) -> str:
    """Classifica pausa por duracao: micro|hesitation|retorical."""
    if duration_s < PAUSE_MICRO_MAX:
        return "micro"
    if duration_s < PAUSE_HESITATION_MAX:
        return "hesitation"
    return "retorical"


def _detect_pauses_pyannote(audio_path: str) -> list[dict] | None:
    """pyannote.audio VAD pipeline. Requer HF_TOKEN."""
    token = os.getenv("HF_TOKEN")
    if not token:
        logger.warning(
            "pyannote_no_hf_token",
            hint="Obter em https://huggingface.co/settings/tokens + export HF_TOKEN=...",
        )
        return None

    try:
        from pyannote.audio import Pipeline
    except ImportError:
        logger.warning("pyannote_not_installed", hint="pip install -e '.[prosody]'")
        return None

    try:
        pipeline = Pipeline.from_pretrained(
            "pyannote/voice-activity-detection", use_auth_token=token
        )
        vad_output = pipeline(audio_path)

        # vad_output eh annotation com segments de VOZ. Pausas sao os GAPS entre voz.
        voice_segments = [(s.start, s.end) for s in vad_output.get_timeline()]
        if not voice_segments:
            return []

        pauses: list[dict] = []
        for i in range(len(voice_segments) - 1):
            _, end_prev = voice_segments[i]
            start_next, _ = voice_segments[i + 1]
            duration = start_next - end_prev
            if duration > 0.05:  # ignora gaps mínimos de artefato
                pauses.append(
                    {
                        "start": round(end_prev, 3),
                        "end": round(start_next, 3),
                        "duration": round(duration, 3),
                        "type": _classify_pause(duration),
                    }
                )
        return pauses
    except Exception as e:  # noqa: BLE001
        logger.warning(
            "pyannote_inference_failed",
            audio_path=audio_path,
            error=str(e),
            error_type=type(e).__name__,
        )
        return None


def _detect_pauses_librosa_fallback(audio_path: str) -> list[dict] | None:
    """Fallback silence-detection via librosa.effects.split. Sem HF token necessario."""
    try:
        import librosa
    except ImportError:
        logger.warning("librosa_not_installed")
        return None

    try:
        y, sr = librosa.load(audio_path, sr=16000, mono=True)
        # top_db=30 = silencio a -30dB do pico.
        intervals = librosa.effects.split(y, top_db=30)
        # Converter voice intervals pra pause intervals (gaps).
        pauses: list[dict] = []
        for i in range(len(intervals) - 1):
            _, end_prev = intervals[i]
            start_next, _ = intervals[i + 1]
            duration = (start_next - end_prev) / sr
            if duration > 0.05:
                pauses.append(
                    {
                        "start": round(end_prev / sr, 3),
                        "end": round(start_next / sr, 3),
                        "duration": round(duration, 3),
                        "type": _classify_pause(duration),
                    }
                )
        return pauses
    except Exception as e:  # noqa: BLE001
        logger.warning(
            "librosa_fallback_failed",
            audio_path=audio_path,
            error=str(e),
            error_type=type(e).__name__,
        )
        return None


def detect_pauses(audio_path: str) -> dict:
    """Detecta pausas classificadas em micro/hesitation/retorical.

    Tenta pyannote (mais preciso) → fallback librosa silence-detection.
    Se ambos falharem, retorna dict com lista vazia (nao crash pipeline).

    Returns:
        {
            "pauses": [{start, end, duration, type}, ...],
            "counts": {"micro": N, "hesitation": M, "retorical": K},
            "total_retorical_ratio": float,
            "source": "pyannote" | "librosa" | "none",
        }
    """
    source = "pyannote"
    pauses = _detect_pauses_pyannote(audio_path)

    if pauses is None:
        logger.info("pyannote_fallback_triggered", audio_path=audio_path)
        pauses = _detect_pauses_librosa_fallback(audio_path)
        source = "librosa"

    if pauses is None:
        logger.warning("pauses_detection_all_failed", audio_path=audio_path)
        pauses = []
        source = "none"

    counts = {"micro": 0, "hesitation": 0, "retorical": 0}
    for p in pauses:
        counts[p["type"]] += 1

    total = sum(counts.values())
    retorical_ratio = (counts["retorical"] / total) if total > 0 else 0.0

    return {
        "pauses": pauses,
        "counts": counts,
        "total_retorical_ratio": round(retorical_ratio, 3),
        "source": source,
    }
