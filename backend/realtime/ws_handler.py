import asyncio
import base64
import json
import logging
import os
import time
import traceback
from concurrent.futures import ThreadPoolExecutor

import cv2
import mediapipe as mp
import numpy as np
from fastapi import WebSocket, WebSocketDisconnect
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

from realtime.session import create_session, delete_session

log = logging.getLogger("realtime")

_DIR        = os.path.join(os.path.dirname(__file__), "..", "analyzers")
_FACE_MODEL = os.path.join(_DIR, "blaze_face_short_range.tflite")
_LAND_MODEL = os.path.join(_DIR, "face_landmarker.task")

_LEFT_IRIS  = [474, 475, 476, 477]
_RIGHT_IRIS = [469, 470, 471, 472]
_LEFT_EYE   = [33, 133]
_RIGHT_EYE  = [362, 263]
_LEFT_TB    = [159, 145]
_H_THRESH   = 0.15
_V_THRESH   = 0.12

METRIC_INTERVAL = 0.5   # send metrics every 500 ms max
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="mediapipe")


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

    if v > _V_THRESH:  return "down"
    if h < -_H_THRESH: return "left"
    if h > _H_THRESH:  return "right"
    return "center"


def _decode_frame(b64: str) -> np.ndarray | None:
    try:
        data = base64.b64decode(b64)
        arr  = np.frombuffer(data, dtype=np.uint8)
        img  = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return None
        # Resize to 320x240 for faster processing regardless of what frontend sends
        return cv2.resize(img, (320, 240))
    except Exception:
        return None


def _process_frame_sync(frame: np.ndarray, face_detector, landmarker) -> tuple[bool, int, str]:
    """Run both MediaPipe models synchronously — called inside thread pool."""
    rgb      = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

    face_result = face_detector.detect(mp_image)
    detections  = face_result.detections or []
    detected    = len(detections) > 0
    count       = len(detections)

    land_result = landmarker.detect(mp_image)
    if land_result.face_landmarks:
        gaze = _gaze_from_landmarks(land_result.face_landmarks[0])
    else:
        gaze = "unknown"

    return detected, count, gaze


async def handle_ws(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()
    session = create_session(session_id)
    log.info("[WS] Session started: %s", session_id)

    face_detector = _build_face_detector()
    landmarker    = _build_landmarker()

    frames_received  = 0
    frames_processed = 0
    last_metric_send = 0.0
    last_frame_time  = time.time()
    loop             = asyncio.get_event_loop()

    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            kind = msg.get("type")

            if kind == "frame":
                frames_received += 1
                last_frame_time  = time.time()

                frame = _decode_frame(msg.get("data", ""))
                if frame is None:
                    continue

                # ── Run MediaPipe in thread pool — never blocks event loop ────
                try:
                    detected, count, gaze = await loop.run_in_executor(
                        _executor,
                        _process_frame_sync,
                        frame, face_detector, landmarker,
                    )
                except Exception as e:
                    log.warning("[WS] Frame processing error (skipping): %s", e)
                    continue
                frames_processed += 1

                session.face_detected = detected
                session.face_count    = count
                session.update_gaze(gaze)

                # ── Rate-limit metric sends to METRIC_INTERVAL ────────────────
                now = time.time()
                if now - last_metric_send >= METRIC_INTERVAL:
                    last_metric_send = now
                    payload = session.to_metrics()
                    payload["frames_received"]  = frames_received
                    payload["frames_processed"] = frames_processed
                    await websocket.send_text(json.dumps({
                        "type":    "metrics",
                        "payload": payload,
                    }))

            elif kind == "transcript":
                session.update_transcript(msg.get("text", ""))

            elif kind == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))

    except WebSocketDisconnect as e:
        log.info("[WS] Client disconnected: session=%s code=%s reason=%s",
                 session_id, e.code, e.reason)

    except Exception as e:
        log.error("[WS] Unexpected error: session=%s error=%s\n%s",
                  session_id, e, traceback.format_exc())
        try:
            await websocket.close(code=1011, reason=str(e)[:100])
        except Exception:
            pass

    finally:
        log.info("[WS] Session closed: %s | frames_rx=%d frames_proc=%d",
                 session_id, frames_received, frames_processed)
        try:
            face_detector.close()
        except Exception:
            pass
        delete_session(session_id)
