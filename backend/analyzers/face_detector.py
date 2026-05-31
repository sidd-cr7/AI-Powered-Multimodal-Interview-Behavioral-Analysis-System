import cv2
import mediapipe as mp

def analyze(video_path: str) -> dict:
    mp_face = mp.solutions.face_detection
    cap = cv2.VideoCapture(video_path)

    frames_processed = 0
    frames_with_face = 0
    max_faces_seen = 0

    with mp_face.FaceDetection(model_selection=1, min_detection_confidence=0.5) as detector:
        while cap.isOpened():
            ok, frame = cap.read()
            if not ok:
                break
            frames_processed += 1
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = detector.process(rgb)
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
