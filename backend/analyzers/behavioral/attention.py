import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

from backend.analyzers.behavioral.utils import (
    FACE_LANDMARKER_PATH, iter_frames, MIN_FRAMES,
)


_LEFT_IRIS  = [474, 475, 476, 477]
_RIGHT_IRIS = [469, 470, 471, 472]
_LEFT_EYE   = [33, 133]
_RIGHT_EYE  = [362, 263]
_LEFT_TB    = [159, 145]
_H_THRESH   = 0.15
_V_THRESH   = 0.12


def _gaze(lm) -> str:
    def h(iris, corners):
        ix = sum(lm[i].x for i in iris) / len(iris)
        lx, rx = lm[corners[0]].x, lm[corners[1]].x
        w = abs(rx - lx) or 1e-6
        return (ix - (lx + rx) / 2) / w

    def v(iris, tb):
        iy = sum(lm[i].y for i in iris) / len(iris)
        ty, by = lm[tb[0]].y, lm[tb[1]].y
        hh = abs(by - ty) or 1e-6
        return (iy - (ty + by) / 2) / hh

    ho = (h(_LEFT_IRIS, _LEFT_EYE) + h(_RIGHT_IRIS, _RIGHT_EYE)) / 2
    vo = v(_LEFT_IRIS, _LEFT_TB)

    if vo > _V_THRESH:  return "down"
    if ho < -_H_THRESH: return "left"
    if ho > _H_THRESH:  return "right"
    return "center"


def analyze(video_path: str) -> dict:
    opts = vision.FaceLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=FACE_LANDMARKER_PATH),
        output_face_blendshapes=False,
        output_facial_transformation_matrixes=False,
        num_faces=1,
    )
    landmarker = vision.FaceLandmarker.create_from_options(opts)

    gaze_log:    list[str] = []
    gaze_shifts: int = 0
    prev_gaze:   str | None = None
    frames_processed = 0

    try:
        for frame in iter_frames(video_path):
            frames_processed += 1
            rgb      = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result   = landmarker.detect(mp_image)

            if result.face_landmarks:
                g = _gaze(result.face_landmarks[0].landmark)
            else:
                g = "unknown"

            gaze_log.append(g)
            if prev_gaze is not None and g != prev_gaze and g != "unknown":
                gaze_shifts += 1
            prev_gaze = g
    finally:
        landmarker.close()

    if frames_processed < MIN_FRAMES:
        return _default()

    center_frames = sum(1 for g in gaze_log if g == "center")
    eye_contact_pct = round(center_frames / frames_processed * 100, 1)

    # Attention = eye contact weighted with gaze stability
    shift_penalty   = min(30, gaze_shifts * 1)
    attention_score = min(100, max(0, round(eye_contact_pct - shift_penalty)))

    if attention_score >= 80:   level = "High"
    elif attention_score >= 60: level = "Moderate"
    elif attention_score >= 40: level = "Low"
    else:                       level = "Very Low"

    return {
        "attention_score":   attention_score,
        "attention_level":   level,
        "eye_contact_pct":   eye_contact_pct,
        "gaze_shifts":       gaze_shifts,
        "frames_analyzed":   frames_processed,
    }


def _default() -> dict:
    return {
        "attention_score": 0, "attention_level": "Very Low",
        "eye_contact_pct": 0.0, "gaze_shifts": 0, "frames_analyzed": 0,
    }
