import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

from analyzers.behavioral.utils import (
    POSE_LANDMARKER_PATH, ensure_pose_model, iter_frames, MIN_FRAMES,
)

# Shoulder landmark indices in MediaPipe Pose
_L_SHOULDER = 11
_R_SHOULDER = 12

# Leaning threshold: shoulder midpoint horizontal drift
_LEAN_THRESHOLD = 0.04


def analyze(video_path: str) -> dict:
    ensure_pose_model()

    opts = vision.PoseLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=POSE_LANDMARKER_PATH),
        num_poses=1,
    )
    landmarker = vision.PoseLandmarker.create_from_options(opts)

    shoulder_mids_x: list[float] = []
    shoulder_mids_y: list[float] = []
    shoulder_widths: list[float] = []
    leaning_events  = 0
    frames_processed = 0

    try:
        for frame in iter_frames(video_path):
            frames_processed += 1
            rgb      = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result   = landmarker.detect(mp_image)

            if result.pose_landmarks:
                lm = result.pose_landmarks[0]
                ls = lm[_L_SHOULDER]
                rs = lm[_R_SHOULDER]
                mid_x = (ls.x + rs.x) / 2
                mid_y = (ls.y + rs.y) / 2
                width = abs(rs.x - ls.x)
                shoulder_mids_x.append(mid_x)
                shoulder_mids_y.append(mid_y)
                shoulder_widths.append(width)
    finally:
        landmarker.close()

    if len(shoulder_mids_x) < MIN_FRAMES:
        return _default()

    xs = np.array(shoulder_mids_x)
    ys = np.array(shoulder_mids_y)

    # Leaning events: horizontal drift from median
    median_x = float(np.median(xs))
    leaning_events = int(np.sum(np.abs(xs - median_x) > _LEAN_THRESHOLD))

    # Stability: low std = stable posture
    x_std = float(np.std(xs))
    y_std = float(np.std(ys))
    total_std = x_std + y_std

    stability_raw    = max(0.0, 1.0 - total_std / 0.08)
    posture_score    = min(100, max(0, round(stability_raw * 100)))
    lean_penalty     = min(25, leaning_events * 2)
    posture_score    = max(0, posture_score - lean_penalty)

    if posture_score >= 85:   level = "Excellent"
    elif posture_score >= 70: level = "Good"
    elif posture_score >= 50: level = "Fair"
    else:                     level = "Poor"

    return {
        "posture_score":   posture_score,
        "posture_level":   level,
        "leaning_events":  leaning_events,
        "frames_analyzed": frames_processed,
    }


def _default() -> dict:
    return {
        "posture_score": 0, "posture_level": "Poor",
        "leaning_events": 0, "frames_analyzed": 0,
    }
