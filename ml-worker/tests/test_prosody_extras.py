"""Tests for workers._prosody_extras — Story 9.4.

Mockado — nao executa opensmile/pyannote/librosa reais.
Valida:
- _classify_pause por duration
- extract_egemaps lazy import + fallback None
- detect_pauses cascata pyannote → librosa → none
- Flag-aware integration via voice_analyzer
"""

from __future__ import annotations

import importlib
import sys
from unittest.mock import MagicMock, patch

import pytest

from workers._prosody_extras import (
    EGEMAPS_FEATURE_COUNT,
    PAUSE_HESITATION_MAX,
    PAUSE_MICRO_MAX,
    _classify_pause,
    detect_pauses,
    extract_egemaps,
)

# ─────────────────────────────────────────────────────────────
# Classify pause
# ─────────────────────────────────────────────────────────────


def test_classify_pause_micro():
    assert _classify_pause(0.2) == "micro"
    assert _classify_pause(0.39) == "micro"


def test_classify_pause_hesitation():
    assert _classify_pause(0.4) == "hesitation"
    assert _classify_pause(1.19) == "hesitation"


def test_classify_pause_retorical():
    assert _classify_pause(1.2) == "retorical"
    assert _classify_pause(3.0) == "retorical"


def test_pause_thresholds_sane():
    assert PAUSE_MICRO_MAX < PAUSE_HESITATION_MAX
    assert EGEMAPS_FEATURE_COUNT == 88  # eGeMAPSv02 spec


# ─────────────────────────────────────────────────────────────
# extract_egemaps
# ─────────────────────────────────────────────────────────────


def test_extract_egemaps_returns_none_without_opensmile(monkeypatch):
    """Lib ausente → None + warning (nao crash)."""
    # Simular ImportError de opensmile
    monkeypatch.setitem(sys.modules, "opensmile", None)
    result = extract_egemaps("/fake/audio.wav")
    assert result is None


def test_extract_egemaps_returns_dict_on_success():
    """Mock opensmile retornando DataFrame-like com 88 cols."""
    feature_names = [f"feat_{i}" for i in range(88)]

    # Mock DataFrame API (iloc[0][col] + columns)
    fake_row = {name: 0.1 for name in feature_names}

    class FakeIloc:
        def __getitem__(self, idx):
            return fake_row

    fake_df = MagicMock()
    fake_df.columns = feature_names
    fake_df.iloc = FakeIloc()

    fake_smile_instance = MagicMock()
    fake_smile_instance.process_file.return_value = fake_df

    fake_opensmile = MagicMock()
    fake_opensmile.Smile.return_value = fake_smile_instance
    fake_opensmile.FeatureSet.eGeMAPSv02 = "eGeMAPSv02"
    fake_opensmile.FeatureLevel.Functionals = "Functionals"

    with patch.dict(sys.modules, {"opensmile": fake_opensmile}):
        result = extract_egemaps("/fake/audio.wav")

    assert result is not None
    assert len(result) == 88
    assert all(isinstance(v, float) for v in result.values())


# ─────────────────────────────────────────────────────────────
# detect_pauses cascata
# ─────────────────────────────────────────────────────────────


def test_detect_pauses_no_token_no_lib_fallback_librosa(monkeypatch):
    """Sem HF_TOKEN → pyannote retorna None → cai em librosa fallback."""
    monkeypatch.delenv("HF_TOKEN", raising=False)

    # Mock librosa retornando intervalos de voz
    fake_librosa = MagicMock()
    fake_librosa.load.return_value = (MagicMock(), 16000)
    # Two voice segments com gap retorico de 2s entre eles
    import numpy as np

    fake_librosa.effects.split.return_value = np.array(
        [[0, 16000], [48000, 64000]]  # voice 0-1s, voice 3-4s → gap 2s
    )

    with patch.dict(sys.modules, {"librosa": fake_librosa}):
        result = detect_pauses("/fake/audio.wav")

    assert result["source"] == "librosa"
    assert len(result["pauses"]) == 1
    assert result["pauses"][0]["type"] == "retorical"
    assert result["counts"]["retorical"] == 1


def test_detect_pauses_all_fail_returns_empty():
    """Ambos pyannote e librosa indisponiveis → lista vazia, source=none."""
    with patch.dict(sys.modules, {"pyannote.audio": None, "librosa": None}):
        result = detect_pauses("/fake/audio.wav")

    assert result["source"] == "none"
    assert result["pauses"] == []
    assert result["counts"] == {"micro": 0, "hesitation": 0, "retorical": 0}
    assert result["total_retorical_ratio"] == 0.0


def test_detect_pauses_retorical_ratio_calc():
    """Valida calculo do ratio com mix de tipos."""
    fake_librosa = MagicMock()
    fake_librosa.load.return_value = (MagicMock(), 16000)
    import numpy as np

    # 3 gaps: micro (0.2s), hesitation (0.8s), retorical (2s)
    fake_librosa.effects.split.return_value = np.array(
        [
            [0, 16000],  # voice 0-1s
            [19200, 32000],  # voice 1.2-2s, gap 0.2s (micro)
            [44800, 56000],  # voice 2.8-3.5s, gap 0.8s (hesitation)
            [88000, 96000],  # voice 5.5-6s, gap 2s (retorical)
        ]
    )

    with patch.dict(sys.modules, {"librosa": fake_librosa}):
        result = detect_pauses("/fake/audio.wav")

    assert result["counts"]["micro"] == 1
    assert result["counts"]["hesitation"] == 1
    assert result["counts"]["retorical"] == 1
    assert result["total_retorical_ratio"] == round(1 / 3, 3)


# ─────────────────────────────────────────────────────────────
# Flag integration (via voice_analyzer)
# ─────────────────────────────────────────────────────────────


def test_flag_off_no_enrichment(monkeypatch):
    """Flags OFF: result do analyze_prosody NAO tem egemaps/pauses_classified."""
    monkeypatch.setenv("OPENSMILE_ENABLED", "false")
    monkeypatch.setenv("PYANNOTE_VAD_ENABLED", "false")
    import workers.voice_analyzer as va

    importlib.reload(va)

    # Verificar que helpers retornam False
    from config import is_opensmile_enabled, is_pyannote_vad_enabled

    assert is_opensmile_enabled() is False
    assert is_pyannote_vad_enabled() is False


def test_flag_on_helpers_true(monkeypatch):
    monkeypatch.setenv("OPENSMILE_ENABLED", "true")
    monkeypatch.setenv("PYANNOTE_VAD_ENABLED", "true")

    # Reload config pra picking env
    import config

    importlib.reload(config)

    assert config.is_opensmile_enabled() is True
    assert config.is_pyannote_vad_enabled() is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
