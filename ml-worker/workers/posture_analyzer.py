import subprocess
import time
from pathlib import Path

import mediapipe as mp
import numpy as np
import structlog

logger = structlog.get_logger()

mp_pose = mp.solutions.pose


def extract_frames(video_path: str, fps: int = 2) -> list[str]:
    """Extract frames from video at given fps using FFmpeg."""
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
    """Calculate angle at point b between segments ba and bc."""
    ba = a - b
    bc = c - b
    cosine = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-8)
    return float(np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0))))


def analyze_posture(video_path: str) -> dict:
    """Analyze posture from video frames using MediaPipe Pose."""
    start = time.time()
    logger.info("posture_analysis_start", video_path=video_path)

    frames = extract_frames(video_path, fps=2)
    if not frames:
        logger.warning("no_frames_extracted")
        return {"score": 0, "confidence": "failed", "metrics": {}}

    import cv2

    alignment_scores = []
    open_posture_count = 0
    centers_of_mass = []
    detected_frames = 0

    with mp_pose.Pose(static_image_mode=True, min_detection_confidence=0.5) as pose:
        for frame_path in frames:
            image = cv2.imread(frame_path)
            if image is None:
                continue

            results = pose.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            if not results.pose_landmarks:
                continue

            detected_frames += 1
            lm = results.pose_landmarks.landmark

            # Key landmarks
            left_shoulder = np.array([lm[11].x, lm[11].y])
            right_shoulder = np.array([lm[12].x, lm[12].y])
            left_hip = np.array([lm[23].x, lm[23].y])
            right_hip = np.array([lm[24].x, lm[24].y])
            nose = np.array([lm[0].x, lm[0].y])

            # Shoulder alignment (horizontal = good)
            shoulder_tilt = abs(left_shoulder[1] - right_shoulder[1])
            shoulder_score = max(0, 100 - shoulder_tilt * 500)

            # Head alignment (centered above shoulders)
            shoulder_center = (left_shoulder + right_shoulder) / 2
            head_offset = abs(nose[0] - shoulder_center[0])
            head_score = max(0, 100 - head_offset * 300)

            # Spine alignment
            hip_center = (left_hip + right_hip) / 2
            spine_angle = _angle_between(
                np.array([shoulder_center[0], 0]),
                shoulder_center,
                hip_center,
            )
            spine_score = max(0, 100 - abs(spine_angle - 180) * 2)

            alignment = round((shoulder_score + head_score + spine_score) / 3)
            alignment_scores.append(alignment)

            # Open vs closed posture (shoulder width relative to hip width)
            shoulder_width = np.linalg.norm(left_shoulder - right_shoulder)
            hip_width = np.linalg.norm(left_hip - right_hip)
            if shoulder_width > hip_width * 0.9:
                open_posture_count += 1

            # Center of mass for stability
            com = (shoulder_center + hip_center) / 2
            centers_of_mass.append(com)

    if detected_frames == 0:
        logger.warning("no_poses_detected")
        return {"score": 0, "confidence": "failed", "metrics": {}}

    # Calculate final metrics
    avg_alignment = round(float(np.mean(alignment_scores)))
    open_posture_pct = round(open_posture_count / detected_frames * 100, 1)

    # Stability score (lower variance = more stable)
    if len(centers_of_mass) > 1:
        com_array = np.array(centers_of_mass)
        com_variance = float(np.var(com_array, axis=0).sum())
        stability_score = round(max(0, 100 - com_variance * 10000))
    else:
        stability_score = 50

    # Overall posture score
    posture_score = round(
        avg_alignment * 0.4 + min(100, open_posture_pct) * 0.3 + stability_score * 0.3
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
        duration_seconds=round(elapsed, 2),
    )

    return {
        "score": posture_score,
        "confidence": confidence,
        "metrics": {
            "alignment_score": avg_alignment,
            "open_posture_pct": open_posture_pct,
            "stability_score": stability_score,
            "detected_frames": detected_frames,
            "total_frames": len(frames),
        },
    }
