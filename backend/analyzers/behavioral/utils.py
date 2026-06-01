import os
import cv2
import numpy as np
import urllib.request
from typing import Generator

# ── Model paths ───────────────────────────────────────────────────────────────
_BASE = os.path.join(os.path.dirname(__file__), "..", "face_landmarker.task")
FACE_LANDMARKER_PATH = os.path.abspath(_BASE)

_POSE_PATH = os.path.join(os.path.dirname(__file__), "pose_landmarker_lite.task")
POSE_LANDMARKER_PATH = os.path.abspath(_POSE_PATH)
POSE_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
)

# ── Configurable thresholds ───────────────────────────────────────────────────
FRAME_SKIP        = 3    # process every Nth frame (performance)
MIN_FRAMES        = 10   # minimum frames needed for meaningful analysis


def ensure_pose_model() -> None:
    if not os.path.exists(POSE_LANDMARKER_PATH):
        urllib.request.urlretrieve(POSE_MODEL_URL, POSE_LANDMARKER_PATH)


def iter_frames(video_path: str, skip: int = FRAME_SKIP) -> Generator[np.ndarray, None, None]:
    """Yield BGR frames from a video file, skipping every `skip` frames."""
    cap = cv2.VideoCapture(video_path)
    idx = 0
    try:
        while cap.isOpened():
            ok, frame = cap.read()
            if not ok:
                break
            if idx % skip == 0:
                yield frame
            idx += 1
    finally:
        cap.release()


def frame_count(video_path: str, skip: int = FRAME_SKIP) -> int:
    cap = cv2.VideoCapture(video_path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    return max(1, total // skip)
