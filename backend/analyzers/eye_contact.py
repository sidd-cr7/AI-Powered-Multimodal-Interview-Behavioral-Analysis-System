import cv2
import mediapipe as mp

LEFT_IRIS  = [474, 475, 476, 477]
RIGHT_IRIS = [469, 470, 471, 472]
LEFT_EYE   = [33, 133]
RIGHT_EYE  = [362, 263]

# Vertical landmarks: top/bottom of left eye
LEFT_EYE_TOP_BOTTOM = [159, 145]

def _h_offset(landmarks, iris_ids: list, corner_ids: list) -> float:
    """Normalised horizontal iris offset: negative = left, positive = right."""
    iris_x  = sum(landmarks[i].x for i in iris_ids) / len(iris_ids)
    left_x  = landmarks[corner_ids[0]].x
    right_x = landmarks[corner_ids[1]].x
    eye_w   = abs(right_x - left_x) or 1e-6
    return (iris_x - (left_x + right_x) / 2) / eye_w

def _v_offset(landmarks, iris_ids: list, top_bottom_ids: list) -> float:
    """Normalised vertical iris offset: positive = down."""
    iris_y  = sum(landmarks[i].y for i in iris_ids) / len(iris_ids)
    top_y   = landmarks[top_bottom_ids[0]].y
    bot_y   = landmarks[top_bottom_ids[1]].y
    eye_h   = abs(bot_y - top_y) or 1e-6
    return (iris_y - (top_y + bot_y) / 2) / eye_h

def analyze(video_path: str, h_thresh: float = 0.15, v_thresh: float = 0.12) -> dict:
    mp_mesh = mp.solutions.face_mesh
    cap = cv2.VideoCapture(video_path)

    frames_processed = 0
    counts = {"center": 0, "left": 0, "right": 0, "down": 0}
    gaze_shifts = 0
    prev_dir: str | None = None

    with mp_mesh.FaceMesh(
        static_image_mode=False,
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    ) as mesh:
        while cap.isOpened():
            ok, frame = cap.read()
            if not ok:
                break
            frames_processed += 1
            rgb    = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = mesh.process(rgb)

            if not result.multi_face_landmarks:
                counts["center"] += 0  # no face = skip frame
                curr_dir = prev_dir or "center"
            else:
                lm     = result.multi_face_landmarks[0].landmark
                h_off  = (_h_offset(lm, LEFT_IRIS, LEFT_EYE) + _h_offset(lm, RIGHT_IRIS, RIGHT_EYE)) / 2
                v_off  = _v_offset(lm, LEFT_IRIS, LEFT_EYE_TOP_BOTTOM)

                if v_off > v_thresh:
                    curr_dir = "down"
                elif h_off < -h_thresh:
                    curr_dir = "left"
                elif h_off > h_thresh:
                    curr_dir = "right"
                else:
                    curr_dir = "center"

                counts[curr_dir] += 1

            if prev_dir is not None and curr_dir != prev_dir:
                gaze_shifts += 1
            prev_dir = curr_dir

    cap.release()

    total = sum(counts.values()) or 1
    dist  = {k: round(v / total * 100, 1) for k, v in counts.items()}

    eye_contact_pct = dist["center"]
    stability = "good" if eye_contact_pct >= 70 else "moderate" if eye_contact_pct >= 40 else "poor"

    return {
        "eye_contact_percentage": eye_contact_pct,
        "looking_away_events": gaze_shifts,
        "gaze_stability": stability,
        "frames_processed": frames_processed,
        "gaze_distribution": dist,
    }
