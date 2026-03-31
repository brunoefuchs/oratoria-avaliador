import time

import mediapipe as mp
import numpy as np
import structlog

from workers.posture_analyzer import extract_frames

logger = structlog.get_logger()

HAND_MODEL_PATH = "/tmp/mediapipe_models/hand_landmarker.task"
FACE_MODEL_PATH = "/tmp/mediapipe_models/face_landmarker.task"


def _estimate_gaze_centered(face_landmarks) -> bool:
    """Estimate if person is looking at camera based on nose/eye alignment."""
    lm = face_landmarks
    # Simple gaze: check if nose tip is centered between eyes
    left_eye = np.array([lm[33].x, lm[33].y])
    right_eye = np.array([lm[263].x, lm[263].y])
    nose_tip = np.array([lm[1].x, lm[1].y])

    eye_center = (left_eye + right_eye) / 2
    offset = np.linalg.norm(nose_tip - eye_center)
    eye_dist = np.linalg.norm(right_eye - left_eye)

    return offset / (eye_dist + 1e-8) < 0.35


def analyze_gestures(video_path: str) -> dict:
    """Analyze hand gestures and eye contact from video frames."""
    start = time.time()
    logger.info("gesture_analysis_start", video_path=video_path)

    frames = extract_frames(video_path, fps=2)
    if not frames:
        return {"score": 0, "confidence": "failed", "metrics": {}}

    BaseOptions = mp.tasks.BaseOptions
    HandLandmarker = mp.tasks.vision.HandLandmarker
    HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
    FaceLandmarker = mp.tasks.vision.FaceLandmarker
    FaceLandmarkerOptions = mp.tasks.vision.FaceLandmarkerOptions
    VisionRunningMode = mp.tasks.vision.RunningMode

    hand_options = HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=HAND_MODEL_PATH),
        running_mode=VisionRunningMode.IMAGE,
        num_hands=2,
    )

    face_options = FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=FACE_MODEL_PATH),
        running_mode=VisionRunningMode.IMAGE,
        num_faces=1,
    )

    hands_visible_count = 0
    above_waist_count = 0
    eye_contact_count = 0
    face_detected_count = 0
    hand_detected_count = 0
    total_frames = len(frames)

    hand_landmarker = HandLandmarker.create_from_options(hand_options)
    face_landmarker = FaceLandmarker.create_from_options(face_options)

    for frame_path in frames:
        image = mp.Image.create_from_file(frame_path)

        # Hand detection
        hand_results = hand_landmarker.detect(image)
        if hand_results.hand_landmarks and len(hand_results.hand_landmarks) > 0:
            hand_detected_count += 1
            hands_visible_count += 1

            for hand_lm in hand_results.hand_landmarks:
                wrist_y = hand_lm[0].y
                if wrist_y < 0.6:
                    above_waist_count += 1
                    break

        # Face/gaze detection
        face_results = face_landmarker.detect(image)
        if face_results.face_landmarks and len(face_results.face_landmarks) > 0:
            face_detected_count += 1
            if _estimate_gaze_centered(face_results.face_landmarks[0]):
                eye_contact_count += 1

    hand_landmarker.close()
    face_landmarker.close()

    # Calculate metrics
    gesticulation_pct = (
        round(hands_visible_count / total_frames * 100, 1) if total_frames > 0 else 0.0
    )
    above_waist_pct = round(above_waist_count / max(1, hands_visible_count) * 100, 1)
    eye_contact_pct = round(eye_contact_count / max(1, face_detected_count) * 100, 1)

    # Gesture score
    if gesticulation_pct < 10:
        gesture_sub = 30
    elif gesticulation_pct > 80:
        gesture_sub = 60
    else:
        gesture_sub = min(100, 50 + gesticulation_pct)

    eye_sub = min(100, eye_contact_pct * 1.2)
    zone_sub = above_waist_pct

    gesture_score = round(gesture_sub * 0.35 + eye_sub * 0.4 + zone_sub * 0.25)
    gesture_score = max(0, min(100, gesture_score))

    detection_rate = (
        (hand_detected_count + face_detected_count) / (total_frames * 2)
        if total_frames > 0
        else 0
    )

    if detection_rate > 0.5:
        confidence = "high"
    elif detection_rate > 0.25:
        confidence = "medium"
    else:
        confidence = "low"

    elapsed = time.time() - start
    logger.info(
        "gesture_analysis_complete",
        score=gesture_score,
        gesticulation_pct=gesticulation_pct,
        eye_contact_pct=eye_contact_pct,
        duration_seconds=round(elapsed, 2),
    )

    return {
        "score": gesture_score,
        "confidence": confidence,
        "metrics": {
            "gesticulation_pct": gesticulation_pct,
            "above_waist_pct": above_waist_pct,
            "eye_contact_pct": eye_contact_pct,
            "hand_detected_frames": hand_detected_count,
            "face_detected_frames": face_detected_count,
            "total_frames": total_frames,
        },
    }
