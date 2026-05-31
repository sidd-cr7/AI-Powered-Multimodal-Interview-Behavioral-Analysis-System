import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision
import urllib.request
import os

MODEL_PATH = os.path.join(os.path.dirname(__file__), "blaze_face_short_range.tflite")

def _ensure_model():
    if not os.path.exists(MODEL_PATH):
        url = "https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite"
        urllib.request.urlretrieve(url, MODEL_PATH)

def analyze(video_path: str) -> dict:
    _ensure_model()

    base_options = mp_python.BaseOptions(model_asset_path=MODEL_PATH)
    options = vision.FaceDetectorOptions(base_options=base_options)
    detector = vision.FaceDetector.create_from_options(options)

    cap = cv2.VideoCapture(video_path)
    frames_processed = 0
    frames_with_face = 0
    max_faces_seen = 0

    while cap.isOpened():
        ok, frame = cap.read()
        if not ok:
            break
        frames_processed += 1
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = detector.detect(mp_image)
        count = len(result.detections) if result.detections else 0
        if count > 0:
            frames_with_face += 1
        if count > max_faces_seen:
            max_faces_seen = count

    cap.release()

    return {
        "face_detected": frames_with_face > 0,
        "face_count": max_faces_seen,
        "frames_processed": frames_processed,
        "frames_with_face": frames_with_face,
        "face_presence_percentage": round(frames_with_face / frames_processed * 100, 1) if frames_processed else 0,
    }
