import asyncio
import base64
import json
import logging
import math
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
from realtime.whisper_transcriber import transcribe_session

log = logging.getLogger("realtime")

_DIR        = os.path.join(os.path.dirname(__file__), "..", "analyzers")
_FACE_MODEL = os.path.join(_DIR, "blaze_face_short_range.tflite")
_LAND_MODEL = os.path.join(_DIR, "face_landmarker.task")

# ── Landmark indices ──────────────────────────────────────────────────────────
_LEFT_IRIS  = [474, 475, 476, 477]
_RIGHT_IRIS = [469, 470, 471, 472]
_LEFT_EYE   = [33, 133]
_RIGHT_EYE  = [362, 263]
_LEFT_TB    = [159, 145]   # top/bottom eyelid for vertical gaze

# Gaze thresholds (relaxed — tighter thresholds cause more UNKNOWN)
_H_THRESH   = 0.12
_V_THRESH   = 0.10

# Head-pose thresholds (degrees) — beyond these we classify as "looking away"
_YAW_THRESH   = 20.0
_PITCH_THRESH = 20.0

METRIC_INTERVAL  = 0.4   # send metrics every 400 ms
_executor        = ThreadPoolExecutor(max_workers=3, thread_name_prefix="mediapipe")

# ── 3-D model points for solvePnP head pose ───────────────────────────────────
# Canonical face model (mm), indices: nose tip, chin, L eye corner,
# R eye corner, L mouth, R mouth
_MODEL_POINTS = np.array([
    [0.0,    0.0,    0.0   ],  # nose tip       (1)
    [0.0,   -63.6,  -12.5 ],  # chin            (152)
    [-43.3,  32.7,  -26.0 ],  # L eye outer     (226)
    [ 43.3,  32.7,  -26.0 ],  # R eye outer     (446)
    [-28.9, -28.9,  -24.1 ],  # L mouth corner  (57)
    [ 28.9, -28.9,  -24.1 ],  # R mouth corner  (287)
], dtype=np.float64)

_LAND_IDS = [1, 152, 226, 446, 57, 287]  # matching landmark indices


def _build_face_detector():
    opts = vision.FaceDetectorOptions(
        base_options=mp_python.BaseOptions(model_asset_path=_FACE_MODEL)
    )
    return vision.FaceDetector.create_from_options(opts)


def _build_landmarker():
    opts = vision.FaceLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=_LAND_MODEL),
        output_face_blendshapes=False,
        output_facial_transformation_matrixes=True,   # needed for head pose
        num_faces=1,
    )
    return vision.FaceLandmarker.create_from_options(opts)


# ── Landmark confidence proxy ─────────────────────────────────────────────────
def _landmark_confidence(lm: list, h: int, w: int) -> float:
    """
    Mediapipe FaceLandmarker doesn't expose a per-landmark score.
    We proxy confidence by checking:
    1. All key landmarks are within frame bounds
    2. Iris landmarks are self-consistent (iris radius reasonable)
    Returns 0.0–1.0.
    """
    scores = []

    # Bounds check on key landmarks
    key_ids = _LEFT_IRIS + _RIGHT_IRIS + _LEFT_EYE + _RIGHT_EYE + _LEFT_TB
    out_of_bounds = sum(
        1 for i in key_ids
        if not (0.0 <= lm[i].x <= 1.0 and 0.0 <= lm[i].y <= 1.0)
    )
    scores.append(max(0.0, 1.0 - out_of_bounds / len(key_ids)))

    # Iris radius sanity — should be 1–8% of image width
    for iris_ids in (_LEFT_IRIS, _RIGHT_IRIS):
        cx = sum(lm[i].x for i in iris_ids) / 4 * w
        cy = sum(lm[i].y for i in iris_ids) / 4 * h
        r  = max(
            math.hypot((lm[i].x * w - cx), (lm[i].y * h - cy))
            for i in iris_ids
        )
        ratio = r / w
        scores.append(1.0 if 0.008 <= ratio <= 0.08 else 0.2)

    return float(np.mean(scores))


# ── Head pose via solvePnP ────────────────────────────────────────────────────
def _head_pose(lm: list, h: int, w: int) -> tuple[float, float, float]:
    """Returns (yaw, pitch, roll) in degrees."""
    image_points = np.array(
        [[lm[i].x * w, lm[i].y * h] for i in _LAND_IDS],
        dtype=np.float64,
    )
    focal   = w                          # approximate focal length
    cam_mat = np.array([
        [focal, 0,     w / 2],
        [0,     focal, h / 2],
        [0,     0,     1    ],
    ], dtype=np.float64)
    dist = np.zeros((4, 1))

    ok, rvec, _ = cv2.solvePnP(
        _MODEL_POINTS, image_points, cam_mat, dist,
        flags=cv2.SOLVEPNP_ITERATIVE,
    )
    if not ok:
        return 0.0, 0.0, 0.0

    rmat, _ = cv2.Rodrigues(rvec)
    # Decompose rotation matrix to Euler angles
    sy   = math.sqrt(rmat[0, 0] ** 2 + rmat[1, 0] ** 2)
    pitch = math.degrees(math.atan2(-rmat[2, 0], sy))
    yaw   = math.degrees(math.atan2( rmat[1, 0], rmat[0, 0]))
    roll  = math.degrees(math.atan2( rmat[2, 1], rmat[2, 2]))
    return yaw, pitch, roll


# ── Iris-based gaze ───────────────────────────────────────────────────────────
def _iris_gaze(lm: list) -> str:
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


# ── Combined gaze (iris + head pose) ─────────────────────────────────────────
def _combined_gaze(lm: list, h: int, w: int) -> tuple[str, float, float, float, float]:
    """
    Returns (gaze_label, confidence, yaw, pitch, roll).
    Head pose overrides iris gaze when head is significantly rotated.
    """
    yaw, pitch, roll = _head_pose(lm, h, w)
    iris             = _iris_gaze(lm)
    conf             = _landmark_confidence(lm, h, w)

    # Head-pose override
    if abs(yaw) > _YAW_THRESH:
        gaze = "right" if yaw > 0 else "left"
    elif pitch > _PITCH_THRESH:
        gaze = "down"
    else:
        gaze = iris   # trust iris when head is roughly forward

    return gaze, conf, yaw, pitch, roll


# ── Frame decode ─────────────────────────────────────────────────────────────
def _decode_frame(b64: str) -> np.ndarray | None:
    try:
        arr = np.frombuffer(base64.b64decode(b64), dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        return cv2.resize(img, (320, 240)) if img is not None else None
    except Exception:
        return None


# ── Sync MediaPipe processing (runs in thread pool) ───────────────────────────
def _process_frame_sync(
    frame: np.ndarray,
    face_detector,
    landmarker,
) -> tuple[bool, int, str, float, float, float, float]:
    """Returns (detected, count, gaze, confidence, yaw, pitch, roll)."""
    h, w  = frame.shape[:2]
    rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

    face_result = face_detector.detect(mp_img)
    detections  = face_result.detections or []
    detected    = len(detections) > 0
    count       = len(detections)

    land_result = landmarker.detect(mp_img)
    if land_result.face_landmarks:
        lm   = land_result.face_landmarks[0]
        gaze, conf, yaw, pitch, roll = _combined_gaze(lm, h, w)
    else:
        gaze, conf, yaw, pitch, roll = "tracking_lost", 0.0, 0.0, 0.0, 0.0

    return detected, count, gaze, conf, yaw, pitch, roll


# ── WebSocket handler ─────────────────────────────────────────────────────────
async def handle_ws(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()
    session = create_session(session_id)
    log.info("[WS] Session started: %s", session_id)

    face_detector    = _build_face_detector()
    landmarker       = _build_landmarker()
    frames_received  = 0
    frames_processed = 0
    last_metric_send = 0.0
    loop             = asyncio.get_event_loop()

    try:
        while True:
            raw  = await websocket.receive_text()
            msg  = json.loads(raw)
            kind = msg.get("type")

            if kind == "frame":
                frames_received += 1
                frame = _decode_frame(msg.get("data", ""))
                if frame is None:
                    continue

                try:
                    detected, count, gaze, conf, yaw, pitch, roll = \
                        await loop.run_in_executor(
                            _executor, _process_frame_sync,
                            frame, face_detector, landmarker,
                        )
                except Exception as e:
                    log.warning("[WS] Frame processing error: %s", e)
                    continue

                frames_processed      += 1
                session.face_detected  = detected
                session.face_count     = count
                session.head_yaw       = yaw
                session.head_pitch     = pitch
                session.head_roll      = roll
                session.update_gaze(gaze, conf)

                now = time.time()
                if now - last_metric_send >= METRIC_INTERVAL:
                    last_metric_send = now
                    payload = session.to_metrics()
                    payload["frames_received"]  = frames_received
                    payload["frames_processed"] = frames_processed
                    await websocket.send_text(json.dumps({"type": "metrics", "payload": payload}))

            elif kind == "audio_chunk":
                # Raw audio bytes from MediaRecorder — buffered for Whisper at session end
                raw_audio = msg.get("data", "")
                if raw_audio:
                    try:
                        session.add_audio_chunk(base64.b64decode(raw_audio))
                    except Exception:
                        pass

            elif kind == "transcript":
                session.update_transcript(msg.get("text", ""))

            elif kind == "end_session":
                # Frontend signals session is ending — run Whisper now
                log.info("[WS] end_session received, running Whisper on %d chunks",
                         len(session.audio_chunks))
                if session.audio_chunks:
                    try:
                        result = await loop.run_in_executor(
                            _executor, transcribe_session, session.audio_chunks
                        )
                        session.set_whisper_result(result)
                        log.info("[WS] Whisper done: %d words, quality=%s",
                                 result["word_count"], result["transcript_quality"])
                        await websocket.send_text(json.dumps({
                            "type":    "whisper_result",
                            "payload": result,
                        }))
                    except Exception as e:
                        log.error("[WS] Whisper failed: %s", e)

            elif kind == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))

    except WebSocketDisconnect as e:
        log.info("[WS] Client disconnected: session=%s code=%s", session_id, e.code)

    except Exception as e:
        log.error("[WS] Unexpected error: %s\n%s", e, traceback.format_exc())
        try:
            await websocket.close(code=1011, reason=str(e)[:100])
        except Exception:
            pass

    finally:
        log.info("[WS] Session closed: %s | rx=%d proc=%d",
                 session_id, frames_received, frames_processed)
        try:
            face_detector.close()
        except Exception:
            pass
        delete_session(session_id)
