import os
import json
import subprocess
import numpy as np
import whisper

_model = None

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


def get_duration(video_path: str) -> float:
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


def is_silent(video_path: str, threshold_db: float = -40.0) -> bool:
    cmd = [
        "ffmpeg", "-i", video_path,
        "-vn", "-acodec", "pcm_s16le",
        "-ar", "16000", "-ac", "1",
        "-f", "s16le", "pipe:1",
    ]
    try:
        raw = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
        if len(raw) < 2:
            return True
        audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        rms = float(np.sqrt(np.mean(audio ** 2)))
        if rms == 0:
            return True
        return (20 * np.log10(rms)) < threshold_db
    except Exception:
        return False


def _is_hallucination(text: str) -> bool:
    lower = text.lower()
    return any(p in lower for p in _HALLUCINATION_PATTERNS)


def _compute_confidence(segments: list, word_count: int, duration: float) -> tuple[int, str]:
    """
    Returns (confidence_score 0-100, transcript_quality label).

    Signals used:
      1. avg_logprob   — Whisper's per-token log probability (0 = perfect, -1.5+ = poor)
      2. no_speech_prob — probability that the segment contains no speech (0 = speech, 1 = silence)
      3. word density  — words per second; very low density on long audio = low confidence
    """
    if not segments:
        return 0, "poor"

    avg_logprob     = sum(s["avg_logprob"]    for s in segments) / len(segments)
    avg_no_speech   = sum(s["no_speech_prob"] for s in segments) / len(segments)

    # ── Signal 1: logprob → 0-100
    # Empirical range: 0.0 (perfect) to -1.5 (very poor). Clamp beyond that.
    LOGPROB_BEST  =  0.0
    LOGPROB_WORST = -1.5
    logprob_score = (avg_logprob - LOGPROB_WORST) / (LOGPROB_BEST - LOGPROB_WORST)
    logprob_score = max(0.0, min(1.0, logprob_score)) * 100

    # ── Signal 2: no_speech_prob penalty
    # High no_speech_prob means Whisper doubts speech was present → penalise
    no_speech_penalty = avg_no_speech * 40   # up to -40 pts

    # ── Signal 3: word density penalty
    # If fewer than 1 word per 3 seconds on a clip > 5 s, penalise sparseness
    density_penalty = 0.0
    if duration > 5 and word_count > 0:
        words_per_sec = word_count / duration
        if words_per_sec < 0.33:
            density_penalty = (0.33 - words_per_sec) / 0.33 * 20  # up to -20 pts

    raw_score = logprob_score - no_speech_penalty - density_penalty
    score = int(max(0, min(100, round(raw_score))))

    if score >= 85:
        quality = "excellent"
    elif score >= 65:
        quality = "good"
    elif score >= 40:
        quality = "fair"
    else:
        quality = "poor"

    return score, quality


def transcribe(video_path: str, transcript_dir: str) -> dict:
    duration = get_duration(video_path)

    if is_silent(video_path):
        return {
            "transcript":         "",
            "word_count":         0,
            "duration_seconds":   duration,
            "speaking_rate_wpm":  0,
            "confidence_score":   0,
            "transcript_quality": "poor",
            "status":             "silent_audio",
        }

    model  = get_model()
    result = model.transcribe(
        video_path,
        language="en",
        temperature=0.0,
        no_speech_threshold=0.6,
        logprob_threshold=-1.0,
        compression_ratio_threshold=2.4,
        condition_on_previous_text=False,
    )

    text = result["text"].strip()
    if _is_hallucination(text):
        text = ""

    words             = text.split()
    word_count        = len(words)
    speaking_rate_wpm = round((word_count / duration) * 60, 1) if duration > 0 and word_count > 0 else 0

    segments                    = result.get("segments", [])
    confidence_score, quality   = _compute_confidence(segments, word_count, duration)

    os.makedirs(transcript_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(video_path))[0]
    with open(os.path.join(transcript_dir, f"{base}.txt"), "w", encoding="utf-8") as f:
        f.write(text)

    return {
        "transcript":         text,
        "word_count":         word_count,
        "duration_seconds":   duration,
        "speaking_rate_wpm":  speaking_rate_wpm,
        "confidence_score":   confidence_score,
        "transcript_quality": quality,
        "status":             "ok",
    }
