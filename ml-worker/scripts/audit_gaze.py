"""Auditoria de detecção de gaze (contato visual).

Roda MediaPipe FaceLandmarker num vídeo, classifica gaze de cada Nth frame
usando _estimar_direcao_olhar, e exporta CSV com timestamp + gaze_x/gaze_y +
classificação + flag de "borderline" (próximo dos limiares).

Uso:
    python scripts/audit_gaze.py <video_path> [--every N] [--out file.csv]

Borderline = quando |gaze_x| está em [0.20, 0.40] OR gaze_y em [0.15, 0.45]
(zona de incerteza ao redor dos thresholds atuais 0.30/0.30/0.55).
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

# Permite rodar standalone do diretorio ml-worker/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cv2  # type: ignore
import mediapipe as mp  # type: ignore

from workers.gesture_analyzer import _estimar_direcao_olhar


GAZE_X_THRESHOLD = 0.30
GAZE_Y_DOWN_THRESHOLD = 0.30
GAZE_Y_UP_THRESHOLD = 0.55


def is_borderline(gaze_x: float, gaze_y: float) -> bool:
    """Marca frame como duvidoso quando esta proximo de algum threshold."""
    if 0.20 <= abs(gaze_x) <= 0.40:
        return True
    if 0.15 <= gaze_y <= 0.45:
        return True
    if -0.65 <= gaze_y <= -0.45:
        return True
    return False


def audit_video(video_path: str, every_n_frames: int, out_path: str) -> None:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Nao consegui abrir video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    base_path = Path("/tmp/mediapipe_models/face_landmarker.task")
    if not base_path.exists():
        raise RuntimeError(f"Modelo nao encontrado em {base_path}")

    BaseOptions = mp.tasks.BaseOptions
    FaceLandmarker = mp.tasks.vision.FaceLandmarker
    FaceLandmarkerOptions = mp.tasks.vision.FaceLandmarkerOptions
    VisionRunningMode = mp.tasks.vision.RunningMode

    options = FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(base_path)),
        running_mode=VisionRunningMode.VIDEO,
        num_faces=1,
        output_face_blendshapes=False,
        output_facial_transformation_matrixes=False,
    )

    rows = []
    counts = {"camera": 0, "esquerda": 0, "direita": 0, "baixo": 0, "cima": 0, "no_face": 0}
    sampled = 0

    with FaceLandmarker.create_from_options(options) as face_landmarker:
        idx = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if idx % every_n_frames != 0:
                idx += 1
                continue

            ts_ms = int((idx / fps) * 1000)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

            try:
                result = face_landmarker.detect_for_video(mp_img, ts_ms)
            except Exception:
                result = None

            sampled += 1
            time_s = round(idx / fps, 2)

            if result is None or not result.face_landmarks:
                counts["no_face"] += 1
                rows.append(
                    {
                        "frame": idx,
                        "time_s": time_s,
                        "gaze_x": "",
                        "gaze_y": "",
                        "direcao": "no_face",
                        "borderline": "",
                    }
                )
                idx += 1
                continue

            gaze = _estimar_direcao_olhar(result.face_landmarks[0])
            counts[gaze["direcao"]] = counts.get(gaze["direcao"], 0) + 1
            rows.append(
                {
                    "frame": idx,
                    "time_s": time_s,
                    "gaze_x": gaze["gaze_x"],
                    "gaze_y": gaze["gaze_y"],
                    "direcao": gaze["direcao"],
                    "borderline": "X" if is_borderline(gaze["gaze_x"], gaze["gaze_y"]) else "",
                }
            )
            idx += 1

    cap.release()

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["frame", "time_s", "gaze_x", "gaze_y", "direcao", "borderline"]
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nSAMPLED: {sampled} frames de {total} totais (1/{every_n_frames}, {fps:.1f} fps)")
    print(f"Thresholds atuais: GAZE_X={GAZE_X_THRESHOLD} | GAZE_Y_DOWN={GAZE_Y_DOWN_THRESHOLD} | GAZE_Y_UP={GAZE_Y_UP_THRESHOLD}")
    print("\nDistribuição:")
    for direcao, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        if sampled == 0:
            continue
        pct = (n / sampled) * 100
        print(f"  {direcao:10s} {n:5d}  ({pct:5.1f}%)")

    borderline = sum(1 for r in rows if r["borderline"] == "X")
    print(f"\nBorderline (suspeito): {borderline} frames ({(borderline / max(1, sampled)) * 100:.1f}%)")
    print(f"\nCSV: {out_path}")
    print("\nCorra `head -50` no CSV ou abra no Excel pra ver frames borderline.")
    print("Cruze os time_s com o vídeo pra confirmar visualmente onde o sistema errou.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("video_path", help="Caminho do video .mp4")
    parser.add_argument(
        "--every",
        type=int,
        default=10,
        help="Sample 1 a cada N frames (default 10 — ~3 fps em video 30fps)",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Caminho do CSV de saida (default: ao lado do video)",
    )
    args = parser.parse_args()

    if not os.path.exists(args.video_path):
        print(f"Video nao encontrado: {args.video_path}")
        sys.exit(1)

    out_path = args.out or os.path.splitext(args.video_path)[0] + "_gaze_audit.csv"
    audit_video(args.video_path, args.every, out_path)


if __name__ == "__main__":
    main()
