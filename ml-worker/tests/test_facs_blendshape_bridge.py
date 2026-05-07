"""Tests Story 10.2 Fase 1 — Bridge MediaPipe blendshapes → AUs."""

from __future__ import annotations

import pytest

from workers._facs_blendshape_bridge import (
    AU_THRESHOLDS,
    CRITICAL_AUS,
    DUCHENNE_AU12_THRESHOLD,
    detect_active_aus,
    is_au_active,
    map_blendshape_csv_row,
    map_blendshapes_to_aus,
)


def test_module_constants():
    """Sanity: thresholds + critical AUs definidos."""
    assert "AU1" in AU_THRESHOLDS
    assert "AU45" in AU_THRESHOLDS
    assert len(CRITICAL_AUS) == 10
    assert CRITICAL_AUS == {"AU1", "AU2", "AU4", "AU5", "AU6", "AU7", "AU9", "AU12", "AU15", "AU45"}
    assert 0 < DUCHENNE_AU12_THRESHOLD < 1


def test_map_empty_dict_returns_zeros():
    """Dict vazio → todas AUs retornam 0.0 (sem KeyError)."""
    aus = map_blendshapes_to_aus({})
    assert all(v == 0.0 for v in aus.values())
    assert "AU1" in aus
    assert "AU45" in aus


def test_map_au1_inner_brow():
    """AU1 = browInnerUp."""
    bs = {"browInnerUp": 0.55}
    aus = map_blendshapes_to_aus(bs)
    assert aus["AU1"] == 0.55


def test_map_au2_outer_brow_average():
    """AU2 = avg(browOuterUpLeft, browOuterUpRight)."""
    bs = {"browOuterUpLeft": 0.4, "browOuterUpRight": 0.6}
    aus = map_blendshapes_to_aus(bs)
    assert aus["AU2"] == 0.5


def test_map_au12_smile():
    """AU12 = avg(mouthSmileL, mouthSmileR)."""
    bs = {"mouthSmileLeft": 0.7, "mouthSmileRight": 0.5}
    aus = map_blendshapes_to_aus(bs)
    assert aus["AU12"] == 0.6


def test_map_jaw_au26_vs_au27_threshold_split():
    """jawOpen baixo → AU26, jawOpen alto → AU27."""
    # jawOpen baixo (< 0.5) → AU26 ativo, AU27 zerado
    bs_low = {"jawOpen": 0.3}
    aus_low = map_blendshapes_to_aus(bs_low)
    assert aus_low["AU26"] == 0.3
    assert aus_low["AU27"] == 0.0

    # jawOpen alto (>= 0.5) → AU27 ativo, AU26 zerado
    bs_high = {"jawOpen": 0.7}
    aus_high = map_blendshapes_to_aus(bs_high)
    assert aus_high["AU26"] == 0.0
    assert aus_high["AU27"] == 0.7


def test_is_au_active_threshold():
    """is_au_active respeita threshold."""
    aus = {"AU1": 0.20}  # abaixo threshold 0.30
    assert is_au_active(aus, "AU1") is False

    aus = {"AU1": 0.45}  # acima threshold
    assert is_au_active(aus, "AU1") is True


def test_duchenne_cross_check_smile_required():
    """AU6 só ativa se AU12 (mouthSmile) também presente — Duchenne genuíno."""
    # Cheek squint forte SEM smile → não é Duchenne
    bs_no_smile = {"cheekSquintLeft": 0.8, "cheekSquintRight": 0.8, "mouthSmileLeft": 0.1, "mouthSmileRight": 0.1}
    aus = map_blendshapes_to_aus(bs_no_smile)
    assert aus["AU6"] == 0.8  # intensity alta
    assert is_au_active(aus, "AU6", blendshapes=bs_no_smile) is False  # mas não Duchenne

    # Cheek squint forte COM smile → Duchenne genuíno
    bs_with_smile = {"cheekSquintLeft": 0.8, "cheekSquintRight": 0.8, "mouthSmileLeft": 0.6, "mouthSmileRight": 0.6}
    aus = map_blendshapes_to_aus(bs_with_smile)
    assert is_au_active(aus, "AU6", blendshapes=bs_with_smile) is True


def test_au7_anti_blink():
    """AU7 NÃO ativa se eyeBlink simultâneo (blink mascara squint)."""
    # Squint forte + blink simultâneo → AU7 NÃO ativa
    bs_blink = {"eyeSquintLeft": 0.6, "eyeSquintRight": 0.6, "eyeBlinkLeft": 0.7, "eyeBlinkRight": 0.7}
    aus = map_blendshapes_to_aus(bs_blink)
    assert is_au_active(aus, "AU7", blendshapes=bs_blink) is False

    # Squint forte SEM blink → AU7 ativa
    bs_squint = {"eyeSquintLeft": 0.6, "eyeSquintRight": 0.6, "eyeBlinkLeft": 0.1, "eyeBlinkRight": 0.1}
    aus = map_blendshapes_to_aus(bs_squint)
    assert is_au_active(aus, "AU7", blendshapes=bs_squint) is True


def test_detect_active_aus_only_critical():
    """only_critical=True retorna apenas 10 AUs críticas."""
    bs = {"browInnerUp": 0.5, "mouthSmileLeft": 0.5, "mouthSmileRight": 0.5}
    result = detect_active_aus(bs, only_critical=True)
    assert set(result.keys()) == CRITICAL_AUS
    assert result["AU1"] is True  # browInnerUp 0.5 > 0.30
    assert result["AU12"] is True  # avg(0.5, 0.5) = 0.5 > 0.40


def test_detect_active_aus_full():
    """only_critical=False retorna todas 22 AUs."""
    bs = {"browInnerUp": 0.5}
    result = detect_active_aus(bs, only_critical=False)
    # Spec menciona ~22 AUs, sub-set inclui AU1..AU45
    assert len(result) >= 20
    assert "AU34" in result  # cheekPuff (não-crítico, mas mapeado)


def test_csv_row_helper():
    """map_blendshape_csv_row converte CSV strings → floats, skip metadata."""
    row = {
        "frame": "0",
        "time_s": "0.0",
        "face_detected": "1",
        "browInnerUp": "0.45",
        "mouthSmileLeft": "0.30",
        "tongueOut": "",  # empty string
    }
    out = map_blendshape_csv_row(row)
    assert "frame" not in out
    assert "time_s" not in out
    assert "face_detected" not in out
    assert out["browInnerUp"] == 0.45
    assert out["mouthSmileLeft"] == 0.30
    assert "tongueOut" not in out  # empty string skipped


def test_au45_blink_detection():
    """AU45 (blink) — frame-event detection."""
    bs_blink = {"eyeBlinkLeft": 0.6, "eyeBlinkRight": 0.6}
    aus = map_blendshapes_to_aus(bs_blink)
    assert aus["AU45"] == 0.6
    assert is_au_active(aus, "AU45") is True

    bs_open = {"eyeBlinkLeft": 0.1, "eyeBlinkRight": 0.1}
    aus = map_blendshapes_to_aus(bs_open)
    assert is_au_active(aus, "AU45") is False
