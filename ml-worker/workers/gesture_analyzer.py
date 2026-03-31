import time

import cv2
import mediapipe as mp
import numpy as np
import structlog

from workers.posture_analyzer import extract_frames

logger = structlog.get_logger()

mp_hands = mp.solutions.hands
mp_face_mesh = mp.solutions.face_mesh

# Iris landmarks for gaze estimation
LEFT_IRIS = [468, 469, 470, 471, 472]
RIGHT_IRIS = [473, 474, 475, 476, 477]
LEFT_EYE_CORNERS = [33, 133]
RIGHT_EYE_CORNERS = [362, 263]


def _estimate_gaze_centered(face_landmarks) -> bool:
    """Estimate if person is looking at camera based on iris position."""
    lm = face_landmarks.landmark

    # Left eye: check if iris is centered between eye corners
    left_corner_l = np.array([lm[33].x, lm[33].y])
    left_corner_r = np.array([lm[133].x, lm[133].y])
    left_iris = np.array([lm[468].x, lm[468].y])

    left_eye_width = np.linalg.norm(left_corner_r - left_corner_l)
    left_iris_offset = np.linalg.norm(left_iris - (left_corner_l + left_corner_r) / 2)
    left_centered = left_iris_offset / (left_eye_width + 1e-8) < 0.25

    # Right eye
    right_corner_l = np.array([lm[362].x, lm[362].y])
    right_corner_r = np.array([lm[263].x, lm[263].y])
    right_iris = np.array([lm[473].x, lm[473].y])

    right_eye_width = np.linalg.norm(right_corner_r - right_corner_l)
    right_iris_offset = np.linalg.norm(
        right_iris - (right_corner_l + right_corner_r) / 2
    )
    right_centered = right_iris_offset / (right_eye_width + 1e-8) < 0.25

    return left_centered and right_centered


def analyze_gestures(video_path: str) -> dict:
    """Analyze hand gestures and eye contact from video frames."""
    start = time.time()
    logger.info("gesture_analysis_start", video_path=video_path)

    frames = extract_frames(video_path, fps=2)
    if not frames:
        return {"score": 0, "confidence": "failed", "metrics": {}}

    hands_visible_count = 0
    above_waist_count = 0
    eye_contact_count = 0
    face_detected_count = 0
    hand_detected_count = 0
    total_frames = len(frames)

    hands = mp_hands.Hands(
        static_image_mode=True,
        max_num_hands=2,
        min_detection_confidence=0.5,
    )
    face_mesh = mp_face_mesh.FaceMesh(
        static_image_mode=True,
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
    )

    for frame_path in frames:
        image = cv2.imread(frame_path)
        if image is None:
            continue

        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Hand detection
        hand_results = hands.process(rgb)
        if hand_results.multi_hand_landmarks:
            hand_detected_count += 1
            hands_visible_count += 1

            # Check if hands are above waist (y < 0.6 in normalized coords)
            for hand_lm in hand_results.multi_hand_landmarks:
                wrist_y = hand_lm.landmark[0].y
                if wrist_y < 0.6:
                    above_waist_count += 1
                    break

        # Face/gaze detection
        face_results = face_mesh.process(rgb)
        if face_results.multi_face_landmarks:
            face_detected_count += 1
            face_lm = face_results.multi_face_landmarks[0]
            if _estimate_gaze_centered(face_lm):
                eye_contact_count += 1

    hands.close()
    face_mesh.close()

    # Calculate metrics
    gesticulation_pct = (
        round(hands_visible_count / total_frames * 100, 1) if total_frames > 0 else 0.0
    )
    above_waist_pct = round(above_waist_count / max(1, hands_visible_count) * 100, 1)
    eye_contact_pct = round(eye_contact_count / max(1, face_detected_count) * 100, 1)

    # Gesture score (0-100)
    # Moderate gesticulation (30-70%) is ideal
    if gesticulation_pct < 10:
        gesture_sub = 30  # Too little
    elif gesticulation_pct > 80:
        gesture_sub = 60  # Too much
    else:
        gesture_sub = min(100, 50 + gesticulation_pct)

    eye_sub = min(100, eye_contact_pct * 1.2)
    zone_sub = above_waist_pct  # Above waist = positive

    gesture_score = round(gesture_sub * 0.35 + eye_sub * 0.4 + zone_sub * 0.25)
    gesture_score = max(0, min(100, gesture_score))

    # Confidence
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
