import subprocess
import time
from pathlib import Path

import mediapipe as mp
import numpy as np
import structlog

logger = structlog.get_logger()

POSE_MODEL_PATH = "/tmp/mediapipe_models/pose_landmarker.task"


def extract_frames(video_path: str, fps: int = 2) -> list[str]:
    """Extrai frames do video no fps dado usando FFmpeg."""
    output_dir = Path(video_path).parent / "frames"
    output_dir.mkdir(exist_ok=True)
    pattern = str(output_dir / "frame_%04d.jpg")

    subprocess.run(
        [
            "ffmpeg",
            "-i",
            video_path,
            "-vf",
            f"fps={fps}",
            "-q:v",
            "2",
            "-y",
            pattern,
        ],
        capture_output=True,
        timeout=120,
    )

    frames = sorted(output_dir.glob("frame_*.jpg"))
    logger.info("frames_extracted", count=len(frames), fps=fps)
    return [str(f) for f in frames]


def _angle_between(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    """Calcula angulo no ponto b entre segmentos ba e bc."""
    ba = a - b
    bc = c - b
    cosine = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-8)
    return float(np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0))))


def _classificar_movimento(centers_of_mass: list, detected_frames: int) -> dict:
    """Classifica padrao de movimento com base no centro de massa.

    Padroes:
    - plantado: >75% parado, <=2 deslocamentos = grounding 90, proposital 70
    - proposital: 3+ steps + 40% parado = grounding 80, proposital 90
    - rigido: <0.5% variancia, >95% parado = grounding 40, proposital 20
    - ansioso: <30% parado = grounding 30, proposital 20
    - misto: fallback = grounding 60, proposital 50
    """
    if len(centers_of_mass) < 2:
        return {
            "padrao": "misto",
            "grounding_score": 60,
            "proposital_score": 50,
            "variancia": 0,
            "ratio_parado": 0.5,
            "num_deslocamentos": 0,
            "deslocamento_medio": 0,
        }

    com_array = np.array(centers_of_mass)
    variancia = float(np.var(com_array, axis=0).sum())

    # Detectar deslocamentos significativos (> threshold entre frames consecutivos)
    # Calibrado para match com avaliacao de referencia (ratio_parado ~0.23)
    threshold_deslocamento = 0.008
    deslocamentos = []
    frames_parado = 0

    for i in range(1, len(com_array)):
        dist = float(np.linalg.norm(com_array[i] - com_array[i - 1]))
        if dist > threshold_deslocamento:
            deslocamentos.append(dist)
        else:
            frames_parado += 1

    ratio_parado = frames_parado / max(1, len(com_array) - 1)
    num_deslocamentos = len(deslocamentos)
    deslocamento_medio = float(np.mean(deslocamentos)) if deslocamentos else 0.0

    # Classificar
    if variancia < 0.0005 and ratio_parado > 0.95:
        padrao = "rigido"
        grounding_score = 40
        proposital_score = 20
    elif ratio_parado > 0.75 and num_deslocamentos <= 2:
        padrao = "plantado"
        grounding_score = 90
        proposital_score = 70
    elif num_deslocamentos >= 3 and ratio_parado >= 0.40:
        padrao = "proposital"
        grounding_score = 80
        proposital_score = 90
    elif ratio_parado < 0.20:
        padrao = "ansioso"
        grounding_score = 30
        proposital_score = 20
    else:
        padrao = "misto"
        grounding_score = 60
        proposital_score = 50

    return {
        "padrao": padrao,
        "grounding_score": grounding_score,
        "proposital_score": proposital_score,
        "variancia": round(variancia, 6),
        "ratio_parado": round(ratio_parado, 3),
        "num_deslocamentos": num_deslocamentos,
        "deslocamento_medio": round(deslocamento_medio, 5),
    }


def analyze_posture(video_path: str) -> dict:
    """Analisa postura usando MediaPipe PoseLandmarker."""
    start = time.time()
    logger.info("posture_analysis_start", video_path=video_path)

    frames = extract_frames(video_path, fps=2)
    if not frames:
        logger.warning("no_frames_extracted")
        return {"score": 0, "confidence": "failed", "metrics": {}}

    BaseOptions = mp.tasks.BaseOptions
    PoseLandmarker = mp.tasks.vision.PoseLandmarker
    PoseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions
    VisionRunningMode = mp.tasks.vision.RunningMode

    options = PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=POSE_MODEL_PATH),
        running_mode=VisionRunningMode.IMAGE,
        num_poses=1,
    )

    alignment_scores = []
    open_posture_count = 0
    ombros_nivelados_count = 0
    centers_of_mass = []
    detected_frames = 0

    with PoseLandmarker.create_from_options(options) as landmarker:
        for frame_path in frames:
            image = mp.Image.create_from_file(frame_path)
            results = landmarker.detect(image)

            if not results.pose_landmarks or len(results.pose_landmarks) == 0:
                continue

            detected_frames += 1
            lm = results.pose_landmarks[0]

            left_shoulder = np.array([lm[11].x, lm[11].y])
            right_shoulder = np.array([lm[12].x, lm[12].y])
            left_hip = np.array([lm[23].x, lm[23].y])
            right_hip = np.array([lm[24].x, lm[24].y])
            nose = np.array([lm[0].x, lm[0].y])

            # Ombros nivelados
            shoulder_tilt = abs(left_shoulder[1] - right_shoulder[1])
            shoulder_score = max(0, 100 - shoulder_tilt * 500)
            if shoulder_tilt < 0.03:
                ombros_nivelados_count += 1

            # Cabeca centralizada
            shoulder_center = (left_shoulder + right_shoulder) / 2
            head_offset = abs(nose[0] - shoulder_center[0])
            head_score = max(0, 100 - head_offset * 300)

            # Coluna alinhada
            hip_center = (left_hip + right_hip) / 2
            spine_angle = _angle_between(
                np.array([shoulder_center[0], 0]),
                shoulder_center,
                hip_center,
            )
            spine_score = max(0, 100 - abs(spine_angle - 180) * 2)

            alignment = round((shoulder_score + head_score + spine_score) / 3)
            alignment_scores.append(alignment)

            # Postura aberta vs fechada
            shoulder_width = np.linalg.norm(left_shoulder - right_shoulder)
            hip_width = np.linalg.norm(left_hip - right_hip)
            if shoulder_width > hip_width * 0.9:
                open_posture_count += 1

            # Centro de massa
            com = (shoulder_center + hip_center) / 2
            centers_of_mass.append(com)

    if detected_frames == 0:
        logger.warning("no_poses_detected", total_frames=len(frames))
        return {"score": 0, "confidence": "failed", "metrics": {}}

    # Metricas finais
    avg_alignment = round(float(np.mean(alignment_scores)))
    open_posture_pct = round(open_posture_count / detected_frames * 100, 1)
    ombros_nivelados_pct = round(ombros_nivelados_count / detected_frames * 100, 1)

    # Classificacao de movimento
    movimento = _classificar_movimento(centers_of_mass, detected_frames)

    # =============================================
    # SCORE DE POSTURA (0-100) — 4 componentes
    # =============================================
    # 35% Alignment + 20% Open posture + 25% Grounding + 20% Proposital

    posture_score = round(
        avg_alignment * 0.35
        + min(100, open_posture_pct) * 0.20
        + movimento["grounding_score"] * 0.25
        + movimento["proposital_score"] * 0.20
    )
    posture_score = max(0, min(100, posture_score))

    confidence = "high" if detected_frames / len(frames) > 0.7 else "medium"
    if detected_frames / len(frames) < 0.3:
        confidence = "low"

    elapsed = time.time() - start
    logger.info(
        "posture_analysis_complete",
        score=posture_score,
        detected_frames=detected_frames,
        total_frames=len(frames),
        padrao_movimento=movimento["padrao"],
        duration_seconds=round(elapsed, 2),
    )

    return {
        "score": posture_score,
        "confidence": confidence,
        "metrics": {
            "alignment_score": avg_alignment,
            "open_posture_pct": open_posture_pct,
            "ombros_nivelados_pct": ombros_nivelados_pct,
            "grounding_score": movimento["grounding_score"],
            "proposital_score": movimento["proposital_score"],
            "padrao_movimento": movimento["padrao"],
            "movimento_detalhes": {
                "variancia": movimento["variancia"],
                "ratio_parado": movimento["ratio_parado"],
                "num_deslocamentos": movimento["num_deslocamentos"],
                "deslocamento_medio": movimento["deslocamento_medio"],
            },
            "sub_scores": {
                "alinhamento": avg_alignment,
                "postura_aberta": round(min(100, open_posture_pct)),
                "grounding": movimento["grounding_score"],
                "movimento_proposital": movimento["proposital_score"],
            },
            "detected_frames": detected_frames,
            "total_frames": len(frames),
        },
    }
