import os
import logging
from fastapi import FastAPI, UploadFile, File, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from analyzers.transcriber          import transcribe, get_duration
from analyzers.face_detector        import analyze as analyze_faces
from analyzers.eye_contact          import analyze as analyze_eyes
from analyzers.transcript_analyzer  import analyze as analyze_transcript
from analyzers.confidence_analyzer  import analyze as analyze_confidence
from analyzers.communication_score  import analyze as score_communication
from analyzers.fusion               import analyze as fuse
from analyzers.feedback_generator   import generate as generate_feedback
from realtime.ws_handler            import handle_ws

from models.schemas import (
    TranscriptAnalysisRequest,  TranscriptAnalysisResponse,
    ConfidenceAnalysisRequest,  ConfidenceAnalysisResponse,
    CommunicationScoreRequest,  CommunicationScoreResponse,
    FusionRequest,              FusionResponse,
    FeedbackRequest,            FeedbackResponse,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger("interview")

UPLOAD_DIR     = "uploads"
TRANSCRIPT_DIR = "transcripts"
FILENAME       = "interview.webm"
os.makedirs(UPLOAD_DIR,     exist_ok=True)
os.makedirs(TRANSCRIPT_DIR, exist_ok=True)

app = FastAPI(title="AI Interview Analysis API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_transcript(filename: str) -> tuple[str, str, str]:
    """Returns (video_path, txt_path, transcript_text). Raises 404 if missing."""
    video_path = os.path.join(UPLOAD_DIR, filename)
    base       = os.path.splitext(filename)[0]
    txt_path   = os.path.join(TRANSCRIPT_DIR, f"{base}.txt")
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video file not found")
    if not os.path.exists(txt_path):
        raise HTTPException(status_code=404, detail="Transcript not found — run /transcribe first")
    with open(txt_path, encoding="utf-8") as f:
        return video_path, txt_path, f.read()


def _run_pipeline(video_path: str, transcript: str, duration: float) -> dict:
    """
    Single source of truth pipeline.
    All downstream modules receive values computed HERE — nothing is recomputed.
    """
    # ── Step 1: Transcript intelligence (uses duration from transcriber) ──────
    t = analyze_transcript(transcript, duration)
    log.info("Transcript analysis: wpm=%.1f filler_rate=%.1f vocab=%.3f words=%d",
             t["speaking_rate_wpm"], t["filler_rate"],
             t["vocabulary_diversity"], t["word_count"])

    # ── Step 2: Confidence language ───────────────────────────────────────────
    c = analyze_confidence(transcript)
    log.info("Confidence analysis: score=%d level=%s confident=%d uncertain=%d",
             c["confidence_language_score"], c["confidence_level"],
             c["confident_phrases"], c["uncertain_phrases"])

    # ── Step 3: Communication score — fed DIRECTLY from t and c ──────────────
    log.info("Communication input: wpm=%.1f vocab=%.3f filler=%.1f conf=%d",
             t["speaking_rate_wpm"], t["vocabulary_diversity"],
             t["filler_rate"], c["confidence_language_score"])
    comm = score_communication(
        t["speaking_rate_wpm"],       # single source of truth
        t["vocabulary_diversity"],    # single source of truth
        t["filler_rate"],             # single source of truth
        c["confidence_language_score"],
    )
    log.info("Communication score: %d (%s)", comm["communication_score"], comm["communication_level"])

    # ── Step 4: Face + eye contact ────────────────────────────────────────────
    face = analyze_faces(video_path)
    eye  = analyze_eyes(video_path)
    log.info("Face: presence=%.1f%%  Eye: contact=%.1f%%",
             face["face_presence_percentage"], eye["eye_contact_percentage"])

    # ── Step 5: Fusion ────────────────────────────────────────────────────────
    log.info("Fusion input: face=%.1f eye=%.1f comm=%d conf=%d",
             face["face_presence_percentage"], eye["eye_contact_percentage"],
             comm["communication_score"], c["confidence_language_score"])
    fusion = fuse(
        face_presence_percentage  = face["face_presence_percentage"],
        eye_contact_percentage    = eye["eye_contact_percentage"],
        communication_score       = comm["communication_score"],
        confidence_language_score = c["confidence_language_score"],
    )
    log.info("Fusion: overall=%d engagement=%d professionalism=%d rating=%s",
             fusion["overall_score"], fusion["engagement_score"],
             fusion["professionalism_score"], fusion["rating"])

    # ── Step 6: Feedback ──────────────────────────────────────────────────────
    feedback = generate_feedback({
        "eye_contact_percentage":    eye["eye_contact_percentage"],
        "face_presence_percentage":  face["face_presence_percentage"],
        "speaking_rate_wpm":         t["speaking_rate_wpm"],
        "filler_rate":               t["filler_rate"],
        "filler_word_count":         t["filler_word_count"],
        "vocabulary_diversity":      t["vocabulary_diversity"],
        "confidence_language_score": c["confidence_language_score"],
        "communication_score":       comm["communication_score"],
        "engagement_score":          fusion["engagement_score"],
        "overall_score":             fusion["overall_score"],
    })

    return {
        "transcript_analysis":    t,
        "confidence_analysis":    c,
        "communication_analysis": comm,
        "face_analysis":          face,
        "eye_contact_analysis":   eye,
        "fusion_analysis":        fusion,
        "feedback":               feedback,
    }


def _silent_pipeline(video_path: str, duration: float) -> dict:
    """Returns a zeroed-out assessment when audio is silent."""
    log.info("Silent audio detected — returning zeroed assessment")
    zero_comm = score_communication(0, 0, 0, 50)
    face      = analyze_faces(video_path)
    eye       = analyze_eyes(video_path)
    fusion    = fuse(
        face_presence_percentage  = face["face_presence_percentage"],
        eye_contact_percentage    = eye["eye_contact_percentage"],
        communication_score       = zero_comm["communication_score"],
        confidence_language_score = 50,
    )
    feedback = generate_feedback({
        "eye_contact_percentage":    eye["eye_contact_percentage"],
        "face_presence_percentage":  face["face_presence_percentage"],
        "speaking_rate_wpm":         0,
        "filler_rate":               0,
        "filler_word_count":         0,
        "vocabulary_diversity":      0,
        "confidence_language_score": 50,
        "communication_score":       zero_comm["communication_score"],
        "engagement_score":          fusion["engagement_score"],
        "overall_score":             fusion["overall_score"],
    })
    return {
        "transcript_analysis": {
            "word_count": 0, "sentence_count": 0,
            "average_words_per_sentence": 0, "unique_word_count": 0,
            "speaking_rate_wpm": 0, "vocabulary_diversity": 0,
            "filler_word_count": 0, "filler_rate": 0, "filler_breakdown": {},
            "status": "silent_audio",
        },
        "confidence_analysis":    analyze_confidence(""),
        "communication_analysis": zero_comm,
        "face_analysis":          face,
        "eye_contact_analysis":   eye,
        "fusion_analysis":        fusion,
        "feedback":               feedback,
    }


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "project": "AI-Powered Multimodal Interview Behavioral Analysis System",
        "status":  "running",
        "version": "2.0.0",
    }


# ── Video endpoints ───────────────────────────────────────────────────────────

@app.post("/upload")
async def upload_recording(file: UploadFile = File(...)):
    filename = file.filename or FILENAME
    dest = os.path.join(UPLOAD_DIR, filename)
    with open(dest, "wb") as f:
        f.write(await file.read())
    return {"status": "saved", "filename": filename}


@app.post("/transcribe/{filename}")
def transcribe_recording(filename: str):
    video_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="File not found")
    result = transcribe(video_path, TRANSCRIPT_DIR)
    return {"filename": filename, **result}


@app.get("/transcript/{filename}")
def get_transcript(filename: str):
    base = os.path.splitext(filename)[0]
    path = os.path.join(TRANSCRIPT_DIR, f"{base}.txt")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Transcript not found")
    with open(path, encoding="utf-8") as f:
        return {"filename": filename, "transcript": f.read()}


@app.post("/analyze/face/{filename}")
def face_analysis(filename: str):
    video_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="File not found")
    return analyze_faces(video_path)


@app.post("/analyze/eye-contact/{filename}")
def eye_contact_analysis(filename: str):
    video_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="File not found")
    return analyze_eyes(video_path)


# ── Intelligence endpoints ────────────────────────────────────────────────────

@app.post("/analyze/transcript", response_model=TranscriptAnalysisResponse)
def transcript_intelligence(req: TranscriptAnalysisRequest):
    return analyze_transcript(req.transcript, req.duration_seconds)


@app.post("/analyze/transcript-intelligence/{filename}", response_model=TranscriptAnalysisResponse)
def transcript_intelligence_from_file(filename: str):
    video_path, _, transcript = _load_transcript(filename)
    duration = get_duration(video_path)
    if duration <= 0:
        raise HTTPException(status_code=422, detail="Could not determine video duration")
    return analyze_transcript(transcript, duration)


@app.post("/analyze/confidence", response_model=ConfidenceAnalysisResponse)
def confidence_analysis(req: ConfidenceAnalysisRequest):
    return analyze_confidence(req.transcript)


@app.post("/analyze/confidence-language/{filename}", response_model=ConfidenceAnalysisResponse)
def confidence_language_from_file(filename: str):
    _, _, transcript = _load_transcript(filename)
    return analyze_confidence(transcript)


@app.post("/analyze/communication", response_model=CommunicationScoreResponse)
def communication_analysis(req: CommunicationScoreRequest):
    return score_communication(
        req.speaking_rate_wpm,
        req.vocabulary_diversity,
        req.filler_rate,
        req.confidence_language_score,
    )


@app.post("/analyze/communication-score/{filename}", response_model=CommunicationScoreResponse)
def communication_score_from_file(filename: str):
    video_path, _, transcript = _load_transcript(filename)
    duration = get_duration(video_path)
    if duration <= 0:
        raise HTTPException(status_code=422, detail="Could not determine video duration")
    t = analyze_transcript(transcript, duration)
    c = analyze_confidence(transcript)
    return score_communication(
        t["speaking_rate_wpm"],
        t["vocabulary_diversity"],
        t["filler_rate"],
        c["confidence_language_score"],
    )


@app.post("/analyze/fusion", response_model=FusionResponse)
def fusion_analysis(req: FusionRequest):
    return fuse(
        req.face_presence_percentage,
        req.eye_contact_percentage,
        req.communication_score,
        req.confidence_language_score,
        req.emotion_score,
        req.voice_confidence_score,
        req.gesture_score,
    )


@app.post("/analyze/fusion/{filename}", response_model=FusionResponse)
def fusion_from_file(filename: str):
    video_path, _, transcript = _load_transcript(filename)
    duration = get_duration(video_path)
    if duration <= 0:
        raise HTTPException(status_code=422, detail="Could not determine video duration")
    t    = analyze_transcript(transcript, duration)
    c    = analyze_confidence(transcript)
    comm = score_communication(t["speaking_rate_wpm"], t["vocabulary_diversity"],
                               t["filler_rate"], c["confidence_language_score"])
    face = analyze_faces(video_path)
    eye  = analyze_eyes(video_path)
    return fuse(face["face_presence_percentage"], eye["eye_contact_percentage"],
                comm["communication_score"], c["confidence_language_score"])


@app.post("/analyze/feedback", response_model=FeedbackResponse)
def feedback_analysis(req: FeedbackRequest):
    return generate_feedback(req.model_dump())


@app.post("/analyze/feedback/{filename}", response_model=FeedbackResponse)
def feedback_from_file(filename: str):
    video_path, _, transcript = _load_transcript(filename)
    duration = get_duration(video_path)
    if duration <= 0:
        raise HTTPException(status_code=422, detail="Could not determine video duration")
    t      = analyze_transcript(transcript, duration)
    c      = analyze_confidence(transcript)
    comm   = score_communication(t["speaking_rate_wpm"], t["vocabulary_diversity"],
                                 t["filler_rate"], c["confidence_language_score"])
    face   = analyze_faces(video_path)
    eye    = analyze_eyes(video_path)
    fusion = fuse(face["face_presence_percentage"], eye["eye_contact_percentage"],
                  comm["communication_score"], c["confidence_language_score"])
    return generate_feedback({
        "eye_contact_percentage":    eye["eye_contact_percentage"],
        "face_presence_percentage":  face["face_presence_percentage"],
        "speaking_rate_wpm":         t["speaking_rate_wpm"],
        "filler_rate":               t["filler_rate"],
        "filler_word_count":         t["filler_word_count"],
        "vocabulary_diversity":      t["vocabulary_diversity"],
        "confidence_language_score": c["confidence_language_score"],
        "communication_score":       comm["communication_score"],
        "engagement_score":          fusion["engagement_score"],
        "overall_score":             fusion["overall_score"],
    })


# ── Real-Time WebSocket ───────────────────────────────────────────────

@app.websocket("/ws/realtime/{session_id}")
async def websocket_realtime(websocket: WebSocket, session_id: str):
    await handle_ws(websocket, session_id)


# ── Master Interview Assessment ───────────────────────────────────────────────

@app.post("/analyze/interview/{filename}")
def full_interview_assessment(filename: str):
    """
    Single source of truth pipeline.
    1. transcribe() is called first — its duration and word_count are authoritative.
    2. If silent, all downstream scores are zeroed consistently.
    3. analyze_transcript() receives duration from transcribe(), never re-fetches it.
    4. All downstream modules receive values from step 3 — nothing is recomputed.
    """
    video_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video file not found")

    # ── Step 1: Transcribe (authoritative source for duration + WPM) ──────────
    transcribe_result = transcribe(video_path, TRANSCRIPT_DIR)
    log.info("Transcribe result: status=%s wpm=%.1f words=%d duration=%.1fs",
             transcribe_result.get("status"), transcribe_result["speaking_rate_wpm"],
             transcribe_result["word_count"], transcribe_result["duration_seconds"])

    # ── Step 2: Silent audio short-circuit ────────────────────────────────────
    if transcribe_result.get("status") == "silent_audio":
        return _silent_pipeline(video_path, transcribe_result["duration_seconds"])

    # ── Step 3: Full pipeline using transcribe()'s duration as truth ──────────
    return _run_pipeline(
        video_path  = video_path,
        transcript  = transcribe_result["transcript"],
        duration    = transcribe_result["duration_seconds"],  # never re-fetched
    )
