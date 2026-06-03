import os
import logging
from fastapi import FastAPI, UploadFile, File, HTTPException, WebSocket
from fastapi.responses import Response, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from analyzers.transcriber              import transcribe, get_duration
from analyzers.face_detector            import analyze as analyze_faces
from analyzers.eye_contact              import analyze as analyze_eyes
from analyzers.transcript_analyzer     import analyze as analyze_transcript
from analyzers.confidence_analyzer     import analyze as analyze_confidence
from analyzers.communication_score     import analyze as score_communication
from analyzers.fusion                  import analyze as fuse
from analyzers.feedback_generator      import generate as generate_feedback
from analyzers.voice_analyzer          import analyze as analyze_voice
from analyzers.behavioral.engine       import analyze as analyze_behavior
from analyzers.interview_coach         import generate_report as generate_coaching
from analyzers.benchmark               import benchmark
from history.store                     import save_session, load_session, list_sessions, compare_sessions, new_session_id
from reporting.pdf_generator           import generate_pdf
from reporting.routes                  import router as report_router
from realtime.ws_handler               import handle_ws

from models.schemas import (
    TranscriptAnalysisRequest,   TranscriptAnalysisResponse,
    ConfidenceAnalysisRequest,   ConfidenceAnalysisResponse,
    CommunicationScoreRequest,   CommunicationScoreResponse,
    FusionRequest,               FusionResponse,
    FeedbackRequest,             FeedbackResponse,
    VoiceAnalysisResponse,       BehavioralAnalysisResponse,
    CoachingReportResponse,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger("interview")

UPLOAD_DIR     = "uploads"
TRANSCRIPT_DIR = "transcripts"
FILENAME       = "interview.webm"
os.makedirs(UPLOAD_DIR,     exist_ok=True)
os.makedirs(TRANSCRIPT_DIR, exist_ok=True)

app = FastAPI(title="AI Interview Analysis API", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(report_router)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_transcript(filename: str) -> tuple[str, str, str]:
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
    # Step 1: Transcript intelligence
    t = analyze_transcript(transcript, duration)
    log.info("Transcript: wpm=%.1f filler=%.1f vocab=%.3f words=%d",
             t["speaking_rate_wpm"], t["filler_rate"], t["vocabulary_diversity"], t["word_count"])

    # Step 2: Confidence language
    c = analyze_confidence(transcript)
    log.info("Confidence: score=%d level=%s", c["confidence_language_score"], c["confidence_level"])

    # Step 3: Communication score
    comm = score_communication(
        t["speaking_rate_wpm"], t["vocabulary_diversity"],
        t["filler_rate"], c["confidence_language_score"],
    )
    log.info("Communication: score=%d level=%s", comm["communication_score"], comm["communication_level"])

    # Step 4: Voice intelligence
    voice = analyze_voice(
        video_path=video_path, transcript=transcript,
        speech_rate_wpm=t["speaking_rate_wpm"],
    )
    log.info("Voice: confidence=%d clarity=%d fluency=%d pauses=%d",
             voice["voice_confidence_score"], voice["clarity_score"],
             voice["fluency_score"], voice["pause_count"])

    # Step 5: Face + eye contact
    face = analyze_faces(video_path)
    eye  = analyze_eyes(video_path)
    log.info("Face: %.1f%%  Eye: %.1f%%",
             face["face_presence_percentage"], eye["eye_contact_percentage"])

    # Step 6: Behavioral intelligence
    behavior = analyze_behavior(video_path)
    log.info("Behavioral: attention=%d posture=%d presence=%d restlessness=%d",
             behavior["attention_score"], behavior["posture_score"],
             behavior["professional_presence_score"], behavior["restlessness_score"])

    # Step 7: Fusion
    fusion = fuse(
        face_presence_percentage    = face["face_presence_percentage"],
        eye_contact_percentage      = eye["eye_contact_percentage"],
        communication_score         = comm["communication_score"],
        confidence_language_score   = c["confidence_language_score"],
        voice_confidence_score      = voice["voice_confidence_score"],
        speech_clarity_score        = voice["clarity_score"],
        fluency_score               = voice["fluency_score"],
        attention_score             = behavior["attention_score"],
        posture_score               = behavior["posture_score"],
        professional_presence_score = behavior["professional_presence_score"],
    )
    log.info("Fusion: overall=%d engagement=%d professionalism=%d mastery=%d rating=%s",
             fusion["overall_score"], fusion["engagement_score"],
             fusion["professionalism_score"], fusion["communication_mastery_score"], fusion["rating"])

    # Step 8: Feedback
    feedback = generate_feedback({
        "eye_contact_percentage":      eye["eye_contact_percentage"],
        "face_presence_percentage":    face["face_presence_percentage"],
        "speaking_rate_wpm":           t["speaking_rate_wpm"],
        "filler_rate":                 t["filler_rate"],
        "filler_word_count":           t["filler_word_count"],
        "vocabulary_diversity":        t["vocabulary_diversity"],
        "confidence_language_score":   c["confidence_language_score"],
        "communication_score":         comm["communication_score"],
        "engagement_score":            fusion["engagement_score"],
        "overall_score":               fusion["overall_score"],
        "voice_confidence_score":      voice["voice_confidence_score"],
        "speech_clarity_score":        voice["clarity_score"],
        "fluency_score":               voice["fluency_score"],
        "hesitation_rate":             voice["hesitation_rate"],
        "pause_count":                 voice["pause_count"],
        "attention_score":             behavior["attention_score"],
        "posture_score":               behavior["posture_score"],
        "professional_presence_score": behavior["professional_presence_score"],
    })

    return {
        "transcript_analysis":    t,
        "confidence_analysis":    c,
        "communication_analysis": comm,
        "voice_analysis":         voice,
        "behavioral_analysis":    behavior,
        "face_analysis":          face,
        "eye_contact_analysis":   eye,
        "fusion_analysis":        fusion,
        "feedback":               feedback,
    }


def _silent_pipeline(video_path: str, duration: float) -> dict:
    log.info("Silent audio — returning zeroed assessment")
    from analyzers.voice_analyzer import _silent_result as voice_silent
    zero_comm = score_communication(0, 0, 0, 50)
    voice     = voice_silent()
    face      = analyze_faces(video_path)
    eye       = analyze_eyes(video_path)
    behavior  = analyze_behavior(video_path)
    fusion    = fuse(
        face_presence_percentage    = face["face_presence_percentage"],
        eye_contact_percentage      = eye["eye_contact_percentage"],
        communication_score         = zero_comm["communication_score"],
        confidence_language_score   = 50,
        voice_confidence_score      = 0,
        speech_clarity_score        = 0,
        fluency_score               = 0,
        attention_score             = behavior["attention_score"],
        posture_score               = behavior["posture_score"],
        professional_presence_score = behavior["professional_presence_score"],
    )
    feedback = generate_feedback({
        "eye_contact_percentage":      eye["eye_contact_percentage"],
        "face_presence_percentage":    face["face_presence_percentage"],
        "speaking_rate_wpm":           0,
        "filler_rate":                 0,
        "filler_word_count":           0,
        "vocabulary_diversity":        0,
        "confidence_language_score":   50,
        "communication_score":         zero_comm["communication_score"],
        "engagement_score":            fusion["engagement_score"],
        "overall_score":               fusion["overall_score"],
        "voice_confidence_score":      0,
        "speech_clarity_score":        0,
        "fluency_score":               0,
        "hesitation_rate":             0,
        "pause_count":                 0,
        "attention_score":             behavior["attention_score"],
        "posture_score":               behavior["posture_score"],
        "professional_presence_score": behavior["professional_presence_score"],
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
        "voice_analysis":         voice,
        "behavioral_analysis":    behavior,
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
        "version": "3.0.0",
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
        req.speaking_rate_wpm, req.vocabulary_diversity,
        req.filler_rate, req.confidence_language_score,
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
        t["speaking_rate_wpm"], t["vocabulary_diversity"],
        t["filler_rate"], c["confidence_language_score"],
    )


@app.post("/analyze/voice/{filename}", response_model=VoiceAnalysisResponse)
def voice_analysis_endpoint(filename: str):
    video_path, _, transcript = _load_transcript(filename)
    duration = get_duration(video_path)
    t = analyze_transcript(transcript, duration) if duration > 0 else {"speaking_rate_wpm": 0}
    return analyze_voice(
        video_path=video_path, transcript=transcript,
        speech_rate_wpm=t["speaking_rate_wpm"],
    )


@app.post("/analyze/behavioral/{filename}", response_model=BehavioralAnalysisResponse)
def behavioral_analysis_endpoint(filename: str):
    video_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video file not found")
    return analyze_behavior(video_path)


@app.post("/analyze/fusion", response_model=FusionResponse)
def fusion_analysis(req: FusionRequest):
    return fuse(
        face_presence_percentage    = req.face_presence_percentage,
        eye_contact_percentage      = req.eye_contact_percentage,
        communication_score         = req.communication_score,
        confidence_language_score   = req.confidence_language_score,
        voice_confidence_score      = req.voice_confidence_score,
        speech_clarity_score        = req.speech_clarity_score,
        fluency_score               = req.fluency_score,
        attention_score             = req.attention_score,
        posture_score               = req.posture_score,
        professional_presence_score = req.professional_presence_score,
        emotion_score               = req.emotion_score,
        gesture_score               = req.gesture_score,
    )


@app.post("/analyze/fusion/{filename}", response_model=FusionResponse)
def fusion_from_file(filename: str):
    video_path, _, transcript = _load_transcript(filename)
    duration = get_duration(video_path)
    if duration <= 0:
        raise HTTPException(status_code=422, detail="Could not determine video duration")
    t        = analyze_transcript(transcript, duration)
    c        = analyze_confidence(transcript)
    comm     = score_communication(t["speaking_rate_wpm"], t["vocabulary_diversity"],
                                   t["filler_rate"], c["confidence_language_score"])
    voice    = analyze_voice(video_path, transcript, t["speaking_rate_wpm"])
    face     = analyze_faces(video_path)
    eye      = analyze_eyes(video_path)
    behavior = analyze_behavior(video_path)
    return fuse(
        face_presence_percentage    = face["face_presence_percentage"],
        eye_contact_percentage      = eye["eye_contact_percentage"],
        communication_score         = comm["communication_score"],
        confidence_language_score   = c["confidence_language_score"],
        voice_confidence_score      = voice["voice_confidence_score"],
        speech_clarity_score        = voice["clarity_score"],
        fluency_score               = voice["fluency_score"],
        attention_score             = behavior["attention_score"],
        posture_score               = behavior["posture_score"],
        professional_presence_score = behavior["professional_presence_score"],
    )


@app.post("/analyze/feedback", response_model=FeedbackResponse)
def feedback_analysis(req: FeedbackRequest):
    return generate_feedback(req.model_dump())


@app.post("/analyze/feedback/{filename}", response_model=FeedbackResponse)
def feedback_from_file(filename: str):
    video_path, _, transcript = _load_transcript(filename)
    duration = get_duration(video_path)
    if duration <= 0:
        raise HTTPException(status_code=422, detail="Could not determine video duration")
    t        = analyze_transcript(transcript, duration)
    c        = analyze_confidence(transcript)
    comm     = score_communication(t["speaking_rate_wpm"], t["vocabulary_diversity"],
                                   t["filler_rate"], c["confidence_language_score"])
    voice    = analyze_voice(video_path, transcript, t["speaking_rate_wpm"])
    face     = analyze_faces(video_path)
    eye      = analyze_eyes(video_path)
    behavior = analyze_behavior(video_path)
    fusion   = fuse(
        face_presence_percentage    = face["face_presence_percentage"],
        eye_contact_percentage      = eye["eye_contact_percentage"],
        communication_score         = comm["communication_score"],
        confidence_language_score   = c["confidence_language_score"],
        voice_confidence_score      = voice["voice_confidence_score"],
        speech_clarity_score        = voice["clarity_score"],
        fluency_score               = voice["fluency_score"],
        attention_score             = behavior["attention_score"],
        posture_score               = behavior["posture_score"],
        professional_presence_score = behavior["professional_presence_score"],
    )
    return generate_feedback({
        "eye_contact_percentage":      eye["eye_contact_percentage"],
        "face_presence_percentage":    face["face_presence_percentage"],
        "speaking_rate_wpm":           t["speaking_rate_wpm"],
        "filler_rate":                 t["filler_rate"],
        "filler_word_count":           t["filler_word_count"],
        "vocabulary_diversity":        t["vocabulary_diversity"],
        "confidence_language_score":   c["confidence_language_score"],
        "communication_score":         comm["communication_score"],
        "engagement_score":            fusion["engagement_score"],
        "overall_score":               fusion["overall_score"],
        "voice_confidence_score":      voice["voice_confidence_score"],
        "speech_clarity_score":        voice["clarity_score"],
        "fluency_score":               voice["fluency_score"],
        "hesitation_rate":             voice["hesitation_rate"],
        "pause_count":                 voice["pause_count"],
        "attention_score":             behavior["attention_score"],
        "posture_score":               behavior["posture_score"],
        "professional_presence_score": behavior["professional_presence_score"],
    })


# ── Real-Time Assessment (uses Whisper transcript + vision metrics) ─────────────

class RealtimeAssessmentRequest(BaseModel):
    transcript:             str
    duration_seconds:       float
    eye_contact_percentage: float
    face_presence_percentage: float
    role:                   str = "software_engineer"


@app.post("/analyze/realtime-assessment")
def realtime_assessment(req: RealtimeAssessmentRequest):
    """Run full scoring pipeline on a realtime session using the Whisper transcript."""
    transcript = req.transcript.strip()
    duration   = max(req.duration_seconds, 1.0)

    if not transcript:
        raise HTTPException(status_code=422, detail="Empty transcript")

    t        = analyze_transcript(transcript, duration)
    c        = analyze_confidence(transcript)
    comm     = score_communication(
        t["speaking_rate_wpm"], t["vocabulary_diversity"],
        t["filler_rate"],       c["confidence_language_score"],
    )
    fusion   = fuse(
        face_presence_percentage  = req.face_presence_percentage,
        eye_contact_percentage    = req.eye_contact_percentage,
        communication_score       = comm["communication_score"],
        confidence_language_score = c["confidence_language_score"],
    )
    feedback = generate_feedback({
        "eye_contact_percentage":    req.eye_contact_percentage,
        "face_presence_percentage":  req.face_presence_percentage,
        "speaking_rate_wpm":         t["speaking_rate_wpm"],
        "filler_rate":               t["filler_rate"],
        "filler_word_count":         t["filler_word_count"],
        "vocabulary_diversity":      t["vocabulary_diversity"],
        "confidence_language_score": c["confidence_language_score"],
        "communication_score":       comm["communication_score"],
        "engagement_score":          fusion["engagement_score"],
        "overall_score":             fusion["overall_score"],
        "voice_confidence_score":    None,
        "speech_clarity_score":      None,
        "fluency_score":             None,
        "hesitation_rate":           0,
        "pause_count":               0,
        "attention_score":           req.eye_contact_percentage,
        "posture_score":             None,
        "professional_presence_score": None,
    })

    return {
        "transcript_analysis":    t,
        "confidence_analysis":    c,
        "communication_analysis": comm,
        "face_analysis":          {"face_presence_percentage": req.face_presence_percentage, "face_detected": req.face_presence_percentage > 0},
        "eye_contact_analysis":   {"eye_contact_percentage": req.eye_contact_percentage, "gaze_stability": "good"},
        "fusion_analysis":        fusion,
        "feedback":               feedback,
    }


# ── Real-Time WebSocket ───────────────────────────────────────────────────────

@app.websocket("/ws/realtime/{session_id}")
async def websocket_realtime(websocket: WebSocket, session_id: str):
    await handle_ws(websocket, session_id)


@app.post("/analyze/coach/{filename}", response_model=CoachingReportResponse)
def coaching_report(filename: str, role: str = "software_engineer"):
    """Generate a full AI coaching report. Pass ?role=ai_ml_engineer etc."""
    video_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video file not found")

    transcribe_result = transcribe(video_path, TRANSCRIPT_DIR)
    if transcribe_result.get("status") == "silent_audio":
        raise HTTPException(status_code=422, detail="No speech detected in recording")

    transcript = transcribe_result["transcript"]
    duration   = transcribe_result["duration_seconds"]

    t        = analyze_transcript(transcript, duration)
    c        = analyze_confidence(transcript)
    comm     = score_communication(t["speaking_rate_wpm"], t["vocabulary_diversity"],
                                   t["filler_rate"], c["confidence_language_score"])
    voice    = analyze_voice(video_path, transcript, t["speaking_rate_wpm"])
    face     = analyze_faces(video_path)
    eye      = analyze_eyes(video_path)
    behavior = analyze_behavior(video_path)
    fusion   = fuse(
        face_presence_percentage    = face["face_presence_percentage"],
        eye_contact_percentage      = eye["eye_contact_percentage"],
        communication_score         = comm["communication_score"],
        confidence_language_score   = c["confidence_language_score"],
        voice_confidence_score      = voice["voice_confidence_score"],
        speech_clarity_score        = voice["clarity_score"],
        fluency_score               = voice["fluency_score"],
        attention_score             = behavior["attention_score"],
        posture_score               = behavior["posture_score"],
        professional_presence_score = behavior["professional_presence_score"],
    )

    merged = {
        **t, **c, **comm, **voice, **face, **eye, **behavior, **fusion,
        "eye_contact_percentage":      eye["eye_contact_percentage"],
        "face_presence_percentage":    face["face_presence_percentage"],
        "communication_score":         comm["communication_score"],
        "voice_confidence_score":      voice["voice_confidence_score"],
        "professional_presence_score": behavior["professional_presence_score"],
    }
    return generate_coaching(merged, role=role)


# ── Master Interview Assessment ───────────────────────────────────────────────

@app.post("/analyze/interview/{filename}")
def full_interview_assessment(filename: str):
    video_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video file not found")

    transcribe_result = transcribe(video_path, TRANSCRIPT_DIR)
    log.info("Transcribe: status=%s wpm=%.1f words=%d duration=%.1fs",
             transcribe_result.get("status"), transcribe_result["speaking_rate_wpm"],
             transcribe_result["word_count"], transcribe_result["duration_seconds"])

    if transcribe_result.get("status") == "silent_audio":
        return _silent_pipeline(video_path, transcribe_result["duration_seconds"])

    return _run_pipeline(
        video_path = video_path,
        transcript = transcribe_result["transcript"],
        duration   = transcribe_result["duration_seconds"],
    )
