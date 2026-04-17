"""Tests for voice_analyzer Whisper turbo + fallback — Story 9.2 AC1, AC2."""

from __future__ import annotations

import importlib
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def voice_analyzer_turbo_on(monkeypatch):
    monkeypatch.setenv("WHISPER_TURBO_ENABLED", "true")
    monkeypatch.delenv("WHISPER_MODEL", raising=False)
    import workers.voice_analyzer as va

    importlib.reload(va)
    return va


@pytest.fixture
def voice_analyzer_turbo_off(monkeypatch):
    monkeypatch.setenv("WHISPER_TURBO_ENABLED", "false")
    monkeypatch.delenv("WHISPER_MODEL", raising=False)
    import workers.voice_analyzer as va

    importlib.reload(va)
    return va


@pytest.fixture
def voice_analyzer_env_override(monkeypatch):
    monkeypatch.setenv("WHISPER_TURBO_ENABLED", "true")
    monkeypatch.setenv("WHISPER_MODEL", "base")
    import workers.voice_analyzer as va

    importlib.reload(va)
    return va


# ─────────────────────────────────────────────────────────────
# AC1 — Model resolution
# ─────────────────────────────────────────────────────────────


def test_ac1_explicit_model_wins(voice_analyzer_turbo_on):
    assert voice_analyzer_turbo_on._resolve_whisper_model("large-v3") == "large-v3"


def test_ac1_flag_on_selects_turbo(voice_analyzer_turbo_on):
    assert voice_analyzer_turbo_on._resolve_whisper_model() == "turbo"


def test_ac1_flag_off_selects_medium(voice_analyzer_turbo_off):
    assert voice_analyzer_turbo_off._resolve_whisper_model() == "medium"


def test_ac1_env_override_wins_over_flag(voice_analyzer_env_override):
    assert voice_analyzer_env_override._resolve_whisper_model() == "base"


# ─────────────────────────────────────────────────────────────
# AC2 — Fallback automatico
# ─────────────────────────────────────────────────────────────


def test_ac2_turbo_load_success(voice_analyzer_turbo_on):
    fake_model = MagicMock()
    with patch("workers.voice_analyzer.whisper.load_model", return_value=fake_model) as mock_load:
        result = voice_analyzer_turbo_on._load_whisper_with_fallback("turbo")
        assert result is fake_model
        mock_load.assert_called_once_with("turbo")


def test_ac2_turbo_fails_fallback_to_medium(voice_analyzer_turbo_on, caplog):
    fake_medium = MagicMock(name="medium_model")

    call_count = {"n": 0}

    def flaky_load(name):
        call_count["n"] += 1
        if name == "turbo":
            raise RuntimeError("simulated turbo OOM")
        return fake_medium

    with patch("workers.voice_analyzer.whisper.load_model", side_effect=flaky_load):
        result = voice_analyzer_turbo_on._load_whisper_with_fallback("turbo")
        assert result is fake_medium
        assert call_count["n"] == 2


def test_ac2_medium_failure_propagates(voice_analyzer_turbo_on):
    """Se ja estamos no fallback medium e ele falha, raise — sem recurso."""
    with patch(
        "workers.voice_analyzer.whisper.load_model",
        side_effect=RuntimeError("medium broken"),
    ):
        with pytest.raises(RuntimeError, match="medium broken"):
            voice_analyzer_turbo_on._load_whisper_with_fallback("medium")
