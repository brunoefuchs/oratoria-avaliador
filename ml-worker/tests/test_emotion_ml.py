"""Tests for workers._emotion_ml — Story 9.3.

Mockado — nao instala transformers/torch reais.
Valida:
- load_wav2vec2_emotion retorna None sem lib
- infer_emotions computa VAD ponderado correto
- Mapeamento EMOTION_TO_VAD cobre labels esperados
- Factory no MODEL_FACTORIES funciona + tonality_analyzer integration flag-aware
"""

from __future__ import annotations

import importlib
import sys
from unittest.mock import MagicMock, patch

import pytest

from workers._emotion_ml import (
    EMOTION_TO_VAD,
    MODEL_ID,
    infer_emotions,
    load_wav2vec2_emotion,
)

# ─────────────────────────────────────────────────────────────
# Constants + mapping
# ─────────────────────────────────────────────────────────────


def test_model_id_is_base_superb():
    assert MODEL_ID == "facebook/wav2vec2-base-superb-er"


def test_emotion_to_vad_covers_core_labels():
    required = {"neu", "hap", "sad", "ang", "fea", "sur"}
    assert required.issubset(set(EMOTION_TO_VAD.keys()))


def test_emotion_to_vad_values_normalized():
    for _label, vad in EMOTION_TO_VAD.items():
        for dim in ("valence", "arousal", "dominance"):
            assert dim in vad
            assert 0.0 <= vad[dim] <= 1.0


# ─────────────────────────────────────────────────────────────
# load_wav2vec2_emotion
# ─────────────────────────────────────────────────────────────


def test_load_returns_none_without_transformers(monkeypatch):
    """Lib ausente → None (graceful fallback)."""
    monkeypatch.setitem(sys.modules, "transformers", None)
    result = load_wav2vec2_emotion()
    assert result is None


# ─────────────────────────────────────────────────────────────
# infer_emotions
# ─────────────────────────────────────────────────────────────


def test_infer_emotions_returns_none_if_bundle_none():
    result = infer_emotions(None, "/fake/audio.wav")
    assert result is None


def test_infer_emotions_computes_vad_correctly():
    """Bundle mockado retorna distribuicao; VAD derivado deve ser ponderado."""
    # Setup: fake librosa (audio dummy)
    fake_librosa = MagicMock()

    import numpy as np

    fake_librosa.load.return_value = (np.zeros(16000, dtype=np.float32), 16000)

    # Setup: fake torch
    fake_torch = MagicMock()
    fake_logits = MagicMock()
    fake_model_output = MagicMock()
    fake_model_output.logits = fake_logits

    # Distribuicao: 80% hap, 20% neu
    # VAD esperado: valence = 0.85*0.8 + 0.5*0.2 = 0.78, arousal = 0.75*0.8 + 0.3*0.2 = 0.66
    fake_probs = np.array([0.8, 0.2], dtype=np.float32)
    fake_probs_tensor = MagicMock()
    fake_probs_tensor.__getitem__ = lambda self, i: MagicMock(item=lambda: fake_probs[i])
    fake_probs_tensor.__iter__ = lambda self: iter(
        [MagicMock(item=lambda p=fake_probs[i]: p) for i in range(2)]
    )

    fake_torch.nn.functional.softmax.return_value = [fake_probs_tensor]
    fake_torch.no_grad.return_value.__enter__ = lambda self: None
    fake_torch.no_grad.return_value.__exit__ = lambda self, *args: None

    # Setup: bundle
    fake_fe = MagicMock(return_value={"input_values": MagicMock()})
    fake_model = MagicMock(return_value=fake_model_output)

    bundle = {
        "model": fake_model,
        "feature_extractor": fake_fe,
        "id2label": {0: "hap", 1: "neu"},
    }

    with patch.dict(sys.modules, {"librosa": fake_librosa, "torch": fake_torch}):
        result = infer_emotions(bundle, "/fake/audio.wav")

    assert result is not None
    assert result["model_id"] == MODEL_ID
    assert result["emocao_dominante_ml"] == "hap"
    # VAD deve estar ponderado (valence alto pra hap)
    assert result["vad_ml"]["valence"] > 0.7
    assert "emocao_distribuicao_ml" in result
    assert len(result["emocao_distribuicao_ml"]) == 2


def test_infer_emotions_handles_exception():
    """Exception em inferencia → None + log warning (nao crash)."""
    # Bundle com feature_extractor que raise
    bundle = {
        "model": MagicMock(),
        "feature_extractor": MagicMock(side_effect=RuntimeError("simulated")),
        "id2label": {0: "neu"},
    }

    fake_librosa = MagicMock()
    import numpy as np

    fake_librosa.load.return_value = (np.zeros(16000), 16000)

    with patch.dict(sys.modules, {"librosa": fake_librosa, "torch": MagicMock()}):
        result = infer_emotions(bundle, "/fake/audio.wav")

    assert result is None


# ─────────────────────────────────────────────────────────────
# Factory integration
# ─────────────────────────────────────────────────────────────


def test_factory_in_registry_not_stub():
    """Story 9.3: wav2vec2_emotion nao eh mais NotImplementedError stub."""
    from workers._model_loader import MODEL_FACTORIES

    factory = MODEL_FACTORIES["wav2vec2_emotion"]
    # Se transformers ausente, deve raise RuntimeError (nao NotImplementedError)
    with patch("workers._emotion_ml.load_wav2vec2_emotion", return_value=None):
        with pytest.raises(RuntimeError, match="indisponivel"):
            factory()


# ─────────────────────────────────────────────────────────────
# Flag integration
# ─────────────────────────────────────────────────────────────


def test_flag_off_by_default(monkeypatch):
    monkeypatch.delenv("TONALITY_ML_ENABLED", raising=False)
    import config

    importlib.reload(config)
    assert config.is_tonality_ml_enabled() is False


def test_flag_on_with_env(monkeypatch):
    monkeypatch.setenv("TONALITY_ML_ENABLED", "true")
    import config

    importlib.reload(config)
    assert config.is_tonality_ml_enabled() is True
