"""Wav2Vec2-Emotion inference — Story 9.3 (Epic 9).

Carrega modelo facebook/wav2vec2-base-superb-er (~400MB) e infere 6 emoções
discretas (anger/happy/sad/neutral/surprise/fear). Mapeamento pra VAD
(Valence/Arousal/Dominance) via tabela academica.

Uso:
    bundle = load_wav2vec2_emotion()  # carregado via ModelGPU factory
    result = infer_emotions(bundle, audio_path)
    # result = {"vad_ml": {...}, "emocao_distribuicao_ml": {...}}

Lib opcional: pip install -e ".[emotion]" (transformers>=4.40).
Lazy imports + graceful fallback se lib ausente.

Modelo: `facebook/wav2vec2-base-superb-er` (~400MB, 6 emoções discretas)
Alternativa: `audeering/wav2vec2-large-robust-12-ft-emotion-msp-dim` (VAD contínuo).
Base model escolhido no Pre-Flight @dev (conservador + cabe em 8.6GB).
"""

from __future__ import annotations

from typing import Any

import structlog

logger = structlog.get_logger()

MODEL_ID = "superb/wav2vec2-base-superb-er"

# Mapeamento emocao → VAD (Russell circumplex model + Ekman FACS cross-ref).
# Valores normalizados [0, 1] baseados em literatura:
# - Russell (1980) - A circumplex model of affect
# - Mehrabian (1996) - Pleasure-Arousal-Dominance (PAD) space
EMOTION_TO_VAD: dict[str, dict[str, float]] = {
    "neu": {"valence": 0.5, "arousal": 0.3, "dominance": 0.5},
    "hap": {"valence": 0.85, "arousal": 0.75, "dominance": 0.7},
    "sad": {"valence": 0.2, "arousal": 0.25, "dominance": 0.25},
    "ang": {"valence": 0.15, "arousal": 0.9, "dominance": 0.75},
    "fea": {"valence": 0.2, "arousal": 0.85, "dominance": 0.2},
    "sur": {"valence": 0.6, "arousal": 0.8, "dominance": 0.5},
    # Aliases em ingles completo (alguns modelos usam full names)
    "neutral": {"valence": 0.5, "arousal": 0.3, "dominance": 0.5},
    "happy": {"valence": 0.85, "arousal": 0.75, "dominance": 0.7},
    "sadness": {"valence": 0.2, "arousal": 0.25, "dominance": 0.25},
    "anger": {"valence": 0.15, "arousal": 0.9, "dominance": 0.75},
    "fear": {"valence": 0.2, "arousal": 0.85, "dominance": 0.2},
    "surprise": {"valence": 0.6, "arousal": 0.8, "dominance": 0.5},
}


def load_wav2vec2_emotion() -> dict[str, Any] | None:
    """Factory pra MODEL_FACTORIES. Retorna bundle com model + feature_extractor.

    Returns:
        {"model": model, "feature_extractor": fe, "id2label": dict} ou None se
        lib transformers ausente.
    """
    try:
        from transformers import AutoFeatureExtractor, AutoModelForAudioClassification
    except ImportError:
        logger.warning(
            "transformers_not_installed",
            hint="pip install -e '.[emotion]' OR pip install transformers",
        )
        return None

    try:
        model = AutoModelForAudioClassification.from_pretrained(MODEL_ID)
        feature_extractor = AutoFeatureExtractor.from_pretrained(MODEL_ID)
        model.eval()
        return {
            "model": model,
            "feature_extractor": feature_extractor,
            "id2label": model.config.id2label,
        }
    except Exception as e:  # noqa: BLE001
        logger.warning(
            "wav2vec2_load_failed", model_id=MODEL_ID, error=str(e), error_type=type(e).__name__
        )
        return None


def _load_audio_mono_16khz(audio_path: str):
    """Carrega audio como waveform 16kHz mono (exigido pelo Wav2Vec2)."""
    import librosa

    audio, sr = librosa.load(audio_path, sr=16000, mono=True)
    return audio, sr


def infer_emotions(bundle: dict[str, Any], audio_path: str) -> dict[str, Any] | None:
    """Inferencia emocional via Wav2Vec2. Retorna distribuicao + VAD derivado.

    Returns:
        {
            "vad_ml": {"valence", "arousal", "dominance"},
            "emocao_distribuicao_ml": {label: prob, ...},
            "emocao_dominante_ml": str,
            "model_id": str,
        }
        ou None se bundle invalido / erro inferencia.
    """
    if bundle is None:
        return None

    try:
        import torch
    except ImportError:
        return None

    try:
        audio, sr = _load_audio_mono_16khz(audio_path)
        inputs = bundle["feature_extractor"](audio, sampling_rate=sr, return_tensors="pt")

        with torch.no_grad():
            outputs = bundle["model"](**inputs)
            logits = outputs.logits
            probs = torch.nn.functional.softmax(logits, dim=-1)[0]

        id2label = bundle["id2label"]
        distribution = {id2label[i]: float(probs[i].item()) for i in range(len(id2label))}

        dominante_label = max(distribution, key=distribution.get)

        # VAD ponderado pela distribuicao (media ponderada por probabilidade)
        vad = {"valence": 0.0, "arousal": 0.0, "dominance": 0.0}
        total_weight = 0.0
        for label, prob in distribution.items():
            label_lower = label.lower()
            if label_lower in EMOTION_TO_VAD:
                mapping = EMOTION_TO_VAD[label_lower]
                for k in vad:
                    vad[k] += mapping[k] * prob
                total_weight += prob

        if total_weight > 0:
            for k in vad:
                vad[k] = round(vad[k] / total_weight, 3)

        return {
            "vad_ml": vad,
            "emocao_distribuicao_ml": {k: round(v, 3) for k, v in distribution.items()},
            "emocao_dominante_ml": dominante_label,
            "model_id": MODEL_ID,
        }
    except Exception as e:  # noqa: BLE001
        logger.warning(
            "wav2vec2_inference_failed",
            audio_path=audio_path,
            error=str(e),
            error_type=type(e).__name__,
        )
        return None
