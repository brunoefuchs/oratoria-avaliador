"""Story 7.4 — Analisador de Expressao Facial.

Mede smile, brow movement e eye openness ao longo do video usando MediaPipe
FaceLandmarker (mesmo modelo ja usado por gesture_analyzer.py para olhar).

Premissa do framework Vinh: rosto representa ~40% da percepcao emocional.
Hoje o app mede corpo e voz mas nao rosto — gap critico do MVP.

Output alimentado para `congruence_analyzer` (cruzamento voz-corpo-rosto).
"""

import time
from pathlib import Path

import mediapipe as mp
import numpy as np
import structlog

logger = structlog.get_logger()

FACE_MODEL_PATH = "/tmp/mediapipe_models/face_landmarker.task"

# Calibracao Story 7.4 Task 0 (2026-04-14)
# Thresholds baseados em literatura (Ekman FACS + MediaPipe community).
# Ajustar via Task 9 se feedback de users em videos diversos divergir.
SMILE_INDEX_THRESHOLD = 0.42  # Smile ativo quando ratio > 0.42
BROW_RAISE_DELTA_THRESHOLD = 0.008  # Elevacao brow significativa em normalized coords
BLINK_EAR_THRESHOLD = 0.18  # Eye Aspect Ratio abaixo disso = piscada
WINDOW_SECONDS = 5.0  # Janelas para variability
TARGET_FPS = 5  # 5fps cobre rosto bem (rosto nao muda dramaticamente em 200ms)

# Landmarks indices (MediaPipe Face Mesh refined — 478 landmarks)
# Boca (smile detection)
MOUTH_LEFT_CORNER = 61
MOUTH_RIGHT_CORNER = 291
JAW_LEFT = 172
JAW_RIGHT = 397

# Sobrancelhas
LEFT_BROW_CENTER = 105
RIGHT_BROW_CENTER = 334

# Olhos (Eye Aspect Ratio — formula classica de Soukupova & Cech 2016)
# Esquerdo
LEFT_EYE_TOP = 159
LEFT_EYE_BOTTOM = 145
LEFT_EYE_LEFT = 33
LEFT_EYE_RIGHT = 133
# Direito
RIGHT_EYE_TOP = 386
RIGHT_EYE_BOTTOM = 374
RIGHT_EYE_LEFT = 362
RIGHT_EYE_RIGHT = 263

# Referencia para detectar movimento de brow (precisamos algo estavel acima do brow)
NOSE_BRIDGE = 6


def _distance(landmarks, idx_a: int, idx_b: int) -> float:
    a = landmarks[idx_a]
    b = landmarks[idx_b]
    return float(np.hypot(a.x - b.x, a.y - b.y))


def _compute_smile_index(landmarks) -> float:
    """Razao mouth_width / jaw_width. Maior = sorriso mais aberto."""
    mouth_width = _distance(landmarks, MOUTH_LEFT_CORNER, MOUTH_RIGHT_CORNER)
    jaw_width = _distance(landmarks, JAW_LEFT, JAW_RIGHT)
    if jaw_width <= 1e-6:
        return 0.0
    return mouth_width / jaw_width


def _compute_brow_elevation(landmarks) -> float:
    """Distancia normalizada entre brow centers e nose bridge.

    Maior valor = sobrancelhas mais altas. Diff entre frames detecta levantamento.
    """
    left = abs(landmarks[LEFT_BROW_CENTER].y - landmarks[NOSE_BRIDGE].y)
    right = abs(landmarks[RIGHT_BROW_CENTER].y - landmarks[NOSE_BRIDGE].y)
    return float((left + right) / 2)


def _eye_aspect_ratio(landmarks, side: str) -> float:
    """Eye Aspect Ratio (EAR) — height/width do olho.

    Piscada/olho fechado: EAR baixo (<0.18). Olho normal: ~0.25-0.35.
    """
    if side == "left":
        top, bottom, left, right = LEFT_EYE_TOP, LEFT_EYE_BOTTOM, LEFT_EYE_LEFT, LEFT_EYE_RIGHT
    else:
        top, bottom, left, right = RIGHT_EYE_TOP, RIGHT_EYE_BOTTOM, RIGHT_EYE_LEFT, RIGHT_EYE_RIGHT
    height = _distance(landmarks, top, bottom)
    width = _distance(landmarks, left, right)
    if width <= 1e-6:
        return 0.0
    return height / width


def _extract_frames_facial(video_path: str, fps: int) -> list[str]:
    """Extrai frames com FFmpeg — mesma implementacao de posture/gesture."""
    import subprocess

    output_dir = Path(video_path).parent / "frames_facial"
    output_dir.mkdir(exist_ok=True)
    pattern = str(output_dir / "frame_%04d.jpg")

    subprocess.run(
        ["ffmpeg", "-i", video_path, "-vf", f"fps={fps}", "-q:v", "2", "-y", pattern],
        capture_output=True,
        timeout=120,
    )
    frames = sorted(output_dir.glob("frame_*.jpg"))
    return [str(f) for f in frames]


def analyze_facial(video_path: str) -> dict:
    """Analisa expressao facial: smile, brow, eye openness.

    Pipeline:
    1. Extrai frames (5fps)
    2. Para cada frame, detecta face mesh
    3. Calcula smile_index, brow_elevation, EAR (esquerdo e direito)
    4. Agrega: frequency, variability, brow raises/min, eye stddev
    5. Diagnostico textual + score 0-100
    """
    start = time.time()
    logger.info("facial_analysis_start", video_path=video_path)

    frames = _extract_frames_facial(video_path, fps=TARGET_FPS)
    if not frames:
        logger.warning("facial_no_frames")
        return _disponivel_false("Falha ao extrair frames do video")

    BaseOptions = mp.tasks.BaseOptions
    FaceLandmarker = mp.tasks.vision.FaceLandmarker
    FaceLandmarkerOptions = mp.tasks.vision.FaceLandmarkerOptions
    VisionRunningMode = mp.tasks.vision.RunningMode

    options = FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=FACE_MODEL_PATH),
        running_mode=VisionRunningMode.IMAGE,
        num_faces=1,
    )

    smile_indices: list[float] = []
    brow_elevations: list[float] = []
    ear_values: list[float] = []  # media dos dois olhos
    detected_count = 0
    total_frames = len(frames)

    with FaceLandmarker.create_from_options(options) as landmarker:
        for frame_path in frames:
            image = mp.Image.create_from_file(frame_path)
            results = landmarker.detect(image)
            if not results.face_landmarks:
                smile_indices.append(np.nan)
                brow_elevations.append(np.nan)
                ear_values.append(np.nan)
                continue
            detected_count += 1
            landmarks = results.face_landmarks[0]
            smile_indices.append(_compute_smile_index(landmarks))
            brow_elevations.append(_compute_brow_elevation(landmarks))
            ear_left = _eye_aspect_ratio(landmarks, "left")
            ear_right = _eye_aspect_ratio(landmarks, "right")
            ear_values.append((ear_left + ear_right) / 2)

    detection_pct = detected_count / total_frames if total_frames else 0.0

    # AC-10: rosto nao detectado em >50% → indisponivel
    if detection_pct < 0.5:
        warnings_list = [
            f"Rosto detectado em apenas {round(detection_pct * 100, 1)}% dos frames "
            "(possivel enquadramento, iluminacao ou oclusao)",
        ]
        return _disponivel_false(
            "Analise facial requer rosto visivel em pelo menos 50% do video",
            warnings_list,
        )

    # Computar metricas agregadas
    smile_arr = np.array([s for s in smile_indices if not np.isnan(s)])
    brow_arr = np.array([b for b in brow_elevations if not np.isnan(b)])
    ear_arr = np.array([e for e in ear_values if not np.isnan(e)])

    # AC-1 — smile_frequency_percent
    smile_active_count = int(np.sum(smile_arr > SMILE_INDEX_THRESHOLD))
    smile_frequency_percent = round(smile_active_count / len(smile_arr) * 100, 1)

    # AC-2 — smile_variability (stdev em janelas de 5s)
    frames_per_window = max(1, int(WINDOW_SECONDS * TARGET_FPS))
    window_means = []
    for i in range(0, len(smile_arr), frames_per_window):
        window = smile_arr[i : i + frames_per_window]
        if len(window) > 0:
            window_means.append(float(np.mean(window)))
    smile_variability = round(float(np.std(window_means)), 3) if len(window_means) > 1 else 0.0

    # AC-3 — brow_raises_per_minute
    # Deteccao: subida rapida (delta > threshold em frames consecutivos)
    brow_raises_count = 0
    in_raise = False
    for i in range(1, len(brow_arr)):
        delta = brow_arr[i] - brow_arr[i - 1]
        if delta > BROW_RAISE_DELTA_THRESHOLD and not in_raise:
            brow_raises_count += 1
            in_raise = True
        elif delta < -BROW_RAISE_DELTA_THRESHOLD * 0.5:
            in_raise = False
    duration_seconds = len(smile_arr) / TARGET_FPS
    brow_raises_per_minute = round(brow_raises_count / max(duration_seconds / 60, 0.01), 1)

    # AC-4 — eye_openness_stddev (filtrando piscadas para nao confundir com fadiga)
    ear_filtered = ear_arr[ear_arr > BLINK_EAR_THRESHOLD]
    eye_openness_stddev = round(float(np.std(ear_filtered)), 4) if len(ear_filtered) > 5 else 0.0

    # Estimativa simples de textura emocional (sub-porcoes)
    neutro_count = int(np.sum((smile_arr <= SMILE_INDEX_THRESHOLD)))
    positivo_count = int(smile_active_count)
    tenso_proxy_count = int(np.sum(ear_arr < BLINK_EAR_THRESHOLD * 1.3))  # squinting
    total_classified = max(neutro_count + positivo_count + tenso_proxy_count, 1)
    emocional_texture = {
        "neutro_percent": round(neutro_count / total_classified * 100, 1),
        "positivo_percent": round(positivo_count / total_classified * 100, 1),
        "tenso_percent": round(tenso_proxy_count / total_classified * 100, 1),
    }

    # =============================================
    # SCORE 0-100 + DIAGNOSTICO
    # =============================================
    # Combina presenca de variacao saudavel:
    # - Smile presente mas nao travado (variability > 0)
    # - Brow ativo (>= 2/min)
    # - Eye openness com variacao (nao monotono)
    score = 50.0  # base

    # Smile saudavel: 20-60% do tempo + variabilidade > 0.005
    if 20 <= smile_frequency_percent <= 60 and smile_variability > 0.005:
        score += 20
    elif smile_frequency_percent < 5:
        score -= 15  # rosto serio demais
    elif smile_frequency_percent > 80 and smile_variability < 0.005:
        score -= 15  # sorriso travado

    # Brow ativo
    if brow_raises_per_minute >= 2:
        score += 15
    elif brow_raises_per_minute >= 1:
        score += 8
    else:
        score -= 10  # rosto estatico

    # Eye openness com variacao saudavel (nao monotono nem ansioso)
    if 0.015 <= eye_openness_stddev <= 0.05:
        score += 10
    elif eye_openness_stddev < 0.005:
        score -= 5

    score = max(0, min(100, round(score)))

    # Diagnostico — Story 7.4 fix QA (2026-04-14)
    # Critério rosto_estatico AGORA usa frequency (mais robusto que variability).
    # Variability falha quando smile esporadico passa do threshold 0.005 mesmo com 90%+ rosto serio.
    if smile_frequency_percent < 15 and brow_raises_per_minute < 1:
        diagnostico = "rosto_estatico"
        feedback = (
            "Sua expressao facial permaneceu praticamente constante "
            f"(sorriso ativo em apenas {round(smile_frequency_percent)}% do tempo, "
            f"{round(brow_raises_per_minute, 1)} elevacao de sobrancelhas por minuto). "
            "Adicionar variacao no sorriso e movimento de sobrancelhas aumenta o engajamento da audiencia."
        )
    elif smile_frequency_percent > 80 and smile_variability < 0.01:
        diagnostico = "expressao_travada"
        feedback = (
            "Sorriso constante (>80% do tempo) com pouca variacao tende a parecer ensaiado. "
            "Permita seu rosto descansar entre momentos de sorriso."
        )
    elif smile_frequency_percent < 5 and brow_raises_per_minute < 1:
        diagnostico = "expressao_monotona"
        feedback = (
            "Rosto serio durante quase todo o video. "
            "Pequenas variacoes (sorriso leve, sobrancelha em momentos-chave) ajudam a transmitir emocao."
        )
    elif brow_raises_per_minute > 8:
        diagnostico = "expressao_exagerada"
        feedback = (
            "Movimento facial muito frequente pode distrair da mensagem. "
            "Use brow raises com mais intencao (1 a 3 vezes por minuto em pontos-chave)."
        )
    else:
        diagnostico = "expressao_equilibrada"
        feedback = (
            "Variacao facial saudavel — sorriso espontaneo + movimento de sobrancelhas em momentos certos. "
            "Continue assim e use os picos para reforcar pontos importantes."
        )

    elapsed = round(time.time() - start, 2)
    logger.info(
        "facial_analysis_complete",
        score=score,
        diagnostico=diagnostico,
        smile_frequency=smile_frequency_percent,
        brow_per_min=brow_raises_per_minute,
        detection_pct=round(detection_pct * 100, 1),
        duration_seconds=elapsed,
    )

    return {
        "disponivel": True,
        "score": score,
        "diagnostico": diagnostico,
        "smile_frequency_percent": smile_frequency_percent,
        "smile_variability": smile_variability,
        "brow_raises_per_minute": brow_raises_per_minute,
        "eye_openness_stddev": eye_openness_stddev,
        "emocional_texture": emocional_texture,
        "feedback": feedback,
        "detection_pct": round(detection_pct * 100, 1),
        "warnings": [],
    }


def _disponivel_false(motivo: str, warnings_list: list[str] | None = None) -> dict:
    return {
        "disponivel": False,
        "score": 0,
        "diagnostico": "indisponivel",
        "smile_frequency_percent": 0.0,
        "smile_variability": 0.0,
        "brow_raises_per_minute": 0.0,
        "eye_openness_stddev": 0.0,
        "emocional_texture": {"neutro_percent": 0, "positivo_percent": 0, "tenso_percent": 0},
        "feedback": motivo,
        "detection_pct": 0.0,
        "warnings": warnings_list or [motivo],
    }
