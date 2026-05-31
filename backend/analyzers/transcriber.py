import os
import json
import subprocess
import numpy as np
import whisper

_model = None

# ── Whisper hallucination phrases to filter out ───────────────────────────────
_HALLUCINATION_PATTERNS = [
    "thank you for watching",
    "thanks for watching",
    "please subscribe",
    "subtitles by",
    "transcribed by",
    "www.",
    ".com",
]

def get_model() -> whisper.Whisper:
    global _model
    if _model is None:
        _model = whisper.load_model("base")
    return _model


# ── Step 2: Real duration via ffprobe ─────────────────────────────────────────
def get_duration(video_path: str) -> float:
    """Extract actual file duration using ffprobe. Never relies on Whisper segments."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        video_path,
    ]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
        info = json.loads(out)
        return round(float(info["format"]["duration"]), 2)
    except Exception:
        return 0.0


# ── Step 3: Silence detection via ffmpeg RMS energy ──────────────────────────
def is_silent(video_path: str, threshold_db: float = -40.0) -> bool:
    """
    Returns True if the mean audio energy is below threshold_db.
    Uses ffmpeg to decode audio to raw PCM, then computes RMS in dB.
    """
    cmd = [
        "ffmpeg", "-i", video_path,
        "-vn",                    # no video
        "-acodec", "pcm_s16le",   # 16-bit PCM
        "-ar", "16000",           # 16 kHz
        "-ac", "1",               # mono
        "-f", "s16le",            # raw format
        "pipe:1",
    ]
    try:
        raw = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
        if len(raw) < 2:
            return True
        audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        rms = float(np.sqrt(np.mean(audio ** 2)))
        if rms == 0:
            return True
        db = 20 * np.log10(rms)
        return db < threshold_db
    except Exception:
        return False


# ── Step 4: Hallucination filter ─────────────────────────────────────────────
def _is_hallucination(text: str) -> bool:
    lower = text.lower()
    return any(p in lower for p in _HALLUCINATION_PATTERNS)


# ── Main transcribe function ──────────────────────────────────────────────────
def transcribe(video_path: str, transcript_dir: str) -> dict:
    # Step 2: get real duration first
    duration = get_duration(video_path)

    # Step 3: silence gate — skip Whisper entirely if audio is silent
    if is_silent(video_path):
        return {
            "transcript": "",
            "word_count": 0,
            "duration_seconds": duration,
            "speaking_rate_wpm": 0,
            "status": "silent_audio",
        }

    # Step 4: transcribe with hallucination suppression
    model = get_model()
    result = model.transcribe(
        video_path,
        language="en",
        temperature=0.0,           # greedy decoding — no random sampling
        no_speech_threshold=0.6,   # skip segment if Whisper is >60% sure it's silence
        logprob_threshold=-1.0,    # discard low-confidence segments
        compression_ratio_threshold=2.4,
        condition_on_previous_text=False,  # prevents hallucination chaining
    )

    text = result["text"].strip()

    # Filter known hallucination phrases
    if _is_hallucination(text):
        text = ""

    # Step 5: correct speaking rate using real duration
    words = text.split()
    word_count = len(words)
    speaking_rate_wpm = round((word_count / duration) * 60, 1) if duration > 0 and word_count > 0 else 0

    # Confidence: average log probability across segments
    segments = result.get("segments", [])
    avg_logprob = round(
        sum(s["avg_logprob"] for s in segments) / len(segments), 3
    ) if segments else None

    # Save transcript
    os.makedirs(transcript_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(video_path))[0]
    with open(os.path.join(transcript_dir, f"{base}.txt"), "w", encoding="utf-8") as f:
        f.write(text)

    return {
        "transcript": text,
        "word_count": word_count,
        "duration_seconds": duration,
        "speaking_rate_wpm": speaking_rate_wpm,
        "avg_logprob": avg_logprob,
        "status": "ok",
    }
