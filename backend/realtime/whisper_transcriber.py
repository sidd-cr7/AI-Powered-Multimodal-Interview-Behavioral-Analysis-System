"""
Faster-Whisper transcriber for realtime session audio.

Receives raw audio bytes (webm/opus chunks from MediaRecorder),
concatenates them, runs Faster-Whisper at session end, and returns
a high-quality transcript with confidence scores.
"""

import io
import logging
import subprocess
import tempfile
import os
import numpy as np
from faster_whisper import WhisperModel

log = logging.getLogger("whisper_rt")

# Load once at import time — "base" is fast enough for interview sessions
# Use "small" for better accuracy if CPU allows
_model: WhisperModel | None = None

WHISPER_MODEL_SIZE = "base"
INTERVIEW_PROMPT   = (
    "This is a job interview. The candidate is answering behavioral and "
    "technical questions about their experience and skills."
)

_HALLUCINATIONS = [
    "thank you for watching", "thanks for watching", "please subscribe",
    "subtitles by", "transcribed by", "www.", ".com",
]


def _get_model() -> WhisperModel:
    global _model
    if _model is None:
        log.info("[Whisper] Loading %s model…", WHISPER_MODEL_SIZE)
        _model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
        log.info("[Whisper] Model ready")
    return _model


def _webm_chunks_to_pcm(chunks: list[bytes]) -> np.ndarray | None:
    """
    Concatenate webm/opus chunks and decode to 16kHz mono PCM via ffmpeg.
    Returns float32 numpy array or None on failure.
    """
    raw = b"".join(chunks)
    if len(raw) < 1024:
        return None

    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
        f.write(raw)
        tmp_in = f.name

    try:
        cmd = [
            "ffmpeg", "-y", "-i", tmp_in,
            "-vn",                    # drop video
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            "-f", "s16le", "pipe:1",
        ]
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
        if len(out) < 2:
            return None
        return np.frombuffer(out, dtype=np.int16).astype(np.float32) / 32768.0
    except Exception as e:
        log.warning("[Whisper] ffmpeg decode failed: %s", e)
        return None
    finally:
        os.unlink(tmp_in)


def transcribe_session(chunks: list[bytes]) -> dict:
    """
    Run Faster-Whisper on the full session audio.
    Returns dict with transcript, word_count, confidence_score, quality.
    """
    if not chunks:
        return _empty()

    audio = _webm_chunks_to_pcm(chunks)
    if audio is None or len(audio) < 16000 * 0.5:  # < 0.5 seconds
        return _empty()

    model = _get_model()

    try:
        segments_gen, info = model.transcribe(
            audio,
            language="en",
            initial_prompt=INTERVIEW_PROMPT,
            beam_size=5,
            best_of=5,
            temperature=0.0,
            condition_on_previous_text=True,
            vad_filter=True,              # built-in Silero VAD — skips silence
            vad_parameters={"min_silence_duration_ms": 500},
            word_timestamps=False,
            no_speech_threshold=0.6,
            log_prob_threshold=-1.0,
            compression_ratio_threshold=2.4,
        )

        segments     = list(segments_gen)
        text_parts   = []
        logprobs     = []

        for seg in segments:
            t = seg.text.strip()
            if not t:
                continue
            if any(h in t.lower() for h in _HALLUCINATIONS):
                continue
            if seg.no_speech_prob > 0.8:
                continue
            text_parts.append(t)
            logprobs.append(seg.avg_logprob)

        transcript = " ".join(text_parts).strip()
        words      = transcript.split()
        duration   = info.duration or 1.0

        confidence, quality = _score(logprobs, len(words), duration)

        log.info("[Whisper] Done — %d words, quality=%s conf=%d",
                 len(words), quality, confidence)

        return {
            "transcript":         transcript,
            "word_count":         len(words),
            "duration_seconds":   round(duration, 1),
            "speaking_rate_wpm":  round(len(words) / (duration / 60), 1) if duration > 0 else 0,
            "confidence_score":   confidence,
            "transcript_quality": quality,
            "source":             "faster-whisper",
        }

    except Exception as e:
        log.error("[Whisper] Transcription failed: %s", e)
        return _empty()


def _score(logprobs: list[float], word_count: int, duration: float) -> tuple[int, str]:
    if not logprobs:
        return 0, "poor"

    avg_lp = sum(logprobs) / len(logprobs)
    score  = (avg_lp - (-1.5)) / (0.0 - (-1.5))  # map [-1.5, 0] → [0, 1]
    score  = int(max(0, min(100, round(score * 100))))

    # Penalise very sparse speech
    if duration > 5 and word_count > 0:
        wps = word_count / duration
        if wps < 0.33:
            score = max(0, score - 15)

    quality = (
        "excellent" if score >= 85 else
        "good"      if score >= 65 else
        "fair"      if score >= 40 else
        "poor"
    )
    return score, quality


def _empty() -> dict:
    return {
        "transcript":         "",
        "word_count":         0,
        "duration_seconds":   0.0,
        "speaking_rate_wpm":  0,
        "confidence_score":   0,
        "transcript_quality": "poor",
        "source":             "faster-whisper",
    }
