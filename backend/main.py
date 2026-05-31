import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# ── Existing analyzers ────────────────────────────────────────────────────────
from analyzers.transcriber       import transcribe
from analyzers.face_detector     import analyze as analyze_faces
from analyzers.eye_contact       import analyze as analyze_eyes

# ── New intelligence analyzers ────────────────────────────────────────────────
from analyzers.transcript_analyzer  import analyze as analyze_transcript
from analyzers.confidence_analyzer  import analyze as analyze_confidence
from analyzers.communication_score  import analyze as score_communication
from analyzers.fusion               import analyze as fuse
from analyzers.feedback_generator   import generate as generate_feedback

# ── Pydantic schemas ──────────────────────────────────────────────────────────
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


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {
        "project": "AI-Powered Multimodal Interview Behavioral Analysis System",
        "status":  "running",
        "version": "2.0.0",
    }


# ══════════════════════════════════════════════════════════════════════════════
# VIDEO ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

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


# ══════════════════════════════════════════════════════════════════════════════
# INTELLIGENCE ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/analyze/transcript", response_model=TranscriptAnalysisResponse)
def transcript_intelligence(req: TranscriptAnalysisRequest):
    return analyze_transcript(req.transcript, req.duration_seconds)


@app.post("/analyze/confidence", response_model=ConfidenceAnalysisResponse)
def confidence_analysis(req: ConfidenceAnalysisRequest):
    return analyze_confidence(req.transcript)


@app.post("/analyze/communication", response_model=CommunicationScoreResponse)
def communication_analysis(req: CommunicationScoreRequest):
    return score_communication(
        req.speaking_rate_wpm,
        req.filler_rate,
        req.confidence_language_score,
    )


@app.post("/analyze/fusion", response_model=FusionResponse)
def fusion_analysis(req: FusionRequest):
    return fuse(
        req.face_presence_percentage,
        req.eye_contact_percentage,
        req.communication_score,
        req.confidence_language_score,
    )


@app.post("/analyze/feedback", response_model=FeedbackResponse)
def feedback_analysis(req: FeedbackRequest):
    return generate_feedback(req.model_dump())
