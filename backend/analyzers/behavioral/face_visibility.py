import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

from backend.analyzers.behavioral.utils import (
    FACE_LANDMARKER_PATH, iter_frames, MIN_FRAMES,
)


_FACE_DETECTOR_PATH = FACE_LANDMARKER_PATH.replace(
    "face_landmarker.task", "blaze_face_short_range.tflite"
)


def analyze(video_path: str) -> dict:
    opts = vision.FaceDetectorOptions(
        base_options=mp_python.BaseOptions(model_asset_path=_FACE_DETECTOR_PATH)
    )
    detector = vision.FaceDetector.create_from_options(opts)

    frames_total    = 0
    frames_with_face = 0
    face_loss_events = 0
    prev_had_face    = True

    try:
        for frame in iter_frames(video_path):
            frames_total += 1
            rgb      = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result   = detector.detect(mp_image)
            has_face = len(result.detections) > 0

            if has_face:
                frames_with_face += 1
            elif prev_had_face:
                face_loss_events += 1

            prev_had_face = has_face
    finally:
        detector.close()

    if frames_total < MIN_FRAMES:
        return _default()

    presence_pct        = round(frames_with_face / frames_total * 100, 1)
    face_visibility_score = min(100, max(0, round(
        presence_pct - face_loss_events * 3
    )))

    return {
        "face_visibility_score": face_visibility_score,
        "face_presence_pct":     presence_pct,
        "face_loss_events":      face_loss_events,
        "frames_analyzed":       frames_total,
    }


def _default() -> dict:
    return {
        "face_visibility_score": 0,
        "face_presence_pct":     0.0,
        "face_loss_events":      0,
        "frames_analyzed":       0,
    }
