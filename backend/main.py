import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from analyzers.transcriber import transcribe
from analyzers.face_detector import analyze as analyze_faces
from analyzers.eye_contact import analyze as analyze_eyes

UPLOAD_DIR = "uploads"
TRANSCRIPT_DIR = "transcripts"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(TRANSCRIPT_DIR, exist_ok=True)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "project": "AI-Powered Multimodal Interview Behavioral Analysis System",
        "status": "running",
    }


# ── Step 1: Upload ────────────────────────────────────────────────────────────
@app.post("/upload")
async def upload_recording(file: UploadFile = File(...)):
    dest = os.path.join(UPLOAD_DIR, file.filename)
    with open(dest, "wb") as f:
        f.write(await file.read())
    return {"status": "saved", "filename": file.filename}


# ── Step 2: Transcribe ────────────────────────────────────────────────────────
@app.post("/transcribe/{filename}")
def transcribe_recording(filename: str):
    video_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="File not found")
    result = transcribe(video_path, TRANSCRIPT_DIR)
    return {"filename": filename, **result}


# ── Step 3: Get saved transcript ──────────────────────────────────────────────
@app.get("/transcript/{filename}")
def get_transcript(filename: str):
    base = os.path.splitext(filename)[0]
    path = os.path.join(TRANSCRIPT_DIR, f"{base}.txt")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Transcript not found")
    with open(path, encoding="utf-8") as f:
        return {"filename": filename, "transcript": f.read()}


# ── Step 4: Face detection ────────────────────────────────────────────────────
@app.post("/analyze/face/{filename}")
def face_analysis(filename: str):
    video_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="File not found")
    return analyze_faces(video_path)


# ── Step 5: Eye contact ───────────────────────────────────────────────────────
@app.post("/analyze/eye-contact/{filename}")
def eye_contact_analysis(filename: str):
    video_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="File not found")
    return analyze_eyes(video_path)
