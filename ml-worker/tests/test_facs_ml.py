"""Tests for workers._facs_ml — Story 9.5.

Mockado — nao instala py-feat real.
Valida:
- Constants (RELEVANT_AUS, AU_TO_EMOTION coverage)
- load_pyfeat_detector retorna None sem lib
- detect_aus_in_frames com detector mockado
- Sampling uniforme de frames
- Mapeamento AU → 6 emoções
- Factory integration
"""

from __future__ import annotations

import importlib
import sys
from unittest.mock import MagicMock, patch

import pytest

from workers._facs_ml import (
    AU_TO_EMOTION,
    EMOCOES_BASICAS,
    RELEVANT_AUS,
    _sample_frames_uniform,
    detect_aus_in_frames,
    load_pyfeat_detector,
)

# ─────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────


def test_relevant_aus_count():
    assert len(RELEVANT_AUS) == 20
    assert "AU12" in RELEVANT_AUS  # Lip Corner Puller (sorriso)
    assert "AU06" in RELEVANT_AUS  # Cheek Raiser (Duchenne marker)


def test_emocoes_basicas_ekman():
    assert set(EMOCOES_BASICAS) == {"alegria", "tristeza", "raiva", "surpresa", "nojo", "medo"}


def test_au_to_emotion_core_mappings():
    """AU12 → alegria, AU09 → nojo, AU20 → medo (Ekman canonical)."""
    assert AU_TO_EMOTION["AU12"]["alegria"] > 0
    assert AU_TO_EMOTION["AU09"]["nojo"] > 0
    assert AU_TO_EMOTION["AU20"]["medo"] > 0
    assert AU_TO_EMOTION["AU15"]["tristeza"] > 0


def test_au_to_emotion_values_valid():
    for _au, mapping in AU_TO_EMOTION.items():
        for emo, weight in mapping.items():
            assert emo in EMOCOES_BASICAS
            assert 0.0 <= weight <= 1.0


# ─────────────────────────────────────────────────────────────
# Frame sampling
# ─────────────────────────────────────────────────────────────


def test_sample_frames_small_returns_all():
    assert _sample_frames_uniform(20, max_frames=60) == list(range(20))


def test_sample_frames_large_caps_at_max():
    result = _sample_frames_uniform(600, max_frames=60)
    assert len(result) == 60
    assert result[0] == 0
    assert result[-1] < 600


def test_sample_frames_uniform_distribution():
    """Step uniforme cobre range inteiro."""
    result = _sample_frames_uniform(360, max_frames=60)
    assert len(result) == 60
    # Primeiro frame proximo a 0, ultimo proximo a 360
    assert result[0] == 0
    assert result[-1] > 300


# ─────────────────────────────────────────────────────────────
# load_pyfeat_detector
# ─────────────────────────────────────────────────────────────


def test_load_returns_none_without_pyfeat(monkeypatch):
    monkeypatch.setitem(sys.modules, "feat", None)
    result = load_pyfeat_detector()
    assert result is None


# ─────────────────────────────────────────────────────────────
# detect_aus_in_frames
# ─────────────────────────────────────────────────────────────


def test_detect_returns_none_if_detector_none():
    assert detect_aus_in_frames(None, ["/fake/f1.jpg"]) is None


def test_detect_returns_none_if_empty_frames():
    fake_detector = MagicMock()
    assert detect_aus_in_frames(fake_detector, []) is None


def test_detect_aus_aggregates_correctly():
    """Mock detector.detect_image retorna DataFrame-like com AU12 alto."""
    fake_detector = MagicMock()

    # Mock Fex (DataFrame) com AU12 alta intensidade media
    fake_fex = MagicMock()
    fake_fex.columns = ["AU06", "AU12", "AU04", "AU20"]

    def column_access(col):
        col_mock = MagicMock()
        if col == "AU12":
            col_mock.mean.return_value = 0.8  # alegria alta
            col_mock.__gt__ = lambda self, threshold: MagicMock(sum=lambda: 15)  # >0.3 em 15 frames
        elif col == "AU06":
            col_mock.mean.return_value = 0.6
            col_mock.__gt__ = lambda self, threshold: MagicMock(sum=lambda: 10)
        else:
            col_mock.mean.return_value = 0.1
            col_mock.__gt__ = lambda self, threshold: MagicMock(sum=lambda: 2)
        return col_mock

    fake_fex.__getitem__ = lambda self, col: column_access(col)
    fake_detector.detect_image.return_value = fake_fex

    frame_paths = [f"/fake/frame_{i:04d}.jpg" for i in range(30)]
    result = detect_aus_in_frames(fake_detector, frame_paths)

    assert result is not None
    assert "au_detection" in result
    assert result["au_detection"]["AU12"] == 0.8
    # AU12 + AU06 ativos → alegria deve dominar
    assert result["emocao_dominante_facial"] == "alegria"
    assert len(result["emocao_distribuicao_facial"]) == 6
    assert set(result["emocao_distribuicao_facial"].keys()) == set(EMOCOES_BASICAS)


def test_detect_handles_inference_exception():
    """Exception em detect_image → None + log (nao crash)."""
    fake_detector = MagicMock()
    fake_detector.detect_image.side_effect = RuntimeError("simulated")

    result = detect_aus_in_frames(fake_detector, ["/fake/f.jpg"])
    assert result is None


# ─────────────────────────────────────────────────────────────
# Factory integration
# ─────────────────────────────────────────────────────────────


def test_pyfeat_factory_in_registry():
    """Story 9.5: pyfeat factory nao eh mais NotImplementedError stub."""
    from workers._model_loader import MODEL_FACTORIES

    factory = MODEL_FACTORIES["pyfeat"]

    # Sem lib → RuntimeError "indisponivel"
    with patch("workers._facs_ml.load_pyfeat_detector", return_value=None):
        with pytest.raises(RuntimeError, match="indisponivel"):
            factory()


# ─────────────────────────────────────────────────────────────
# Flag integration
# ─────────────────────────────────────────────────────────────


def test_flag_off_by_default(monkeypatch):
    monkeypatch.delenv("PYFEAT_ENABLED", raising=False)
    import config

    importlib.reload(config)
    assert config.is_pyfeat_enabled() is False


def test_flag_on_with_env(monkeypatch):
    monkeypatch.setenv("PYFEAT_ENABLED", "true")
    import config

    importlib.reload(config)
    assert config.is_pyfeat_enabled() is True
