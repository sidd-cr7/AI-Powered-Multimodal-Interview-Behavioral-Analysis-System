import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

from analyzers.behavioral.utils import (
    FACE_LANDMARKER_PATH, iter_frames, MIN_FRAMES, FRAME_SKIP,
)

# Nose tip landmark index
_NOSE_TIP = 1

# Movement threshold: normalised displacement per frame considered a "shift"
_SHIFT_THRESHOLD = 0.015


def analyze(video_path: str) -> dict:
    opts = vision.FaceLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=FACE_LANDMARKER_PATH),
        output_face_blendshapes=False,
        output_facial_transformation_matrixes=False,
        num_faces=1,
    )
    landmarker = vision.FaceLandmarker.create_from_options(opts)

    positions:       list[tuple[float, float]] = []
    movement_events: int = 0
    frames_processed = 0

    try:
        for frame in iter_frames(video_path):
            frames_processed += 1
            rgb      = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result   = landmarker.detect(mp_image)

            if result.face_landmarks:
                lm = result.face_landmarks[0][_NOSE_TIP]
                positions.append((lm.x, lm.y))
    finally:
        landmarker.close()

    if len(positions) < MIN_FRAMES:
        return _default()

    xs = np.array([p[0] for p in positions])
    ys = np.array([p[1] for p in positions])

    # Frame-to-frame displacement
    dx = np.diff(xs)
    dy = np.diff(ys)
    displacements = np.sqrt(dx**2 + dy**2)

    movement_events = int(np.sum(displacements > _SHIFT_THRESHOLD))

    # Stability: low std of position = stable head
    pos_std = float(np.std(xs) + np.std(ys))
    # Map std 0.0 (perfect) → 100, 0.1+ (very unstable) → 0
    stability_raw = max(0.0, 1.0 - pos_std / 0.10)
    head_stability_score = min(100, max(0, round(stability_raw * 100)))

    # Penalise excessive movement events
    event_penalty = min(30, movement_events * 2)
    head_stability_score = max(0, head_stability_score - event_penalty)

    return {
        "head_stability_score": head_stability_score,
        "movement_events":      movement_events,
        "frames_analyzed":      frames_processed,
    }


def _default() -> dict:
    return {"head_stability_score": 0, "movement_events": 0, "frames_analyzed": 0}
