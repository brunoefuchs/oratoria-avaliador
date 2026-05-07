"""WavLM-base+ Feature Extractor (Story 10.1 — Path 1 v2).

Infra-only: extrai embeddings prosódicos via layers 3-10 weighted-sum.
NÃO substitui wav2vec2-emotion pra classification (sem classifier head
drop-in pra PT/EN — descoberto no Pre-Flight 2026-05-06).

Clientes planejados (Epic 11+):
- vocal_resonance dim (Roger Love gap competitivo)
- speaker style features
- Custom VAD head treinado em GT próprio

Layer recipe (research wave 2026-05-06, 04-deep-read):
- Layers 3-10 (de 12 total no base+) cobrem prosódia/voice quality
- Weighted-sum learnable: weights = softmax(nn.Parameter(torch.ones(8)))
- Pool temporal: mean-pooling sobre tempo após weighted-sum

Modelo: microsoft/wavlm-base-plus (~400MB, 94M params)
NUNCA usar checkpoints ASR-fine-tuned (degradam prosódia).
"""

from __future__ import annotations

from typing import Any

import structlog

logger = structlog.get_logger()


MODEL_ID = "microsoft/wavlm-base-plus"
LAYER_START = 3  # inclusive
LAYER_END = 10  # inclusive (8 layers total)
N_LAYERS = LAYER_END - LAYER_START + 1
HIDDEN_SIZE = 768  # base+ hidden_size

# VRAM target conservador — base+ é ~400MB peso, +ativações ~150MB
# Margem confortável vs RTX 4060 8.6GB
VRAM_PEAK_TARGET_GB = 0.5


def load_wavlm_emotion() -> dict[str, Any] | None:
    """Factory pra MODEL_FACTORIES — carrega WavLM-base+.

    Returns:
        {"model": model, "feature_extractor": fe, "layer_weights": Parameter}
        ou None se transformers não instalado / erro de download.

    Raises:
        RuntimeError: se modelo carregado for ASR-fine-tuned (CTC head detected).
    """
    try:
        import torch
        import torch.nn as nn
        from transformers import AutoFeatureExtractor, AutoModel
    except ImportError:
        logger.warning(
            "transformers_or_torch_not_installed_for_wavlm",
            hint="pip install transformers torch",
        )
        return None

    try:
        # output_hidden_states=True ativa todas as 13 hidden states (embedding + 12 layers)
        model = AutoModel.from_pretrained(MODEL_ID, output_hidden_states=True)

        # Reject ASR-tuned checkpoints — research wave 04-deep-read:
        # "Fine-tuning ASRs does not facilitate the downstream speech emotion
        # recognition task, indicating a loss of prosodic information during
        # ASR fine-tuning."
        model_class = type(model).__name__
        if "CTC" in model_class or "ForCTC" in model_class:
            raise RuntimeError(
                f"Refusing ASR-fine-tuned checkpoint: {model_class}. "
                f"Use base SSL model only ({MODEL_ID})."
            )

        feature_extractor = AutoFeatureExtractor.from_pretrained(MODEL_ID)
        model.eval()

        # Weighted-sum learnable sobre layers 3-10 (8 layers)
        # Inicializa uniforme (1/8 cada) — softmax aplicado na forward.
        layer_weights = nn.Parameter(torch.ones(N_LAYERS))

        logger.info(
            "wavlm_emotion_loaded",
            model_id=MODEL_ID,
            model_class=model_class,
            n_layers=N_LAYERS,
            layer_range=f"{LAYER_START}-{LAYER_END}",
        )

        return {
            "model": model,
            "feature_extractor": feature_extractor,
            "layer_weights": layer_weights,
            "model_id": MODEL_ID,
        }
    except Exception as e:  # noqa: BLE001
        logger.warning(
            "wavlm_load_failed",
            model_id=MODEL_ID,
            error=str(e),
            error_type=type(e).__name__,
        )
        return None


def extract_features(bundle: dict, audio_path: str):
    """Extrai embedding prosódico (768,) via layers 3-10 weighted-sum.

    Args:
        bundle: dict retornado por load_wavlm_emotion()
        audio_path: caminho .wav (16kHz mono recomendado)

    Returns:
        torch.Tensor shape (HIDDEN_SIZE,) ou None em caso de NaN/Inf detectado.
    """
    try:
        import librosa
        import torch
    except ImportError:
        logger.warning("librosa_or_torch_missing_for_wavlm_extract")
        return None

    try:
        audio, sr = librosa.load(audio_path, sr=16000, mono=True)
        if len(audio) == 0:
            logger.warning("wavlm_empty_audio", audio_path=audio_path)
            return None

        inputs = bundle["feature_extractor"](
            audio,
            sampling_rate=16000,
            return_tensors="pt",
        )

        with torch.no_grad():
            outputs = bundle["model"](**inputs, output_hidden_states=True)

        # outputs.hidden_states é tuple de 13 tensors (embedding + 12 layers)
        # Index 0 = embedding inicial, 1-12 = layers 1-12.
        # Pegamos LAYER_START..LAYER_END inclusive.
        hidden = outputs.hidden_states  # tuple len=13
        if len(hidden) < LAYER_END + 1:
            logger.warning(
                "wavlm_unexpected_layer_count",
                expected_min=LAYER_END + 1,
                got=len(hidden),
            )
            return None

        # Stack: (N_LAYERS, batch=1, seq, 768)
        selected = torch.stack(hidden[LAYER_START : LAYER_END + 1])

        # Weighted-sum com softmax pra normalizar pesos
        weights = torch.softmax(bundle["layer_weights"], dim=0)
        # Broadcast: (N_LAYERS, 1, 1, 1) * (N_LAYERS, 1, T, 768) → soma sobre N_LAYERS
        weighted = (selected * weights.view(-1, 1, 1, 1)).sum(dim=0)  # (1, T, 768)

        # Pool temporal: mean sobre dimensão tempo
        pooled = weighted.mean(dim=1).squeeze(0)  # (768,)

        # NaN/Inf guards
        if torch.isnan(pooled).any() or torch.isinf(pooled).any():
            logger.warning(
                "wavlm_nan_or_inf_detected",
                audio_path=audio_path,
                has_nan=bool(torch.isnan(pooled).any()),
                has_inf=bool(torch.isinf(pooled).any()),
            )
            return None

        return pooled

    except Exception as e:  # noqa: BLE001
        logger.warning(
            "wavlm_extract_failed",
            audio_path=audio_path,
            error=str(e),
            error_type=type(e).__name__,
        )
        return None


def get_vram_peak_gb() -> float:
    """Retorna peak VRAM allocated em GB. Zero se CUDA não disponível."""
    try:
        import torch

        if not torch.cuda.is_available():
            return 0.0
        return torch.cuda.max_memory_allocated() / 1e9
    except Exception:  # noqa: BLE001
        return 0.0
