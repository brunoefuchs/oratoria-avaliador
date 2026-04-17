"""py-feat FACS inference — Story 9.5 (Epic 9).

Detector SVM CPU-only do py-feat para 20 Action Units (FACS Ekman) + 6 emoções
básicas. Substitui as 3 heurísticas do facial_analyzer por medição científica.

Uso:
    detector = load_pyfeat_detector()
    result = detect_aus_in_frames(detector, frame_paths)
    # result = {"au_detection": {...}, "emocao_distribuicao_facial": {...}, ...}

Lib opcional: pip install -e ".[facs]". Lazy import + graceful fallback.

Modelo: py-feat `Detector` default (SVM + HOG) — CPU puro, zero VRAM.
Alternativa deep: `au_model="xgb"` ou deep CNN backbones (mais lento).
"""

from __future__ import annotations

from typing import Any

import structlog

logger = structlog.get_logger()

# AUs relevantes pra comunicacao (subset do FACS completo — 20 mais usadas).
# Fonte: Ekman, P. & Friesen, W. (1978) Facial Action Coding System Manual.
RELEVANT_AUS = [
    "AU01",  # Inner Brow Raiser
    "AU02",  # Outer Brow Raiser
    "AU04",  # Brow Lowerer
    "AU05",  # Upper Lid Raiser
    "AU06",  # Cheek Raiser (Duchenne marker)
    "AU07",  # Lid Tightener
    "AU09",  # Nose Wrinkler
    "AU10",  # Upper Lip Raiser
    "AU11",  # Nasolabial Deepener
    "AU12",  # Lip Corner Puller (sorriso real)
    "AU14",  # Dimpler
    "AU15",  # Lip Corner Depressor
    "AU17",  # Chin Raiser
    "AU20",  # Lip Stretcher
    "AU23",  # Lip Tightener
    "AU24",  # Lip Pressor
    "AU25",  # Lips Part
    "AU26",  # Jaw Drop
    "AU28",  # Lip Suck
    "AU43",  # Eyes Closed
]

# Mapeamento AU → 6 emocoes basicas de Ekman.
# Fonte: Ekman & Friesen (1978), Rosenberg & Ekman (2020) — AU combinations.
# Peso indica contribuicao relativa da AU para a emocao.
AU_TO_EMOTION: dict[str, dict[str, float]] = {
    # Alegria (Duchenne smile): AU06 + AU12 (marcador genuino)
    "AU06": {"alegria": 0.5},
    "AU12": {"alegria": 0.5},
    # Tristeza: AU01 + AU04 + AU15
    "AU01": {"tristeza": 0.35, "surpresa": 0.25, "medo": 0.15},
    "AU15": {"tristeza": 0.7},
    # Raiva: AU04 + AU05 + AU07 + AU23
    "AU04": {"raiva": 0.45, "tristeza": 0.3},
    "AU05": {"raiva": 0.3, "surpresa": 0.4, "medo": 0.15},
    "AU07": {"raiva": 0.55},
    "AU23": {"raiva": 0.6},
    # Surpresa: AU01 + AU02 + AU05 + AU25/26
    "AU02": {"surpresa": 0.55},
    "AU26": {"surpresa": 0.5},
    # Nojo: AU09 + AU10 + AU15
    "AU09": {"nojo": 0.7},
    "AU10": {"nojo": 0.45, "raiva": 0.2},
    # Medo: AU01 + AU02 + AU04 + AU05 + AU20
    "AU20": {"medo": 0.6},
    # Outros (contribuicao menor/indireta)
    "AU11": {"nojo": 0.15},
    "AU14": {"alegria": 0.2, "tristeza": 0.1},
    "AU17": {"tristeza": 0.3, "raiva": 0.2},
    "AU24": {"raiva": 0.35},
    "AU25": {"surpresa": 0.2},
    "AU28": {"tristeza": 0.15},
    "AU43": {},  # eyes closed — nao associada diretamente
}

EMOCOES_BASICAS = ("alegria", "tristeza", "raiva", "surpresa", "nojo", "medo")


def load_pyfeat_detector() -> Any:
    """Factory pra MODEL_FACTORIES. Carrega Detector default (SVM CPU)."""
    try:
        from feat import Detector
    except ImportError:
        logger.warning(
            "pyfeat_not_installed", hint="pip install -e '.[facs]' OR pip install py-feat"
        )
        return None

    try:
        # Default: face_model="retinaface", au_model="svm", emotion_model="resmasknet"
        detector = Detector(device="cpu")
        return detector
    except Exception as e:  # noqa: BLE001
        logger.warning("pyfeat_load_failed", error=str(e), error_type=type(e).__name__)
        return None


def _sample_frames_uniform(total_frames: int, max_frames: int = 60) -> list[int]:
    """Sampling uniforme para manter overhead controlado.

    Vídeo 3min @ 2fps = 360 frames. Processar todos em py-feat CPU = ~2min.
    Com max_frames=60, processa ~10% → overhead <=30s conforme AC6.
    """
    if total_frames <= max_frames:
        return list(range(total_frames))

    step = total_frames / max_frames
    return [int(i * step) for i in range(max_frames)]


def detect_aus_in_frames(detector: Any, frame_paths: list[str]) -> dict[str, Any] | None:
    """Roda py-feat em subset de frames + agrega AUs/emocoes.

    Args:
        detector: py-feat Detector
        frame_paths: lista de paths pra frames .jpg extraidos

    Returns:
        {
            "au_detection": {AU01: mean_intensity, ...},
            "emocao_distribuicao_facial": {alegria: prop, ...},
            "emocao_dominante_facial": str,
            "micro_expressions_count": int,
            "frames_processados": int,
        }
        ou None se detector invalido / erro total.
    """
    if detector is None or not frame_paths:
        return None

    indices = _sample_frames_uniform(len(frame_paths), max_frames=60)
    sampled_paths = [frame_paths[i] for i in indices]

    try:
        # py-feat retorna DataFrame com colunas AU01..AU45 + emotions
        fex = detector.detect_image(sampled_paths)
    except Exception as e:  # noqa: BLE001
        logger.warning("pyfeat_detection_failed", error=str(e), error_type=type(e).__name__)
        return None

    # Agregar AU mean intensities (0-1 normalizado)
    au_means: dict[str, float] = {}
    for au in RELEVANT_AUS:
        if au in fex.columns:
            try:
                au_means[au] = round(float(fex[au].mean()), 3)
            except Exception:  # noqa: BLE001
                au_means[au] = 0.0

    # Micro-expressions: AU detectada em >10% frames com intensidade >0.3
    n = max(1, len(sampled_paths))
    micro_count = 0
    for au, _intensity in au_means.items():
        if au in fex.columns:
            try:
                detected_pct = (fex[au] > 0.3).sum() / n
                if detected_pct > 0.1:
                    micro_count += 1
            except Exception:  # noqa: BLE001
                pass

    # Derivar distribuicao de emocoes via AU mapping
    emocao_scores = {emo: 0.0 for emo in EMOCOES_BASICAS}
    total_weight = 0.0
    for au, intensity in au_means.items():
        mapping = AU_TO_EMOTION.get(au, {})
        for emo, weight in mapping.items():
            if emo in emocao_scores:
                emocao_scores[emo] += intensity * weight
                total_weight += intensity * weight

    if total_weight > 0:
        for emo in emocao_scores:
            emocao_scores[emo] = round(emocao_scores[emo] / total_weight, 3)
    else:
        # Sem signal: tudo neutro (distribuir uniforme)
        for emo in emocao_scores:
            emocao_scores[emo] = round(1.0 / len(emocao_scores), 3)

    dominante = max(emocao_scores, key=emocao_scores.get)

    return {
        "au_detection": au_means,
        "emocao_distribuicao_facial": emocao_scores,
        "emocao_dominante_facial": dominante,
        "micro_expressions_count": micro_count,
        "frames_processados": len(sampled_paths),
    }
