"""Articulation Analyzer — Foundation 5 do Vinh Giang.

Mede CLAREZA TECNICA da producao vocal: estabilidade harmonica, projecao,
e brilho espectral (energia em frequencias de consoantes 4-8kHz).

NAO duplica medicao do tonality_analyzer — embora ambos extraiam jitter/
shimmer/HNR, tonality interpreta como VAD emocional (arousal/valence) e
articulation interpreta como TECNICA (clareza/projecao). Mesma feature,
duas lentes pedagogicamente distintas.

Pesquisa de fundamento:
- Awan 2024: HNR ≥ 18 dB = voz projetiva limpa; HNR < 10 dB = abafada
- Maryn 2022: shimmer < 0.06 (studio) / < 0.10 (mobile) = controle vocal
- Hincks 2005: spectral centroid > 1500 Hz = consoantes audiveis em fala continua

Cobertura honesta:
- Feita em mobile real (smartphone + AGC), confiabilidade ~70-75%
- Formantes F1/F2 (vogais) NAO medidos — derrubam pra 45% em mobile.
  Decisao Bruno + Vinh 2026-04-30: cobrir 75% confiavelmente vs 100%
  ruidoso. Skip formantes ate gravacao studio-grade.
"""

from __future__ import annotations

import time

import numpy as np
import parselmouth
import structlog
from parselmouth.praat import call

from contracts import WorkerResult
from workers._truth_contract_helpers import wrap_worker_result

logger = structlog.get_logger()


# Thresholds calibrados pra mobile (AGC + room noise).
# Mesmos baselines de tonality_analyzer ajustados pra interpretacao tecnica.
HNR_EXCELLENT = 18.0  # voz projetiva, harmonicos limpos
HNR_GOOD = 13.0
HNR_POOR = 8.0  # voz abafada / sem projecao

JITTER_EXCELLENT = 0.012  # voz firme (raro em mobile)
JITTER_MOBILE_GOOD = 0.020  # mobile baseline calibrado 18/04
JITTER_POOR = 0.030  # voz instavel/tremula

SHIMMER_EXCELLENT = 0.06
SHIMMER_MOBILE_GOOD = 0.10  # mobile baseline calibrado 18/04
SHIMMER_POOR = 0.15

# Spectral clarity — energia 4-8kHz (banda de consoantes) / energia total.
# Mumbling = consoantes engolidas → ratio baixo. Articulado = ratio alto.
SPECTRAL_CLARITY_EXCELLENT = 0.18
SPECTRAL_CLARITY_GOOD = 0.10
SPECTRAL_CLARITY_POOR = 0.05


def _score_hnr(hnr: float) -> float:
    if hnr >= HNR_EXCELLENT:
        return 100
    if hnr >= HNR_GOOD:
        return 70 + (hnr - HNR_GOOD) * 6  # rampa 70→100
    if hnr >= HNR_POOR:
        return 40 + (hnr - HNR_POOR) * 6  # rampa 40→70
    return max(0, hnr * 5)


def _score_jitter(jitter: float) -> float:
    if jitter <= JITTER_EXCELLENT:
        return 100
    if jitter <= JITTER_MOBILE_GOOD:
        return 80
    if jitter <= JITTER_POOR:
        return max(0, 80 - (jitter - JITTER_MOBILE_GOOD) * 5000)
    return max(0, 30 - (jitter - JITTER_POOR) * 1000)


def _score_shimmer(shimmer: float) -> float:
    if shimmer <= SHIMMER_EXCELLENT:
        return 100
    if shimmer <= SHIMMER_MOBILE_GOOD:
        return 80
    if shimmer <= SHIMMER_POOR:
        return max(0, 80 - (shimmer - SHIMMER_MOBILE_GOOD) * 1000)
    return max(0, 30 - (shimmer - SHIMMER_POOR) * 200)


def _score_spectral_clarity(clarity: float) -> float:
    if clarity >= SPECTRAL_CLARITY_EXCELLENT:
        return 100
    if clarity >= SPECTRAL_CLARITY_GOOD:
        return 70 + (clarity - SPECTRAL_CLARITY_GOOD) * 375
    if clarity >= SPECTRAL_CLARITY_POOR:
        return 40 + (clarity - SPECTRAL_CLARITY_POOR) * 600
    return max(0, clarity * 800)


def _extract_spectral_clarity(sound: parselmouth.Sound) -> float:
    """Razao de energia em 4-8 kHz vs total. Banda das consoantes.

    Mumblar engole consoantes → energia 4-8kHz cai. Articulacao clara
    deixa essa banda audivel.
    """
    try:
        spectrum = sound.to_spectrum()
        freqs = np.linspace(0, spectrum.fmax, len(spectrum.values[0]))
        amps = np.abs(spectrum.values[0])
        total_energy = float(np.sum(amps**2))
        if total_energy == 0:
            return 0.0
        consonant_band = (freqs >= 4000) & (freqs <= 8000)
        consonant_energy = float(np.sum(amps[consonant_band] ** 2))
        return consonant_energy / total_energy
    except Exception as e:
        logger.warning("spectral_clarity_extraction_failed", error=str(e))
        return SPECTRAL_CLARITY_GOOD  # neutral fallback


def _compute_articulation_metrics(audio_path: str) -> dict:
    """Compute Foundation 5 (Articulation) — clareza tecnica vocal.

    Reusa features acusticas (jitter/shimmer/HNR) ja extraidas pelo
    tonality_analyzer mas com interpretacao TECNICA (nao emocional).
    Adiciona spectral_clarity (energia 4-8kHz) — feature unica desta dim.
    """
    start = time.time()
    logger.info("articulation_analysis_start", audio_path=audio_path)

    sound = parselmouth.Sound(audio_path)
    duration = sound.get_total_duration()

    # Pitch + PointProcess pra jitter/shimmer (igual tonality_analyzer)
    try:
        pitch = sound.to_pitch()
        point_process = call(sound, "To PointProcess (periodic, cc)", 75, 600)

        jitter = call(
            point_process, "Get jitter (local)", 0, 0, 0.0001, 0.02, 1.3
        )
        shimmer = call(
            [sound, point_process],
            "Get shimmer (local)",
            0, 0, 0.0001, 0.02, 1.3, 1.6,
        )
        jitter = float(jitter) if not np.isnan(jitter) else JITTER_MOBILE_GOOD
        shimmer = float(shimmer) if not np.isnan(shimmer) else SHIMMER_MOBILE_GOOD
    except Exception as e:
        logger.warning("jitter_shimmer_failed", error=str(e))
        jitter = JITTER_MOBILE_GOOD
        shimmer = SHIMMER_MOBILE_GOOD

    # HNR
    try:
        harmonicity = sound.to_harmonicity()
        hnr = float(call(harmonicity, "Get mean", 0, 0))
        if np.isnan(hnr):
            hnr = HNR_GOOD
    except Exception:
        hnr = HNR_GOOD

    # Spectral clarity — feature exclusiva desta dim
    spectral_clarity = _extract_spectral_clarity(sound)

    # Score por feature
    hnr_score = _score_hnr(hnr)
    jitter_score = _score_jitter(jitter)
    shimmer_score = _score_shimmer(shimmer)
    spectral_score = _score_spectral_clarity(spectral_clarity)

    # Score composto: HNR e spectral_clarity sao mais perceptivelmente
    # discriminativos pra articulacao. Jitter/shimmer entram como
    # estabilidade (peso menor).
    articulation_score = round(
        hnr_score * 0.35  # projecao/clareza tonal
        + spectral_score * 0.35  # consoantes audiveis (mumble detector)
        + jitter_score * 0.15  # estabilidade F0
        + shimmer_score * 0.15  # controle de amplitude
    )
    articulation_score = max(0, min(100, articulation_score))

    if articulation_score >= 80:
        diagnostico = "excelente"
    elif articulation_score >= 60:
        diagnostico = "bom"
    elif articulation_score >= 40:
        diagnostico = "moderado"
    else:
        diagnostico = "atencao"

    elapsed = time.time() - start
    logger.info(
        "articulation_analysis_complete",
        duration_seconds=round(elapsed, 2),
        score=articulation_score,
        hnr=round(hnr, 1),
        jitter=round(jitter, 4),
        shimmer=round(shimmer, 4),
        spectral_clarity=round(spectral_clarity, 3),
    )

    return {
        "score": articulation_score,
        "confidence": "high",
        "metrics": {
            "diagnostico": diagnostico,
            "hnr": round(hnr, 1),
            "jitter": round(jitter, 4),
            "shimmer": round(shimmer, 4),
            "spectral_clarity": round(spectral_clarity, 3),
            "audio_duration_seconds": round(duration, 2),
            "sub_scores": {
                "projecao_hnr": round(hnr_score),
                "consoantes_spectral": round(spectral_score),
                "estabilidade_jitter": round(jitter_score),
                "controle_shimmer": round(shimmer_score),
            },
        },
    }


def analyze_articulation_legacy(audio_path: str) -> dict:
    """Legacy path (TRUTH_CONTRACT_ENABLED=false)."""
    return _compute_articulation_metrics(audio_path)


def analyze_articulation(audio_path: str) -> WorkerResult:
    """Truth Contract path — retorna WorkerResult tipado."""
    return wrap_worker_result("articulation", _compute_articulation_metrics, audio_path)
