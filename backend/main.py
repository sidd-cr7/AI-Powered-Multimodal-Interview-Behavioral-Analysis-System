import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from analyzers.transcriber          import transcribe
from analyzers.face_detector        import analyze as analyze_faces
from analyzers.eye_contact          import analyze as analyze_eyes
from analyzers.transcript_analyzer  import analyze as analyze_transcript
from analyzers.confidence_analyzer  import analyze as analyze_confidence
from analyzers.communication_score  import analyze as score_communication
from analyzers.fusion               import analyze as fuse
from analyzers.feedback_generator   import generate as generate_feedback

from models.schemas import (
    TranscriptAnalysisRequest,  TranscriptAnalysisResponse,
    ConfidenceAnalysisRequest,  ConfidenceAnalysisResponse,
    CommunicationScoreRequest,  CommunicationScoreResponse,
    FusionRequest,              FusionResponse,
    FeedbackRequest,            FeedbackResponse,
)

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
    """Reads the saved transcript and video duration — no request body needed."""
    base         = os.path.splitext(filename)[0]
    txt_path     = os.path.join(TRANSCRIPT_DIR, f"{base}.txt")
    video_path   = os.path.join(UPLOAD_DIR, filename)

    if not os.path.exists(txt_path):
        raise HTTPException(status_code=404, detail="Transcript not found — run /transcribe first")
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video file not found")

    with open(txt_path, encoding="utf-8") as f:
        transcript = f.read()

    from analyzers.transcriber import get_duration
    duration = get_duration(video_path)
    if duration <= 0:
        raise HTTPException(status_code=422, detail="Could not determine video duration")

    return analyze_transcript(transcript, duration)


@app.post("/analyze/confidence", response_model=ConfidenceAnalysisResponse)
def confidence_analysis(req: ConfidenceAnalysisRequest):
    return analyze_confidence(req.transcript)


@app.post("/analyze/confidence-language/{filename}", response_model=ConfidenceAnalysisResponse)
def confidence_language_from_file(filename: str):
    """Reads saved transcript automatically — no request body needed."""
    base     = os.path.splitext(filename)[0]
    txt_path = os.path.join(TRANSCRIPT_DIR, f"{base}.txt")
    if not os.path.exists(txt_path):
        raise HTTPException(status_code=404, detail="Transcript not found — run /transcribe first")
    with open(txt_path, encoding="utf-8") as f:
        transcript = f.read()
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
    """Runs full pipeline: reads saved transcript → transcript intelligence
    → confidence analysis → communication score. No request body needed."""
    base       = os.path.splitext(filename)[0]
    txt_path   = os.path.join(TRANSCRIPT_DIR, f"{base}.txt")
    video_path = os.path.join(UPLOAD_DIR, filename)

    if not os.path.exists(txt_path):
        raise HTTPException(status_code=404, detail="Transcript not found — run /transcribe first")
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video file not found")

    with open(txt_path, encoding="utf-8") as f:
        transcript = f.read()

    from analyzers.transcriber import get_duration
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
    """Full auto-pipeline: runs every analyzer on the saved video and transcript,
    then fuses all signals into a final assessment. No request body needed."""
    video_path = os.path.join(UPLOAD_DIR, filename)
    base       = os.path.splitext(filename)[0]
    txt_path   = os.path.join(TRANSCRIPT_DIR, f"{base}.txt")

    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video file not found")
    if not os.path.exists(txt_path):
        raise HTTPException(status_code=404, detail="Transcript not found — run /transcribe first")

    with open(txt_path, encoding="utf-8") as f:
        transcript = f.read()

    from analyzers.transcriber import get_duration
    duration = get_duration(video_path)
    if duration <= 0:
        raise HTTPException(status_code=422, detail="Could not determine video duration")

    face  = analyze_faces(video_path)
    eye   = analyze_eyes(video_path)
    t     = analyze_transcript(transcript, duration)
    c     = analyze_confidence(transcript)
    comm  = score_communication(
        t["speaking_rate_wpm"],
        t["vocabulary_diversity"],
        t["filler_rate"],
        c["confidence_language_score"],
    )

    return fuse(
        face_presence_percentage  = face["face_presence_percentage"],
        eye_contact_percentage    = eye["eye_contact_percentage"],
        communication_score       = comm["communication_score"],
        confidence_language_score = c["confidence_language_score"],
    )


@app.post("/analyze/feedback", response_model=FeedbackResponse)
def feedback_analysis(req: FeedbackRequest):
    return generate_feedback(req.model_dump())


@app.post("/analyze/feedback/{filename}", response_model=FeedbackResponse)
def feedback_from_file(filename: str):
    """Full auto-pipeline: runs every analyzer, fuses results, then generates
    coaching feedback. No request body needed."""
    video_path = os.path.join(UPLOAD_DIR, filename)
    base       = os.path.splitext(filename)[0]
    txt_path   = os.path.join(TRANSCRIPT_DIR, f"{base}.txt")

    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video file not found")
    if not os.path.exists(txt_path):
        raise HTTPException(status_code=404, detail="Transcript not found — run /transcribe first")

    with open(txt_path, encoding="utf-8") as f:
        transcript = f.read()

    from analyzers.transcriber import get_duration
    duration = get_duration(video_path)
    if duration <= 0:
        raise HTTPException(status_code=422, detail="Could not determine video duration")

    face  = analyze_faces(video_path)
    eye   = analyze_eyes(video_path)
    t     = analyze_transcript(transcript, duration)
    c     = analyze_confidence(transcript)
    comm  = score_communication(
        t["speaking_rate_wpm"],
        t["vocabulary_diversity"],
        t["filler_rate"],
        c["confidence_language_score"],
    )
    fusion = fuse(
        face_presence_percentage  = face["face_presence_percentage"],
        eye_contact_percentage    = eye["eye_contact_percentage"],
        communication_score       = comm["communication_score"],
        confidence_language_score = c["confidence_language_score"],
    )

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
