import base64
import json
import logging
import numpy as np
import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision
from fastapi import WebSocket, WebSocketDisconnect

from realtime.session import create_session, get_session, delete_session, RealtimeSession

log = logging.getLogger("realtime")

# ── MediaPipe model paths (reuse models already downloaded by analyzers) ──────
import os
_DIR = os.path.join(os.path.dirname(__file__), "..", "analyzers")
_FACE_MODEL = os.path.join(_DIR, "blaze_face_short_range.tflite")
_LAND_MODEL = os.path.join(_DIR, "face_landmarker.task")

# ── Landmark indices ──────────────────────────────────────────────────────────
_LEFT_IRIS  = [474, 475, 476, 477]
_RIGHT_IRIS = [469, 470, 471, 472]
_LEFT_EYE   = [33, 133]
_RIGHT_EYE  = [362, 263]
_LEFT_TB    = [159, 145]
_H_THRESH   = 0.15
_V_THRESH   = 0.12


def _build_face_detector():
    opts = vision.FaceDetectorOptions(
        base_options=mp_python.BaseOptions(model_asset_path=_FACE_MODEL)
    )
    return vision.FaceDetector.create_from_options(opts)


def _build_landmarker():
    opts = vision.FaceLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=_LAND_MODEL),
        output_face_blendshapes=False,
        output_facial_transformation_matrixes=False,
        num_faces=1,
    )
    return vision.FaceLandmarker.create_from_options(opts)


def _gaze_from_landmarks(lm) -> str:
    def h_off(iris_ids, corner_ids):
        ix = sum(lm[i].x for i in iris_ids) / len(iris_ids)
        lx, rx = lm[corner_ids[0]].x, lm[corner_ids[1]].x
        w = abs(rx - lx) or 1e-6
        return (ix - (lx + rx) / 2) / w

    def v_off(iris_ids, tb_ids):
        iy = sum(lm[i].y for i in iris_ids) / len(iris_ids)
        ty, by = lm[tb_ids[0]].y, lm[tb_ids[1]].y
        h = abs(by - ty) or 1e-6
        return (iy - (ty + by) / 2) / h

    h = (h_off(_LEFT_IRIS, _LEFT_EYE) + h_off(_RIGHT_IRIS, _RIGHT_EYE)) / 2
    v = v_off(_LEFT_IRIS, _LEFT_TB)

    if v > _V_THRESH:   return "down"
    if h < -_H_THRESH:  return "left"
    if h > _H_THRESH:   return "right"
    return "center"


def _decode_frame(b64: str) -> np.ndarray | None:
    try:
        data = base64.b64decode(b64)
        arr  = np.frombuffer(data, dtype=np.uint8)
        return cv2.imdecode(arr, cv2.IMREAD_COLOR)
    except Exception:
        return None


async def handle_ws(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()
    session = create_session(session_id)
    log.info("Realtime session started: %s", session_id)

    face_detector = _build_face_detector()
    landmarker    = _build_landmarker()

    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            kind = msg.get("type")

            # ── Frame: run vision analysis ────────────────────────────────────
            if kind == "frame":
                frame = _decode_frame(msg.get("data", ""))
                if frame is None:
                    continue

                rgb      = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

                # Face detection
                face_result          = face_detector.detect(mp_image)
                detections           = face_result.detections or []
                session.face_detected = len(detections) > 0
                session.face_count    = len(detections)

                # Gaze tracking
                land_result = landmarker.detect(mp_image)
                if land_result.face_landmarks:
                    gaze = _gaze_from_landmarks(land_result.face_landmarks[0].landmark)
                    session.update_gaze(gaze)
                else:
                    session.update_gaze("unknown")

                await websocket.send_text(json.dumps({
                    "type":    "metrics",
                    "payload": session.to_metrics(),
                }))

            # ── Transcript update from Web Speech API ─────────────────────────
            elif kind == "transcript":
                session.update_transcript(msg.get("text", ""))

            # ── Ping / keepalive ──────────────────────────────────────────────
            elif kind == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))

    except WebSocketDisconnect:
        log.info("Realtime session ended: %s", session_id)
    except Exception as e:
        log.error("Realtime error [%s]: %s", session_id, e)
    finally:
        face_detector.close()
        delete_session(session_id)
