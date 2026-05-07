"""Story 10.2 Fase 1 — Bridge MediaPipe blendshapes → AUs FACS.

Mapping determinístico (sem ML) baseado em tabela documentada em
`docs/research/2026-05-06-avaliador-oratoria-landscape/05-mediapipe-au-bridge-spec.md`.

Substitui py-feat (bloqueia Py3.12) por código nativo no stack atual
(MediaPipe Apache 2.0, OpenFace 3.0 inviável por license CMU non-commercial).

Caveat científico: blendshapes ARKit ≠ AUs FACS canônicos. Correspondência
"loosely correspond" — validação empírica vs py-feat na Fase 2 obrigatória.

Cobertura:
- 22 AUs mapeadas (das ~30+ FACS canônicas)
- 10 AUs CRÍTICAS pra oratória cobertas (AU1, AU2, AU4, AU5, AU6, AU7,
  AU9, AU12, AU15, AU45)

Cross-checks integrados:
- Duchenne genuíno (AU6 só ativa com mouthSmile simultâneo)
- AU7 NÃO ativa se eyeBlink em mesmo frame
"""

from __future__ import annotations

from typing import TypedDict

import structlog

logger = structlog.get_logger()


# ─────────────────────────────────────────────────────────────────────────────
# THRESHOLDS por AU (calibrados pra mobile, ajuste empírico Fase 2)
# Pattern: SMILE_INDEX_THRESHOLD = 0.42 do facial_analyzer.py existente.
# ─────────────────────────────────────────────────────────────────────────────

AU_THRESHOLDS: dict[str, float] = {
    "AU1": 0.30,   # Inner Brow Raiser (browInnerUp)
    "AU2": 0.30,   # Outer Brow Raiser (browOuterUpL+R / 2)
    "AU4": 0.30,   # Brow Lowerer (browDownL+R / 2)
    "AU5": 0.40,   # Upper Lid Raiser (eyeWideL+R / 2)
    "AU6": 0.30,   # Cheek Raiser (cheekSquintL+R / 2) — requer Duchenne cross-check
    "AU7": 0.30,   # Lid Tightener (eyeSquintL+R / 2) — não ativa se blink
    "AU9": 0.20,   # Nose Wrinkler (noseSneerL+R / 2)
    "AU10": 0.30,  # Upper Lip Raiser (mouthUpperUpL+R / 2)
    "AU12": 0.40,  # Lip Corner Puller / smile (mouthSmileL+R / 2)
    "AU14": 0.30,  # Dimpler (mouthDimpleL+R / 2)
    "AU15": 0.30,  # Lip Corner Depressor (mouthFrownL+R / 2)
    "AU17": 0.30,  # Chin Raiser (mouthShrugUpper+Lower / 2)
    "AU18": 0.30,  # Lip Puckerer (mouthPucker)
    "AU19": 0.40,  # Tongue Show (tongueOut) — raro em oratória
    "AU20": 0.30,  # Lip Stretcher (mouthStretchL+R / 2)
    "AU22": 0.30,  # Lip Funneler (mouthFunnel)
    "AU24": 0.40,  # Lip Pressor (mouthPressL+R+mouthClose / 3)
    "AU26": 0.20,  # Jaw Drop (jawOpen baixo-médio)
    "AU27": 0.50,  # Mouth Stretch (jawOpen alto)
    "AU28": 0.30,  # Lip Suck (mouthRollLower+Upper / 2)
    "AU34": 0.40,  # Cheek Puff (cheekPuff)
    "AU45": 0.50,  # Blink (eyeBlinkL+R / 2) — frame-event
}

# AUs críticas pra oratória (cobertura obrigatória — Fase 2 valida estes)
CRITICAL_AUS = {"AU1", "AU2", "AU4", "AU5", "AU6", "AU7", "AU9", "AU12", "AU15", "AU45"}

# Cross-check Duchenne: AU6 só "genuíno" se AU12 simultâneo
DUCHENNE_AU12_THRESHOLD = 0.40


class BlendshapeDict(TypedDict, total=False):
    """52 blendshapes ARKit-style expostos por MediaPipe FaceLandmarker."""

    # Eyes
    eyeBlinkLeft: float
    eyeBlinkRight: float
    eyeWideLeft: float
    eyeWideRight: float
    eyeSquintLeft: float
    eyeSquintRight: float
    # Brow
    browInnerUp: float
    browOuterUpLeft: float
    browOuterUpRight: float
    browDownLeft: float
    browDownRight: float
    # Cheek
    cheekSquintLeft: float
    cheekSquintRight: float
    cheekPuff: float
    # Nose
    noseSneerLeft: float
    noseSneerRight: float
    # Mouth
    mouthSmileLeft: float
    mouthSmileRight: float
    mouthFrownLeft: float
    mouthFrownRight: float
    mouthDimpleLeft: float
    mouthDimpleRight: float
    mouthStretchLeft: float
    mouthStretchRight: float
    mouthPressLeft: float
    mouthPressRight: float
    mouthClose: float
    mouthPucker: float
    mouthFunnel: float
    mouthShrugUpper: float
    mouthShrugLower: float
    mouthRollLower: float
    mouthRollUpper: float
    mouthUpperUpLeft: float
    mouthUpperUpRight: float
    mouthLowerDownLeft: float
    mouthLowerDownRight: float
    # Jaw
    jawOpen: float
    jawForward: float
    jawLeft: float
    jawRight: float
    # Tongue
    tongueOut: float


def _avg(*values: float) -> float:
    """Média de N valores, com guard contra NaN/None."""
    valid = [v for v in values if v is not None and not (isinstance(v, float) and v != v)]
    if not valid:
        return 0.0
    return sum(valid) / len(valid)


def map_blendshapes_to_aus(bs: dict[str, float]) -> dict[str, float]:
    """Mapeia 52 blendshapes ARKit → 22 AUs FACS aproximadas.

    Args:
        bs: dict com 52 blendshape names → float [0,1].
            Aceita dict parcial (campos ausentes tratados como 0).

    Returns:
        dict com 22 AUs → intensity float [0,1] (não-thresholded).
        Use is_au_active(aus, "AU6") pra binary com threshold + cross-check.
    """
    g = lambda k: float(bs.get(k, 0.0))  # noqa: E731

    aus: dict[str, float] = {
        # Brow
        "AU1": g("browInnerUp"),
        "AU2": _avg(g("browOuterUpLeft"), g("browOuterUpRight")),
        "AU4": _avg(g("browDownLeft"), g("browDownRight")),
        # Eyes
        "AU5": _avg(g("eyeWideLeft"), g("eyeWideRight")),
        "AU7": _avg(g("eyeSquintLeft"), g("eyeSquintRight")),
        "AU45": _avg(g("eyeBlinkLeft"), g("eyeBlinkRight")),
        # Cheek
        "AU6": _avg(g("cheekSquintLeft"), g("cheekSquintRight")),
        "AU34": g("cheekPuff"),
        # Nose
        "AU9": _avg(g("noseSneerLeft"), g("noseSneerRight")),
        # Mouth
        "AU10": _avg(g("mouthUpperUpLeft"), g("mouthUpperUpRight")),
        "AU12": _avg(g("mouthSmileLeft"), g("mouthSmileRight")),
        "AU14": _avg(g("mouthDimpleLeft"), g("mouthDimpleRight")),
        "AU15": _avg(g("mouthFrownLeft"), g("mouthFrownRight")),
        "AU17": _avg(g("mouthShrugUpper"), g("mouthShrugLower")),
        "AU18": g("mouthPucker"),
        "AU20": _avg(g("mouthStretchLeft"), g("mouthStretchRight")),
        "AU22": g("mouthFunnel"),
        "AU24": _avg(g("mouthPressLeft"), g("mouthPressRight"), g("mouthClose")),
        "AU28": _avg(g("mouthRollLower"), g("mouthRollUpper")),
        # Jaw — AU26 (drop) vs AU27 (stretch) divididos por threshold
        "AU26": min(g("jawOpen"), AU_THRESHOLDS["AU27"]) if g("jawOpen") < AU_THRESHOLDS["AU27"] else 0.0,
        "AU27": g("jawOpen") if g("jawOpen") >= AU_THRESHOLDS["AU27"] else 0.0,
        # Tongue
        "AU19": g("tongueOut"),
    }
    return aus


def is_au_active(aus: dict[str, float], au_name: str, blendshapes: dict[str, float] | None = None) -> bool:
    """Retorna se AU está ativa (intensity > threshold + cross-checks).

    Cross-checks integrados:
    - AU6: requer AU12 (mouthSmile) simultâneo pra ser "Duchenne genuíno"
    - AU7: NÃO ativa se eyeBlink no mesmo frame (eyeBlink mascara squint)

    Args:
        aus: dict do map_blendshapes_to_aus()
        au_name: "AU1" .. "AU45"
        blendshapes: dict original — opcional, requerido pra cross-checks
                     (AU6 Duchenne, AU7 anti-blink).

    Returns:
        True se AU passa threshold E cross-checks.
    """
    if au_name not in aus:
        return False

    intensity = aus[au_name]
    threshold = AU_THRESHOLDS.get(au_name, 0.30)

    if intensity < threshold:
        return False

    # Cross-check Duchenne: AU6 sem AU12 simultâneo NÃO é cheek raiser
    # genuíno (pode ser squint sem sorriso).
    if au_name == "AU6" and blendshapes is not None:
        au12_mouth_smile = _avg(
            blendshapes.get("mouthSmileLeft", 0.0),
            blendshapes.get("mouthSmileRight", 0.0),
        )
        if au12_mouth_smile < DUCHENNE_AU12_THRESHOLD:
            return False

    # Cross-check AU7: blink mascara squint genuíno
    if au_name == "AU7" and blendshapes is not None:
        eye_blink = _avg(
            blendshapes.get("eyeBlinkLeft", 0.0),
            blendshapes.get("eyeBlinkRight", 0.0),
        )
        if eye_blink >= AU_THRESHOLDS["AU45"]:
            return False

    return True


def detect_active_aus(
    bs: dict[str, float],
    only_critical: bool = False,
) -> dict[str, bool]:
    """Detecta AUs ativas em 1 frame com cross-checks aplicados.

    Args:
        bs: blendshape dict
        only_critical: se True, retorna só as 10 AUs críticas pra oratória

    Returns:
        dict {AU_name: bool}
    """
    aus = map_blendshapes_to_aus(bs)
    target_aus = CRITICAL_AUS if only_critical else aus.keys()
    return {au: is_au_active(aus, au, blendshapes=bs) for au in target_aus}


def map_blendshape_csv_row(row: dict[str, str]) -> dict[str, float]:
    """Helper pra ler CSV gerado pelo extract_blendshapes.py spike.

    Converte strings → float, ignora colunas non-blendshape (frame, time_s,
    face_detected).

    Returns:
        dict com 52 blendshape floats.
    """
    skip_keys = {"frame", "time_s", "face_detected"}
    out = {}
    for k, v in row.items():
        if k in skip_keys or v == "":
            continue
        try:
            out[k] = float(v)
        except (ValueError, TypeError):
            out[k] = 0.0
    return out
